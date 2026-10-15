"""Disposable loopback HTTPS acceptance. No trust-store changes or real accounts.

Uses Uvicorn TLS as a test terminator; does not certify a deployed reverse proxy.
"""
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from http.cookiejar import CookieJar
from ipaddress import ip_address
import json
import os
from pathlib import Path
import socket
import ssl
import subprocess
import sys
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.request import build_opener, HTTPSHandler, HTTPCookieProcessor, ProxyHandler, Request

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from scripts.drill_support import isolated_environment


def certificate(folder):
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'Nodum disposable TLS fixture')])
    now = datetime.now(timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name)
            .public_key(key.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(now-timedelta(minutes=1)).not_valid_after(now+timedelta(hours=1))
            .add_extension(x509.SubjectAlternativeName([x509.IPAddress(ip_address('127.0.0.1'))]), critical=False)
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
            .sign(key, hashes.SHA256()))
    certfile, keyfile = folder/'certificate.pem', folder/'private.key'
    certfile.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    keyfile.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                        serialization.NoEncryption()))
    keyfile.chmod(0o600)
    return certfile, keyfile


@contextmanager
def running_fixture():
    with tempfile.TemporaryDirectory(prefix='nodum-tls-') as directory:
        folder = Path(directory)
        cert, key = certificate(folder)
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        base = f'https://127.0.0.1:{port}'
        env = isolated_environment()
        env.update(DATABASE_URL='sqlite:///'+str(folder/'synthetic.db'), AUTH_PUBLIC_ORIGIN=base)
        seed = ('from app.sqlite_repository import SQLiteRepository; from demo_product import seed_demo; '
                'from datetime import datetime,timezone; r=SQLiteRepository(); r.initialize(seed_demo=False); '
                'seed_demo(r,datetime.now(timezone.utc))')
        subprocess.run([sys.executable, '-c', seed], cwd=ROOT/'backend', env=env,
                       check=True, capture_output=True, timeout=30)
        server = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1',
                                   '--port', str(port), '--ssl-certfile', str(cert), '--ssl-keyfile', str(key),
                                   '--no-access-log', '--no-proxy-headers'], cwd=ROOT/'backend', env=env,
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        trusted = ssl.create_default_context(cafile=str(cert))
        opener = build_opener(ProxyHandler({}), HTTPSHandler(context=trusted))
        try:
            for _ in range(100):
                if server.poll() is not None:
                    raise RuntimeError('TLS fixture exited before startup')
                try:
                    with opener.open(base+'/health', timeout=1) as response:
                        if response.status == 200:
                            break
                except URLError:
                    time.sleep(.1)
            else:
                raise RuntimeError('TLS fixture startup deadline exceeded')
            yield base, trusted
        finally:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill(); server.wait(timeout=5)


def run():
    with running_fixture() as (base, trusted):
        jar = CookieJar()
        client = build_opener(ProxyHandler({}), HTTPSHandler(context=trusted), HTTPCookieProcessor(jar))
        def request(path, payload=None, *, csrf=None, origin=None, expected=200):
            headers = {}
            if payload is not None:
                headers.update({'Content-Type':'application/json', 'Origin':origin or base})
            if csrf:
                headers['X-CSRF-Token'] = csrf
            req = Request(base+path, data=None if payload is None else json.dumps(payload).encode(), headers=headers)
            try:
                response = client.open(req, timeout=5)
            except HTTPError as exc:
                response = exc
            with response:
                if response.status != expected:
                    raise RuntimeError('TLS acceptance response status mismatch')
                return json.loads(response.read()), response.headers
        session, headers = request('/auth/session')
        cookie = headers.get('Set-Cookie', '')
        assert all(flag in cookie for flag in ['__Host-nodum_session=', 'Secure', 'HttpOnly', 'SameSite=lax', 'Path=/'])
        assert 'Domain=' not in cookie and headers.get('Cache-Control') == 'no-store'
        anonymous = next(iter(jar)).value
        request('/auth/login', {'username':'demo-manager','password':'Synthetic-demo-only-2026'},
                csrf=session['csrf_token'], origin='https://untrusted.example', expected=403)
        login, _ = request('/auth/login', {'username':'demo-manager','password':'Synthetic-demo-only-2026'},
                           csrf=session['csrf_token'])
        assert next(iter(jar)).value != anonymous
        snapshot, _ = request('/manager/snapshot')
        assert snapshot['buildings']
        request('/auth/logout', {}, csrf='wrong', expected=403)
        request('/auth/logout', {}, csrf=login['csrf_token'])
        request('/manager/snapshot', expected=401)
        try:
            untrusted = build_opener(ProxyHandler({}), HTTPSHandler(context=ssl.create_default_context()))
            untrusted.open(base+'/health', timeout=3)
        except URLError as exc:
            assert isinstance(exc.reason, ssl.SSLCertVerificationError)
        else:
            raise RuntimeError('Untrusted certificate was accepted')
        try:
            wrong_name = build_opener(ProxyHandler({}), HTTPSHandler(context=trusted))
            wrong_name.open(base.replace('127.0.0.1', 'localhost')+'/health', timeout=3)
        except URLError as exc:
            assert isinstance(exc.reason, ssl.SSLCertVerificationError)
        else:
            raise RuntimeError('Certificate hostname mismatch was accepted')
        return {'https':'verified with temporary CA only', 'secure_cookie':'PASS', 'rotation':'PASS',
                'csrf_and_origin':'PASS', 'authenticated_manager':'PASS', 'logout':'PASS',
                'untrusted_certificate':'rejected', 'wrong_certificate_hostname':'rejected', 'deployment_proxy':'not tested'}


if __name__ == '__main__':
    print(json.dumps(run(), indent=2))

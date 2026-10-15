"""Disposable software pilot drill: no dotenv loading, real credentials or external calls.
Run from any directory with the installed backend Python: python backend/scripts/pilot_drill.py
"""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import json
import socket
import time
from datetime import datetime, timezone
from urllib.request import urlopen
from urllib.error import HTTPError

root = Path(__file__).resolve().parents[2]
backend = root / 'backend'
sys.path.insert(0, str(backend))
from app.sqlite_repository import SQLiteRepository
from demo_product import seed_demo
from scripts.drill_support import isolated_environment

with tempfile.TemporaryDirectory(prefix='nodum-pilot-drill-') as folder:
    folder = Path(folder)
    original = folder / 'synthetic.db'
    archive = folder / 'archive.db'
    restored = folder / 'restored.db'
    # Deliberately exclude inherited private/provider configuration.
    env = isolated_environment()
    env.update(APP_ENV='production', NODUM_AUTHORIZATION_MODE='scoped', NODUM_AI_ENABLED='false',
               AUTH_PUBLIC_ORIGIN='https://nodum.example', DATABASE_URL='sqlite:///'+str(original),
               HOST='127.0.0.1', ACCESS_LOG='false', RING_MODE='simulation', RING_REQUIRED='false')
    saved = dict(os.environ)
    os.environ.clear();os.environ.update(env)
    try:
        repo = SQLiteRepository(env['DATABASE_URL'])
        repo.initialize(seed_demo=False)
        seed_demo(repo, datetime.now(timezone.utc), presentation=True)
    finally:
        os.environ.clear();os.environ.update(saved)
    def run(*args):
        p = subprocess.run([sys.executable, *args],cwd=backend,env=env,capture_output=True,text=True,timeout=35)
        if p.returncode:raise RuntimeError('Isolated CLI failed; details withheld')
        return json.loads(p.stdout)
    result = {'backup':run('-m','app.maintenance','backup','--source',str(original),'--destination',str(archive))}
    result['restore'] = run('-m','app.maintenance','restore','--source',str(archive),'--destination',str(restored))
    env['DATABASE_URL']='sqlite:///'+str(restored)
    result['preflight']=run('-m','app.preflight')['status']
    with socket.socket() as s:
        s.bind(('127.0.0.1',0));port=s.getsockname()[1]
    env['PORT']=str(port)
    server=subprocess.Popen([sys.executable,'-m','app.run'],cwd=backend,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        base=f'http://127.0.0.1:{port}'
        for _ in range(50):
            if server.poll() is not None:raise RuntimeError('Server exited')
            try:
                with urlopen(base+'/health',timeout=1) as response:
                    assert json.load(response)=={'status':'healthy'}
                break
            except OSError:time.sleep(.1)
        else:raise RuntimeError('Startup deadline exceeded')
        result['health']='200 healthy'
        for path, expected in [('/manager/snapshot',401),('/docs',404)]:
            try:
                with urlopen(base+path,timeout=2) as response:status=response.status
            except HTTPError as e:status=e.code
            assert status==expected,(path,status)
            result[path]=status
        assert SQLiteRepository(env['DATABASE_URL']).list_structure_nodes()
        result['restored_records']='present'
    finally:
        server.terminate();server.wait(timeout=10)
    (root/'artifacts').mkdir(exist_ok=True)
    (root/'artifacts/pilot-drill-result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result))

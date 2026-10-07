"""Read-only changed-file secret scan and optional public dependency OSV check.

Run from repository root: backend/.venv/Scripts/python.exe backend/scripts/release_checks.py
Add --dependencies to query OSV for pinned public backend requirements.
Never prints matched secret contents. This pattern scan is not a Gitleaks replacement.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]


def scan():
    paths = subprocess.check_output(['git','ls-files','-m','-o','--exclude-standard','-z'],cwd=ROOT).decode().split('\0')
    patterns = [r'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b', r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
        r'\bgh[pousr]_[A-Za-z0-9]{30,}\b', r'\bsk-(?:proj-)?[A-Za-z0-9_-]{30,}\b',
        r'''(?i)(?:password|secret|api_key|access_token|signing_key)\s*[:=]\s*["']([^"'\n]{16,})["']''']
    findings=[]; count=0
    for name in sorted(set(paths)):
        path=ROOT/name
        if not name or '.qa-f-' in name or not path.is_file() or path.suffix.lower() not in {'.py','.ts','.tsx','.js','.mjs','.json','.md','.txt','.yml','.yaml','.toml','.env'}:
            continue
        try: content=path.read_text(encoding='utf-8-sig')
        except (UnicodeError,OSError): continue
        count+=1
        for number,line in enumerate(content.splitlines(),1):
            for pattern in patterns:
                match=re.search(pattern,line)
                if not match: continue
                # Explicit, documented fixture markers are unusable demonstration data.
                if match.lastindex and re.search(r'(?i)synthetic|simulation-|fixture-|not-valid|example|placeholder|change-me',match.group(1)):
                    continue
                if match.lastindex and name=='backend/tests/test_auth.py' and match.group(1)=='test-only-password-782!':
                    continue  # Existing, deliberately public authentication fixture.
                findings.append({'file':name,'line':number,'kind':'credential/private-key pattern'})
    return {'files_scanned':count,'findings':findings}


def dependencies():
    pins=[]
    raw=(ROOT/'backend/requirements.txt').read_bytes()
    text=raw.decode('utf-16' if raw.startswith(b'\xff\xfe') else 'utf-16-le' if b'\0' in raw else 'utf-8-sig')
    for line in text.splitlines():
        match=re.fullmatch(r'([A-Za-z0-9_.-]+)==([^\s]+)',line.strip())
        if match: pins.append({'package':{'name':match[1],'ecosystem':'PyPI'},'version':match[2]})
    if not pins: raise RuntimeError('No requirement pins parsed; dependency audit is incomplete')
    body=json.dumps({'queries':pins}).encode()
    with urlopen(Request('https://api.osv.dev/v1/querybatch',data=body,headers={'Content-Type':'application/json'}),timeout=40) as response:
        results=json.load(response)['results']
    if len(results)!=len(pins): raise RuntimeError('Incomplete OSV response; dependency audit is incomplete')
    findings=[{'package':pin['package']['name'],'version':pin['version'],'advisories':[v['id'] for v in result.get('vulns',[])]}
        for pin,result in zip(pins,results) if result.get('vulns')]
    return {'source':'https://api.osv.dev/v1/querybatch','packages_checked':len(pins),'findings':findings}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dependencies',action='store_true')
    args=parser.parse_args()
    report={'secrets':scan()}
    if args.dependencies: report['backend_dependencies']=dependencies()
    print(json.dumps(report,indent=2))
    raise SystemExit(bool(report['secrets']['findings'] or report.get('backend_dependencies',{}).get('findings')))

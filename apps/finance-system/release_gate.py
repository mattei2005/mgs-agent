#!/usr/bin/env python3
"""Fail-closed release gate. Private real fixtures stay outside Git/public assets."""
import argparse,datetime,hashlib,json,os,pathlib,re,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parent

def code_manifest():
    paths=[p for p in ROOT.iterdir() if p.is_file() and p.suffix in {'.mjs','.py','.sql','.json'}]
    for folder in ('public','tests'):
        paths.extend(p for p in (ROOT/folder).rglob('*') if p.is_file() and p.suffix in {'.mjs','.py','.js','.css','.html','.json'})
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(set(paths))}

def validate_fixture(manifest):
    m=json.loads(manifest.read_text());p=(ROOT/m['path']).resolve()
    if not p.is_relative_to(ROOT/'private') or not p.is_file():raise ValueError('Release fixture must be an existing protected private file')
    if hashlib.sha256(p.read_bytes()).hexdigest()!=m['sha256']:raise ValueError('Release fixture SHA-256 mismatch')
    s=json.loads(p.read_text())
    if s.get('id')!='workspace-2026-08' or s.get('revision')!=m['revision'] or not s.get('result',{}).get('domain',{}).get('facts'):raise ValueError('Wrong or incomplete real August fixture')
    if not m.get('source_evidence'):raise ValueError('Fixture provenance missing')
    return p,m

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--phase',choices=['preflight','node','python','all'],default='all');parser.add_argument('--manifest',type=pathlib.Path,default=ROOT/'private/release-fixtures/manifest.json');parser.add_argument('--output',type=pathlib.Path,default=ROOT/'private/release-gate');a=parser.parse_args()
    fixture,m=validate_fixture(a.manifest);a.output.mkdir(parents=True,exist_ok=True,mode=0o700)
    before=code_manifest();env={**os.environ,'FINANCE_RELEASE_GATE':'1','FINANCE_AUGUST_FIXTURE':str(fixture)}
    results=[]
    for phase in (['node','python'] if a.phase=='all' else [a.phase]):
        if phase=='preflight':continue
        cmd=['node','--test',*[str(p.relative_to(ROOT)) for p in sorted((ROOT/'tests').glob('*.test.mjs'))]] if phase=='node' else [sys.executable,'-m','unittest','discover','-s','tests','-p','test_*.py']
        started=datetime.datetime.now(datetime.timezone.utc);p=subprocess.run(cmd,cwd=ROOT,env=env,capture_output=True,text=True,timeout=900)
        text=p.stdout+p.stderr;(a.output/(phase+'.log')).write_text(text)
        if phase=='node':
            fields={k:int(v) for k,v in re.findall(r'^# (tests|pass|fail|skipped|cancelled|todo) (\d+)$',text,re.M)}
            passed=p.returncode==0 and fields.get('tests',0)>0 and fields.get('pass')==fields.get('tests') and fields.get('fail')==0 and fields.get('skipped')==0 and fields.get('cancelled')==0 and fields.get('todo')==0
        else:
            matches=re.findall(r'Ran (\d+) tests?',text);fields={'tests':int(matches[-1]) if matches else 0};passed=p.returncode==0 and fields['tests']>0 and bool(re.search(r'^OK$',text,re.M)) and 'skipped=' not in text
        record={'phase':phase,'pass':passed,'exit':p.returncode,'counts':fields,'started_at':started.isoformat(),'seconds':(datetime.datetime.now(datetime.timezone.utc)-started).total_seconds()};results.append(record);print(json.dumps(record),flush=True)
        if not passed:raise RuntimeError('Release gate failed; inspect '+str(a.output/(phase+'.log')))
    if before!=code_manifest():raise RuntimeError('Code changed during validation; release blocked')
    result={'pass':True,'phase':a.phase,'fixture_sha256':m['sha256'],'fixture_revision':m['revision'],'code':before,'results':results,'verified_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'financial_writes':0}
    (a.output/(a.phase+'-result.json')).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'pass':True,'phase':a.phase,'skips_allowed':False,'financial_writes':0}))
if __name__=='__main__':
    try:main()
    except Exception as e:print(json.dumps({'pass':False,'error':str(e)}));sys.exit(1)

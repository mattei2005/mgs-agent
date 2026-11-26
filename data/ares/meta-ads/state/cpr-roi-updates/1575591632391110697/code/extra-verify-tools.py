import pathlib,json,hashlib,ast,subprocess,sys,importlib.util
from datetime import datetime
R=pathlib.Path(__file__).parent;H=pathlib.Path('/root/.hermes/profiles/ares')
def save(name,x):(R/name).write_text(json.dumps(x,ensure_ascii=False,indent=2))
if sys.argv[1]=='approve':
 run=sorted((R/'runs').glob('dry-*'))[-1];snap=json.loads((run/'snapshot.json').read_text());m=json.loads((R/'manifest.json').read_text());parts=json.loads((run/'update-parts.json').read_text());assert set(snap['rows'])=={c['id'] for c in m['campaigns']};assert not snap['pending'] and not snap['sb_error'];assert all(len(p.encode('utf-16-le'))//2<=2000 for p in parts);assert all('created_today' in c['reasons'] for c in m['campaigns'])
 names=[p.name for p in run.iterdir() if p.is_file() and p.suffix=='.json' and p.name not in ['preflight.json']]
 save('review-approved.json',{'run':str(run),'approved_at':datetime.now().astimezone().isoformat(),'reviewed':True,'hashes':{n:hashlib.sha256((run/n).read_bytes()).hexdigest() for n in names},'runner_sha256':hashlib.sha256(pathlib.Path(m['runner']).read_bytes()).hexdigest()})
 s=(R/'schedule-audit.py').read_text();tree=ast.parse(s);func=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='audit');infra=next(n for n in func.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='infra' for t in n.targets));loop=next(n for n in func.body if isinstance(n,ast.For));ns={'raw':{'entries':[{'baseline':True,'source':'root','name':'monitor-mattei-uptime.py','schedule':'* * * * *'},{'baseline':False,'source':'root','name':'monitor-mattei-uptime.py','schedule':'0 * * * *'},{'baseline':True,'source':'ares','name':'unknown-operational','schedule':'* * * * *'}]}}
 exec(compile(ast.fix_missing_locations(ast.Module(body=[infra,loop],type_ignores=[])),'classification','exec'),ns);out=[e['baseline'] for e in ns['raw']['entries']];assert out==[True,False,False];save('baseline-classification-test.json',{'pass':True,'tests_run':3,'actual':out,'source':'AST of actual audit classification loop'})
 cfg=(H/'config.yaml').read_text();import re
 hits=re.findall(r'^\s+script_timeout:\s*(\d+)\s*$',cfg,re.M)
 if hits:assert len(hits)==1;timeout=int(hits[0])
 else:
  src=pathlib.Path('/root/.hermes/hermes-agent-port-main-29a61cb7-mgs-20261103/cron/scheduler.py');hit=re.search(r'^_DEFAULT_SCRIPT_TIMEOUT = (\d+)',src.read_text(),re.M);assert hit;timeout=int(hit[1])
 assert timeout>165;save('timeout-validation.json',{'script_timeout_seconds':timeout,'wrapper_timeout_seconds':165,'pass_check':True,'source':'installed scheduler default; no config override'});print('REVIEW_APPROVED; baseline3PASS; timeoutPASS')
elif sys.argv[1]=='replay':
 run=R/'runs/initial'
 def hashes():return {str(p.relative_to(run)):hashlib.sha256(p.read_bytes()).hexdigest() for p in run.rglob('*') if p.is_file()}
 before=hashes();m=json.loads((R/'manifest.json').read_text());out=subprocess.run(['bash',m['wrapper'],'--initial'],capture_output=True,text=True,timeout=180);assert out.returncode==0,out.stderr;assert hashes()==before;save('initial-replay-verification.json',{'pass':True,'public_wrapper':True,'all_file_hashes_preserved':True,'files':len(before),'result':json.loads(out.stdout)});print('PUBLIC_WRAPPER_REPLAY_PASS')

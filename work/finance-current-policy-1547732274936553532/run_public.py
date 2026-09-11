import os,json,subprocess,sys,shutil,pathlib
sys.path.insert(0,'/root/mgs-agent/scripts');from mgs_google_workspace_auth import load_env
load_env()
def op(*args):
 p=subprocess.run(['op',*args],capture_output=True,text=True,env=os.environ,timeout=60);assert p.returncode==0,p.stderr[-500:];return json.loads(p.stdout)
items=op('item','list','--format=json');owner=next(x for x in items if x.get('title')=='MGS Finance - rodolfo - dash.mgsdigitalcorp.com');managers=[x for x in items if 'mgs finance' in x.get('title','').lower() and 'nicolas' in x.get('title','').lower()];assert len(managers)==1
def creds(item):
 d=op('item','get',item['id'],'--vault',item['vault']['id'],'--format=json');fields={str(f.get('label','')).lower():f.get('value') for f in d.get('fields',[])};u=fields.get('username');p=fields.get('password');assert u and p;return {'username':u,'password':p}
payload={'owner':creds(owner),'manager':creds(managers[0])};node=shutil.which('node');assert node;script=sys.argv[1] if len(sys.argv)>1 else 'tests/current-policy-public.mjs';r=subprocess.run([node,script],cwd='/root/mgs-agent/apps/finance-system',input=json.dumps(payload),capture_output=True,text=True,timeout=900);path=pathlib.Path('/root/mgs-agent/work/finance-current-policy-1547732274936553532/public-run-output.json');path.write_text(r.stdout.strip()+'\n');print(r.stdout.strip());assert r.returncode==0,r.stderr[-1500:]

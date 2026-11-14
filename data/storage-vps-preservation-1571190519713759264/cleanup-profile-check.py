#!/usr/bin/env python3
import pathlib,subprocess,json,time,os,argparse,datetime
p=argparse.ArgumentParser();p.add_argument('--phase',choices=['before','after'],required=True);a=p.parse_args()
out=pathlib.Path(__file__).resolve().parent
scratch=pathlib.Path('/root/.hermes/profiles/zeus/cache/scratch/vps-retire-checks-1571196199548092428');scratch.mkdir(mode=0o700,exist_ok=True)
launcher='/root/.local/bin/hermes';marker='MGS_CLEANUP_SMOKE_OK';results={}
for profile in ['zeus','ares','atena']:
 row={};start=time.monotonic()
 for name,args in [('config',[launcher,'-p',profile,'config','check']),('smoke',[launcher,'-p',profile,'chat','--oneshot','-Q','-t','','--max-turns','1','--run-budget','60','-q','Reply only MGS_CLEANUP_SMOKE_OK. Do not use tools or modify files.'])]:
  try:
   r=subprocess.run(args,capture_output=True,text=True,timeout=100,env={**os.environ,'TERM':'dumb'})
   text=r.stdout+'\n'+r.stderr;log=scratch/f'{a.phase}-{profile}-{name}.log';log.write_text(text);os.chmod(log,0o600)
   ok=r.returncode==0 and (name!='smoke' or marker in r.stdout)
   row[name]={'returncode':r.returncode,'passed':ok,'profile_explicit':profile,'tools_disabled':name=='smoke','private_log':str(log)}
  except subprocess.TimeoutExpired:
   row[name]={'passed':False,'timeout':True,'profile_explicit':profile}
  if not row[name]['passed']:
   results[profile]=row;(out/f'profile-{a.phase}.json').write_text(json.dumps({'phase':a.phase,'results':results,'passed':False},indent=2)+'\n');raise SystemExit('Profile check failed: '+profile+'/'+name)
 row['elapsed_seconds']=round(time.monotonic()-start,2);results[profile]=row
receipt={'phase':a.phase,'passed':True,'results':results,'observed_at':datetime.datetime.now().astimezone().isoformat()};(out/f'profile-{a.phase}.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'phase':a.phase,'configs_passed':3,'smokes_passed':3,'tools_disabled':True}))

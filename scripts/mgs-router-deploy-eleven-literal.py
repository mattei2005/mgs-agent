#!/usr/bin/env python3
"""Publish the owner-authorized literal Keitaro compatibility; no DNS/unit/credential writes."""
import json,hashlib,shutil,os,subprocess,time
from pathlib import Path
from datetime import datetime,timezone
import requests
BASE=Path('/root/mgs-agent');APPROVAL='1556086016140509195'
CAND=Path('/root/.hermes/profiles/zeus/cache/scratch/mgs-router-'+APPROVAL)
LIVE=Path('/opt/mgs-router/mgs-router');STATE=Path('/var/lib/mgs-router')
BACK=Path('/root/.local/share/mgs-router-rollbacks')/APPROVAL/'release'
OUT=BASE/'data/mgs-router-eleven-literal-release-receipt.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(args):
 r=subprocess.run(args,capture_output=True,text=True,timeout=45)
 if r.returncode:raise RuntimeError('command_failed:'+Path(args[0]).name)
 return r.stdout.strip()
def pids():return {n:run(['systemctl','show',n+'-gateway.service','-p','MainPID','--value']) for n in ['zeus','atena','ares']}
def main():
 assert CAND.exists() and not BACK.exists(),'reconcile_existing_release_before_replay'
 BACK.mkdir(mode=0o700,parents=True)
 watched=[STATE/f for f in ['routes.json','domains.json','users.json','domain-checks.json']]+[Path('/etc/systemd/system/mgs-router.service')]
 before={str(p):sha(p) for p in watched};gateways=pids();oldhash=sha(LIVE)
 shutil.copy2(LIVE,BACK/'mgs-router');os.chmod(BACK/'mgs-router',0o700)
 for p in watched[:4]:shutil.copy2(p,BACK/p.name);os.chmod(BACK/p.name,0o600)
 run([str(BACK/'mgs-router'),'--state',str(BACK),'--origin','https://route.mgsdigitalcorp.com','--check'])
 run([str(CAND),'--state',str(BACK),'--origin','https://route.mgsdigitalcorp.com','--check'])
 probe=BACK/'candidate-check';probe.mkdir(mode=0o700)
 plan=json.loads((BASE/'data/mgs-router-eleven-domains-import-plan.json').read_text())['configuration']
 (probe/'routes.json').write_text(json.dumps(plan));os.chmod(probe/'routes.json',0o600)
 for f in ['users.json','domains.json','domain-checks.json']:shutil.copy2(BACK/f,probe/f)
 run([str(CAND),'--state',str(probe),'--origin','https://route.mgsdigitalcorp.com','--check'])
 receipt={'authorization_message_id':APPROVAL,'status':'publishing','backup':str(BACK),'previous_binary_sha256':oldhash,'candidate_sha256':sha(CAND),'backup_and_candidate_real_binary_checks':True,'before_store_hashes':before,'gateway_pids_before':gateways,'DNS_writes':0,'unit_writes':0,'credential_writes':0}
 def save():OUT.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
 save()
 try:
  stage=LIVE.with_name('mgs-router-'+APPROVAL);shutil.copy2(CAND,stage);os.chmod(stage,0o755);os.replace(stage,LIVE)
  run(['systemctl','restart','mgs-router.service'])
  ok=False
  for delay in [0,2,5,10]:
   if delay:time.sleep(delay)
   try:r=requests.get('https://route.mgsdigitalcorp.com/healthz',timeout=25);ok=r.status_code==200 and r.json().get('status')=='ok'
   except requests.RequestException:continue
   if ok:break
  assert ok and run(['systemctl','is-active','mgs-router.service'])=='active'
  assert sha(LIVE)==sha(CAND) and {str(p):sha(p) for p in watched}==before and pids()==gateways
  receipt.update(status='deployed_health_and_invariants_validated',stores_unit_gateway_pids_unchanged=True,validated_at=datetime.now(timezone.utc).isoformat());save()
 except Exception as e:
  stage=LIVE.with_name('mgs-router-rollback-'+APPROVAL);shutil.copy2(BACK/'mgs-router',stage);os.chmod(stage,0o755);os.replace(stage,LIVE);run(['systemctl','restart','mgs-router.service'])
  receipt.update(status='failed_binary_rolled_back',error=type(e).__name__,rollback_binary_hash_matches=sha(LIVE)==oldhash);save();raise
 with (BASE/'logs/events-audit.jsonl').open('a') as f:f.write(json.dumps({'timestamp':receipt['validated_at'],'agent':'zeus','action':'router_literal_keitaro_compatibility_published','thread_id':'1555381168894115912',**receipt})+'\n')
 print(json.dumps({k:receipt[k] for k in ['status','candidate_sha256','backup_and_candidate_real_binary_checks','stores_unit_gateway_pids_unchanged','DNS_writes','unit_writes','credential_writes']}))
if __name__=='__main__':main()

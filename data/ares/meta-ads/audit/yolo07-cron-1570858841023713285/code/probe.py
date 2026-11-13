import pathlib,json,importlib.util,sys,subprocess
BASE=pathlib.Path('/root/mgs-agent');ROOT=BASE/'data/ares/meta-ads/audit/yolo07-cron-1570858841023713285';ROOT.mkdir(parents=True,exist_ok=True)
def mod(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m
d=mod('probe_daily','/root/.hermes/profiles/ares/scripts/shein-daily-report.py')
dc=d.Discord();msg=dc.call('GET','/channels/1570801075621986305/messages/1570858841023713285');assert msg['author']['id']=='344196393512075265' and '1569767319339663361' in msg['content'];d.save(ROOT/'authorization-readback.json',msg)
for aid in ['1492168699397108','7840111366055613']:
 p=subprocess.run([sys.executable,str(BASE/'scripts/mgs-ares-asset-scope.py'),'check-account',aid,'--json'],capture_output=True,text=True);assert p.returncode==0 and json.loads(p.stdout)['allowed']
import os
os.environ['ARES_META_GRAPH_VERSION']='v26.0';meta=mod('probe_meta',BASE/'scripts/ares-meta-common.py');contract=d.load(d.CONTRACT);token,_=meta.get_token_from_1password(contract['credential_architecture']['shared_car_shein_bisu']['token_item'])
results=[]
for label,path,fields in [('corporate_identity','me','id,name,client_business_id'),('target','act_1492168699397108','id,name,currency,timezone_name,account_status'),('same_manager_control','act_7840111366055613','id,name,currency,timezone_name')]:
 st,data,_=meta.graph_get(path,token,{'fields':fields});safe={'label':label,'http':st,'observed_at':d.now()}
 if st==200:safe['identity']={k:data.get(k) for k in fields.split(',')}
 else:
  err=data.get('error',{});safe['error']={k:err.get(k) for k in ['code','error_subcode','type','message']}
 results.append(safe);d.save(ROOT/'live-preflight.json',results)
print(json.dumps(results,ensure_ascii=False))

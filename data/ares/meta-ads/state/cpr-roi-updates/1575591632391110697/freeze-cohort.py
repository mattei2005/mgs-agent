import importlib.util,sys,json
from pathlib import Path
from datetime import datetime
P=Path('/root/.hermes/profiles/ares/scripts/shein-g004-cpr-roi-20261126.py');spec=importlib.util.spec_from_file_location('fixed07',P);m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
x=m.load(m.ROOT/'manifest.json');d,delivery,_=m.helpers();dc=d.Discord();dc.verify([{'thread_id':m.TID,'channel_id':x['parent_id']}]);auth=dc.call('GET','/channels/'+m.TID+'/messages/'+m.REQUEST)
assert auth['author']['id']==m.USER and auth['content']==x['request_text'] and auth['channel_id']==m.TID
assert datetime.fromisoformat(auth['timestamp'])==datetime.fromisoformat(x['request_time'])
m.save(m.ROOT/'authorization.json',{'id':auth['id'],'channel_id':auth['channel_id'],'author_id':auth['author']['id'],'content':auth['content'],'timestamp':auth['timestamp'],'get_verified':True})
sc=next(b for b in m.load(m.BASE/'data/ares/discord/shein-intraday-report-bindings.json')['bindings'] if b['thread_id']==m.TID);assert (sc['account_id'],sc['channel_id'])==(m.AID,x['parent_id'])
b={'thread_id':m.TID,'channel_id':x['parent_id'],'account_id':m.AID,'account_name':x['account_name'],'manager_code':'g004'}
run=m.ROOT/'discovery';run.mkdir(exist_ok=True);r=d.Runner({'policy_id':m.REQUEST},run,[b],x['date']);a=r.source(run,'account',lambda:r.graph('act_'+m.AID,{'fields':'id,name,currency,timezone_name'}))
assert a['id'] in (m.AID,'act_'+m.AID) and (a['name'],a['currency'])==(x['account_name'],x['currency']);assert a['timezone_name']==x['timezone_name']
rows=r.source(run,'campaigns',lambda:r.paged('act_'+m.AID+'/campaigns',{'fields':m.META_FIELDS,'limit':500,'filtering':json.dumps([{'field':'effective_status','operator':'IN','value':['ACTIVE','PAUSED','ARCHIVED','IN_PROCESS','WITH_ISSUES']}])}))
cs=[]
for c in rows:
 if m.candidate(c,x,datetime.fromisoformat(x['request_time'])):
  number=c['name'].split(' - ')[0];assert number.isdigit();cs.append({**c,'number':number,'reasons':['created_today']})
assert len({c['id'] for c in cs})==len(cs)
if x['cohort_frozen']:assert {c['id'] for c in cs}=={c['id'] for c in x['campaigns']}
x.update(campaigns=cs,cohort_frozen=True,state='COHORT_FROZEN',preflight=a);m.save(m.ROOT/'manifest.json',x);m.save(m.ROOT/'binding.json',b)
print(json.dumps({'cohort':[{'number':c['number'],'created_time':c['created_time'],'status':c['status']} for c in cs],'live_account':a,'selection_cutoff':x['request_time'],'frozen':True},ensure_ascii=False))

#!/usr/bin/env python3
"""Freeze authenticated today's new and materially edited campaigns."""
import importlib.util,json
from datetime import datetime
from pathlib import Path
H=Path('/root/.hermes/profiles/ares/scripts')
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
n=module('new_updates',H/'shein-g004-cpr-roi-20261127.py')
def extra(e):
    x=e.get('extra_data') or {}
    return json.loads(x) if isinstance(x,str) else x

def material(e,start,end):
    at=datetime.fromisoformat(e['event_time'])
    if not start<=at<=end or str(e.get('actor_id','0'))=='0':return False
    kind=e['event_type'];x=extra(e)
    if not kind.startswith('update_') or 'after_review' in kind:return False
    if 'run_status' in kind:
        r=x.get('run_status',{})
        return {r.get('old_value'),r.get('new_value')}=={1,15}
    if kind=='update_ad_set_bid_strategy':
        av=x.get('additional_value') or {}
        return x.get('old_value') is not None and (x.get('old_value')!=x.get('new_value') or av.get('old_value')!=av.get('new_value'))
    return x.get('old_value') not in (None,'',[],{}) and x.get('old_value')!=x.get('new_value')

def fields(kind):
    base='id,account_id,name'
    if kind.startswith('update_ad_set_'):return base+',campaign_id,bid_amount,status,effective_status'
    if kind.startswith('update_ad_'):return base+',campaign_id,adset_id,status,effective_status'
    return base+',created_time,status,configured_status,effective_status,daily_budget,bid_strategy'

def select(events,objects,campaigns,start,end):
    evidence={}
    for e in events:
        if not material(e,start,end):continue
        obj=objects[str(e['object_id'])]
        assert obj['id']==str(e['object_id']) and obj['account_id']==n.AID
        cid=obj.get('campaign_id',obj['id']);c=campaigns[cid]
        assert c['id']==cid and c['account_id']==n.AID
        if datetime.fromisoformat(c['created_time']).astimezone(n.NY).date().isoformat()==n.DAY:continue
        evidence.setdefault(cid,[]).append({k:e.get(k) for k in ('event_time','event_type','object_id','actor_id','actor_name','application_id','application_name')})
    members=[]
    for cid,events in evidence.items():
        c=campaigns[cid];number=c['name'].split(' - ')[0];assert number.isdigit()
        members.append({**c,'number':number,'membership_source':'edited_today','edit_evidence':events})
    return sorted(members,key=lambda c:int(c['number']))
s=__import__('types').SimpleNamespace(fields=fields,material=material,select=select)

def main():
 p=n.ROOT;pf=n.load(p/'preflight.json');msg=pf['messages'][0];a=pf['account'];end=datetime.fromisoformat(msg['timestamp']);start=end.astimezone(n.NY).replace(hour=0,minute=0,second=0,microsecond=0)
 assert start.date().isoformat()==n.DAY
 m={'request_id':n.REQUEST,'source_message_id':n.REQUEST,'requester_discord_id':n.USER,'request_time':end.isoformat(),'request_text':msg['content'],'mode':'finite_read_only_periodic_cpr_roi','account_id':n.AID,'account_name':a['name'],'domain':'yolokfx.com','thread_id':n.TID,'parent_id':pf['binding']['channel_id'],'date':n.DAY,'timezone':a['timezone_name'],'timezone_name':a['timezone_name'],'currency':a['currency'],'dynamic_discovery':{'enabled':False,'criterion':'created_time','date':n.DAY},'cadence_minutes':30,'expires_at':(start+n.timedelta(days=1)).isoformat(),'meta_writes':False,'dashboard_writes':False,'runner':str(H/'shein-g004-cpr-roi-20261127.py'),'wrapper':str(H/'shein-g004-cpr-roi-20261127.sh'),'metric_cpr':'Meta spend/offsite_conversion.fb_pixel_add_to_wishlist','metric_roi':'100*(SB_NET_REVENUE/SB_INVESTIMENT_ADJUSTED-1)','campaigns':[],'edited_campaigns':[],'slots':[],'cohort_frozen':False,'antecedent_request_id':'1573371023603142820','confirmation_message_id':'1576000421925757091','discover_future_edits':False}
 if (p/'manifest.json').exists():
  prior=n.load(p/'manifest.json')
  if prior.get('cohort_frozen'):print(json.dumps({'status':'ALREADY_FROZEN','count':len(prior['campaigns'])}));return
 n.save(p/'manifest.json',m);b=n.scope(m);d,_=n.helpers();r=d.Runner({'policy_id':n.REQUEST},p,[b],n.DAY)
 campaigns=r.source(p,'intake-campaigns',lambda:r.paged('act_'+n.AID+'/campaigns',{'fields':'id,name,account_id,created_time,status,configured_status,effective_status','filtering':json.dumps([{'field':'effective_status','operator':'IN','value':['ACTIVE','PAUSED','DELETED','ARCHIVED','WITH_ISSUES']}]),'limit':500}))
 fresh=n.candidates(campaigns,end)
 events=r.source(p,'intake-activities',lambda:r.paged('act_'+n.AID+'/activities',{'fields':'event_time,event_type,object_id,actor_id,actor_name,application_id,application_name,extra_data','since':start.isoformat(),'until':end.isoformat(),'limit':100}))
 targets={str(e['object_id']):s.fields(e['event_type']) for e in events if s.material(e,start,end)}
 def batch(targets):
  out={};items=list(targets.items())
  for off in range(0,len(items),50):
   chunk=items[off:off+50];st,children,_=r.meta.graph_batch_get(r.token,[{'path':cid,'params':{'fields':f}} for cid,f in chunk]);assert st==200 and len(children)==len(chunk)
   for (cid,_),ch in zip(chunk,children):
    assert ch['code']==200
    obj=json.loads(ch['body']) if isinstance(ch['body'],str) else ch['body'];assert obj['id']==cid and obj['account_id']==n.AID;out[cid]=obj
  return out
 objects=r.source(p,'intake-edit-objects',lambda:batch(targets));parents={str(o.get('campaign_id',o['id'])) for o in objects.values()}
 parents=r.source(p,'intake-edit-campaigns',lambda:batch({cid:'id,name,account_id,created_time,status,configured_status,effective_status,daily_budget,bid_strategy' for cid in parents}))
 edits=s.select(events,objects,parents,start,end)
 selection={'source_message_id':n.REQUEST,'since':start.isoformat(),'until':end.isoformat(),'complete_pagination':True,'activities_count':len(events),'campaigns':edits,'discover_future_edits':False,'physical_actor_limitation':'Profile/application alone does not prove the human at keyboard.'};n.save(p/'selection-edits.json',selection)
 # Preserve explicit operational messages from Joe as attribution context, not a new Meta action.
 dc=d.Discord();recent=dc.call('GET','/channels/1558131278589460584/messages?limit=100')
 human=[{k:x.get(k) for k in ('id','timestamp','content','author')} for x in recent if x['author']['id']==n.USER and start<=datetime.fromisoformat(x['timestamp'])<=end]
 n.save(p/'requester-origin-messages.json',human)
 for c in edits:fresh.setdefault(c['id'],c)
 m.update(campaigns=list(fresh.values()),edited_campaigns=edits,cohort_frozen=True,cohort_cutoff=end.isoformat(),edited_cohort_authorization={'message_id':n.REQUEST,'since':start.isoformat(),'until':end.isoformat(),'discover_future_edits':False,'selection_path':str(p/'selection-edits.json')})
 n.save(p/'manifest.json',m)
 print(json.dumps({'status':'FROZEN','new':[c['number'] for c in fresh.values() if c['membership_source']=='created_today'],'edited':[c['number'] for c in edits],'total':len(fresh),'activities':len(events),'origin_requests':[{k:x[k] for k in ('id','timestamp','content')} for x in human]},ensure_ascii=False))
if __name__=='__main__':main()

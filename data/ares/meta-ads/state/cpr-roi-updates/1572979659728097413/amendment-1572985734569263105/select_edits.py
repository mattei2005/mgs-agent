"""Read-only frozen material-change cohort for the authenticated amendment."""
import importlib.util,json
from pathlib import Path
from datetime import datetime
P=Path(__file__).parent
SPEC=importlib.util.spec_from_file_location('updates_amendment',Path('/root/.hermes/profiles/ares/scripts/shein-g004-cpr-roi-20261119.py'))
assert SPEC is not None and SPEC.loader is not None
n=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(n)

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

def main():
    msg=n.load(n.ROOT/'amendment-1572985734569263105-message.json');end=datetime.fromisoformat(msg['timestamp']);start=datetime.fromisoformat(n.DAY+'T00:00:00-05:00')
    events=n.load(P/'activities.json');events=[e for e in events if material(e,start,end)]
    b=n.scope(n.load(n.ROOT/'manifest.json'));d,_=n.helpers();r=d.Runner({'policy_id':n.REQUEST},P,[b],n.DAY)
    targets={str(e['object_id']):fields(e['event_type']) for e in events}
    def batch(targets):
        out={};items=list(targets.items())
        for off in range(0,len(items),50):
            chunk=items[off:off+50];st,children,_=r.meta.graph_batch_get(r.token,[{'path':cid,'params':{'fields':f}} for cid,f in chunk]);assert st==200 and len(children)==len(chunk)
            for (cid,_),ch in zip(chunk,children):
                assert ch['code']==200
                obj=json.loads(ch['body']) if isinstance(ch['body'],str) else ch['body'];assert obj['id']==cid and obj['account_id']==n.AID;out[cid]=obj
        return out
    objects=r.source(P,'objects',lambda:batch(targets));parents={str(o.get('campaign_id',o['id'])) for o in objects.values()}
    campaigns=r.source(P,'campaigns',lambda:batch({cid:'id,name,account_id,created_time,status,configured_status,effective_status,daily_budget,bid_strategy' for cid in parents}))
    members=select(events,objects,campaigns,start,end)
    n.save(P/'selection.json',{'source_message_id':msg['id'],'since':start.isoformat(),'until':end.isoformat(),'complete_pagination':True,'activities_count':len(n.load(P/'activities.json')),'material_events_count':len(events),'campaigns':members,'attribution_limitation':'Meta profile/application proves technical origin, not person at keyboard. Ares reactivations overlap already explicitly requested IDs.','discover_future_edits':False})
    print(json.dumps({'numbers':[c['number'] for c in members],'campaigns':len(members),'events':len(events),'actors':sorted({e['actor_name'] for e in events})},ensure_ascii=False))
if __name__=='__main__':main()

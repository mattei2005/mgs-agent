"""Reconcile confirmed SHEIN two-phase shells; never replay unidentified copies."""
from __future__ import annotations
from datetime import datetime,timezone
from .transport import BatchOperation


def reconcile(engine,bundle,transport,record):
    campaigns=record.get('campaign_ids') or []
    if len(campaigns)!=len(bundle.campaigns):
        raise ValueError('unconfirmed campaign copy: preserve uncertainty; no blind replay')
    if len(record.get('adset_ids') or [])!=len(campaigns):
        reads=engine._batch(bundle,transport,[BatchOperation('shell_sets_'+str(i),'GET',cid+'/adsets?fields=id,name,status,start_time&limit=50',kind='readback') for i,cid in enumerate(campaigns,1)],'recovery_shell_inventory')
        ids=[];missing=[]
        for i,(row,spec,cid) in enumerate(zip(reads,bundle.campaigns,campaigns),1):
            if row.body.get('paging',{}).get('next'):raise ValueError('shell inventory incomplete')
            rows=[r for r in row.body.get('data',[]) if r.get('status')!='DELETED']
            if len(rows)>1:raise ValueError('ambiguous adset shell: no copy replay')
            if rows:ids.append(str(rows[0]['id']))
            else:
                # Lost responses may precede edge consistency. Do not trust immediate emptiness.
                pending=[j for j in record.get('write_journal',[]) if j.get('state') in {'IN_FLIGHT','PARTIAL_OR_UNCERTAIN'} and j.get('stage')=='adset_copy']
                if pending and (datetime.now(timezone.utc)-datetime.fromisoformat(pending[-1]['at'])).total_seconds()<60:
                    raise ValueError('adset write uncertain: wait for scoped readback convergence, no retry')
                ids.append(None)
                missing.append(BatchOperation('adset_copy_'+str(i),'POST',spec.source_adset_id+'/copies',body={'campaign_id':cid,'deep_copy':'false','status_option':spec.status,'start_time':spec.start_time},kind='adset_copy'))
        if missing:
            results=engine._batch(bundle,transport,missing,'recovery_shell_adset_copy')
            for row in results:ids[int(row.name.rsplit('_',1)[1])-1]=str(row.body['copied_adset_id'])
        record['adset_ids']=ids
    ops=[]
    for i,(spec,cid,setid) in enumerate(zip(bundle.campaigns,campaigns,record['adset_ids']),1):
        ops.extend([BatchOperation('shell_campaign_'+str(i),'GET',cid+'?fields=id,name,status,daily_budget,bid_strategy,start_time',kind='readback'),BatchOperation('shell_adset_'+str(i),'GET',setid+'?fields=id,name,status,start_time',kind='readback')])
    read=engine._batch(bundle,transport,ops,'recovery_shell_readback');byname={r.name:r.body for r in read};updates=[]
    for i,(spec,cid,setid) in enumerate(zip(bundle.campaigns,campaigns,record['adset_ids']),1):
        desired={'name':spec.name,**spec.campaign_updates,'status':spec.status,'start_time':spec.start_time}
        observed=byname['shell_campaign_'+str(i)]
        if any(str(observed.get(k))!=str(v) for k,v in desired.items()):updates.append(BatchOperation('shell_campaign_update_'+str(i),'POST',cid,body=desired,kind='campaign_update'))
        desired={'name':spec.adset_name,'status':spec.status,**spec.adset_updates}
        observed=byname['shell_adset_'+str(i)]
        if any(observed.get(k)!=v for k,v in desired.items()):updates.append(BatchOperation('shell_adset_update_'+str(i),'POST',setid,body=desired,kind='adset_update'))
    if updates:engine._batch(bundle,transport,updates,'recovery_shell_normalize')
    record['stage']='shells_normalized'

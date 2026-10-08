"""Per-lane durable write journal; no POST retries and no credentials."""
from __future__ import annotations
from contextvars import ContextVar
from datetime import datetime, timezone
import hashlib
import json
import re
from typing import Any

CURRENT: ContextVar[Any] = ContextVar('engine_bundle_progress', default=None)


def begin(operations, stage):
    current=CURRENT.get()
    if not current:return None
    record,save=current
    writes=[o for o in operations if o.method.upper()!='GET']
    if not writes:
        save();return None
    entry={'stage':stage,'state':'IN_FLIGHT','at':datetime.now(timezone.utc).isoformat(),'operations':[{'name':o.name,'method':o.method,'path':o.relative_url.split('?')[0],'body_digest':hashlib.sha256(json.dumps(o.body,sort_keys=True).encode()).hexdigest()} for o in writes]}
    record.setdefault('write_journal',[]).append(entry);save();return entry


def finish(entry, rows, error=None):
    current=CURRENT.get()
    if not current:return
    record,save=current
    confirmed=[]
    for row in rows:
        if not 200<=row.code<300:continue
        ids={k:row.body[k] for k in ['id','copied_campaign_id','copied_adset_id','copied_ad_id'] if row.body.get(k)}
        if ids:confirmed.append({'name':row.name,'ids':ids})
    if error is not None:confirmed.extend(error.get('successful_children') or [])
    if entry is not None:
        entry['state']='CONFIRMED' if error is None else 'PARTIAL_OR_UNCERTAIN'
        entry['confirmed']=confirmed
    slots=record.setdefault('confirmed_objects',{})
    for row in confirmed:
        slots[row['name']]=row.get('ids') or {}
        m=re.fullmatch(r'existing_post_(?:recovery_)?creative_(\d+)_(\d+)',row['name'])
        if m and row.get('ids',{}).get('id'):
            record.setdefault('existing_post_creative_ids',{})[m[1]+'.'+m[2]]=str(row['ids']['id'])
    for target,prefix,key in [('campaign_ids','campaign_copy','copied_campaign_id'),('campaign_ids','campaign_create','id'),('adset_ids','adset_copy','copied_adset_id'),('adset_ids','adset_create','id')]:
        found={int(m[1]):str(ids[key]) for name,ids in slots.items() if (m:=re.fullmatch(prefix+r'_(\d+)',name)) and ids.get(key)}
        count=len(record.get('idempotency_keys') or [])
        if count and len(found)==count and set(found)==set(range(1,count+1)):
            record[target]=[found[i] for i in range(1,count+1)]
    save()

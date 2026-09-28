#!/usr/bin/env python3
import json, os, re, subprocess, time
from datetime import date, timedelta
import requests

TARGET='2026-09-20'
vault=os.environ.get('OP_DEFAULT_VAULT','MGS Conteúdo')
proc=subprocess.run(['op','item','get','SMS Funnel Dashboard','--vault',vault,'--format','json','--reveal'],text=True,capture_output=True,timeout=60)
if proc.returncode:
    raise SystemExit('credential_unavailable')
fields={str(x.get('label') or x.get('id') or '').lower():str(x.get('value') or '') for x in json.loads(proc.stdout).get('fields',[])}
email=fields.get('username') or fields.get('email') or ''
password=fields.get('password') or ''
if not email or not password:
    raise SystemExit('credential_incomplete')
s=requests.Session(); s.headers.update({'User-Agent':'MGS-Zeus-SMSFunnel-ReadOnly/1.0'})
r=s.post('https://web2.smsfunnel.com.br/api/login',json={'email':email,'password':password,'utm':''},timeout=30)
r.raise_for_status(); token=str((r.json() or {}).get('access_token') or '')
if not token: raise SystemExit('token_missing')
h={'Authorization':f'Bearer {token}'}
common={'global':'false','t':str(int(time.time()*1000))}
all_campaigns=[]
for page in range(1,20):
    rr=s.get('https://web2.smsfunnel.com.br/api/campaigns',params={'page':page,'per_page':100,**common},headers=h,timeout=60)
    rr.raise_for_status(); payload=rr.json() or {}
    rows=payload.get('data') if isinstance(payload,dict) else payload
    rows=rows if isinstance(rows,list) else []
    all_campaigns.extend(rows)
    if len(rows)<100: break
selected=[]
for c in all_campaigns:
    name=str(c.get('name') or '')
    up=name.upper()
    if 'CREDITOPARAVEICULO' not in up or 'QUIZ' not in up:
        continue
    cid=str(c.get('id') or '')
    rr=s.get(f'https://web2.smsfunnel.com.br/api/analytics/funnel-performance/{cid}/sequences',params={'start_date':TARGET,'end_date':TARGET,**common},headers=h,timeout=60)
    status=rr.status_code
    data=[]
    if status==200:
        body=rr.json() or {}
        data=body.get('data') if isinstance(body,dict) else body
        data=data if isinstance(data,list) else []
    selected.append({
      'campaign_id':cid,'campaign_name':name,'active':c.get('active'),'lead_list_id':c.get('lead_list_id'),
      'http':status,'sequence_row_count':len(data),'sequence_keys':sorted({k for row in data for k in row}),
      'sequences':[{k:row.get(k) for k in ['id','sequence_id','name','sms_sent','cost','sequence_type','interval','interval_type_id'] if k in row} for row in data]
    })
print(json.dumps({'target_date':TARGET,'campaigns_seen':len(all_campaigns),'selected_count':len(selected),'selected':selected},ensure_ascii=False,indent=2))

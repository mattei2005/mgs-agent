#!/usr/bin/env python3
"""Fetch Meta campaigns read-only for Ares. Never prints tokens."""
from __future__ import annotations
import argparse, datetime as dt, json, importlib.util, urllib.parse
from pathlib import Path
spec=importlib.util.spec_from_file_location('common','/root/mgs-agent/scripts/ares-meta-common.py')
common=importlib.util.module_from_spec(spec); spec.loader.exec_module(common)
BASE=Path('/root/mgs-agent/data/ares/meta-ads')

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--account-id', required=True)
    ap.add_argument('--item', required=True, help='Exact 1Password item name for this ad account')
    ap.add_argument('--limit', type=int, default=100)
    ap.add_argument('--out')
    args=ap.parse_args()
    token, field=common.get_token_from_1password(args.item)
    fields='id,name,status,effective_status,created_time,updated_time,objective,daily_budget,lifetime_budget,buying_type,special_ad_categories'
    status,payload,headers=common.graph_get(f'act_{args.account_id}/campaigns', token, {'fields':fields,'limit':args.limit})
    result={'ok':200 <= status < 300,'http_status':status,'account_id':args.account_id,'token_item':args.item,'token_field':field,'token_len':len(token),'fetched_at_utc':dt.datetime.now(dt.UTC).isoformat()}
    if result['ok']:
        campaigns=payload.get('data',[])
        result['count']=len(campaigns)
        result['campaigns']=campaigns
        result['paging_present']='paging' in payload
    else:
        result['error']=common.safe_meta_error(payload)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    summary=dict(result)
    if 'campaigns' in summary:
        summary['campaigns']=[{k:c.get(k) for k in ['id','name','status','effective_status','created_time','daily_budget'] if k in c} for c in result['campaigns'][:20]]
    print(json.dumps(summary,indent=2,ensure_ascii=False))
    return 0 if result['ok'] else 2
if __name__ == '__main__':
    raise SystemExit(main())

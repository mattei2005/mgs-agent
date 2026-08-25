#!/usr/bin/env python3
"""Read-only token/account smoke check. Does not print access token."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
import importlib.util
spec=importlib.util.spec_from_file_location('common','/root/mgs-agent/scripts/ares-meta-common.py')
common=importlib.util.module_from_spec(spec); spec.loader.exec_module(common)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--account-id', required=True)
    ap.add_argument('--item', required=True, help='Exact 1Password item name for this ad account')
    ap.add_argument('--out')
    args=ap.parse_args()
    token, field = common.get_token_from_1password(args.item)
    fields='name,account_id,account_status,currency,timezone_name,timezone_offset_hours_utc,amount_spent,balance,spend_cap,business_name'
    status,payload,headers=common.graph_get(f'act_{args.account_id}', token, {'fields':fields})
    result={'ok':200 <= status < 300,'http_status':status,'account_id':args.account_id,'token_item':args.item,'token_field':field,'token_len':len(token)}
    if result['ok']:
        result['account']={k:payload.get(k) for k in ['name','account_id','account_status','currency','timezone_name','timezone_offset_hours_utc','amount_spent','balance','spend_cap','business_name'] if k in payload}
    else:
        result['error']=common.safe_meta_error(payload)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps(result,indent=2,ensure_ascii=False))
    return 0 if result['ok'] else 2
if __name__ == '__main__':
    raise SystemExit(main())

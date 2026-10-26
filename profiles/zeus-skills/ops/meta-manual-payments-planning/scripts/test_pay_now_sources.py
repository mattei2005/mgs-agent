#!/usr/bin/env python3
"""Regression checks against REAL pixel-verified run evidence, no provider writes."""
import argparse, copy, importlib.util, json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--run-dir',required=True);a=p.parse_args();b=Path(a.run_dir)
s=importlib.util.spec_from_file_location('publisher',Path(__file__).with_name('publish_pay_now.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
c=json.loads(Path('/root/mgs-agent/data/meta-manual-payments/digital-trust-workbook-contract.json').read_text());v=json.loads((b/'visual-verification.json').read_text());ts=json.loads((b/'targets.json').read_text());passed=0;positive=0
for t in ts:
 if t['account_id']not in v['verified_account_ids']:continue
 rp=b/(t['account_id']+'-receipt.json');r=json.loads(rp.read_text());e=m.verified_entry(r,t,c,v,rp);assert e['account_id']==t['account_id'];passed+=1;positive+=1
 if r['status']!='current_balance_pay_now_unavailable':continue
 for kind in ['missing_proof','wrong_balance','wrong_identity','has_actionable_button']:
  rr=copy.deepcopy(r);vv=copy.deepcopy(v);aid=t['account_id']
  if kind=='missing_proof':vv['disabled_balance_checks'].pop(aid)
  if kind=='wrong_balance':vv['disabled_balance_checks'][aid]['balance_usd']='999999999'
  if kind=='wrong_identity':rr['account_id']='123'
  if kind=='has_actionable_button':rr['pay_now_ax_button_count']=1
  try:m.verified_entry(rr,t,c,vv,rp)
  except AssertionError:passed+=1
  else:raise AssertionError('fail_closed_test_failed_'+kind)
assert positive,'no_real_receipts_tested'
print(json.dumps({'status':'pass','real_receipts':positive,'checks_passed':passed,'google_writes':0,'meta_writes':0,'payments':0}))

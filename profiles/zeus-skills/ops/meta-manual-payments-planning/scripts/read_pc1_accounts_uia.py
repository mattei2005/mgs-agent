#!/usr/bin/env python3
"""Scoped read-only Accounts balance collector via native UIA ValuePattern.
No navigation, synthetic keyboard, new tabs, billing actions or Google writes.
Requires approved Rodolfo Chrome Accounts already open; restores blank Search.
"""
import argparse,json,os,re,shutil,subprocess,sys,time
from pathlib import Path
from datetime import datetime
R=Path(shutil.which('hermes')).resolve().parents[2];sys.path.insert(0,str(R))
from pm.environments import activate_dependencies
activate_dependencies(R)
os.environ['HERMES_CUA_DRIVER_CMD']='/root/mgs-agent/scripts/mgs-pc1-cua-driver-ssh.sh'
from tools.computer_use_tool import handle_computer_use,release_computer_use_session
from tools.computer_use import cua_backend
cua_backend._cua_configured_ax_max_elements=lambda:2400;cua_backend._computer_use_max_image_dimension=lambda:3200
p=argparse.ArgumentParser();p.add_argument('--run-dir',required=True);p.add_argument('--account-ids',nargs='+',required=True);p.add_argument('--restore-blank-confirmed',action='store_true',required=True);a=p.parse_args();B=Path(a.run_dir);H=Path('/root/mgs-agent/data/meta-manual-payments');C=json.loads((H/'digital-trust-workbook-contract.json').read_text());T={t['account_id']:t for t in json.loads((B/'targets.json').read_text())};assert len(a.account_ids)<=6 and len(set(a.account_ids))==len(a.account_ids);assert set(a.account_ids)<=set(C['pay_now_account_ids'])<=set(T);assert C['business_id']=='155263197283282' and C['h_source']=='accounts_list_outstanding_balance' and not C['payments_authorized'];assert all(not(B/(i+'-receipt.json')).exists() for i in a.account_ids)
s=os.environ['HERMES_SESSION_ID'];lock='/root/mgs-agent/scripts/mgs-pc1-computer-use-lock.py';r=subprocess.run([sys.executable,lock,'acquire','--agent','zeus','--session-id',s,'--thread-id',C['thread_id'],'--ttl','900'],capture_output=True,text=True);assert r.returncode==0,'pc1_lease_busy';es=[];text='';last={};changed=False;gate_open=False;completed=[]
def call(x):
 d=handle_computer_use(x,session_id=s);return json.loads(d) if isinstance(d,str) else d
def cap():
 global es,text,last,gate_open
 # A filter can rerender the AX root briefly. Wait read-only; never input on
 # an unidentified frame and never wait through a real provider/native gate.
 for attempt in range(4):
  last=call({'action':'capture','mode':'ax','pid':bind['pid'],'window_id':bind['window_id']});assert not last.get('error');full=json.loads(Path(last['elements_file']).read_text()) if last.get('elements_file') else last;es=full.get('elements',[]);text='\n'.join(e.get('label','') for e in es);gate_open=bool(re.search(r'Windows Security|passkey for Facebook|security/twofactor/reauth|Confirm it.s you|temporarily blocked|going too fast|Log in to Facebook',text,re.I));assert not gate_open,'native_or_provider_gate'
  if 'Accounts' in text and 'Rodolfo' in text:return full
  if attempt<3:time.sleep(1)
 raise AssertionError('wrong_surface')
def search():
 ss=[e for e in es if e.get('role') in ['Edit','TextField','SearchBox'] and e.get('label')=='Search'];assert len(ss)==1,'search_not_unique';return ss[0]
def setquery(q):
 cap()
 # Accounts may turn this operation's query into a Name-contains chip.
 # Restore only that exact known query under the caller's blank-baseline gate.
 chips=[e for e in es if e.get('role')=='Button' and e.get('label','').startswith('Clear Name contains ')]
 if chips:
  assert len(chips)==1 and chips[0]['label'][len('Clear Name contains '):] in {T[aid]['name'] for aid in a.account_ids},'unknown_filter_do_not_clear'
  r=call({'action':'click','element':chips[0]['index']});assert r.get('ok') is True and not r.get('code') and not r.get('error'),'filter_clear_failed';time.sleep(1);cap()
 r=call({'action':'set_value','element':search()['index'],'value':q});assert r.get('ok') is True and not r.get('code') and not r.get('error'),'uia_set_failed';return r
try:
 ws=json.loads(subprocess.run(['/root/mgs-agent/scripts/mgs-pc1-cua-driver-ssh.sh','call','list_windows'],capture_output=True,text=True,timeout=50).stdout)['windows'];assert not any(w.get('app_name')=='CredentialUIBroker.exe' for w in ws),'native_auth_dialog_present';bind=json.loads((H/'pc1-browser-surface.json').read_text());assert any(w.get('pid')==bind['pid'] and w.get('window_id')==bind['window_id'] and w.get('app_name')=='chrome.exe' and not w.get('minimized') for w in ws),'approved_chrome_not_live';cap()
 for aid in a.account_ids:
  t=T[aid];ar=setquery(t['name']);changed=True;deadline=time.monotonic()+35
  while True:
   full=cap();matches=[e for e in es if e.get('role')=='DataItem' and e.get('label','').startswith(t['name']+' ID: '+aid+' ') and re.search(r'\$[0-9,]+\.\d{2}',e.get('label',''))]
   if len(matches)==1:time.sleep(1);full=cap();break
   assert time.monotonic()<deadline,'searched_row_not_ready_'+aid;time.sleep(1)
  matches=[e for e in es if e.get('role')=='DataItem' and e.get('label','').startswith(t['name']+' ID: '+aid+' ') and re.search(r'\$[0-9,]+\.\d{2}',e.get('label',''))];assert len(matches)==1;label=matches[0]['label'];(B/(aid+'.txt')).write_text(text);(B/(aid+'-elements.json')).write_text(json.dumps(full,ensure_ascii=False));v=call({'action':'capture','mode':'vision','pid':bind['pid'],'window_id':bind['window_id']});assert v.get('screenshot_path');pic=B/(aid+'.png');shutil.copy2(v['screenshot_path'],pic);row={'account_id':aid,'name':t['name'],'business_id':C['business_id'],'read_at':datetime.now().astimezone().isoformat(),'screenshot':str(pic),'text_path':str(B/(aid+'.txt')),'ui_surface':'Billing & payments > Accounts > Ad accounts; UIA ValuePattern Search exact row','row_label':label,'amount':re.search(r'\$([0-9,]+\.\d{2})',label)[1].replace(',',''),'source':'accounts_list_outstanding_balance','status':'accounts_list_outstanding_balance_read','input_route':'uia_valuepattern_verified_by_filtered_result','payments_executed':0,'meta_writes':0,'sheets_writes':0};rp=B/(aid+'-receipt.json');rp.write_text(json.dumps(row,ensure_ascii=False,indent=2));rp.chmod(0o600);completed.append(aid);print(json.dumps({k:row[k] for k in ['account_id','name','amount','read_at','screenshot']},ensure_ascii=False),flush=True)
 print(json.dumps({'status':'uia_accounts_batch_captured','accounts':len(completed),'run_dir':str(B),'tabs_opened':0,'tabs_closed':0,'meta_writes':0,'sheet_writes':0}),flush=True)
finally:
 try:
  if changed and not gate_open:setquery('');cap()
 finally:
  release_computer_use_session(s);subprocess.run([sys.executable,lock,'release','--agent','zeus','--session-id',s],capture_output=True,text=True)

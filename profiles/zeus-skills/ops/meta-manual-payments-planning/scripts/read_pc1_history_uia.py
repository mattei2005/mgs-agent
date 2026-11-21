#!/usr/bin/env python3
"""Read approved Meta card history via native UIA and a scoped owned tab.
Requires the caller's original Chrome tab baseline. Creates only a verified
New Tab, fills the native address bar using UIA, and navigates with an explicit
foreground Enter. Reads history and closes only attributable appended tabs,
requiring original-tab prefix parity. Never pays or writes Sheets.
"""
import argparse,os,sys,json,subprocess,time,re,shutil
from pathlib import Path
from datetime import datetime
R=Path(shutil.which('hermes')).resolve().parents[2];sys.path.insert(0,str(R))
from pm.environments import activate_dependencies
activate_dependencies(R)
os.environ['HERMES_CUA_DRIVER_CMD']='/root/mgs-agent/scripts/mgs-pc1-cua-driver-ssh.sh'
from tools.computer_use_tool import handle_computer_use,release_computer_use_session
from tools.computer_use import cua_backend
cua_backend._cua_configured_ax_max_elements=lambda:2400;cua_backend._computer_use_max_image_dimension=lambda:3200
p=argparse.ArgumentParser();p.add_argument('--account-id',required=True);p.add_argument('--run-dir',required=True);p.add_argument('--owned-tab-proof',required=True);a=p.parse_args();C=json.loads(Path('/root/mgs-agent/data/meta-manual-payments/digital-trust-workbook-contract.json').read_text());assert a.account_id in C['account_ids'] and C['business_id']=='155263197283282' and not C['payments_authorized'];assert Path(a.owned_tab_proof).is_file();B=Path(a.run_dir);B.mkdir(parents=True,exist_ok=True);assert not (B/(a.account_id+'-receipt.json')).exists();bind=json.loads(Path('/root/mgs-agent/data/meta-manual-payments/pc1-browser-surface.json').read_text());s=os.environ['HERMES_SESSION_ID'];lock='/root/mgs-agent/scripts/mgs-pc1-computer-use-lock.py';r=subprocess.run([sys.executable,lock,'acquire','--agent','zeus','--session-id',s,'--thread-id',C['thread_id'],'--ttl','600'],capture_output=True,text=True);assert r.returncode==0,'lease_busy'
def call(a):
 d=handle_computer_use(a,session_id=s);return json.loads(d) if isinstance(d,str) else d
def cap():
 global capture_size,gate_seen
 d=call({'action':'capture','mode':'ax','pid':bind['pid'],'window_id':bind['window_id']});capture_size=(d.get('width'),d.get('height'));assert not d.get('error');full=json.loads(Path(d['elements_file']).read_text()) if d.get('elements_file') else d;es=full.get('elements',[]);text='\n'.join(e.get('label','') for e in es if e.get('role')!='TabItem');gate_seen=bool(re.search(r'Windows Security|passkey for Facebook|security/twofactor/reauth|Confirm it.s you|temporarily blocked|going too fast|Log in to Facebook',text,re.I));assert not gate_seen,'native_or_provider_gate';return full,es,text
def action(x):
 r=call(x);assert r.get('ok') is True and not r.get('code') and not r.get('error');return r
created=False;initial_tabs=[];gate_seen=False
def browser_tabs(es):return [e for e in es if e.get('role')=='TabItem' and e.get('bounds',[0,99999])[1]<50]
try:
 ws=json.loads(subprocess.run(['/root/mgs-agent/scripts/mgs-pc1-cua-driver-ssh.sh','call','list_windows'],capture_output=True,text=True,timeout=45).stdout)['windows'];assert not any(w.get('app_name')=='CredentialUIBroker.exe' for w in ws),'native_auth_dialog_present'
 full,es,text=cap();initial_tabs=browser_tabs(es);(B/(a.account_id+'-tabs-before.json')).write_text(json.dumps(full,ensure_ascii=False));newbuttons=[e for e in es if e.get('role')=='Button' and e.get('label')=='New Tab'];assert len(newbuttons)==1;action({'action':'click','element':newbuttons[0]['index']});time.sleep(1);full,es,text=cap();assert len(browser_tabs(es))==len(initial_tabs)+1 and any(e.get('label','').startswith('New Tab') for e in browser_tabs(es)),'new_tab_not_verified';created=True;fields=[e for e in es if e.get('role')=='Edit' and e.get('label')=='Address and search bar'];assert len(fields)==1
 url='https://business.facebook.com/latest/billing_hub/accounts/details/?business_id=155263197283282&asset_id='+a.account_id+'&payment_account_id='+a.account_id;action({'action':'set_value','element':fields[0]['index'],'value':url});time.sleep(1);full,es,text=cap();ss=[e for e in es if e.get('role')=='ListItem' and e.get('label','').startswith(url+',')];assert len(ss)==1,'direct_url_suggestion_not_unique';r=action({'action':'key','keys':'return','delivery_mode':'foreground','bring_to_front':True});(B/(a.account_id+'-navigate.json')).write_text(json.dumps(r,ensure_ascii=False));deadline=time.monotonic()+65
 while True:
  full,es,text=cap()
  if '\nDate\nPayment method\nAmount\nStatus\n' in text or 'No payment activity' in text or 'You have no recent spending.' in text or 'View transaction history' in text:break
  assert time.monotonic()<deadline,'billing_page_not_ready';time.sleep(2)
 time.sleep(2);full,es,text=cap()
 for attempt in range(3):
  dates=[e for e in es if e.get('role')=='Text' and e.get('label')=='Date'];
  if not dates or 150<=dates[0].get('bounds',[0,99999])[1]<=1000:break
  action({'action':'scroll','coordinate':[round(capture_size[0]*.7),round(capture_size[1]*.7)],'direction':'down','amount':5,'delivery_mode':'foreground','bring_to_front':True});time.sleep(1);full,es,text=cap()
 tp=B/(a.account_id+'.txt');tp.write_text(text);(B/(a.account_id+'-elements.json')).write_text(json.dumps(full,ensure_ascii=False));v=call({'action':'capture','mode':'vision','pid':bind['pid'],'window_id':bind['window_id']});pic=B/(a.account_id+'.png');shutil.copy2(v['screenshot_path'],pic);start=text.find('\nDate\nPayment method\nAmount\nStatus\n');end=text.find('\nView all activity',start);excerpt=text[start:end if end>=0 else start+3000] if start>=0 else ''
 rec={'status':'read','account_requested':a.account_id,'read_at':datetime.now().astimezone().isoformat(),'text_path':str(tp),'elements_path':str(B/(a.account_id+'-elements.json')),'screenshot':str(pic),'no_recent_spending_message':'You have no recent spending.' in text,'headings':[e.get('label') for e in es if e.get('role') in ['Heading','Document']],'billing_excerpt':excerpt,'input_route':'native_UIA_NewTab_ValuePattern_foreground_enter','owned_tab_proof':a.owned_tab_proof};rp=B/(a.account_id+'-receipt.json');rp.write_text(json.dumps(rec,ensure_ascii=False,indent=2));rp.chmod(0o600);print(json.dumps({**rec,'receipt_path':str(rp)},ensure_ascii=False))
finally:
 try:
  if created and not gate_seen:
   full,es,text=cap();tabs=browser_tabs(es);assert 1<=len(tabs)-len(initial_tabs)<=2,'tab_cleanup_ambiguous_count'
   def base_label(e):return e.get('label','').split(' - Memory usage')[0]
   assert [base_label(t) for t in tabs[:len(initial_tabs)]]==[base_label(t) for t in initial_tabs],'preexisting_tab_prefix_changed'
   assert all(t.get('label','').startswith(('Meta Business Suite','New Tab')) for t in tabs[len(initial_tabs):]),'new_tab_identity_ambiguous'
   while len(tabs)>len(initial_tabs):
    owned=max(tabs,key=lambda e:e['bounds'][0]);x,y,w,h=owned['bounds'];cl=[e for e in es if e.get('role')=='Button' and e.get('label')=='Close' and x<=e.get('bounds',[99999])[0]<x+w and e.get('bounds',[0,99999])[1]<50];assert len(cl)==1,'owned_close_not_unique';oldcount=len(tabs);action({'action':'click','element':cl[0]['index']});time.sleep(1);full,es,text=cap();tabs=browser_tabs(es);assert len(tabs)==oldcount-1,'tab_close_not_verified'
   (B/(a.account_id+'-tabs-after.json')).write_text(json.dumps(full,ensure_ascii=False))
 finally:
  release_computer_use_session(s);subprocess.run([sys.executable,lock,'release','--agent','zeus','--session-id',s],capture_output=True,text=True)

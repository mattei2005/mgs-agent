#!/usr/bin/env python3
"""Scoped PC1 native UI adapter for the approved Digital Trust batch.
No credentials, API/session export, billing, or person assignments.
The caller owns the batch run lock; this adapter owns the shared PC1 lease.
"""
from __future__ import annotations
import argparse, datetime as dt, importlib.util, json, os, re, subprocess, sys, time, uuid
from pathlib import Path
ROOT=Path('/root/mgs-agent')
STATE=ROOT/'data/meta-digital-trust-40-20261007-state.json'
LEASE=ROOT/'scripts/mgs-pc1-computer-use-lock.py'
URL='https://business.facebook.com/latest/settings/ad_accounts?business_id=155263197283282'
RUNTIME=Path('/root/.hermes/hermes-agent-port-main-46904a3b-mgs')
SESSION=os.environ.get('MGS_PC1_SESSION') or 'pc1-native-'+uuid.uuid4().hex
mutation=False
handler=None
release=None
pid=None
wid=None
last_capture={}
intent_path=ROOT/'data/meta-digital-trust-40-20261007-pc1-intent.json'

def atomic(path,data):
    tmp=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    fd=os.open(tmp,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    with os.fdopen(fd,'w') as f:
        json.dump(data,f,ensure_ascii=False,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
    os.replace(tmp,path)

def call(a):
    if handler is None:raise RuntimeError('native_handler_not_initialized')
    d=handler(a,session_id=SESSION)
    d=json.loads(d) if isinstance(d,str) else d
    if not isinstance(d,dict):raise RuntimeError('invalid_cua_result')
    return d

def cap():
    global last_capture
    d=call({'action':'capture','mode':'som','pid':pid,'window_id':wid})
    if d.get('error') or not d.get('width') or not d.get('height'):raise RuntimeError('native_capture_failed')
    full=json.loads(Path(d['elements_file']).read_text()) if d.get('elements_file') else d
    last_capture=d
    es=full.get('elements',[])
    labels='\n'.join(e.get('label','') for e in es if e.get('role')!='TabItem')
    if re.search(r'new device|additional checks|2FA Entry|Confirm it.s you|Try another way|Log into Facebook|Log in to Facebook|Enter your password',labels,re.I):raise RuntimeError('security_or_auth_gate')
    return es

def text(es):return '\n'.join(e.get('label','') for e in es if e.get('role')!='TabItem')
def match(es,label,role):
    v=[e for e in es if e.get('role')==role and e.get('label')==label]
    if len(v)!=1:raise RuntimeError('control_missing_or_nonunique:'+role+':'+label[:60])
    return v[0]

def act(a):
    d=call(a)
    if d.get('code')=='background_unavailable':
        cap();a=dict(a,delivery_mode='foreground');d=call(a)
    if d.get('error') or d.get('code') or d.get('effect')=='suspected_noop':raise RuntimeError('native_input_refused')
    # Never repeat an unverifiable input. A new capture grounds the next action.
    time.sleep(.5);cap()
    return d

def click(label,role='Button'):
    e=match(cap(),label,role)
    return act({'action':'click','element':e['index']})
def type_field(label,value,role='Edit'):
    if value not in {'001','America/Los_Angeles'}:raise RuntimeError('nonsecret_input_allowlist')
    click(label,role);act({'action':'type','text':value})
def navigate():
    cap();act({'action':'key','keys':'ctrl+l'});act({'action':'type','text':URL});act({'action':'key','keys':'return'})
    deadline=time.monotonic()+35
    while True:
        es=cap();t=text(es)
        if any(e.get('label')=='Add' and e.get('role')=='Button' for e in es):break
        if time.monotonic()>deadline:raise RuntimeError('page_render_unavailable')
        time.sleep(2)
    if 'Owned by: Digital Trust' not in t or 'Rodolfo Mattei (You)' not in t:raise RuntimeError('business_or_actor_readback_missing')
    return es

def preflight():
    navigate();click('Add');click('Create a new ad account','DataItem')
    es=cap();t=text(es)
    if 'maximum number of ad accounts' in t.lower():raise RuntimeError('maximum_account_gate')
    match(es,'Ad account name','Edit')
    if not any(e['role']=='ComboBox' and e['label'].startswith('Time zone ') for e in es):raise RuntimeError('details_form_mismatch')
    click('Cancel')
    return {'kind':'preflight_ok','business_id':'155263197283282','business_name':'Digital Trust','create_form':True,'maximum_gate':False,'backend':'pc1_native','meta_writes':0}

def create(s,from_confirm=False):
    global mutation
    if intent_path.exists():
        old=json.loads(intent_path.read_text())
        if old.get('status')=='submitted_unconfirmed':raise RuntimeError('prior_native_intent_unconfirmed')
        if old.get('status')=='confirmed_popup' and old.get('seq')==len(s['completed'])+1:
            return old['result']
        if int(old.get('seq',0))>len(s['completed'])+1:raise RuntimeError('native_intent_sequence_conflict')
    if not from_confirm:
        navigate();click('Add');click('Create a new ad account','DataItem')
        type_field('Ad account name','001')
        es=cap();z=[e for e in es if e['role']=='ComboBox' and e['label'].startswith('Time zone ')]
        if len(z)!=1:raise RuntimeError('timezone_combo_mismatch')
        click(z[0]['label'],'ComboBox');type_field('Time zone','America/Los_Angeles','ComboBox')
        es=cap();options=[e for e in es if e['role']=='ListItem' and e['label'].endswith(' America/Los Angeles')]
        if len(options)!=1:raise RuntimeError('timezone_option_missing')
        click(options[0]['label'],'ListItem')
        t=text(cap())
        if 'America/Los Angeles' not in t or 'Currency USD — US Dollars' not in t:raise RuntimeError('details_readback_mismatch')
        click('Next');match(cap(),'My business','RadioButton');click('My business','RadioButton');click('Next')
    es=cap();t=text(es)
    if 'The ad account will be created and added to the Digital Trust business portfolio.' not in t:raise RuntimeError('confirmation_business_mismatch')
    if not any(e['label']=='001' and e['role']=='Text' for e in es):raise RuntimeError('confirmation_name_missing')
    terms=[e for e in es if e['role']=='CheckBox']
    if len(terms)!=1 or 'Meta Commercial Terms' not in t:raise RuntimeError('terms_scope_mismatch')
    click(terms[0]['label'],'CheckBox')
    match(cap(),'Create ad account','Button')
    # Intent reaches durable storage BEFORE the only non-idempotent action.
    intent={'request_id':s['request_id'],'seq':len(s['completed'])+1,'status':'submitted_unconfirmed','at':dt.datetime.now(dt.timezone.utc).isoformat(),'backend':'pc1_native','business_id':s['business_id'],'defaults':s['account_defaults']}
    atomic(intent_path,intent);mutation=True
    click('Create ad account')
    deadline=time.monotonic()+65
    while True:
        es=cap();t=text(es)
        if re.search(r'Ad account created successfully|Ad account created',t):break
        if re.search(r'Unable to add ad account|maximum number of ad accounts|Network request timed out|Error performing query|unusual activity|security check',t,re.I):raise RuntimeError('meta_error_popup')
        if time.monotonic()>deadline:raise RuntimeError('creation_outcome_not_confirmed')
        time.sleep(2)
    evidence=last_capture.get('screenshot_path')
    result={'kind':'created_confirmation','confirmation':'meta_success_popup','backend':'pc1_native','clicked_at':intent['at'],'evidence_screenshot':evidence,'account':{'id':None,'selected_asset_id':None,'owner':'Digital Trust','owner_verified':False,'assigned_people':None,'rodolfo_full_access':None,'people_readback':'unverified','name':'001','timezone':'America/Los_Angeles','currency':'USD','usage':'My business','payment_method_added':False}}
    # Preserve popup proof before dismissal. A crash afterward must never replay.
    intent.update(status='confirmed_popup',result=result);atomic(intent_path,intent)
    try:
        click('Done');time.sleep(3);es=cap();t=text(es)
        ids=[]
        for i,e in enumerate(es):
            if e['label'].strip()=='ID:' and i+1<len(es) and es[i+1]['label'].isdigit():ids.append(es[i+1]['label'])
        known=set(s.get('preexisting_ids',[]))|{e.get('id') for e in s['completed']}|{e.get('id') for e in s.get('excluded_live_accounts',[])}
        if len(set(ids))==1 and ids[0] not in known and 'Owned by: Digital Trust' in t:
            a=result['account'];a.update(id=ids[0],owner_verified=True)
            if 'Rodolfo Mattei (You)' in t and 'Full access' in t:a.update(rodolfo_full_access=True,people_readback='visible_person_and_access')
    except Exception:result['validation_note']='popup_confirmed_details_unverified'
    intent['result']=result;atomic(intent_path,intent)
    return result

def main():
    global handler,release,pid,wid
    p=argparse.ArgumentParser();p.add_argument('--preflight',action='store_true');p.add_argument('--from-confirm',action='store_true');a=p.parse_args()
    s=json.loads(STATE.read_text())
    if s['request_id']!='meta-digital-trust-40-1557475850310393879' or s['business_id']!='155263197283282' or s['target']!=40:raise RuntimeError('contract_identity_mismatch')
    if s['account_defaults']!={'name':'001','timezone':'America/Los_Angeles','currency':'USD','usage':'My business'}:raise RuntimeError('contract_defaults_mismatch')
    if not a.preflight and (len(s['completed'])>=40 or s.get('status') not in {'scheduled','in_progress','retry_pending'}):return {'kind':'blocked','reason':'checkpoint_not_executable'}
    l=subprocess.run([sys.executable,str(LEASE),'acquire','--agent','zeus','--session-id',SESSION,'--thread-id','1544113212075548683','--ttl','420'],capture_output=True,text=True)
    if l.returncode:return {'kind':'deferred','reason':'pc1_lease_busy','side_effect':'none'}
    try:
        sys.path.insert(0,str(RUNTIME))
        from pm.environments import activate_dependencies
        activate_dependencies(RUNTIME)
        from tools.computer_use_tool import handle_computer_use,release_computer_use_session
        from tools.computer_use import cua_backend
        cua_backend._cua_configured_ax_max_elements=lambda:1600
        handler=handle_computer_use;release=release_computer_use_session
        d=call({'action':'list_windows'});ws=d.get('windows',[])
        matches=[w for w in ws if 'chrome' in str(w.get('app_name','')).lower() and 'Meta Business Suite' in str(w.get('title','')) and not w.get('minimized')]
        if len(matches)!=1:raise RuntimeError('visible_meta_chrome_nonunique')
        pid=matches[0]['pid'];wid=matches[0]['window_id']
        return preflight() if a.preflight else create(s,a.from_confirm)
    except Exception as e:
        return {'kind':'blocked' if mutation else 'failed_prewrite_or_validation','reason':str(e)[:180],'side_effect':'unknown' if mutation else 'none'}
    finally:
        if release:release(SESSION)
        subprocess.run([sys.executable,str(LEASE),'release','--agent','zeus','--session-id',SESSION],capture_output=True,text=True)
if __name__=='__main__':
    try:r=main()
    except Exception as e:r={'kind':'failed_prewrite_or_validation','reason':str(e)[:180],'side_effect':'none'}
    print(json.dumps(r,ensure_ascii=False))

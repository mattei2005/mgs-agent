#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fcntl
import importlib.util
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

BASE=Path('/root/mgs-agent'); PROFILE=Path('/root/.hermes/profiles/ares')
if str(BASE/'scripts') not in sys.path: sys.path.insert(0,str(BASE/'scripts'))
from ares_campaign_v3.daily_cpv import ACCOUNT_ID, SP, DailyBlocked, DailyPaths, LiveDailyBackend, active_budget_minor, atomic_json, stock_counts, update_inventory_assignments
from ares_campaign_v3.media_registry import MediaRegistry

CAMPAIGN_ID='120250888588510632'; ADSET_ID='120250888589000632'; THREAD='discord:thread:1540939724636819507'
CHECKPOINT=BASE/'data/ares/meta-ads/engine-v3/state/cpv-c20-advideos-canary-recovery-20260823.json'
SEALED=PROFILE/'work/creditoparaveiculo-c20-advideos-canary/manifest/sealed.json'
AUDIT=BASE/'data/ares/meta-ads/engine-v3/audit/canary/cpv-c20-advideos-canary-finalize-20260823.json'
STATE=BASE/'data/ares/meta-ads/engine-v3/state/cpv-c20-advideos-canary-finalize-20260823.json'
LOCK=BASE/'data/ares/meta-ads/engine-v3/state/cpv-c20-advideos-canary-finalize-20260823.lock'
CANARY_MODULE=BASE/'scripts/ares-creditoparaveiculo-c20-advideo-canary.py'
TOKEN_ITEM='Token Meta API - 00 - ANUNCIANTE - Rafael Lucas Oliveira - CPV - G006'

def load_common():
 spec=importlib.util.spec_from_file_location('c20_finalize_common',BASE/'scripts/ares-meta-common.py')
 if not spec or not spec.loader: raise RuntimeError('cannot load Meta common')
 m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def load_canary():
 spec=importlib.util.spec_from_file_location('c20_finalize_canary',CANARY_MODULE)
 if not spec or not spec.loader: raise RuntimeError('cannot load C20 canary module')
 m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def inventory(path): return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]

def get(common,token,path,fields,stage):
 status,body,_=common.graph_get(path,token,{'fields':fields})
 if status!=200 or not isinstance(body,dict): raise DailyBlocked(stage,'direct GET failed',{'http':status,'error':common.safe_meta_error(body)})
 return body

def auth():
 op=json.loads(DailyPaths().operation.read_text()); a=op['daily_new_campaign_routine']['c20_advideo_canary_20260823']
 if a.get('status')!='authorized_corrective_recovery_existing_shell' or a.get('corrective_authorized_by')!='Rodolfo Mattei' or a.get('corrective_authorization_source')!=THREAD: raise DailyBlocked('authorization','C20 finalization authorization missing')
 return a

def readback(common,token,checkpoint,sealed):
 campaign=get(common,token,CAMPAIGN_ID,'id,name,status,effective_status,configured_status,daily_budget,bid_strategy,start_time,issues_info','campaign_get')
 adset=get(common,token,ADSET_ID,'id,name,status,effective_status,configured_status,start_time,issues_info','adset_get')
 desired=sealed['campaigns'][0]
 if campaign.get('name')!=desired['name'] or campaign.get('daily_budget')!='3000' or campaign.get('bid_strategy')!='LOWEST_COST_WITHOUT_CAP' or str(campaign.get('configured_status') or campaign.get('status')) not in {'PAUSED','ACTIVE'} or campaign.get('issues_info'): raise DailyBlocked('campaign_readback','C20 campaign mismatch',campaign)
 if adset.get('name')!=desired['adset_name'] or str(adset.get('configured_status') or adset.get('status'))!='ACTIVE' or adset.get('issues_info'): raise DailyBlocked('adset_readback','C20 adset mismatch',adset)
 ads=[]; creatives=[]; assignments=[]
 by_name={str(row['name']):row for row in desired['ads']}
 if set(checkpoint.get('ads') or {})!=set(by_name) or len(checkpoint.get('creatives') or {})!=3: raise DailyBlocked('checkpoint','C20 checkpoint does not contain exact 3x3 IDs')
 for ad_name,ad_id in sorted(checkpoint['ads'].items()):
  ad=get(common,token,str(ad_id),'id,name,status,effective_status,configured_status,adset_id,creative{id,name,status,effective_object_story_id},issues_info','ad_get')
  if ad.get('name')!=ad_name or str(ad.get('configured_status') or ad.get('status'))!='ACTIVE' or str(ad.get('adset_id'))!=ADSET_ID or ad.get('issues_info'): raise DailyBlocked('ad_readback','C20 ad mismatch',{'ad_id':ad_id})
  crref=ad.get('creative') or {}; cid=str(crref.get('id') or '')
  cr=get(common,token,cid,'id,name,status,effective_object_story_id,asset_feed_spec,object_story_spec','creative_get')
  raw=json.dumps(cr,ensure_ascii=False)
  if str(cr.get('status') or '').upper()!='ACTIVE' or not cr.get('effective_object_story_id') or 'b01fb13c20' not in raw or 'b01fb13c20g01' not in raw or 'b01fb13c08' in raw: raise DailyBlocked('creative_readback','C20 creative/status/UTM mismatch',{'creative_id':cid})
  media=by_name[ad_name]['media']; assignments.append({'asset_id':media['asset_id'],'campaign_id':CAMPAIGN_ID,'adset_id':ADSET_ID,'ad_id':str(ad_id),'creative_id':cid,'vertical_video_id':media['vertical_video_id'],'square_video_id':media['square_video_id']})
  ads.append({'ad_id':str(ad_id),'name':ad_name,'effective_status':ad.get('effective_status')}); creatives.append({'creative_id':cid,'story_id':cr.get('effective_object_story_id'),'utm_valid':True})
 return {'campaign':campaign,'adset':adset,'ads':ads,'creatives':creatives,'assignments':assignments}

def activate(common,token):
 before=get(common,token,CAMPAIGN_ID,'id,status,effective_status,configured_status,daily_budget','campaign_before_activate')
 if str(before.get('configured_status') or before.get('status'))!='ACTIVE':
  status,body,_=common.graph_post_once(CAMPAIGN_ID,token,{'status':'ACTIVE'})
  if status!=200 or body.get('success') is not True:
   after=get(common,token,CAMPAIGN_ID,'id,status,effective_status,configured_status,daily_budget','campaign_ambiguous_activate')
   if str(after.get('configured_status') or after.get('status'))!='ACTIVE': raise DailyBlocked('campaign_activate','activation failed',{'http':status,'error':common.safe_meta_error(body)})
 for attempt in range(1,13):
  after=get(common,token,CAMPAIGN_ID,'id,name,status,effective_status,configured_status,daily_budget,bid_strategy,issues_info','campaign_activate_readback')
  if str(after.get('configured_status') or after.get('status'))=='ACTIVE' and after.get('daily_budget')=='3000' and not after.get('issues_info'): return {'attempt':attempt,'body':after}
  if attempt<12: time.sleep(5)
 raise DailyBlocked('campaign_activate_readback','C20 activation did not converge')

def run(dry_run):
 auth(); cp=json.loads(CHECKPOINT.read_text()); sealed=json.loads(SEALED.read_text()); registry=MediaRegistry(DailyPaths().registry)
 for ad in sealed['campaigns'][0]['ads']:
  m=ad['media']; registry.require_ready(ACCOUNT_ID,m['asset_id'],m['checksum'])
 common=load_common(); token,field=common.get_token_from_1password(item_name=TOKEN_ITEM)
 rb=readback(common,token,cp,sealed)
 plan={'status':'DRY_RUN_OK' if dry_run else 'READY_TO_FINALIZE','campaign_id':CAMPAIGN_ID,'adset_id':ADSET_ID,'ads':rb['ads'],'creatives':rb['creatives'],'association_verified':True,'activation_budget_usd':30,'side_effects':{'writes':False} if dry_run else {'activation':'pending'}}
 if dry_run: atomic_json(AUDIT.with_name(AUDIT.stem+'-dry-run.json'),plan); return plan
 LOCK.parent.mkdir(parents=True,exist_ok=True)
 with LOCK.open('a+') as lock:
  fcntl.flock(lock.fileno(),fcntl.LOCK_EX)
  if STATE.exists() and json.loads(STATE.read_text()).get('status')=='COMPLETE': return {**json.loads(STATE.read_text()),'idempotent_readback':True}
  audit={'kind':'c20_finalize_existing','authorized_by':'Rodolfo Mattei','authorization_source':THREAD,'stage':'READBACK_VALIDATED','plan':plan,'readback':rb,'created_at_sp':datetime.now(SP).isoformat()}; atomic_json(AUDIT,audit)
  activation=activate(common,token); audit.update(stage='ACTIVE_READBACK_VALIDATED',activation=activation); atomic_json(AUDIT,audit)
  paths=DailyPaths(); backend=LiveDailyBackend(paths); drive=backend.drive_preflight()['drive']; inv=inventory(paths.inventory); by_asset={str(x.get('asset_id')):x for x in inv}; drive_rows={str(x.get('id')):x for x in drive.get('files') or []}; moves={}
  for a in rb['assignments']:
   item=by_asset[a['asset_id']]; moves[str(item['asset_drive_id'])]=backend.move_asset(drive_rows[str(item['asset_drive_id'])])
  update_inventory_assignments(paths.inventory,inv,rb['assignments'],moves,AUDIT); load_canary().update_local_states(CAMPAIGN_ID,AUDIT,datetime.now(SP))
  status,payload,_=common.graph_get(f'act_{ACCOUNT_ID}/campaigns',token,{'fields':'id,status,effective_status,configured_status,daily_budget','limit':500}); campaigns=payload.get('data') or [] if status==200 else []
  active=active_budget_minor(campaigns); cap=50000
  if active>cap: raise DailyBlocked('budget_cap','C20 final active budget exceeds cap',{'active_minor':active})
  backend2=LiveDailyBackend(paths); drive_after=backend2.drive_preflight()['drive']; stock=stock_counts(inventory(paths.inventory),drive_after)
  final={'status':'COMPLETE','campaign_id':CAMPAIGN_ID,'adset_id':ADSET_ID,'ad_ids':sorted(cp['ads'].values()),'creative_ids':sorted(cp['creatives'].values()),'campaign_readback':activation['body'],'ads':rb['ads'],'creatives':rb['creatives'],'assets_used':3,'budget_active_minor':active,'budget_remaining_minor':cap-active,'budget_cap_minor':cap,'stock_remaining':stock,'first_delivery_mode':'observe_only_no_auto_pause','completed_at_sp':datetime.now(SP).isoformat(),'audit':str(AUDIT)}
  atomic_json(STATE,final); audit.update(stage='COMPLETE',final=final,completed_at_sp=final['completed_at_sp']); atomic_json(AUDIT,audit)
  for p in [BASE/'data/ares/meta-ads/engine-v3/state/cpv-c20-advideos-canary-20260823.json',BASE/'data/ares/meta-ads/engine-v3/audit/canary/cpv-c20-advideos-canary-20260823.json']:
   d=json.loads(p.read_text()); d.update(status='COMPLETE_RECOVERED',final=final,recovery_audit=str(AUDIT)); atomic_json(p,d)
  fcntl.flock(lock.fileno(),fcntl.LOCK_UN); return final

def main():
 ap=argparse.ArgumentParser(); g=ap.add_mutually_exclusive_group(required=True); g.add_argument('--dry-run',action='store_true'); g.add_argument('--execute',action='store_true'); ap.add_argument('--confirm-execute',action='store_true'); a=ap.parse_args()
 if a.execute and not a.confirm_execute: raise SystemExit('--execute requires --confirm-execute')
 print(json.dumps(run(a.dry_run),ensure_ascii=False,indent=2)); return 0
if __name__=='__main__':
 try: raise SystemExit(main())
 except Exception as e: print(json.dumps({'status':'FAILED','error_type':type(e).__name__,'message':str(e)[:700]},ensure_ascii=False)); raise SystemExit(2)

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
from types import SimpleNamespace
from typing import Any

BASE = Path('/root/mgs-agent')
PROFILE = Path('/root/.hermes/profiles/ares')
if str(BASE / 'scripts') not in sys.path:
    sys.path.insert(0, str(BASE / 'scripts'))

from ares_campaign_v3.daily_cpv import (
    ACCOUNT_ACT, ACCOUNT_ID, SP, DailyBlocked, DailyPaths, LiveDailyBackend,
    active_budget_minor, atomic_json, utc_now,
)
from ares_campaign_v3.daily_cpv import stock_counts, update_inventory_assignments
from ares_campaign_v3.prevalidation import verify_prevalidation

# Avoid importing a private helper under an invalid expression above.
from ares_campaign_v3.daily_cpv import load_json

CAMPAIGN_ID = '120250888588510632'
ADSET_ID = '120250888589000632'
REQUEST_ID = 'cpv-c20-advideos-canary-20260823'
TOKEN_ITEM = 'Token Meta API - 00 - ANUNCIANTE - Rafael Lucas Oliveira - CPV - G006'
SEALED = PROFILE / 'work/creditoparaveiculo-c20-advideos-canary/manifest/sealed.json'
RECOVERY_STATE = BASE / 'data/ares/meta-ads/engine-v3/state/cpv-c20-advideos-canary-recovery-20260823.json'
RECOVERY_LOCK = BASE / 'data/ares/meta-ads/engine-v3/state/cpv-c20-advideos-canary-recovery-20260823.lock'
RECOVERY_AUDIT = BASE / 'data/ares/meta-ads/engine-v3/audit/canary/cpv-c20-advideos-canary-recovery-20260823.json'
CANARY_STATE = BASE / 'data/ares/meta-ads/engine-v3/state/cpv-c20-advideos-canary-20260823.json'
CANARY_AUDIT = BASE / 'data/ares/meta-ads/engine-v3/audit/canary/cpv-c20-advideos-canary-20260823.json'
CANARY_MODULE = BASE / 'scripts/ares-creditoparaveiculo-c20-advideo-canary.py'
THREAD_SOURCE = 'discord:thread:1540939724636819507'


def rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def load_canary_module():
    spec = importlib.util.spec_from_file_location('c20_canary_runtime', CANARY_MODULE)
    if not spec or not spec.loader:
        raise RuntimeError('cannot load C20 canary module')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_common():
    spec = importlib.util.spec_from_file_location('c20_recovery_common', BASE / 'scripts/ares-meta-common.py')
    if not spec or not spec.loader:
        raise RuntimeError('cannot load Meta common')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def auth() -> dict[str, Any]:
    operation = load_json(DailyPaths().operation)
    value = operation['daily_new_campaign_routine']['c20_advideo_canary_20260823']
    if (
        value.get('status') != 'authorized_corrective_recovery_existing_shell'
        or value.get('corrective_authorized_by') != 'Rodolfo Mattei'
        or value.get('corrective_authorization_source') != THREAD_SOURCE
        or 'recover existing paused C20 shell/adset' not in str(value.get('corrective_scope') or '')
    ):
        raise DailyBlocked('authorization', 'C20 corrective recovery authorization is missing or drifted')
    return value


def graph_snapshot(common, token: str) -> dict[str, Any]:
    req = [
        {'name':'campaign','path':CAMPAIGN_ID,'params':{'fields':'id,name,status,effective_status,configured_status,daily_budget,bid_strategy,start_time,source_campaign_id,issues_info'}},
        {'name':'adsets','path':f'{CAMPAIGN_ID}/adsets','params':{'fields':'id,name,status,effective_status,configured_status,start_time,source_adset_id,issues_info','limit':20}},
        {'name':'ads','path':f'{CAMPAIGN_ID}/ads','params':{'fields':'id,name,status,effective_status,configured_status,adset_id,creative{id,name,status,effective_object_story_id},issues_info','limit':50}},
    ]
    status, payload, _ = common.graph_batch_get(token, req)
    if status != 200 or any(int(item.get('code') or 0) != 200 for item in payload):
        raise DailyBlocked('readback', 'C20 recovery hierarchy GET failed', {'http': status})
    by = {item['name']: item['body'] for item in payload}
    return {'campaign': by['campaign'], 'adsets': by['adsets'].get('data') or [], 'ads': by['ads'].get('data') or []}


def validate_only(common, token: str, path: str, payload: dict[str, Any], stage: str) -> dict[str, Any]:
    status, body, _ = common.graph_post_once(path, token, {**payload, 'execution_options':['validate_only']})
    if status != 200 or body.get('success') is not True:
        raise DailyBlocked(stage, 'validate_only failed', {'http': status, 'error': common.safe_meta_error(body)})
    return {'http': status, 'success': True}


def post_once(common, token: str, path: str, payload: dict[str, Any], stage: str, *, expect_id: bool=False) -> dict[str, Any]:
    status, body, _ = common.graph_post_once(path, token, payload)
    ok = status in {200,201} and isinstance(body,dict) and not body.get('error')
    if expect_id:
        ok = ok and bool(body.get('id'))
    else:
        ok = ok and body.get('success') is True
    if not ok:
        raise DailyBlocked(stage, 'single-attempt write failed', {'http': status, 'error': common.safe_meta_error(body)})
    return body


def bounded_object(common, token: str, object_id: str, fields: str, predicate, stage: str) -> dict[str, Any]:
    last = {}
    for attempt in range(1,13):
        status, body, _ = common.graph_get(object_id, token, {'fields':fields})
        if status == 200 and isinstance(body,dict):
            last = body
            if predicate(body):
                return {'attempt':attempt,'body':body}
        if attempt < 12:
            time.sleep(3)
    raise DailyBlocked(stage, 'bounded object readback failed', {'object_id':object_id,'last':last})


def creative_inventory(common, token: str, names: set[str]) -> dict[str,list[dict[str,Any]]]:
    result = {name: [] for name in names}
    after = None
    for _ in range(20):
        params = {'fields':'id,name,status,effective_object_story_id','limit':500}
        if after:
            params['after'] = after
        status, body, _ = common.graph_get(f'act_{ACCOUNT_ID}/adcreatives', token, params)
        if status != 200:
            raise DailyBlocked('creative_inventory','creative inventory GET failed',{'http':status})
        for row in body.get('data') or []:
            name = str(row.get('name') or '')
            if name in result:
                result[name].append(row)
        after = str((((body.get('paging') or {}).get('cursors') or {}).get('after')) or '')
        if not after:
            break
    return result


def ad_validate_with_propagation(common, token: str, payload: dict[str,Any]) -> list[dict[str,Any]]:
    attempts=[]
    transient_5xx=0
    for attempt in range(1,7):
        status, body, _ = common.graph_post_once(f'act_{ACCOUNT_ID}/ads', token, {**payload,'execution_options':['validate_only']})
        success = status==200 and body.get('success') is True
        attempts.append({'attempt':attempt,'http':status,'success':success,'error':None if success else common.safe_meta_error(body)})
        if success:
            return attempts
        err=(body.get('error') or {}) if isinstance(body,dict) else {}
        propagation = int(err.get('error_subcode') or 0)==2446289
        if 500 <= status < 600 and transient_5xx < 2:
            transient_5xx += 1
            time.sleep(10)
            continue
        if propagation:
            time.sleep(5)
            continue
        break
    raise DailyBlocked('ad_validate','ad validate_only did not pass',{'attempts':attempts})


def run(*, dry_run: bool) -> dict[str,Any]:
    auth()
    sealed = load_json(SEALED)
    if not verify_prevalidation(sealed):
        raise DailyBlocked('manifest','sealed C20 manifest digest is invalid')
    campaign_spec = sealed['campaigns'][0]
    if 'b01fb13c20' not in campaign_spec['name'] or len(campaign_spec.get('ads') or []) != 3:
        raise DailyBlocked('manifest','sealed manifest is not exact C20 1x1x3')
    common=load_common()
    token,field=common.get_token_from_1password(item_name=TOKEN_ITEM)
    snapshot=graph_snapshot(common,token)
    if str(snapshot['campaign'].get('configured_status') or snapshot['campaign'].get('status'))!='PAUSED':
        raise DailyBlocked('preflight','C20 shell is not PAUSED')
    if len(snapshot['adsets'])!=1 or str(snapshot['adsets'][0].get('id'))!=ADSET_ID:
        raise DailyBlocked('preflight','C20 exact adset identity mismatch')
    if snapshot['ads']:
        raise DailyBlocked('preflight','C20 unexpectedly already has ads',{'count':len(snapshot['ads'])})

    campaign_update={'name':campaign_spec['name'],'status':'PAUSED',**campaign_spec['campaign_updates']}
    adset_update={'name':campaign_spec['adset_name'],'status':'ACTIVE'}
    campaign_validation=validate_only(common,token,CAMPAIGN_ID,campaign_update,'campaign_update_validate')
    adset_validation=validate_only(common,token,ADSET_ID,adset_update,'adset_update_validate')
    plan={
        'status':'DRY_RUN_OK' if dry_run else 'READY_TO_EXECUTE',
        'campaign_id':CAMPAIGN_ID,'adset_id':ADSET_ID,
        'campaign_update':campaign_validation,'adset_update':adset_validation,
        'missing_creatives':3,'missing_ads':3,'activation_budget_usd':30,
        'side_effects':{'writes':False} if dry_run else {'writes':'pending confirmation'},
    }
    if dry_run:
        atomic_json(RECOVERY_AUDIT.with_name(RECOVERY_AUDIT.stem+'-dry-run.json'),plan)
        return plan

    RECOVERY_LOCK.parent.mkdir(parents=True,exist_ok=True)
    with RECOVERY_LOCK.open('a+') as lock:
        fcntl.flock(lock.fileno(),fcntl.LOCK_EX)
        if RECOVERY_STATE.exists():
            prior=load_json(RECOVERY_STATE)
            if prior.get('status')=='COMPLETE':
                return {**prior,'idempotent_readback':True}
            checkpoint=prior
        else:
            checkpoint={'schema_version':1,'status':'IN_PROGRESS','campaign_id':CAMPAIGN_ID,'adset_id':ADSET_ID,'creatives':{},'ads':{},'created_at_sp':datetime.now(SP).isoformat()}
        audit={'kind':'c20_corrective_recovery','authorized_by':'Rodolfo Mattei','authorization_source':THREAD_SOURCE,'stage':'IN_PROGRESS','plan':plan,'checkpoint':checkpoint,'created_at_sp':datetime.now(SP).isoformat()}
        atomic_json(RECOVERY_AUDIT,audit)
        try:
            if snapshot['campaign'].get('name')!=campaign_spec['name'] or snapshot['campaign'].get('daily_budget')!='3000':
                post_once(common,token,CAMPAIGN_ID,campaign_update,'campaign_update')
            campaign_rb=bounded_object(common,token,CAMPAIGN_ID,'id,name,status,effective_status,configured_status,daily_budget,bid_strategy,start_time',lambda b:b.get('name')==campaign_spec['name'] and b.get('daily_budget')=='3000' and str(b.get('configured_status') or b.get('status'))=='PAUSED','campaign_update_readback')
            if snapshot['adsets'][0].get('name')!=campaign_spec['adset_name']:
                post_once(common,token,ADSET_ID,adset_update,'adset_update')
            adset_rb=bounded_object(common,token,ADSET_ID,'id,name,status,effective_status,configured_status,start_time,issues_info',lambda b:b.get('name')==campaign_spec['adset_name'] and str(b.get('configured_status') or b.get('status'))=='ACTIVE','adset_update_readback')
            audit.update(stage='SHELL_NORMALIZED',campaign_readback=campaign_rb,adset_readback=adset_rb)
            atomic_json(RECOVERY_AUDIT,audit)

            desired_names={str(row['creative_payload']['name']) for row in campaign_spec['ads']}
            existing=creative_inventory(common,token,desired_names)
            for name,found in existing.items():
                if len(found)>1:
                    raise DailyBlocked('creative_inventory','duplicate exact C20 creative names',{'name':name,'ids':[x.get('id') for x in found]})
                if len(found)==1:
                    checkpoint['creatives'][name]=str(found[0]['id'])
            atomic_json(RECOVERY_STATE,checkpoint)

            for ad in campaign_spec['ads']:
                creative_payload=ad['creative_payload']
                creative_name=str(creative_payload['name'])
                creative_id=str(checkpoint['creatives'].get(creative_name) or '')
                if not creative_id:
                    created=post_once(common,token,f'act_{ACCOUNT_ID}/adcreatives',creative_payload,f'creative_create_{creative_name}',expect_id=True)
                    creative_id=str(created['id'])
                    checkpoint['creatives'][creative_name]=creative_id
                    checkpoint['status']='CREATIVES_IN_PROGRESS'
                    atomic_json(RECOVERY_STATE,checkpoint)
                bounded_object(common,token,creative_id,'id,name,status,effective_object_story_id',lambda b:b.get('name')==creative_name and str(b.get('status') or '').upper()=='ACTIVE' and bool(b.get('effective_object_story_id')),'creative_readback')
                ad_name=str(ad['name'])
                if ad_name in checkpoint['ads']:
                    continue
                ad_payload={'name':ad_name,'adset_id':ADSET_ID,'status':'ACTIVE','creative':{'creative_id':creative_id}}
                checkpoint.setdefault('ad_validate',{})[ad_name]=ad_validate_with_propagation(common,token,ad_payload)
                atomic_json(RECOVERY_STATE,checkpoint)
                created_ad=post_once(common,token,f'act_{ACCOUNT_ID}/ads',ad_payload,f'ad_create_{ad_name}',expect_id=True)
                checkpoint['ads'][ad_name]=str(created_ad['id'])
                checkpoint['status']='ADS_IN_PROGRESS'
                atomic_json(RECOVERY_STATE,checkpoint)

            hierarchy=graph_snapshot(common,token)
            if len(hierarchy['ads'])!=3 or any(str(row.get('configured_status') or row.get('status'))!='ACTIVE' or row.get('issues_info') for row in hierarchy['ads']):
                raise DailyBlocked('readback','C20 ads hierarchy invalid before activation',{'ads':hierarchy['ads']})
            creatives=[]
            assignments=[]
            manifest_by_ad={str(row['name']):row for row in campaign_spec['ads']}
            for row in hierarchy['ads']:
                ad_name=str(row['name']); creative=row.get('creative') or {}; creative_id=str(creative.get('id') or '')
                cr=bounded_object(common,token,creative_id,'id,name,status,effective_object_story_id,asset_feed_spec,object_story_spec',lambda b:str(b.get('status') or '').upper()=='ACTIVE' and bool(b.get('effective_object_story_id')),'creative_final_readback')['body']
                raw=json.dumps(cr,ensure_ascii=False)
                if 'b01fb13c20' not in raw or 'b01fb13c20g01' not in raw or 'b01fb13c08' in raw:
                    raise DailyBlocked('utm_readback','C20 creative UTM mismatch',{'creative_id':creative_id})
                spec=manifest_by_ad[ad_name]
                media=spec['media']
                assignments.append({'asset_id':media['asset_id'],'campaign_id':CAMPAIGN_ID,'adset_id':ADSET_ID,'ad_id':str(row['id']),'creative_id':creative_id,'vertical_video_id':media['vertical_video_id'],'square_video_id':media['square_video_id']})
                creatives.append({'creative_id':creative_id,'effective_object_story_id':cr.get('effective_object_story_id'),'utm_valid':True})

            post_once(common,token,CAMPAIGN_ID,{'status':'ACTIVE'},'campaign_activate')
            active_rb=bounded_object(common,token,CAMPAIGN_ID,'id,name,status,effective_status,configured_status,daily_budget,bid_strategy,start_time,issues_info',lambda b:str(b.get('configured_status') or b.get('status'))=='ACTIVE' and b.get('daily_budget')=='3000' and not b.get('issues_info'),'campaign_activate_readback')

            paths=DailyPaths(); backend=LiveDailyBackend(paths); backend.meta_preflight(); drive=backend.drive_preflight()['drive']
            selected_ids={str(row['asset_id']) for row in assignments}
            inv=rows(paths.inventory)
            by_asset={str(row.get('asset_id')):row for row in inv if str(row.get('asset_id')) in selected_ids}
            drive_rows={str(row.get('id')):row for row in drive.get('files') or []}
            moves={}
            for assignment in assignments:
                item=by_asset[assignment['asset_id']]; drive_row=drive_rows[str(item['asset_drive_id'])]
                moves[str(item['asset_drive_id'])]=backend.move_asset(drive_row)
            update_inventory_assignments(paths.inventory,inv,assignments,moves,RECOVERY_AUDIT)
            canary=load_canary_module(); canary.update_local_states(CAMPAIGN_ID,RECOVERY_AUDIT,datetime.now(SP))
            post_meta=backend.meta_preflight(); active_minor=active_budget_minor(post_meta['campaigns']); cap_minor=50000
            if active_minor>cap_minor:
                raise DailyBlocked('budget_cap','active budget exceeds USD500 after C20',{'active_minor':active_minor})
            drive_after=backend.drive_preflight()['drive']; stock=stock_counts(rows(paths.inventory),drive_after)
            final={'status':'COMPLETE','campaign_id':CAMPAIGN_ID,'adset_id':ADSET_ID,'ad_ids':sorted(checkpoint['ads'].values()),'creative_ids':sorted(checkpoint['creatives'].values()),'campaign_readback':active_rb['body'],'creatives':creatives,'budget_active_minor':active_minor,'budget_remaining_minor':cap_minor-active_minor,'budget_cap_minor':cap_minor,'stock_remaining':stock,'assets_used':3,'first_delivery_mode':'observe_only_no_auto_pause','completed_at_sp':datetime.now(SP).isoformat()}
            checkpoint.update(final); atomic_json(RECOVERY_STATE,checkpoint)
            audit.update(stage='COMPLETE',final=final,checkpoint=checkpoint,completed_at_sp=final['completed_at_sp']); atomic_json(RECOVERY_AUDIT,audit)
            original_state=load_json(CANARY_STATE); original_state.update(final); atomic_json(CANARY_STATE,original_state)
            original_audit=load_json(CANARY_AUDIT); original_audit.update(stage='COMPLETE_RECOVERED',recovery_audit=str(RECOVERY_AUDIT),final=final); atomic_json(CANARY_AUDIT,original_audit)
            return final
        except Exception as exc:
            checkpoint.update(status='FAILED_RECONCILIATION_REQUIRED',failure={'type':type(exc).__name__,'message':str(exc)[:700]},updated_at_utc=utc_now()); atomic_json(RECOVERY_STATE,checkpoint)
            audit.update(stage='FAILED_RECONCILIATION_REQUIRED',failure=checkpoint['failure'],checkpoint=checkpoint,failed_at_utc=utc_now()); atomic_json(RECOVERY_AUDIT,audit)
            raise
        finally:
            fcntl.flock(lock.fileno(),fcntl.LOCK_UN)


def parser():
    ap=argparse.ArgumentParser(description='C20 existing-shell corrective recovery')
    mode=ap.add_mutually_exclusive_group(required=True); mode.add_argument('--dry-run',action='store_true'); mode.add_argument('--execute',action='store_true')
    ap.add_argument('--confirm-execute',action='store_true'); return ap


def main():
    args=parser().parse_args()
    if args.execute and not args.confirm_execute: raise SystemExit('--execute requires --confirm-execute')
    result=run(dry_run=args.dry_run); print(json.dumps(result,ensure_ascii=False,indent=2)); return 0

if __name__=='__main__':
    try: raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({'status':'FAILED','error_type':type(exc).__name__,'message':str(exc)[:700]},ensure_ascii=False)); raise SystemExit(2)

#!/usr/bin/env python3
"""Try up to 3 Meta replacement clone alternatives, then stop.

All created test objects are PAUSED; partial/invalid attempts are marked DELETED.
Never prints tokens.
"""
from __future__ import annotations

import importlib.util, json, subprocess, urllib.parse, urllib.request, urllib.error
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

BASE = Path('/root/mgs-agent/data/ares/meta-ads')
COMMON_PATH = Path('/root/mgs-agent/scripts/ares-meta-common.py')
AUDIT_DIR = BASE / 'audit' / 'clone'
ACCOUNT_ID = '1356770869843984'
SOURCE_CAMPAIGN_ID = '120248290564280604'
SOURCE_ADSET_ID = '120248290564260604'  # imagens from loser campaign
WINNER_AD_IDS = ['120248290564590604', '120248290297210604', '120248290564610604']
TZ = ZoneInfo('Europe/Madrid')


def load_common():
    spec = importlib.util.spec_from_file_location('common', COMMON_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError('cannot load common')
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod


def post(common, token, path, params):
    params = {k:v for k,v in params.items() if v is not None}
    params['access_token'] = token
    req = urllib.request.Request(
        f'https://graph.facebook.com/{common.GRAPH_VERSION}/{path.lstrip("/")}',
        data=urllib.parse.urlencode(params).encode(),
        headers={'User-Agent':'mgs-ares-meta-ads/0.1'}
    )
    try:
        common._throttle_before_request()
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, json.loads(resp.read().decode()), dict(resp.headers)
    except urllib.error.HTTPError as e:
        body=e.read().decode('utf-8','replace')
        try: payload=json.loads(body)
        except Exception: payload={'raw':body[:1000]}
        return e.code, payload, dict(e.headers)


def safe_error(common, payload):
    return common.safe_meta_error(payload) if isinstance(payload, dict) else payload


def cleanup_campaign(common, token, cid, reason, audit):
    if not cid:
        return None
    st,p,_=post(common, token, cid, {'status':'DELETED'})
    vst,vp,_=common.graph_get(cid, token, {'fields':'id,name,status,effective_status,daily_budget'})
    rec={'campaign_id':cid,'reason':reason,'delete_status':st,'delete_payload':safe_error(common,p),'verify_status':vst,'verify':vp if vst==200 else safe_error(common,vp)}
    audit.setdefault('cleanups',[]).append(rec)
    return rec


def summarize_campaign(common, token, cid):
    st,c,_=common.graph_get(cid, token, {'fields':'id,name,status,effective_status,daily_budget,start_time,objective'})
    st_ads,ads,_=common.graph_get(f'{cid}/ads', token, {'fields':'id,name,status,effective_status', 'limit':50})
    st_adsets,adsets,_=common.graph_get(f'{cid}/adsets', token, {'fields':'id,name,status,effective_status', 'limit':50})
    return {'campaign_status':st,'campaign':c if st==200 else safe_error(common,c),'ads_status':st_ads,'ads':ads.get('data',[]) if st_ads==200 else safe_error(common,ads),'adsets_status':st_adsets,'adsets':adsets.get('data',[]) if st_adsets==200 else safe_error(common,adsets)}


def attempt_1_existing_script(common, token, audit):
    res=subprocess.run(['/root/mgs-agent/scripts/ares-meta-replacement-clone.py','--account-id',ACCOUNT_ID,'--operation-id','OpenzedFinanzas-CC-ES','--loser-campaign-id',SOURCE_CAMPAIGN_ID,'--daily-budget-usd','25'], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300)
    out={}
    try: out=json.loads(res.stdout.strip() or '{}')
    except Exception: out={'raw_stdout':res.stdout[-1000:]}
    rec={'alternative':1,'name':'exact custom build: campaign+adsets+3 ads','exit_code':res.returncode,'stdout':out,'stderr_tail':res.stderr[-1000:]}
    cid=out.get('created_campaign_id') or out.get('new_campaign_id')
    if res.returncode==0 and out.get('status')=='created_paused':
        rec['verification']=summarize_campaign(common, token, cid)
        ads=rec['verification'].get('ads') or []
        c=rec['verification'].get('campaign') or {}
        if c.get('status')=='PAUSED' and str(c.get('daily_budget'))=='2500' and len(ads)==3:
            rec['result']='success_exact_format'
            audit['alternatives'].append(rec)
            return True, cid
    cleanup_campaign(common, token, cid, 'alt1_failed_or_not_exact', audit)
    rec['result']='failed'
    audit['alternatives'].append(rec)
    return False, None


def attempt_2_campaign_copies_endpoint(common, token, audit, start_local):
    # Native copy API. If it creates non-exact structure, cleanup.
    params={
        'deep_copy':'true',
        'status_option':'PAUSED',
        'rename_options':json.dumps({'rename_strategy':'DEEP_RENAME','rename_suffix':f' - RPL - {start_local.strftime("%Y%m%d")} - COPYAPI'}),
    }
    st,p,_=post(common, token, f'{SOURCE_CAMPAIGN_ID}/copies', params)
    if isinstance(p, dict):
        copied_campaigns = p.get('copied_campaigns') or []
        first_copied = copied_campaigns[0] if copied_campaigns and isinstance(copied_campaigns[0], dict) else {}
        cid = p.get('copied_campaign_id') or p.get('id')
        if not cid and isinstance(first_copied, dict):
            cid = first_copied.get('id')
    else:
        cid = None
    rec={'alternative':2,'name':'Meta native campaign copies endpoint','status':st,'payload':safe_error(common,p),'created_campaign_id':cid}
    if cid:
        rec['verification']=summarize_campaign(common, token, cid)
        ads=rec['verification'].get('ads') or []
        c=rec['verification'].get('campaign') or {}
        # Native copy usually preserves old budget and ad count; only accept exact requested format.
        if c.get('status')=='PAUSED' and str(c.get('daily_budget'))=='2500' and len(ads)==3:
            rec['result']='success_exact_format'
            audit['alternatives'].append(rec)
            return True, cid
        cleanup_campaign(common, token, cid, 'alt2_not_exact_or_failed', audit)
    rec['result']='failed_or_not_exact'
    audit['alternatives'].append(rec)
    return False, None


def attempt_3_manual_campaign_adset_then_ad_copies(common, token, audit, start_local):
    # Create a single replacement campaign/adset, then copy 3 winner ads into it.
    st,src_campaign,_=common.graph_get(SOURCE_CAMPAIGN_ID, token, {'fields':'name,objective,buying_type,bid_strategy,special_ad_categories'})
    st2,src_adset,_=common.graph_get(SOURCE_ADSET_ID, token, {'fields':'name,billing_event,optimization_goal,destination_type,targeting,promoted_object'})
    if st!=200 or st2!=200:
        rec={'alternative':3,'name':'manual campaign+adset then ad copies','result':'blocked_read_source','campaign_read':st,'adset_read':st2}
        audit['alternatives'].append(rec); return False, None
    src_name=src_campaign.get('name') or 'Replacement'
    prefix=' - '.join(src_name.split(' - ')[:4])
    name=f'{prefix} - RPL - {start_local.strftime("%Y%m%d")} - ADCOPY'
    stc,pc,_=post(common, token, f'act_{ACCOUNT_ID}/campaigns', {
        'name':name,
        'objective':src_campaign.get('objective'),
        'buying_type':src_campaign.get('buying_type') or 'AUCTION',
        'status':'PAUSED',
        'daily_budget':'2500',
        'bid_strategy':src_campaign.get('bid_strategy'),
        'special_ad_categories':json.dumps(src_campaign.get('special_ad_categories') or []),
        'special_ad_category_country':json.dumps(['ES']),
        'start_time':start_local.strftime('%Y-%m-%dT%H:%M:%S%z'),
    })
    rec={'alternative':3,'name':'manual campaign+adset then ad copies','campaign_create_status':stc,'campaign_payload':safe_error(common,pc)}
    cid=pc.get('id') if isinstance(pc,dict) else None
    if stc not in (200,201) or not cid:
        rec['result']='failed_campaign_create'; audit['alternatives'].append(rec); return False, None
    sta,pa,_=post(common, token, f'act_{ACCOUNT_ID}/adsets', {
        'name':'Conjunto RPL - Ad Copy',
        'campaign_id':cid,
        'status':'PAUSED',
        'billing_event':src_adset.get('billing_event'),
        'optimization_goal':src_adset.get('optimization_goal'),
        'destination_type':src_adset.get('destination_type'),
        'targeting':json.dumps(src_adset.get('targeting') or {}),
        'promoted_object':json.dumps(src_adset.get('promoted_object') or {}),
        'attribution_spec':json.dumps([{'event_type':'CLICK_THROUGH','window_days':1}]),
        'start_time':start_local.strftime('%Y-%m-%dT%H:%M:%S%z'),
    })
    rec['adset_create_status']=sta; rec['adset_payload']=safe_error(common,pa)
    adset_id=pa.get('id') if isinstance(pa,dict) else None
    if sta not in (200,201) or not adset_id:
        cleanup_campaign(common, token, cid, 'alt3_adset_failed', audit)
        rec['result']='failed_adset_create'; audit['alternatives'].append(rec); return False, None
    copied=[]
    for adid in WINNER_AD_IDS:
        stp,pp,_=post(common, token, f'{adid}/copies', {'adset_id':adset_id,'status_option':'PAUSED'})
        copied.append({'source_ad_id':adid,'status':stp,'payload':safe_error(common,pp)})
    rec['ad_copy_results']=copied
    rec['verification']=summarize_campaign(common, token, cid)
    ads=rec['verification'].get('ads') or []
    c=rec['verification'].get('campaign') or {}
    if c.get('status')=='PAUSED' and str(c.get('daily_budget'))=='2500' and len(ads)==3:
        rec['result']='success_exact_format'; audit['alternatives'].append(rec); return True, cid
    cleanup_campaign(common, token, cid, 'alt3_not_exact_or_failed', audit)
    rec['result']='failed_or_not_exact'; audit['alternatives'].append(rec); return False, None


def main():
    common=load_common(); token,_=common.get_token_from_1password()
    start_local=(datetime.now(timezone.utc).astimezone(TZ)+timedelta(days=1)).replace(hour=1,minute=0,second=0,microsecond=0)
    audit={'created_at':datetime.now(timezone.utc).isoformat(),'source_campaign_id':SOURCE_CAMPAIGN_ID,'goal':'create one paused replacement campaign in requested format','max_alternatives':3,'alternatives':[],'cleanups':[]}
    success=False; success_campaign=None
    for fn in (attempt_1_existing_script,):
        success, success_campaign = fn(common, token, audit)
        if success: break
    if not success:
        success, success_campaign = attempt_2_campaign_copies_endpoint(common, token, audit, start_local)
    if not success:
        success, success_campaign = attempt_3_manual_campaign_adset_then_ad_copies(common, token, audit, start_local)
    audit['final']={'success':success,'campaign_id':success_campaign,'blocker':None if success else 'No alternative could create ads; likely Meta pending account authentication/action required'}
    out=AUDIT_DIR / f'clone-troubleshoot-3alts-{datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")}.json'
    out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'success':success,'campaign_id':success_campaign,'audit':str(out),'alternatives_tried':len(audit['alternatives']),'cleanups':len(audit['cleanups']),'final':audit['final']},ensure_ascii=False,indent=2))
    return 0 if success else 1

if __name__=='__main__':
    raise SystemExit(main())

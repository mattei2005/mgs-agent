"""Exact real request validation, guarded GET only; no runner/QA/state mutation."""
import copy, hashlib, json, os, sys
from pathlib import Path
from datetime import datetime, timezone
B=Path('/root/mgs-agent');W=B/'work/t_fc58be96'
installed='--installed' in sys.argv
sys.path[:0]=([] if installed else [str(W/'stage')])+[str(B/'scripts')]
assert os.environ.get('HERMES_PROFILE')=='ares'
from ares_campaign_v3 import shein_single_clone as route, shein_continuation as central
from ares_campaign_v3 import shein_reviewed_targeting as reviewed, shein_reviewed_img as img
from ares_campaign_v3.shein_channel_authority import _get
from ares_campaign_v3 import shein_request_queue as queue
R='shein-1565747351543480374';A='937846586033361'
sp=B/'data/ares/meta-ads/state/shein-campaigns/single-clone'/R/'state.json'
cp=B/'data/ares/meta-ads/engine-v3/state/checkpoints'/(R+'-'+A+'.json')
descriptor_path=Path(json.loads((W/'deployment-receipt.json').read_text())['descriptor']) if installed else W/'continuation.json'
s=json.loads(sp.read_text());c=json.loads(cp.read_text());d=json.loads(descriptor_path.read_text())
assert d==json.loads((W/'continuation.json').read_text())
base=json.loads((W/'baseline-state-hashes.json').read_text())
def unchanged():
    assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in base.items())
unchanged()
assert s['request']==json.loads((B/'data/ares/meta-ads/audit/shein/campaigns/intake'/R/'request-ready.json').read_text())
auth=queue.authorize_queue_request(s['request'],B)
messages={}
def getter(path):
    result=_get(path);messages[path]=result
    return result
proof=central.validate_descriptor(d,s,c,get_message=getter)
assert proof['accepted_targeting']['kind']==img.KIND
context={'descriptor':d,'state':s,'checkpoint':c,'verified':proof}
config=json.loads((B/'data/ares/meta-ads/engine-v3/config.json').read_text())
common=route._load_common();token,_=common.get_token_from_1password(config['accounts'][A]['token_item'])
client=route.ReadOnlyClient(common)
http,account,_=client.graph_get('act_'+A,token,{'fields':'id,account_id,name,currency,timezone_name'})
assert http==200 and account['account_id']==A and account['currency']=='USD' and account['timezone_name']=='America/New_York'
http,source,_=client.graph_get(s['source']['adset']['id'],token,{'fields':'id,targeting,bid_amount,attribution_spec,promoted_object,billing_event,optimization_goal,is_dynamic_creative'})
assert http==200 and source['targeting']==s['source']['adset']['targeting'] and source['bid_amount']==90
rows=[];trees=[]
marker=central.APPROVED_RESUME.set(context)
try:
    for slot in d['reviewed_targeting']['slots']:
        tree=route._readback(client,token,slot['campaign_id']);trees.append(tree)
        reviewed.validate_tree(reviewed.active_context(),tree)
        reviewed.validate_activation_tree(tree)
        assert all(x['status']=='PAUSED' for x in [tree['campaign']]+tree['adsets']['data']+tree['ads']['data'])
        rows.append({'campaign_id':tree['campaign']['id'],'campaign_status':tree['campaign']['status'],
                     'budget_minor':tree['campaign']['daily_budget'],'bid_strategy':tree['campaign']['bid_strategy'],
                     'adset_id':tree['adsets']['data'][0]['id'],'bid_amount':tree['adsets']['data'][0]['bid_amount'],
                     'start_time':tree['campaign']['start_time'],'targeting':tree['adsets']['data'][0]['targeting'],
                     'ad_ids':sorted(x['id'] for x in tree['ads']['data'])})
finally:central.APPROVED_RESUME.reset(marker)
assert len(rows)==8 and sum(len(r['ad_ids']) for r in rows)==16
# Negative tests use the exact recorded GETs only. Never substitute this getter in production.
negatives=[]
def rejected(name,fn):
    try:fn()
    except (ValueError,KeyError):negatives.append(name)
    else:raise AssertionError('negative not rejected: '+name)
def cached(path):return copy.deepcopy(messages[path])
for key in ['continuation_of','account','account_id','authorized_by','source_thread_id','source_channel_id','source_campaign_number','budget_usd','bid_strategy','bid_usd','source_message_id','recovery_review_message_id','recovery_review_content','reviewed_targeting_kind']:
    bad=copy.deepcopy(d);bad[key]='999'
    rejected('descriptor:'+key,lambda:central.validate_descriptor(bad,s,c,get_message=cached))
for field in ['execution_started_at','resolved_request','manifest','target_manifest','source','request']:
    bad=copy.deepcopy(s)
    if field=='execution_started_at':bad[field]='2030-01-01T00:00:00+00:00'
    elif field=='resolved_request':bad[field]['start_time']='2030-01-01T00:00:00+00:00'
    elif field in ['manifest','target_manifest']:bad[field]['campaigns'][0]['adset_updates']['bid_amount']='90'
    elif field=='source':bad[field]['campaign']['id']='999'
    elif field=='request':bad[field]['request_id']='another'
    rejected('state:'+field,lambda:central.validate_descriptor(d,bad,c,get_message=cached))
for mid in img.MESSAGE_IDS:
    for field in ['author','message_reference','content','edited_timestamp']:
        def corrupted(path,mid=mid,field=field):
            m=cached(path)
            if m['id']==mid:m[field]={'id':'999','bot':False} if field=='author' else {'message_id':'999'} if field=='message_reference' else 'changed'
            return m
        rejected('message:'+mid+':'+field,lambda:central.validate_descriptor(d,s,c,get_message=corrupted))
for field in ['age_min','unknown_age','device','extra_device','bid','budget','clock','campaign_id','adset_id','ad_id','lineage','account_id']:
    tree=copy.deepcopy(trees[0]);aset=tree['adsets']['data'][0]
    if field=='age_min':aset['targeting']['age_min']=25
    elif field=='unknown_age':aset['targeting']['user_age_unknown']=False
    elif field=='device':aset['targeting']['targeting_automation']['individual_setting']={'device':1}
    elif field=='extra_device':aset['targeting']['targeting_automation']['individual_setting']={'device':0,'age':1}
    elif field=='bid':aset['bid_amount']=90
    elif field=='budget':tree['campaign']['daily_budget']='3500'
    elif field=='clock':aset['start_time']='2030-01-01T00:00:00+00:00'
    elif field=='campaign_id':tree['campaign']['id']='999'
    elif field=='adset_id':aset['id']='999'
    elif field=='ad_id':tree['ads']['data'][0]['id']='999'
    elif field=='lineage':tree['ads']['data'][0]['source_ad_id']='999'
    elif field=='account_id':tree['campaign']['account_id']='999'
    rejected('live:'+field,lambda:reviewed.validate_tree(context,tree))
unchanged()
result={'at':datetime.now(timezone.utc).isoformat(),'profile':os.environ['HERMES_PROFILE'],
        'installed':installed,'module_origin':img.__file__,'request_id':R,'account_id':A,
        'descriptor_path':str(W/'continuation.json'),'descriptor_digest':central.content_digest(d),
        'binding_digest':img.BINDING_DIGEST,'authority_live':True,'proof':proof,'live':rows,
        'negative_checks':negatives,'negative_count':len(negatives),'campaign_count':len(rows),'ad_count':sum(len(r['ad_ids']) for r in rows),
        'http_requests':client.http_requests,'logical_gets':client.logical_gets,'meta_writes':0,'drive_writes':0,'uploads':0,'reservations':0,
        'operational_state_hashes_unchanged':True,'serving_verified':False,'semantic_and_rendered_qa_executed':False}
(W/('real-readonly-installed.json' if installed else 'real-readonly-stage.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:result[k] for k in ['profile','installed','request_id','binding_digest','campaign_count','ad_count','negative_count','http_requests','meta_writes','operational_state_hashes_unchanged','serving_verified']}))

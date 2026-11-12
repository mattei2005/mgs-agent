"""Maintenance-only read-only acceptance. Never calls campaign/activate/execute."""
import argparse
import copy
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from ares_campaign_v3 import shein_elapsed_continuation as effective
from ares_campaign_v3 import shein_copy_schedule as schedule
from ares_campaign_v3 import shein_single_clone as route
from ares_campaign_v3.activation import validate_live, elapsed_policy_allows_activation, stable_story
from ares_campaign_v3.schema import Manifest

ROOT=Path('/root/mgs-agent')
AUDIT=ROOT/'data/ares/meta-ads/audit/maintenance/t_32bc2e19'
RID='shein-1570314359530459327'; AID='937846586033361'
parser=argparse.ArgumentParser();parser.add_argument('--installed',action='store_true');parser.add_argument('--live',action='store_true')
args=parser.parse_args()
base=ROOT if args.installed else AUDIT/'sandbox'
s,c,o,op,p,pr,rp=effective.load(ROOT,RID,AID)
now=datetime.now(timezone.utc)
auth=effective.live_authority(s['request'],pr,op,p)
bound=effective.binding(s,c,o,p,pr,now=now)
if not args.installed:
    for source in [*effective.paths(ROOT,RID,AID)[:3], ROOT/effective.POLICY_FILE,
                   ROOT/'data/ares/meta-ads/operations/SHEIN-US-DIRECT-profiles.json']:
        target=base/source.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
    receipt={'kind':effective.KIND,'issued_at':now.isoformat(),'binding':bound,'authority':auth,
             'maintenance_task_id':'t_32bc2e19','meta_writes':0,'drive_writes':0,'qa_certified':False}
    dest=effective.paths(base,RID,AID)[-1];dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
    grants={'kind':effective.KIND,'grants':{RID:{'account_id':AID,'authority_message_id':p['source_message_id'],'receipt_digest':effective.digest(receipt)}}}
    gp=base/effective.GRANTS_FILE;gp.parent.mkdir(parents=True,exist_ok=True);gp.write_text(json.dumps(grants,indent=2,sort_keys=True)+'\n')
else:
    receipt=json.loads(rp.read_text())
effective.BASE=base;schedule.BASE=base
creation=Manifest.from_dict(s['manifest']);target=Manifest.from_dict(s['target_manifest'])
assert len(target.campaigns)==10
assert all(spec.start_intent=='SCHEDULED' for spec in target.campaigns)
if args.live:
    common=route._load_common()
    config=json.loads((ROOT/'data/ares/meta-ads/engine-v3/config.json').read_text())
    token,_=common.get_token_from_1password(config['accounts'][AID]['token_item'])
    reader=route.ReadOnlyClient(common)
    http,account,_=reader.graph_get('act_'+AID,token,{'fields':'id,currency,timezone_name,name'})
    assert http==200 and account['id']=='act_'+AID and account['timezone_name']==pr['timezone'] and account['currency']=='USD'
    trees=[route._readback(reader,token,slot['campaign_id']) for slot in bound['slots']]
else:
    trees=[]
    for bundle in c['bundles']:
        rows={r['name']:r['body'] for r in bundle['readback_results'] if r.get('code')==200}
        for i in range(1,len(bundle['campaign_ids'])+1):
            trees.append({k:copy.deepcopy(rows['readback_'+k+'_'+str(i)]) for k in ['campaign','adsets','ads']})
results=[]
for index,(slot,tree,spec) in enumerate(zip(bound['slots'],trees,target.campaigns)):
    assert tree['campaign']['status']=='PAUSED' and tree['campaign']['id']==slot['campaign_id']
    assert [x['id'] for x in tree['adsets']['data']]==[slot['adset_id']]
    assert {x['id'] for x in tree['ads']['data']}==set(slot['ad_ids'])
    for node in [tree['campaign'],*tree['adsets']['data']]:
        assert effective.instant(node['start_time'])==effective.instant(slot['observed_start_time'])
    assert effective.proof(spec.start_time,tree['campaign']['start_time'],request_id=RID,account_id=AID,
                           campaign_id=slot['campaign_id'],idempotency_key=slot['idempotency_key'])
    warnings=route.verify_readback({**s['manifest'],'campaigns':[s['manifest']['campaigns'][index]]},s['source'],tree)
    validate_live(tree,tree,spec,RID)
    assert elapsed_policy_allows_activation(spec,RID,tree)
    # Exercise final configured-ACTIVE readback/QA path on an in-memory tree only.
    final=copy.deepcopy(tree)
    for node in [final['campaign'],*final['adsets']['data'],*final['ads']['data']]:node['status']='ACTIVE'
    final['campaign']['effective_status']='ACTIVE'
    route.verify_readback({**s['target_manifest'],'campaigns':[s['target_manifest']['campaigns'][index]]},s['source'],final)
    validate_live(final,tree,spec,RID)
    # Exact extra second must not pass either consumer.
    bad=copy.deepcopy(tree);bad['campaign']['start_time']='2026-11-12T01:20:28-0500'
    for consumer in [lambda:route.verify_readback({**s['manifest'],'campaigns':[s['manifest']['campaigns'][index]]},s['source'],bad),
                     lambda:validate_live(bad,tree,spec,RID)]:
        try:consumer()
        except ValueError:pass
        else:raise AssertionError('consumer accepted unproven second')
    results.append({'campaign_id':slot['campaign_id'],'adset_id':slot['adset_id'],'ad_ids':slot['ad_ids'],
                    'start_time':slot['observed_start_time'],'classification':slot['classification'],
                    'semantic_read_only':True,'activation_pre_read_validator':True,'elapsed_activation_guard':True,
                    'final_readback_validator_in_memory':True,'warnings':warnings})
# Reuse one grant under another top-level operation/request cannot admit the target.
for field,value in [('operation','Other'),('request_id','other-request')]:
    bad=copy.deepcopy(s['target_manifest']);bad[field]=value
    try:Manifest.from_dict(bad)
    except ValueError:pass
    else:raise AssertionError('schema admitted cross-request target')
assert s['media_qa']==json.loads(effective.paths(ROOT,RID,AID)[0].read_text())['media_qa']
summary={'verified_at':datetime.now(timezone.utc).isoformat(),'installed':args.installed,'live_get':args.live,
         'request_id':RID,'account_id':AID,'counts':{'campaigns':len(results),'adsets':len(results),'ads':sum(len(x['ad_ids']) for x in results)},
         'media_qa_preserved_count':len(s['media_qa']),'receipt_digest':effective.digest(receipt),
         'trees':results,'meta_writes':0,'drive_writes':0,'qa_complete':False,'activation_executed':False,
         'phase_preserved':s['phase'],'clock_preserved':s['execution_started_at']}
if args.live:
    (AUDIT/('installed' if args.installed else 'staging')).mkdir(exist_ok=True)
    out=AUDIT/('installed' if args.installed else 'staging')/'live-trees.json'
    out.write_text(json.dumps(stable_story(trees),indent=2,sort_keys=True)+'\n')
path=AUDIT/('acceptance-installed.json' if args.installed else 'acceptance-staging.json')
path.write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n')
print(json.dumps({k:v for k,v in summary.items() if k!='trees'},ensure_ascii=False))

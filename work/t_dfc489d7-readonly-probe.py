#!/usr/bin/env python3
"""One-task diagnostic; no production install or campaign execution."""
import copy, fcntl, hashlib, importlib.util, json, sys, time
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
R=Path('/root/mgs-agent');sys.path.insert(0,str(R/'scripts'))
from ares_campaign_v3 import target_page_clone as target, target_continuation as continuation, progress
from ares_campaign_v3.schema import Manifest
from ares_campaign_v3.engine import CampaignEngine
from ares_campaign_v3.cli import real_transport_factory
from ares_campaign_v3.transport import BatchOperation
P=R/'data/ares/meta-ads/audit/eggbev/target-clone/eggbev-pg23187-1570285402068091011/execution-now-1570313437379170436/request.json'
OUT=R/'work/t_dfc489d7-readonly-proof.json'
def load(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def now():return datetime.now(timezone.utc).isoformat()
cfg=load(R/'data/ares/meta-ads/engine-v3/config.json');q=load(P);payload=load(P.parent/'manifest.json')
assert q['account_id']=='1034081997659047' and q['request_id']=='eggbev-pg23187-1570285402068091011'
checkpoint=Path(cfg['state_root'])/'checkpoints'/f"{q['request_id']}-{q['account_id']}.json"
audit=Path(cfg['audit_root'])/(q['request_id']+'.json')
parent=load(R/'work/t_506005a4-blocker-proof.json')
protected=[R/p for p in parent['protected_sha256']]+[checkpoint,audit,R/'data/ares/meta-ads/engine-v3/media-registry.json']
before={str(p):sha(p) for p in protected}
assert all(before[str(R/p)]==v for p,v in parent['protected_sha256'].items())
spec=importlib.util.spec_from_file_location('readonly_target_runner',R/'scripts/ares-eggbev-target-clone.py');runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
proof={'task_id':'t_dfc489d7','started_at':now(),'request_id':q['request_id'],'account_id':q['account_id'],'approved_content_digest':payload['prevalidation']['content_digest'],'meta_mutations':0,'drive_mutations':0,'rounds':[],'protected_before':before}
def save():OUT.write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n')
class GetOnly:
    def __init__(self,inner):self.inner=inner;self.get_count=0
    @property
    def last_outer_headers(self):return self.inner.last_outer_headers
    def execute(self,operations,stage):
        assert operations and all(op.method.upper()=='GET' and not op.body for op in operations),'NO MUTATIONS ALLOWED'
        self.get_count+=len(operations)
        return self.inner.execute(operations,stage)
with (P.parent/'target-clone.lock').open('a+') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    assert progress.CURRENT.get() is None
    common,meta,sb,token=runner.runtime()
    source=runner.source_read(q,common,meta,token)
    proof['source_unchanged']=runner.source_comparison(source)==runner.source_comparison(load(P.parent/'source-live.json'))
    assert proof['source_unchanged']
    for round_index,delay in enumerate([0,30,60],1):
        if delay:time.sleep(delay)
        with continuation.admission(P,payload,cfg,meta=meta,token=token) as admitted:
            manifest=Manifest.from_dict(payload)
            assert manifest.digest=='6a0cab5797e867efea9626c27227f7fa100627f1693a3ac3867e3f6c276c7b44'
            engine=CampaignEngine(cfg,transport_factory=real_transport_factory(cfg,manifest))
            bundle=engine.planner.build(manifest).lanes[q['account_id']][0]
            transport=GetOnly(engine.transport_factory(q['account_id']))
            record=copy.deepcopy(admitted['record'])
            ids=target.reconcile_existing(engine,bundle,transport,record,require_shells=True)
            observation={'at':now(),'round':round_index,'confirmed_ids':ids,'slots':[]}
            for stage in target.stages(bundle.campaigns):
                if stage.name!='target_seed_create':continue
                for original in stage.operations:
                    if original.name not in {'target_seed_create_1_2','target_seed_create_1_3'}:continue
                    assert target._uncertain(record,original.name),'Original uncertain classification changed'
                    op=replace(original,relative_url=target._resolve(original.relative_url,ids),body=target._resolve(original.body,ids))
                    result={'operation':op.name,'expected_name':op.body['name'],'expected_adset_id':op.body['adset_id'],'expected_creative_id':op.body['creative']['creative_id'],'uncertain':True}
                    try:result['unique_exact_match_id']=target._adopt_uncertain(engine,bundle,transport,op,record)
                    except ValueError as exc:
                        assert str(exc)=='uncertain target mutation unresolved; no POST replay; retain request for convergence/reconciliation'
                        result['unique_exact_match_id']=None
                        result['verdict']='UNRESOLVED_NO_POST_REPLAY'
                    observation['slots'].append(result)
            rows=target._inventory(engine,bundle,transport,ids['campaign_id_1']+'/ads','id,name,account_id,campaign_id,adset_id,status,effective_status,source_ad_id,creative{id}','readonly_diagnostic_ads')
            observation['ads']=[{k:v for k,v in row.items() if k in {'id','name','account_id','campaign_id','adset_id','status','effective_status','source_ad_id','creative'}} for row in rows]
            campaign=engine._batch(bundle,transport,[BatchOperation('readonly_campaign','GET',ids['campaign_id_1']+'?fields=id,account_id,name,status,effective_status,daily_budget',kind='readback')],'readonly_diagnostic_campaign')[0].body
            observation['campaign']={k:v for k,v in campaign.items() if k in {'id','account_id','name','status','effective_status','daily_budget'}}
            observation['get_operations']=transport.get_count
            observation['known_media_observations']=record.get('target_clone_known_media_observed',{})
            proof['rounds'].append(observation);save()
            if all(s.get('unique_exact_match_id') for s in observation['slots']):break
    proof['finished_at']=now()
    proof['protected_after']={str(p):sha(p) for p in protected}
    proof['all_protected_unchanged']=proof['protected_after']==before
    assert proof['all_protected_unchanged'],'Canonical file changed concurrently; do not adopt'
    proof['resolution']='UNIQUE_MATCHES_AVAILABLE_FOR_ARES' if all(s.get('unique_exact_match_id') for s in proof['rounds'][-1]['slots']) else 'BLOCKED_META_SIDE_EFFECTS_UNRESOLVED'
    proof['no_durable_adoption']=True
    save()
print(json.dumps({'proof':str(OUT),'resolution':proof['resolution'],'rounds':len(proof['rounds']),'last_observation':proof['rounds'][-1],'all_protected_unchanged':proof['all_protected_unchanged'],'source_unchanged':proof['source_unchanged'],'meta_mutations':0,'drive_mutations':0},ensure_ascii=False,indent=2))

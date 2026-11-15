"""Maintenance-only receipt/config install with CAS and live admission, zero Engine."""
import copy,fcntl,json,sys
from pathlib import Path
R=Path('/root/mgs-agent');M=R/'data/ares/meta-ads/audit/maintenance/t_9700e988';sys.path.insert(0,str(R/'scripts'))
from ares_campaign_v3 import target_start_revision as rev
from ares_campaign_v3 import target_continuation as tc
import importlib.util
h=R/'data/ares/meta-ads/audit/eggbev/target-clone/eggbev-pg23189-1571342489162489937';config=R/'data/ares/meta-ads/engine-v3/config.json';receipt=rev.load(M/'continuation-candidate.json');rid=receipt['request_id'];aid=receipt['account_id']
with (h/'target-clone.lock').open('a+') as lock,config.with_suffix('.json.lock').open('a+') as cfglock:
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(cfglock,fcntl.LOCK_EX)
    before=config.read_bytes();cfg=json.loads(before);after=copy.deepcopy(cfg)
    rp=Path(cfg['state_root'])/'target-continuations'/f'{rid}-{aid}.json'
    assert cfg['accounts'][aid]['target_page_replacement']['continuations']=={},'unexpected concurrent continuation binding'
    for p,sha in rev.load(M/'protected-before.json').items():assert rev.file_digest(p)==sha,p
    tests=rev.load(M/'installed-final-tests.json');assert all(x['success'] for x in tests) and sum(x['tests'] for x in tests)==487
    for p,sha in rev.load(M/'tested-runtime-hashes.json').items():assert rev.file_digest(R/p)==sha,p
    raw=(M/'continuation-candidate.json').read_bytes()
    if rp.exists():assert rp.read_bytes()==raw,'receipt collision'
    else:rev.atomic_bytes(rp,raw)
    binding={'receipt_path':str(rp),'sha256':rev.file_digest(rp)}
    after['accounts'][aid]['target_page_replacement']['continuations'][rid]=binding
    spec=importlib.util.spec_from_file_location('install_readonly_runtime',R/'scripts/ares-eggbev-target-clone.py');runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
    _,meta,_,token=runner.runtime()
    with tc.admission(h/'request.json',rev.load(h/'manifest.json'),after,meta=meta,token=token) as admitted:
        ids=copy.deepcopy(admitted['ids'])
        assert ids=={'campaign_id_1':'120251246081230629','adset_id_1':'120251246081300629','creative_id_1_1':'1612556403313873'}
        # Exercise elapsed schema only, never Engine/dry-run against live data.
        from ares_campaign_v3.schema import Manifest
        manifest=Manifest.from_dict(rev.load(h/'manifest.json'));tc.require_execution(manifest)
        assert manifest.digest==receipt['manifest_digest']
    assert config.read_bytes()==before
    restored=copy.deepcopy(after);restored['accounts'][aid]['target_page_replacement']['continuations'].pop(rid);assert restored==cfg
    rev.atomic_json(config,after);assert rev.load(config)==after
    for p,sha in rev.load(M/'protected-before.json').items():assert rev.file_digest(p)==sha,p
    result={'status':'INSTALLED_VALIDATED','task_id':'t_9700e988','execution_owner_task':'t_bdfc754f','request_id':rid,'receipt_path':str(rp),'receipt_sha256':binding['sha256'],'config_sha256_before':rev.file_digest(M/'before/config.json'),'config_sha256_after':rev.file_digest(config),'only_config_delta':'accounts/'+aid+'/target_page_replacement/continuations/'+rid,'ids':ids,'manifest_digest':manifest.digest,'original_approved_digest':receipt['original_approved_digest'],'approval_message_id':receipt['approval_message_id'],'instruction_message_id':receipt['instruction_message_id'],'start_time':receipt['start_time'],'fresh_live_authority_and_admission':True,'elapsed_schema_verified':True,'operational_engine_calls':0,'meta_writes':0,'drive_writes':0,'protected_files_unchanged':len(rev.load(M/'protected-before.json'))}
    rev.atomic_json(M/'install-receipt.json',result)
print(json.dumps(result,ensure_ascii=False,indent=2))

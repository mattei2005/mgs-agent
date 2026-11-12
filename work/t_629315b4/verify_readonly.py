"""Maintenance live acceptance. Forbid all Meta mutations; no Drive client."""
import copy
import fcntl
import importlib.util
import json
import sys
from pathlib import Path
sys.path.insert(0,'/root/mgs-agent/scripts')
from ares_campaign_v3.transport import GraphBatchTransport
from ares_campaign_v3 import target_continuation as tc
BASE=Path('/root/mgs-agent')
HOME=BASE/'data/ares/meta-ads/audit/eggbev/target-clone/eggbev-pg23187-1570285402068091011/execution-now-1570313437379170436'
OUT=BASE/'work/t_629315b4'
OUT.mkdir(parents=True,exist_ok=True)
spec=importlib.util.spec_from_file_location('maintenance_target_check',BASE/'scripts/ares-eggbev-target-clone.py')
assert spec and spec.loader
runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
original_runtime=runner.runtime
counts={'meta_mutations':0,'graph_gets':0,'metadata_gets':0,'batch_get_children':0,'batch_outer_requests':0,'drive_writes':0}
def deny(*args,**kwargs):
    counts['meta_mutations']+=1
    raise AssertionError('maintenance forbids Meta mutations')
def runtime():
    common,meta,sb,token=original_runtime()
    for name in ['graph_post','graph_post_once','graph_delete','graph_delete_once']:
        if hasattr(meta,name):setattr(meta,name,deny)
    original_get=meta.graph_get
    def get(*args,**kwargs):
        counts['graph_gets']+=1
        return original_get(*args,**kwargs)
    meta.graph_get=get
    original_metadata=meta.graph_get_credential_metadata
    def metadata(*args,**kwargs):
        counts['metadata_gets']+=1
        return original_metadata(*args,**kwargs)
    meta.graph_get_credential_metadata=metadata
    return common,meta,sb,token
runner.runtime=runtime
original_batch=GraphBatchTransport.execute
def batch(self,operations,stage):
    if any(op.method!='GET' for op in operations):return deny()
    counts['batch_get_children']+=len(operations);counts['batch_outer_requests']+=1
    return original_batch(self,operations,stage)
GraphBatchTransport.execute=batch
protected=[]
for row in tc.load(BASE/'backups/t_629315b4/inventory.json'):
    if row['path'].startswith(('data/ares/meta-ads/engine-v3/state/checkpoints/','data/ares/meta-ads/engine-v3/audit/','data/ares/meta-ads/audit/eggbev/target-clone/')):protected.append(row)
assert protected
before={row['path']:tc.file_digest(BASE/row['path']) for row in protected}
assert all(before[row['path']]==row['sha256'] for row in protected)
with (HOME/'target-clone.lock').open('a+') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    result=runner.execute(HOME/'request.json',confirm=True,approved_digest='920a08d00c7a5f1a0d93cad744c98bb5c7875c559605d8d126cf6648b9a03499',approval_message_id='1570313437379170436',check_only=True)
after={row['path']:tc.file_digest(BASE/row['path']) for row in protected}
assert before==after
assert counts['meta_mutations']==0 and result['meta_writes']==0 and result['drive_writes']==0
assert result['confirmed_ids']=={'campaign_id_1':'120251175890330629','adset_id_1':'120251175890720629','creative_id_1_1':'2190284505251875'}
proof={'task_id':'t_629315b4','read_only_acceptance':result,'calls':counts,'protected_file_count':len(protected),'protected_files_unchanged':before==after,'protected_sha256':after,'original_error_and_schedule_preserved':True,'commercial_execution_performed':False}
(OUT/'live-acceptance.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in proof.items() if k!='protected_sha256'},ensure_ascii=False,indent=2))

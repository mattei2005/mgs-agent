"""Freeze only four proven local mirrored copies; no deletion."""
import datetime,gzip,importlib.util,json,os,pathlib,subprocess
from typing import Any
R=pathlib.Path('/root/mgs-agent');O=pathlib.Path(__file__).parent;P=pathlib.Path('/root/.hermes/secure-backups/storage-finance-archives-1572257170626580601')
assert not(O/'manifest.json').exists(),'Frozen manifest must not be overwritten'
spec=importlib.util.spec_from_file_location('archive_four_gate',O/'gate.py');assert spec is not None and spec.loader is not None;g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
c=json.loads((O/'candidate-four-local-copies.json').read_text());rows=json.load(gzip.open(P/'reviewed326.json.gz','rt'));targets=c['targets'];paths=[x['path']for x in targets];assert len(paths)==4
for row in targets:assert g.meta(row['path'])==row['metadata']and g.sha(row['path'])==row['sha256']
retained=[x for x in rows if x['path']not in paths];assert len(retained)==322
# No target belongs to tracked institutional files, mount, symlink or process.
assert not subprocess.check_output(['git','-C',str(R),'ls-files','-z','--',*paths]);assert not g.runtime_refs(paths)
index=g.census(paths)
with gzip.open(P/'source-census.json.gz','wt',compresslevel=6)as f:json.dump(index,f,separators=(',',':'))
transport=[R/'apps/finance-system/finance_gam_revenue_sync.py',R/'apps/finance-system/deploy/runcloud_ops.py',R/'scripts/mgs_google_workspace_auth.py']
evidence={}
for x in json.loads((O/'dump-lineage.json').read_text()):
 for k in ['result_path','plan_path']:evidence[x[k]]=g.sha(x[k])
evidence[str(O/'dump-lineage.json')]=g.sha(O/'dump-lineage.json');evidence[str(O/'role-summary.json')]=g.sha(O/'role-summary.json')
manifest:dict[str,Any]=dict(status='frozen_awaiting_exact_critical_confirmation',request_message_id='1572257170626580601',thread_id='1569928464033783862',targets=targets,file_count=4,directory_count=0,reclaim_bytes=sum(x['metadata']['blocks']*512 for x in targets),gate_sha256=g.sha(O/'gate.py'),retained_reviewed_files=retained,retained_local_dumps=c['retained_local'],remote_recovery=json.loads((O/'remote-recovery-readback.json').read_text()),transport_source_hashes={str(p):g.sha(p)for p in transport},retained_evidence=evidence,source_census_path=str(P/'source-census.json.gz'),source_census_sha256=g.sha(P/'source-census.json.gz'),source_census_entries=len(index),runtime=g.health(),launcher=os.path.realpath('/root/.local/bin/hermes'),deletion_effect='Only four older local backup copy pathnames disappear. Exact remote originals verified by full SHA256/size/catalogue remain; current local fallback17Nov and three partial-run local dumps remain. No original report/receipt/source/schema, production fact or remote backup is deleted. Historical contents remain byte recoverable remotely; remote retrieval is required to regain the removed local path. Catalogue proof is not a materialized database restore.',future_retention_or_cron_changes=False,newly_discovered_file_retained=str(R/'apps/finance-system/private/gam-email-runs/20261117T080318-0500/mgs_finance-before.dump'),frozen_at=datetime.datetime.now().astimezone().isoformat())
g.shape(manifest);(O/'manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n');h=subprocess.check_output(['sha256sum',str(O/'manifest.json')],text=True).split()[0];(O/'manifest.sha256').write_text(h+'  manifest.json\n')
print(json.dumps({'manifest_sha256':h,'gate_sha256':manifest['gate_sha256'],'targets':4,'reclaim_bytes':manifest['reclaim_bytes'],'reclaim_MiB':round(manifest['reclaim_bytes']/1024**2,2),'reclaim_GiB':round(manifest['reclaim_bytes']/1024**3,3),'protected_code_or_job_entries':len(index),'retained_original_files':322,'deletions':0}))

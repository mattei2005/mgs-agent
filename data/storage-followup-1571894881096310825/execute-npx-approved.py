"""Run exactly the native-confirmed frozen NPX gate once, then read back."""
import os,sys,json,pathlib,subprocess,importlib.util,datetime
sys.dont_write_bytecode=True
OUT=pathlib.Path(__file__).parent;ROOT=pathlib.Path('/root/mgs-agent')
PRIVATE=pathlib.Path('/root/.hermes/secure-backups/storage-followup-1571894881096310825')
def save(name,obj): (OUT/name).write_text(json.dumps(obj,indent=2)+'\n')
def checkpoint(state,step):
    subprocess.run(['python3',str(ROOT/'scripts/mgs-knowledge-control.py'),'checkpoint-upsert','--id','ZEUS-STORAGE-REMAINDER-1571894881096310825','--agent','zeus','--thread-id','1569928464033783862','--objective','Executar somente a retirada NPX10628files535dirs7links confirmada por Rodolfo1571951994090946631; preservar ambiente utilizado e recuperacao.','--state',state,'--next-step',step,'--source','data/storage-followup-1571894881096310825/npx-retirement-final.json;discord:1569928464033783862/1571951994090946631'],capture_output=True,check=True,text=True)
spec=importlib.util.spec_from_file_location('approved_NPX_gate',OUT/'npx-gate.py');assert spec and spec.loader;g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
assert g.sha(OUT/'npx-retirement-manifest.json')=='7ca6a44275d589695f391d4431c454386558ce318a216486d64270b4a9ecfe1d'
assert g.sha(OUT/'npx-gate.py')=='370734de22329e63aca8d4b85f6ff93bee4de145b7ef1bbbdcf11cd3847c1816'
assert not any((OUT/n).exists()for n in ['npx-approval.json','npx-start.json','npx-journal.jsonl','npx-filesystem-result.json'])
m,rows=g.load()
# Snapshot the entire surviving environment, plus profile controls, without secrets.
keep_before=g.tree(g.KEEP);extra={str(pathlib.Path(g.KEEP)/rel):g.sha(pathlib.Path(g.KEEP)/rel)for rel in ['package.json','package-lock.json','node_modules/.package-lock.json']}
controls={str(pathlib.Path('/root/.hermes/profiles')/p/n):g.sha(pathlib.Path('/root/.hermes/profiles')/p/n)for p in ['zeus','ares','atena']for n in ['SOUL.md','config.yaml']}
(PRIVATE/'npx-kept-tree-before.json').write_text(json.dumps(keep_before,separators=(',',':'))+'\n');save('npx-protected-controls-before.json',controls)
# Reject overlap with profiles, browser assets, Git and financial state.
for protected in ['/root/.hermes','/root/mgs-agent','/root/.cache/ms-playwright','/root/.cache/huggingface']:
    t=pathlib.Path(g.TARGET);p=pathlib.Path(protected);assert t!=p and p not in t.parents and t not in p.parents
approval=dict(owner_id=g.OWNER,thread_id=g.THREAD,native_readback_verified=True,scope_expansion_authorized=False,confirmation_content='Sim',question_message_id='1571903106302873692',confirmation_message_id='1571951994090946631',manifest_sha256=g.sha(OUT/'npx-retirement-manifest.json'),executor_sha256=g.sha(OUT/'npx-gate.py'))
g.approval(approval);g.envelope('npx_retirement_start',approval);g.envelope('npx_retirement_completed',approval);save('npx-approval.json',approval)
checkpoint('approved_exact_npx_execution_pending','Sim1571951994090946631 recebido e validado. Frozen gate revalida escopo/fingerprints/consumidores/recovery; executar1x. Se parcial ler journal, nunca repetir exclusao cegamente.')
r=subprocess.run(['python3','-B',str(OUT/'npx-gate.py'),'--execute'],capture_output=True,text=True,timeout=240);save('npx-execution-output.json',dict(exit_code=r.returncode,stdout=r.stdout,stderr=r.stderr));assert r.returncode==0,r.stderr[-2500:]
post=json.loads(r.stdout);journal=[json.loads(x)for x in(OUT/'npx-journal.jsonl').read_text().splitlines()]
assert len(journal)==len(rows)and {x['relative']for x in journal}=={x['relative']for x in rows}and all(x['absent']for x in journal)
assert not os.path.lexists(g.TARGET)and g.tree(g.KEEP)==keep_before
assert all(g.sha(p)==h for p,h in extra.items())and all(g.sha(p)==h for p,h in controls.items())
reader=PRIVATE/'npx-recover.py';assert g.sha(reader)==m['protected_helpers'][str(reader)]
r=subprocess.run(['python3','-B',str(reader),str(OUT/'npx-retirement-manifest.json')],capture_output=True,text=True,timeout=180);save('npx-independent-post.json',dict(exit_code=r.returncode,stdout=r.stdout,stderr=r.stderr));assert r.returncode==0,r.stderr[-2000:];ind=json.loads(r.stdout)
assert ind['regular_files_materialized_in_RAM']==10628 and ind['original_payload_reads']==0
interval=json.load(open(OUT/'npx-disk-interval.json'));counts={k:sum(x['kind']==k for x in journal)for k in ['file','directory','link']};assert counts==dict(file=10628,directory=535,link=7)
result=dict(status='filesystem_retired_validated_availability_governance_pending',confirmation_message_id=approval['confirmation_message_id'],question_message_id=approval['question_message_id'],manifest_sha256=approval['manifest_sha256'],executor_sha256=approval['executor_sha256'],target=g.TARGET,files_deleted=counts['file'],directories_deleted_including_root=counts['directory'],symlinks_deleted=counts['link'],journal_entries=len(journal),retained_environment_unchanged=True,protected_profile_controls_unchanged=len(controls),post_retained_RAM_files=post['recovery']['regular_files_materialized_in_RAM'],post_independent_RAM_files=ind['regular_files_materialized_in_RAM'],original_source_payload_reads_by_recovery=0,symlink_targets_verified=7,full_layout_materialized=False,Security_scan_or_authentication_executed=False,runtime=post['runtime'],runtime_unchanged=True,observed_available_delta_bytes=interval['observed_global_delta_bytes'],delta_is_global_filesystem_observation=True,whole_disk_review_complete=False,at=datetime.datetime.now().astimezone().isoformat())
save('npx-retirement-final.json',result)
checkpoint('npx_filesystem_retired_validated_governance_pending','10628files535dirs7links ausentes/journal11170exato;RAM10628x2posPASS/f4a9tree6controlsiguais/PIDsbootiguais. Nao repetir exclusao. Falta disponibilidade3perfis/canarioCLI/inventario/REPORT/Git.')
print(json.dumps(result))

"""Execute only the frozen stage code lot after native confirmation."""
import os, sys, pathlib, json, subprocess, importlib.util, stat, datetime
sys.dont_write_bytecode = True
OUT = pathlib.Path(__file__).parent
ROOT = pathlib.Path('/root/mgs-agent')
def save(name, data):
    (OUT / name).write_text(json.dumps(data, indent=2) + '\n')
def disk():
    s = os.statvfs('/')
    return dict(at=datetime.datetime.now().astimezone().isoformat(), total=s.f_blocks*s.f_frsize, used=(s.f_blocks-s.f_bfree)*s.f_frsize, available=s.f_bavail*s.f_frsize)
def checkpoint(state, next_step):
    subprocess.run(['python3', str(ROOT/'scripts/mgs-knowledge-control.py'), 'checkpoint-upsert', '--id', 'ZEUS-STORAGE-STAGES-1571713397446418446', '--agent', 'zeus', '--thread-id', '1569928464033783862', '--objective', 'Retirar somente 1239 copias de codigo confirmadas por Rodolfo; preservar fontes e diretorios.', '--state', state, '--next-step', next_step, '--source', 'data/storage-stages-1571713397446418446/retirement-final.json;discord:1569928464033783862/1571887665589133363'], check=True, capture_output=True)
spec = importlib.util.spec_from_file_location('approved_gate', OUT/'retire.py')
g = importlib.util.module_from_spec(spec); spec.loader.exec_module(g)
assert g.rec.sha(OUT/'retirement-manifest.json') == '7cd63295cd37cec57dffab01cacf5a7bdc4c822987028b47d42f2d63235181de'
assert g.rec.sha(OUT/'retire.py') == '938385d63c4206d88f22d97655e8b0b420980b8945f42640ee1f7f295b90da32'
assert not any((OUT/n).exists() for n in ['approval.json', 'retirement-start.json', 'retirement-journal.jsonl', 'retirement-filesystem-result.json'])
m, rows = g.rec.load(); target_paths = {x['source']['path'] for x in rows}
# All remaining regular stage files and directory identities are outside deletion.
def survivors():
    files = {}; dirs = {}
    for root in m['allowed_roots']:
        for d, ds, fs in os.walk(root, followlinks=False):
            s = os.lstat(d); dirs[d] = [s.st_dev, s.st_ino, stat.S_IMODE(s.st_mode), s.st_uid, s.st_gid]
            for n in fs:
                p = pathlib.Path(d)/n
                if str(p) in target_paths: continue
                s = os.lstat(p)
                assert stat.S_ISREG(s.st_mode)
                files[str(p)] = dict(metadata=g.rec.metadata(p), sha256=g.rec.sha(p))
    return dict(files=files, directories=dirs)
before_survivors = survivors(); save('retained-stage-before.json', before_survivors)
controls = {str(pathlib.Path('/root/.hermes/profiles')/p/n): g.rec.sha(pathlib.Path('/root/.hermes/profiles')/p/n) for p in ['zeus','ares','atena'] for n in ['SOUL.md','config.yaml']}
save('protected-controls-before.json', controls)
a = dict(owner_id=g.OWNER, thread_id=g.THREAD, native_readback_verified=True, scope_expansion_authorized=False, confirmation_content='sim', question_message_id='1571727696801562719', confirmation_message_id='1571887665589133363', manifest_sha256=g.rec.sha(OUT/'retirement-manifest.json'), executor_sha256=g.rec.sha(OUT/'retire.py'))
g.approval(a)
for action in ['stage_code_retirement_start','stage_code_retirement_completed']: g.envelope(action,a)
save('approval.json',a)
checkpoint('approved_execution_preflight', 'Sim1571887665589133363 recebido; executar frozen gate uma vez; se parcial reconciliar journal, nunca repetir unlink cegamente.')
# Gate rechecks consumers, exact targets, retained providers and RAM recovery.
before = disk(); save('retirement-disk-before.json',before)
r = subprocess.run(['python3','-B',str(OUT/'retire.py'),'--execute'],capture_output=True,text=True,timeout=240)
after = disk(); save('retirement-disk-immediate-after.json',after)
save('execution-output.json',dict(exit_code=r.returncode,stdout=r.stdout,stderr=r.stderr))
assert r.returncode == 0, r.stderr[-2000:]
post = json.loads(r.stdout)
journal = [json.loads(x) for x in (OUT/'retirement-journal.jsonl').read_text().splitlines()]
assert len(journal)==len(rows)==1239 and {x['path'] for x in journal}==target_paths
assert all(x['absent'] and not os.path.lexists(x['path']) for x in journal)
assert survivors()==before_survivors
assert all(g.rec.sha(p)==h for p,h in controls.items())
save('retirement-preservation.json',dict(status='PASS',retained_stage_regular_files=len(before_survivors['files']),retained_stage_directories=len(before_survivors['directories']),protected_controls=len(controls),all_equal=True,targets_absent=len(journal)))
# Repeat the independent private reader, using retained inputs only.
private = pathlib.Path(m['targets_index']).parent/'recover.py'
assert private.exists()
r = subprocess.run(['python3','-B',str(private)],capture_output=True,text=True,timeout=180)
save('independent-post.json',dict(exit_code=r.returncode,stdout=r.stdout,stderr=r.stderr))
assert r.returncode==0,r.stderr[-2000:]
result = dict(status='filesystem_retirement_validated_availability_and_governance_pending',confirmation_message_id=a['confirmation_message_id'],manifest_sha256=a['manifest_sha256'],executor_sha256=a['executor_sha256'],files_deleted=len(journal),directories_deleted=0,post_RAM_restores=post['RAM_recovery']['files_materialized'],original_source_payload_reads=post['RAM_recovery']['original_source_payload_reads'],independent_reader_exit_code=r.returncode,runtime_unchanged=True,retained_stage_files_unchanged=len(before_survivors['files']),retained_directories=len(before_survivors['directories']),protected_controls_unchanged=len(controls),observed_available_delta_bytes=after['available']-before['available'],delta_is_global_filesystem_observation=True,full_historical_environment_restore=False,whole_disk_review_complete=False,at=datetime.datetime.now().astimezone().isoformat())
save('retirement-final.json',result)
checkpoint('filesystem_retired_validated_governance_pending','1239 ausentes/journal exato; RAM recovery pos/independente OK; validar disponibilidade3perfis e concluir inventario/REPORT/Git. Nao repetir exclusao.')
print(json.dumps(result))

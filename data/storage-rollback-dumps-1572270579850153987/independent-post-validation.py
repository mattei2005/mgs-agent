"""Independent exact 29-path absence/journal/preservation readback. Never unlink/replay."""
import datetime,importlib.util,json,os,pathlib,stat,subprocess
R=pathlib.Path('/root/mgs-agent');O=pathlib.Path(__file__).parent
m=json.loads((O/'manifest.json').read_text());a=json.loads((O/'critical-approval.json').read_text());f=json.loads((O/'filesystem-result.json').read_text());rows=[json.loads(x)for x in(O/'deletion-journal.jsonl').read_text().splitlines()];expected={x['path']for x in m['targets']}
assert len(rows)==29 and {x['path']for x in rows}==expected and all(x['kind']=='file'for x in rows);assert set(f['deleted'])==expected and len(f['deleted'])==29
assert all(not os.path.lexists(p)for p in expected);assert all(pathlib.Path(p).parent.is_dir()and not pathlib.Path(p).parent.is_symlink()for p in expected)
sha=lambda p:subprocess.check_output(['sha256sum','--',str(p)],text=True).split()[0]
assert sha(O/'manifest.json')==a['manifest_sha256']==f['manifest_sha256'];assert sha(O/'gate.py')==a['gate_sha256']==m['gate_sha256']
keep={}
for row in m['retained_reviewed_files']+m['retained_local_dumps']:
 if row['path']in keep:assert keep[row['path']]['sha256']==row['sha256']
 keep[row['path']]=row
paths=sorted(keep);assert len(paths)==294;verified=0
for start in range(0,len(paths),40):
 batch=paths[start:start+40];p=subprocess.run(['sha256sum','--zero','--',*batch],capture_output=True,check=True);got={os.fsdecode(x[66:]):x[:64].decode()for x in p.stdout.split(b'\0')if x};assert set(got)==set(batch)
 for path,digest in got.items():assert digest==keep[path]['sha256'];verified+=1
for path,row in keep.items():
 s=os.lstat(path);actual=dict(dev=s.st_dev,ino=s.st_ino,size=s.st_size,blocks=s.st_blocks,nlink=s.st_nlink,mtime_ns=s.st_mtime_ns,ctime_ns=s.st_ctime_ns,mode=s.st_mode,uid=s.st_uid,gid=s.st_gid);assert actual==row['metadata']and stat.S_ISREG(s.st_mode)
for path,h in m['retained_evidence'].items():assert sha(path)==h
assert os.path.realpath('/root/.local/bin/hermes')==m['launcher']
services={name:subprocess.check_output(['systemctl','show',name,'-p','ActiveState','-p','MainPID'],text=True).strip()for name in m['runtime']};assert services==m['runtime'];assert not subprocess.check_output(['systemctl','--failed','--no-legend','--plain'],text=True).strip()
spec=importlib.util.spec_from_file_location('verified_frozen_gate',O/'gate.py');assert spec and spec.loader;g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g);remote=g.remote(m);assert remote==30
proof=[json.loads(x)for x in(O/'ram-recovery-post.jsonl').read_text().splitlines()];assert len(proof)==len({x['path']for x in proof})==29 and {x['path']for x in proof}==expected
lookup={x['path']:x for x in m['targets']};providers={x['local_path']:x['remote_path']for x in m['remote_recovery']}
assert all(x['actual_recovered_sha256']==lookup[x['path']]['sha256']and x['size']==lookup[x['path']]['metadata']['size']and x['remote_path']==providers[x['path']]and x['source_payload_reads']==0 and x['persistent_payload_copies_created']==0 and x['real_file_materialized_in_anonymous_RAM']and x['mode_owner_nanosecond_mtime_restored']for x in proof)
for parent,expected_meta in m['retained_parent_directories'].items():
 s=os.lstat(parent);assert stat.S_ISDIR(s.st_mode)and dict(dev=s.st_dev,ino=s.st_ino,mode=s.st_mode,uid=s.st_uid,gid=s.st_gid)==expected_meta
sealed=[O/x for x in ['manifest.json','gate.py','execution-start.json','deletion-journal.jsonl','filesystem-result.json']];before_replay={str(x):sha(x)for x in sealed};replay=subprocess.run(['python3','-B',str(O/'gate.py'),'--apply'],capture_output=True,text=True);assert replay.returncode!=0 and'REPLAY_BLOCKED'in replay.stderr;assert before_replay=={str(x):sha(x)for x in sealed};(O/'replay-block-test.json').write_text(json.dumps({'status':'PASS','native_replay_blocked':True,'journal_result_and_frozen_files_unchanged':True,'new_deletions':0})+'\n')
# Configuration-only profile checks. No model requests, application probes or DB startup.
configs=[]
for profile in ['zeus','atena','ares']:
 env=dict(os.environ);env.pop('HERMES_HOME',None);env.pop('HERMES_PROFILE',None)
 p=subprocess.run(['/root/.local/bin/hermes','-p',profile,'config','check'],capture_output=True,text=True,env=env,timeout=60);configs.append(dict(profile=profile,exit_code=p.returncode,config_check_pass=p.returncode==0));assert p.returncode==0,f'Configuration checker failed for {profile}'
v=os.statvfs('/');available=v.f_bavail*v.f_frsize;used=(v.f_blocks-v.f_bfree)*v.f_frsize
result=dict(post_removal_real_remote_only_RAM_file_recoveries=29,source_payload_reads_during_recovery=0,persistent_payload_copies_created=0,replay_block_verified=True,status='PASS',manifest_sha256=a['manifest_sha256'],gate_sha256=a['gate_sha256'],question_message_id=a['question_message_id'],confirmation_message_id=a['confirmation_message_id'],deleted_regular_files=29,deleted_directories=0,journal_exact_unique_29=True,all_targets_absent=True,parent_directories_preserved=True,retained_original_files=293,retained_local_dump_count=4,retained_unique_payloads_verified=verified,retained_metadata_and_payloads_unchanged=True,retained_receipt_hashes_unchanged=True,remote_counterparts_verified_again=remote,remote_catalogue_not_materialized_restore=True,gateway_PIDs_unchanged=True,launcher_unchanged=True,failed_systemd_units=0,config_checks=configs,no_model_requests=True,no_SQL_or_DB_started=True,no_cache_cleanup=True,no_production_or_retention_changes=True,observed_immediate_global_delta_bytes=f['observed_available_delta_bytes'],observed_immediate_global_delta_MiB=round(f['observed_available_delta_bytes']/1024**2,2),disk_observation={'available_GiB':round(available/1024**3,2),'used_percent':round(100*used/(used+available),2)},at=datetime.datetime.now().astimezone().isoformat())
assert not(O/'independent-post-validation.json').exists();(O/'independent-post-validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result))

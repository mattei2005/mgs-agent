"""Execute the exact native UV retirement confirmed by Rodolfo, once."""
import pathlib,json,os,subprocess,sys,importlib.util,datetime,stat
sys.dont_write_bytecode=True
ROOT=pathlib.Path('/root/mgs-agent');OUT=pathlib.Path(__file__).parent;PRIVATE=pathlib.Path('/root/.hermes/secure-backups/storage-uv-1571959754081837281')
def save(n,d):(OUT/n).write_text(json.dumps(d,indent=2)+'\n')
def checkpoint(state,step):
 subprocess.run(['python3',str(ROOT/'scripts/mgs-knowledge-control.py'),'checkpoint-upsert','--id','ZEUS-STORAGE-UV-1571959754081837281','--agent','zeus','--thread-id','1569928464033783862','--objective','Executar uma vez o lote nativo UV193alvos confirmado1571969258986938601; preservar instalados/cachePM e verificar resultado real.','--state',state,'--next-step',step,'--source','data/storage-uv-1571959754081837281/retirement-final.json;discord:1569928464033783862/1571969258986938601'],capture_output=True,check=True,text=True)
spec=importlib.util.spec_from_file_location('UV_approved_gate',OUT/'prune-gate.py');assert spec and spec.loader;g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
assert g.sha(OUT/'prune-manifest.json')=='a878f47d10bd25d28eff9dcc4673dbf58172ccaefbb19163c2c8a67e4b8143ed'
assert g.sha(OUT/'prune-gate.py')=='87d66ae35db2bf091003c9df93c8ad8ab352ac1ad0915a636a8611b03a157804'
assert not any((OUT/n).exists()for n in ['prune-approval.json','prune-start.json','prune-native-result.json','prune-post.json'])
m,rows=g.load()
controls={str(pathlib.Path('/root/.hermes/profiles')/p/n):g.sha(pathlib.Path('/root/.hermes/profiles')/p/n)for p in ['zeus','ares','atena']for n in ['SOUL.md','config.yaml']};save('retirement-controls-before.json',controls)
# The managed Hermes cache is a different root; compare payloads, not mutable hardlink ctime.
managed=pathlib.Path(json.load(open(OUT/'hermes-uv-isolation.json'))['hermes_cache_path']);assert not any(managed==pathlib.Path(t)or pathlib.Path(t)in managed.parents or managed in pathlib.Path(t).parents for t in m['targets'])
def managed_paths():
 result={};payload=[]
 for d,ds,fs in os.walk(managed,followlinks=False):
  for n in ds+fs:
   p=pathlib.Path(d)/n;s=os.lstat(p);kind='file'if stat.S_ISREG(s.st_mode)else'directory'if stat.S_ISDIR(s.st_mode)else'link'if stat.S_ISLNK(s.st_mode)else'other';assert kind!='other'
   row=dict(kind=kind,dev=s.st_dev,ino=s.st_ino,mode=stat.S_IMODE(s.st_mode),uid=s.st_uid,gid=s.st_gid)
   if kind=='file':row.update(size=s.st_size,mtime_ns=s.st_mtime_ns);payload.append(str(p))
   if kind=='link':row['target']=os.readlink(p)
   result[str(p.relative_to(managed))]=row
 return result,payload
managed_before,names=managed_paths();managed_hashes=g.payload_hashes(names);(PRIVATE/'managed-cache-before-metadata.json').write_text(json.dumps(managed_before,separators=(',',':'))+'\n');(PRIVATE/'managed-cache-before-sha256.json').write_text(json.dumps(managed_hashes,separators=(',',':'))+'\n')
a=dict(owner_id=g.OWNER,thread_id=g.THREAD,native_readback_verified=True,scope_expansion_authorized=False,historical_cached_state_retirement_approved=True,confirmation_content='sim',question_message_id='1571968776956809328',confirmation_message_id='1571969258986938601',manifest_sha256=g.sha(OUT/'prune-manifest.json'),executor_sha256=g.sha(OUT/'prune-gate.py'))
g.approval(a);g.envelope('UV_native_prune_start',a);g.envelope('UV_native_prune_completed',a);save('prune-approval.json',a)
checkpoint('approved_native_uv_execution_pending','Sim1571969258986938601 validado; frozenmanifest/exec originais. Executar1x native prune offline/semforce/ci. Se falha ler native-result e target-readback; nunca repetir comando cegamente.')
r=subprocess.run(['python3','-B',str(OUT/'prune-gate.py'),'--execute'],capture_output=True,text=True,timeout=300);save('execution-output.json',dict(exit_code=r.returncode,stdout=r.stdout,stderr=r.stderr));assert r.returncode==0,r.stderr[-2500:]
post=json.loads(r.stdout);native=json.load(open(OUT/'prune-native-result.json'));readback=json.load(open(OUT/'prune-target-readback.json'));assert native['exit_code']==0 and len(readback)==193 and {x['path']for x in readback}==set(m['targets'])and all(x['absent']for x in readback)
assert all(not os.path.lexists(t)for t in m['targets']);assert all(g.sha(p)==h for p,h in controls.items());managed_after,newnames=managed_paths();assert managed_after==managed_before and g.payload_hashes(newnames)==managed_hashes
result=dict(status='native_uv_retirement_validated_availability_governance_pending',confirmation_message_id=a['confirmation_message_id'],question_message_id=a['question_message_id'],manifest_sha256=a['manifest_sha256'],executor_sha256=a['executor_sha256'],native_exit_code=native['exit_code'],native_argv=m['native_argv'],native_targets_absent=193,removed_node_counts=m['target_node_counts'],retained_cache_payloads_verified=post['retained_unique_payloads_hashed'],remaining_cache_metadata_nodes=post['whole_cache_metadata_nodes'],managed_cache_preserved=True,managed_cache_payloads_verified=len(managed_hashes),profile_controls_unchanged=len(controls),runtime=post['runtime'],runtime_unchanged=True,observed_available_delta_bytes=native['observed_global_delta_bytes'],global_filesystem_delta_not_exclusive_attribution=True,historical_cached_state_retirement_approved=True,exact_old_environment_restore_proven=False,new_retention_or_cron=False,whole_disk_review_complete=False,at=datetime.datetime.now().astimezone().isoformat())
save('retirement-final.json',result)
checkpoint('native_uv_retired_validated_governance_pending','193alvos ausentes/native0;235046files26594dirs415links;63046retainedhashes ecachePM/6controlsiguais;PIDsbootiguais. Nao repetirprune. Falta3profiles/configsmokes e inventario/REPORT/Git;globalaberto.')
print(json.dumps(result))

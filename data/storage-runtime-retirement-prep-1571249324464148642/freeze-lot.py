import pathlib,importlib.util,json,subprocess,os,time,collections,stat,datetime,gzip
os.umask(0o077)
OUT=pathlib.Path(__file__).parent;SEC=pathlib.Path('/root/.hermes/secure-backups/runtime-retirement/1571249324464148642');spec=importlib.util.spec_from_file_location('validator',OUT/'verify-lot.py');assert spec and spec.loader;v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
assert not(OUT/'deletion-manifest.json').exists(),'Frozen manifest already exists; reconcile before retry'
# All source Git probes finished before this point. Freeze exact metadata twice.
assert not v.process_references(list(v.EXPECTED));assert not v.consumer_references()
first={p:v.collect(p,SEC/('target-'+str(n)+'-ledger.jsonl.gz'))for n,p in enumerate(v.EXPECTED)};time.sleep(1);second={p:v.collect(p)for p in v.EXPECTED};assert all(first[p]['fingerprint']==second[p]['fingerprint']for p in first)
inodes={};counts={'files':0,'directories':0,'symlinks':0};targets=[];naive=0
for p,action in v.EXPECTED.items():
 r=first[p];targets.append({'path':p,'action':action,'fingerprint':r['fingerprint'],'counts':r['counts'],'root_identity':r['root_identity']})
 for k,n in r['counts'].items():counts[k]+=n
 for node in r['nodes']:
  key=(node['dev'],node['ino']);entry=inodes.setdefault(key,{'bytes':node['allocated'],'nlink':node['nlink'],'kind':node['kind'],'links_in_set':0});entry['links_in_set']+=1;naive+=node['allocated']
reclaim=sum(r['bytes']for r in inodes.values()if r['kind']=='directory'or r['links_in_set']>=r['nlink'])
protected=json.load(open(OUT/'protected-before.json'));retained_hashes=protected['files'][:]
# Freeze Git administration from retained stores, not broad ancestor content.
for root in ['hermes-agent-port-main-59004a62-mgs','hermes-agent-port-main-3f2afed3-mgs-20261021']:
 for name in ['config','HEAD','packed-refs']:
  p=pathlib.Path('/root/.hermes')/root/'.git'/name
  if p.is_file():retained_hashes.append({'path':str(p),'sha256':v.sha(p)})
for row in protected['launchers'].values():
 pass
launcher=pathlib.Path('/root/.local/bin/hermes').resolve();retained_hashes.append({'path':str(launcher),'sha256':v.sha(launcher)})
code=json.load(open(OUT/'code-recovery-spec.json'));env=json.load(open(OUT/'environment-audit.json'));retained_paths=[code['retained_repository'],'/root/.hermes/hermes-agent','/root/.hermes/hermes-agent-port-main-29a61cb7-mgs-20261103','/root/.hermes/hermes-agent-port-main-59004a62-mgs','/root/.hermes/hermes-agent-port-main-59004a62-mgs/.git/objects','/root/.local/share/uv/python/cpython-3.14-linux-x86_64-gnu/bin/python3.14']
retained_paths +=['/root/.hermes/profiles/'+p for p in ['zeus','ares','atena']]
retained_paths +=[code['archive'],env['python_overrides']['archive'],env['node_preservation']['archive'],str(SEC)]
for p in [pathlib.Path(code['archive']),*[p for p in SEC.iterdir()if p.is_file()and p.name.endswith(('.pack','.json','.json.gz','.tar.gz'))]]:retained_hashes.append({'path':str(p),'sha256':v.sha(p)})
retained_hashes.append({'path':str(pathlib.Path(retained_paths[5]).resolve()),'sha256':v.sha(pathlib.Path(retained_paths[5]).resolve())})
seen=set();retained_hashes=[r for r in retained_hashes if not(r['path']in seen or seen.add(r['path']))]
for path in v.EXPECTED:
 for profile in ['/root/.hermes/profiles/zeus','/root/.hermes/profiles/ares','/root/.hermes/profiles/atena']:
  assert not pathlib.Path(path).is_relative_to(profile)and not pathlib.Path(profile).is_relative_to(path)
helper_sha={p:v.sha(OUT/p)for p in ['verify-lot.py','recover-retained.py','execute-lot.py']}
fs=os.statvfs('/');used=(fs.f_blocks-fs.f_bfree)*fs.f_frsize;available=fs.f_bavail*fs.f_frsize;new_storage=0;seen_inodes=set()
for root in [SEC,OUT]:
 for directory,dirs,files in os.walk(root,followlinks=False):
  for p in [pathlib.Path(directory),*[pathlib.Path(directory,n)for n in files]]:
   s=p.lstat();key=(s.st_dev,s.st_ino)
   if key not in seen_inodes:seen_inodes.add(key);new_storage+=s.st_blocks*512
m={'schema_version':1,'lot_id':'runtime-retirement-1571249324464148642','authority':{'owner_id':'344196393512075265','preparation_message_id':'1571249324464148642','thread_id':'1569928464033783862'},'no_deletion_authorization':True,'targets':targets,'counts':counts,'naive_allocated_bytes':naive,'inode_aware_reclaim_bytes':reclaim,'new_preservation_and_evidence_bytes_at_freeze':new_storage,'estimated_net_reduction_vs_preparation_start_bytes':reclaim-new_storage,'full_old_python_environment_rebuilt':False,'irreversible_effect':'Old paths, legacy launcher and linked-worktree registration disappear; exact code/state/Node payloads and Python local adjustments are preserved, but old Python environments stop being ready-to-run and require recreation. No claim of full runnable old-Python restoration.','native_admin_scope':'Only .git/worktrees/hermes-agent-port-main-ad2d4822-mgs exists in the frozen admin parent. Native git worktree remove --force removes the linked checkout/registration; the exact parent is removed only if empty. No object store, branch ref, other worktree or common Git root is deleted.','retained_paths':retained_paths,'retained_hashes':retained_hashes,'live_launcher_target':str(launcher),'gateway_pids':{p:r['pid']for p,r in protected['services'].items()},'helper_sha256':helper_sha,'filesystem_before':{'used_bytes':used,'available_bytes':available,'used_percent':round(100*used/(used+available),2),'projected_after_delete_percent':round(100*(used-reclaim)/(used+available),2)},'required_approval':'Fresh native Rodolfo confirmation of this exact manifest SHA256 and executor SHA256, after disclosure; no prior lot approval transfers.','created_at':datetime.datetime.now().astimezone().isoformat()}
p=OUT/'deletion-manifest.json';p.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n');digest=v.sha(p);(OUT/'deletion-manifest.sha256').write_text(digest+'  deletion-manifest.json\n');subprocess.run(['sha256sum','-c','deletion-manifest.sha256'],cwd=OUT,check=True)
print(json.dumps({'manifest_sha256':digest,'counts':counts,'exact_paths':len(targets),'reclaim_gib':round(reclaim/2**30,3),'new_preservation_gib':round(new_storage/2**30,3),'estimated_net_gib':round((reclaim-new_storage)/2**30,3),'filesystem':m['filesystem_before'],'helper_sha256':helper_sha}))

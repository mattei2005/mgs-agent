import pathlib,os,json,gzip,subprocess,tarfile,hashlib,io,stat,datetime,shutil
os.umask(0o077)
OUT=pathlib.Path('/root/mgs-agent/data/storage-runtime-review-1571217101597712496');SEC=pathlib.Path('/root/.hermes/secure-backups/runtime-review/20261114-1571217101597712496');STAGE=pathlib.Path('/root/.hermes/hermes-agent-stage-main-7cc3fb8c-mgs');NEST=pathlib.Path('/root/.hermes/secure-backups/hermes-update/20261012-1559192694096404537-preport/clean-target-7cc3fb8c');SCR=pathlib.Path('/root/.hermes/profiles/zeus/cache/scratch/runtime-code-replay-1571217101597712496');SCR.mkdir(mode=0o700,exist_ok=True)
HEAD='e6ad505398ac5956bdbefd9e111a598c5e6b6575';BASE='7cc3fb8cb55898747dd1dfa56fda3e16ebba028e';REPO='/root/.hermes/hermes-agent-port-main-3f2afed3-mgs-20261021';ENV={**os.environ,'GIT_OPTIONAL_LOCKS':'0'}
def run(*args,**kw):return subprocess.run(list(args),capture_output=True,check=True,env=ENV,**kw)
def sha(p):return run('sha256sum',str(p)).stdout.decode().split()[0]
stage=json.load(gzip.open(OUT/'hermes-agent-stage-main-7cc3fb8c-mgs-git.json.gz','rt'));ignored=json.load(gzip.open(OUT/'hermes-agent-stage-main-7cc3fb8c-mgs-ignored.json.gz','rt'))['potential_meaningful'];nested=json.load(open(OUT/'nested-code-comparison.json'))
assert not nested['missing_base_paths']
patch=run('git','-C',str(STAGE),'diff','--binary','--no-ext-diff','HEAD').stdout
entries=[]
for rel in stage['untracked_paths']+ignored:entries.append(('stage-overlay/'+rel,STAGE/rel))
for rel in nested['different_paths']+nested['extra_paths']:entries.append(('nested-overlay/'+rel,NEST/rel))
# Preserve Git administration (including reflogs/config/index/alternates) but not duplicate object packs.
for d,ds,fs in os.walk(STAGE/'.git',followlinks=False):
 if pathlib.Path(d)==STAGE/'.git':ds[:]=[x for x in ds if x!='objects']
 for f in fs:entries.append(('stage-git-metadata/'+str(pathlib.Path(d,f).relative_to(STAGE/'.git')),pathlib.Path(d,f)))
assert len({name for name,p in entries})==len(entries)
record=[]
for name,p in entries:
 s=p.lstat();r={'member':name,'source':str(p),'mode':s.st_mode,'size':s.st_size,'mtime_ns':s.st_mtime_ns,'ctime_ns':s.st_ctime_ns}
 if stat.S_ISREG(s.st_mode):r['sha256']=sha(p)
 elif stat.S_ISLNK(s.st_mode):r['link_target']=os.readlink(p)
 else:raise AssertionError('Unexpected overlay type')
 record.append(r)
archive=SEC/'code-differences-and-git-metadata.tar.gz';assert not archive.exists(),'Existing preservation archive: reconcile before retry'
with tarfile.open(archive,'w:gz',format=tarfile.PAX_FORMAT,dereference=False) as tf:
 for name,p in entries:tf.add(p,arcname=name,recursive=False)
 for name,data in [('stage-working-tree.patch',patch),('stage-refs.json',json.dumps(stage['ref_objects']).encode())]:
  m=tarfile.TarInfo(name);m.mode=0o600;m.size=len(data);tf.addfile(m,io.BytesIO(data))
# Read every preserved byte independently, without extracting Git configuration or auth code into a live path.
seen=set();small={}
with tarfile.open(archive,'r:gz') as tf:
 for m in tf:
  assert m.name not in seen;seen.add(m.name)
  if m.isfile() or m.islnk():
   data=tf.extractfile(m).read();small[m.name]=data
   rr=next((r for r in record if r['member']==m.name),None)
   if rr:assert hashlib.sha256(data).hexdigest()==rr['sha256'] and len(data)==rr['size']
  elif m.issym():assert next(r for r in record if r['member']==m.name)['link_target']==m.linkname
assert seen=={r['member'] for r in record}|{'stage-working-tree.patch','stage-refs.json'}
# Replay the exact dirty source patch on pristine blobs recovered from the retained repository.
stagedest=SCR/'stage-changed-code';stagedest.mkdir(exist_ok=True)
for rel in stage['modified_paths']:
 p=stagedest/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(run('git','-C',REPO,'show',HEAD+':'+rel).stdout)
 mode=run('git','-C',REPO,'ls-tree',HEAD,'--',rel).stdout.split()[0];os.chmod(p,0o755 if mode==b'100755' else 0o644)
patchfile=SCR/'stage-working-tree.patch';patchfile.write_bytes(small['stage-working-tree.patch']);run('git','-C',str(stagedest),'apply','--check',str(patchfile));run('git','-C',str(stagedest),'apply',str(patchfile))
replayed=0
for rel in stage['modified_paths']:
 assert sha(stagedest/rel)==sha(STAGE/rel);replayed+=1
for r in record:
 if r['member'].startswith('stage-overlay/'):
  rel=r['member'][len('stage-overlay/'):];p=stagedest/rel;p.parent.mkdir(parents=True,exist_ok=True)
  if 'sha256' in r:p.write_bytes(small[r['member']]);assert sha(p)==r['sha256'];replayed+=1
# Materialize only differing/extra nested code, not a bulky second full checkout.
nestdest=SCR/'nested-different-code';nestdest.mkdir(exist_ok=True);nested_replayed=0
for r in record:
 if not r['member'].startswith('nested-overlay/'):continue
 rel=r['member'][len('nested-overlay/'):];p=nestdest/rel;p.parent.mkdir(parents=True,exist_ok=True)
 if 'sha256' in r:p.write_bytes(small[r['member']]);assert sha(p)==r['sha256'];nested_replayed+=1
# Ensure source overlays and Git administrative files did not drift during preservation.
for r in record:
 p=pathlib.Path(r['source']);s=p.lstat();assert (s.st_mode,s.st_size,s.st_mtime_ns,s.st_ctime_ns)==(r['mode'],r['size'],r['mtime_ns'],r['ctime_ns'])
 if 'sha256' in r:assert sha(p)==r['sha256']
proof={'status':'code_preservation_and_focused_replay_validated','authority_message_id':'1571217101597712496','archive':str(archive),'archive_sha256':sha(archive),'archive_allocated_bytes':archive.stat().st_blocks*512,'self_contained':False,'required_retained_repositories':[REPO,'/root/.hermes/hermes-agent-port-main-59004a62-mgs','/root/.hermes/hermes-agent-port-main-29a61cb7-mgs-20261103','/root/.hermes/hermes-agent'],'stage_base_commit':HEAD,'nested_base_commit':BASE,'stage_modified_files_replayed':len(stage['modified_paths']),'stage_overlay_files_replayed':replayed,'nested_modified_or_extra_files_replayed':nested_replayed,'nested_unchanged_base_files_verified':nested['matched_regular_files'],'git_metadata_members':sum(r['member'].startswith('stage-git-metadata/') for r in record),'preserved_members':len(seen),'original_overlay_hashes_and_metadata_unchanged':True,'no_live_profile_or_sqlite_open':True,'full_old_virtualenv_rebuilt':False,'old_environment_cache_disposal_requires_exact_confirmation':True,'scratch_replay_root':str(SCR),'created_at':datetime.datetime.now().astimezone().isoformat()}
(SEC/'code-preservation-manifest.json').write_text(json.dumps({'entries':record,'stage_modified_paths':stage['modified_paths'],'nested_missing_paths':nested['missing_base_paths'],'proof':proof},indent=2)+'\n');(OUT/'code-preservation-result.json').write_text(json.dumps(proof,indent=2)+'\n')
print(json.dumps(proof))

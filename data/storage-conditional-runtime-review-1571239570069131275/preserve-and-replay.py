import pathlib,os,json,subprocess,tarfile,io,hashlib,stat,datetime,runpy,types,sys,ast
os.umask(0o077)
ID='1571239570069131275';BASE=pathlib.Path('/root/mgs-agent');OUT=BASE/('data/storage-conditional-runtime-review-'+ID);SEC=pathlib.Path('/root/.hermes/secure-backups/runtime-review/20261114-'+ID);SCR=pathlib.Path('/root/.hermes/profiles/zeus/cache/scratch/conditional-runtime-replay-'+ID);SCR.mkdir(mode=0o700,exist_ok=True)
ENV=dict(os.environ,GIT_OPTIONAL_LOCKS='0',PYTHONDONTWRITEBYTECODE='1');RETAINED=pathlib.Path('/root/.hermes/hermes-agent-port-main-3f2afed3-mgs-20261021')
def run(*a,**kw):return subprocess.run(list(map(str,a)),capture_output=True,env=ENV,check=True,**kw)
def sha(p):return run('sha256sum','--',p).stdout.decode().split()[0]
records=[];patches={};states=[];refproof=[]
for f in sorted(OUT.glob('*-git-state.json')):
 d=json.load(open(f));states.append(d);root=pathlib.Path(d['root']);prefix=root.name
 meaningful=[x for x in d['ignored_paths']if not any(y in x.split('/')for y in ['.venv','node_modules','__pycache__','.pytest_cache','.pytest-cache','.git','.ruff_cache'])and not x.endswith(('.pyc','.pyo'))]
 patch=run('git','-C',root,'diff','--binary','--no-ext-diff','HEAD').stdout;patches[prefix]=patch
 # HEAD recovery must exercise every tracked tree/blob, not just cat-file -e.
 result=subprocess.run(['git','-C',str(RETAINED),'archive','--format=tar',d['head']],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,env=ENV)
 assert result.returncode==0,(prefix,'retained full archive unreadable')
 refs=sorted({x.rsplit(' ',1)[1]for x in d['refs']}|{d['head']})
 p=run('git','-C',RETAINED,'cat-file','--batch-check=%(objectname) %(objecttype)',input=('\n'.join(refs)+'\n').encode())
 missing=[line for line in p.stdout.decode().splitlines()if line.endswith(' missing')]
 refproof.append({'root':str(root),'base':d['head'],'retained_repository':str(RETAINED),'full_base_archive_readable':True,'distinct_ref_targets':len(refs),'ref_objects_missing_in_retained':missing})
 entries=[('overlay/'+x,root/x)for x in d['untracked_paths']+meaningful]
 gitpointer=root/'.git'
 if gitpointer.is_file():entries.append(('git-worktree-pointer',gitpointer));admin=pathlib.Path(run('git','-C',root,'rev-parse','--path-format=absolute','--git-dir').stdout.decode().strip())
 else:admin=gitpointer
 for directory,dirs,files in os.walk(admin,followlinks=False):
  if pathlib.Path(directory)==admin:dirs[:]=[x for x in dirs if x not in ['objects','hooks']]
  for name in files:entries.append(('git-admin/'+str(pathlib.Path(directory,name).relative_to(admin)),pathlib.Path(directory,name)))
 for name,p in entries:
  s=p.lstat();r={'member':prefix+'/'+name,'source':str(p),'mode':s.st_mode,'size':s.st_size,'mtime_ns':s.st_mtime_ns,'ctime_ns':s.st_ctime_ns}
  if stat.S_ISREG(s.st_mode):r['sha256']=sha(p)
  elif stat.S_ISLNK(s.st_mode):r['link_target']=os.readlink(p)
  else:raise AssertionError('unexpected preservation node')
  records.append(r)
archive=SEC/'conditional-code-state-and-git-admin.tar.gz'
assert not archive.exists(),'Archive already exists; reconcile before replay'
with tarfile.open(archive,'w:gz',dereference=False,format=tarfile.PAX_FORMAT)as tf:
 for r in records:tf.add(r['source'],arcname=r['member'],recursive=False)
 for d in states:
  for suffix,data in [('working-tree.patch',patches[pathlib.Path(d['root']).name]),('git-state.json',json.dumps(d).encode())]:
   name=pathlib.Path(d['root']).name+'/'+suffix;info=tarfile.TarInfo(name);info.mode=0o600;info.size=len(data);tf.addfile(info,io.BytesIO(data))
# Independent reader verifies all archive payloads and materializes overlays only.
expected={r['member']:r for r in records};seen=set();recovered_patches={}
with tarfile.open(archive,'r:gz')as tf:
 for m in tf:
  assert m.name not in seen;seen.add(m.name)
  r=expected.get(m.name)
  if m.isfile()or m.islnk():
   h=tf.extractfile(m);assert h is not None;data=h.read()
   if r:assert len(data)==r['size']and hashlib.sha256(data).hexdigest()==r['sha256']
   if m.name.endswith('/working-tree.patch'):recovered_patches[m.name.split('/')[0]]=data
   if '/overlay/'in m.name:
    prefix,rel=m.name.split('/overlay/',1);p=SCR/prefix/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data);os.chmod(p,stat.S_IMODE(r['mode']))
  elif m.issym():assert r and m.linkname==r['link_target']
assert seen==set(expected)|{pathlib.Path(d['root']).name+'/'+x for d in states for x in ['working-tree.patch','git-state.json']}
replays=[]
for d in states:
 root=pathlib.Path(d['root']);dest=SCR/root.name;dest.mkdir(exist_ok=True)
 for rel in d['modified_paths']:
  p=dest/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(run('git','-C',RETAINED,'show',d['head']+':'+rel).stdout)
  mode=run('git','-C',RETAINED,'ls-tree',d['head'],'--',rel).stdout.split()[0];os.chmod(p,0o755 if mode==b'100755'else 0o644)
 patch=SCR/(root.name+'.patch');patch.write_bytes(recovered_patches[root.name]);run('git','-C',dest,'apply','--check',patch);run('git','-C',dest,'apply',patch)
 changed=[]
 for rel in d['modified_paths']:
  assert sha(dest/rel)==sha(root/rel);changed.append(rel)
 overlays=[r for r in records if r['member'].startswith(root.name+'/overlay/')]
 for r in overlays:
  rel=r['member'].split('/overlay/',1)[1]
  if 'sha256'in r:assert sha(dest/rel)==r['sha256']
 replays.append({'root':str(root),'modified_source_files_replayed':len(changed),'overlay_files_replayed':len(overlays),'historical_test_state_files_replayed':sum('/MagicMock/'in r['member']for r in overlays)})
# No source admin/overlay mutation while it was read; no live SQLite was opened.
for r in records:
 p=pathlib.Path(r['source']);s=p.lstat();assert(s.st_mode,s.st_size,s.st_mtime_ns,s.st_ctime_ns)==(r['mode'],r['size'],r['mtime_ns'],r['ctime_ns'])
 if 'sha256'in r:assert sha(p)==r['sha256']
manifest={'entries':records,'ref_recovery':refproof,'archive':str(archive),'archive_sha256':sha(archive),'created_at':datetime.datetime.now().astimezone().isoformat()}
(SEC/'preservation-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
# Exercise actual inactive adapters only through their blocked early-return branch.
# A subprocess tripwire makes any lease/PC1/API dispatch fail the test immediately.
tests=[];g=runpy.run_path(str(BASE/'scripts/meta-digital-trust-pc1-create-one.py'),run_name='readonly_adapter_audit');fn=g['main'];gg=fn.__globals__
def forbidden(*a,**kw):raise AssertionError('Forbidden subprocess during read-only review')
gg['subprocess']=types.SimpleNamespace(run=forbidden)
argv=sys.argv[:]
try:
 sys.argv=['readonly-review']
 for name in ['meta-digital-trust-40-20261007-state.json','meta-digital-trust-49-20261013-state.json']:
  gg['STATE']=BASE/'data'/name;result=fn();assert result=={'kind':'blocked','reason':'checkpoint_not_executable'};tests.append({'state':name,'real_adapter_result':result,'subprocess_calls':0})
finally:sys.argv=argv
active=pathlib.Path('/root/.hermes/hermes-agent-port-main-29a61cb7-mgs-20261103');old=pathlib.Path('/root/.hermes/hermes-agent-port-main-46904a3b-mgs');api=[]
for rel,names in [('pm/environments.py',['activate_dependencies']),('tools/computer_use/tool.py',['handle_computer_use','release_computer_use_session']),('tools/computer_use/cua_backend.py',['_cua_configured_ax_max_elements'])]:
 row={'source':rel,'symbols':{}}
 for n in names:
  defs=[]
  for root in [old,active]:
   t=ast.parse((root/rel).read_text());node=next(x for x in ast.walk(t)if isinstance(x,(ast.FunctionDef,ast.AsyncFunctionDef))and x.name==n);defs.append(ast.dump(node.args,include_attributes=False))
  row['symbols'][n]={'old_and_current_signature_equal':defs[0]==defs[1]}
 api.append(row)
proof={'status':'source_patch_and_small_historical_state_replay_validated_not_disposal_ready','archive':str(archive),'archive_sha256':sha(archive),'archive_bytes':archive.stat().st_size,'archive_allocated':archive.stat().st_blocks*512,'preserved_payload_entries':len(records),'replays':replays,'ref_recovery':refproof,'self_contained':False,'required_retained_repository':str(RETAINED),'source_overlays_and_git_admin_unchanged':True,'live_sqlite_opened':False,'historical_sqlite_logical_restore_tested':False,'old_virtualenv_rebuilt':False,'old_virtualenv_local_overrides_audited':False,'node_modules_rebuilt':False,'ignored_build_assets_preserved':True,'inactive_adapter_gate_tests':tests,'static_migration_api_review':api,'pc1_meta_campaign_actions':0,'production_code_changes':0,'deletions':0,'scratch':str(SCR),'created_at':datetime.datetime.now().astimezone().isoformat()}
(OUT/'preservation-result.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(proof,ensure_ascii=False))

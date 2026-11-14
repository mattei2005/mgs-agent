import pathlib,subprocess,json,gzip,os,datetime
os.umask(0o077)
OUT=pathlib.Path('/root/mgs-agent/data/storage-runtime-retirement-prep-1571249324464148642');SEC=pathlib.Path('/root/.hermes/secure-backups/runtime-retirement/1571249324464148642');RETAINED=pathlib.Path('/root/.hermes/hermes-agent-port-main-3f2afed3-mgs-20261021');env=dict(os.environ,GIT_OPTIONAL_LOCKS='0')
def run(*a,**kw):return subprocess.run(list(map(str,a)),capture_output=True,check=True,env=env,**kw)
def sha(p):return run('sha256sum','--',p).stdout.decode().split()[0]
roots=[pathlib.Path('/root/.hermes/hermes-agent-port-main-'+s+'-mgs')for s in ['46904a3b','ad2d4822']];gitproof=[]
for root in roots:
 raw=run('git','-C',root,'cat-file','--batch-all-objects','--batch-check=%(objectname)').stdout;ids=sorted(set(raw.decode().splitlines()))
 with gzip.open(SEC/(root.name+'-all-objects.txt.gz'),'wt')as f:f.write('\n'.join(ids)+'\n')
 check=run('git','-C',RETAINED,'cat-file','--batch-check=%(objectname) %(objecttype)',input=('\n'.join(ids)+'\n').encode()).stdout.decode().splitlines();missing=[line.split()[0]for line in check if line.endswith(' missing')]
 proof={'root':str(root),'all_objects_including_alternates':len(ids),'retained_repository':str(RETAINED),'objects_not_in_retained':len(missing),'missing_object_pack':None}
 if missing:
  dest=SEC/(root.name+'-unique-objects.pack')
  with dest.open('wb')as f:
   p=subprocess.run(['git','-C',str(root),'pack-objects','--stdout'],input=('\n'.join(missing)+'\n').encode(),stdout=f,stderr=subprocess.PIPE,env=env);assert p.returncode==0
  bare=SEC/(root.name+'-unique.git');run('git','init','--bare','--quiet',bare)
  with dest.open('rb')as f:p=subprocess.run(['git','--git-dir='+str(bare),'index-pack','--stdin'],stdin=f,capture_output=True,env=env);assert p.returncode==0
  checked=run('git','--git-dir='+str(bare),'cat-file','--batch-check=%(objectname) %(objecttype)',input=('\n'.join(missing)+'\n').encode()).stdout.decode().splitlines();assert len(checked)==len(missing)and not any(x.endswith(' missing')for x in checked);proof['missing_object_pack']={'path':str(dest),'sha256':sha(dest),'verified_objects':len(missing),'retained_bare_store':str(bare)}
 gitproof.append(proof)
# Keep the exact source-code replay contract independent from the soon-retired paths.
oldout=pathlib.Path('/root/mgs-agent/data/storage-conditional-runtime-review-1571239570069131275');old=json.load(open(oldout/'preservation-result.json'));manifest=json.load(open(pathlib.Path(old['archive']).parent/'preservation-manifest.json'));spec=[]
for root in roots:
 d=json.load(open(OUT/(root.name+'-git-state.json')));paths=list(d['modified_paths']);paths +=[r['member'].split('/overlay/',1)[1]for r in manifest['entries']if r['member'].startswith(root.name+'/overlay/')]
 assert len(paths)==len(set(paths));spec.append({'label':root.name,'base':d['head'],'modified_paths':d['modified_paths'],'expected_files':[{'path':rel,'sha256':sha(root/rel),'mode':(root/rel).stat().st_mode & 0o7777}for rel in paths if(root/rel).is_file()]})
code={'archive':old['archive'],'sha256':old['archive_sha256'],'retained_repository':str(RETAINED),'roots':spec};(OUT/'code-recovery-spec.json').write_text(json.dumps(code,indent=2)+'\n')
admin=pathlib.Path('/root/.hermes/hermes-agent-port-main-59004a62-mgs/.git/worktrees');children=sorted(p.name for p in admin.iterdir());assert children==['hermes-agent-port-main-ad2d4822-mgs'],children
registration=admin/children[0];assert pathlib.Path((registration/'gitdir').read_text().strip()).resolve()==roots[1]/'.git';assert (roots[1]/'.git').read_text().strip()=='gitdir: '+str(registration)
printable={'git_object_coverage':gitproof,'code_recovery_files':sum(len(r['expected_files'])for r in spec),'worktree_admin_root':str(admin),'worktree_admin_children':children,'worktree_registry_only_expected_root':True,'all_source_refs_and_unreachable_objects_preserved_or_retained':True,'created_at':datetime.datetime.now().astimezone().isoformat()};(OUT/'git-recovery-and-registration.json').write_text(json.dumps(printable,indent=2)+'\n');print(json.dumps(printable))

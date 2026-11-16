"""Prepare one independently recoverable duplicate NPX tree, without removal."""
import os,sys,pathlib,json,gzip,subprocess,shutil,importlib.util,datetime,time,urllib.parse
sys.dont_write_bytecode=True
OUT=pathlib.Path(__file__).parent
spec=importlib.util.spec_from_file_location('npx_gate',OUT/'npx-gate.py');assert spec and spec.loader;g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
PRIVATE=pathlib.Path('/root/.hermes/secure-backups/storage-followup-1571894881096310825')
assert not(OUT/'npx-retirement-manifest.json').exists()
os.umask(0o077)
for root in [g.TARGET,g.KEEP]:
    for p in [pathlib.Path(root),*pathlib.Path(root).parents]:assert not p.is_symlink()
a=g.tree(g.TARGET);b=g.tree(g.KEEP);assert set(a)==set(b)
files=[r for r,s in a.items()if s['kind']=='file'];hashes={}
for root in [g.TARGET,g.KEEP]:
    names=[str(pathlib.Path(root)/r)for r in files]
    for i in range(0,len(names),150):
        raw=subprocess.check_output(['sha256sum','--zero','--',*names[i:i+150]])
        for part in raw.split(b'\0'):
            if part:h,n=part.split(b'  ',1);hashes[os.fsdecode(n)]=h.decode()
assert g.tree(g.TARGET)==a and g.tree(g.KEEP)==b
diff=[r for r in files if hashes[str(pathlib.Path(g.TARGET)/r)]!=hashes[str(pathlib.Path(g.KEEP)/r)]]
assert sorted(diff)==['node_modules/.package-lock.json','package-lock.json','package.json']
backups=PRIVATE/'npx-original-metadata'
if backups.exists():assert backups.is_dir() and not any(backups.iterdir()),'partial backup requires reconciliation'
else:backups.mkdir(mode=0o700)
providers={}
for i,rel in enumerate(diff):
    src=pathlib.Path(g.TARGET)/rel;obj=json.load(open(src))
    def check(x):
        if isinstance(x,dict):
            for k,v in x.items():
                assert k.lower() not in {'_authtoken','_auth','password','authorization','access_token','refresh_token'}
                check(v)
        elif isinstance(x,list):
            for v in x:check(v)
        elif isinstance(x,str)and x.startswith(('http://','https://')):
            u=urllib.parse.urlsplit(x);assert u.username is None and u.password is None
    check(obj);dest=backups/(str(i)+'.json');shutil.copy2(src,dest);os.chmod(dest,0o600);assert g.sha(dest)==hashes[str(src)];providers[rel]=str(dest)
rows=[]
for rel,s in a.items():
    x=dict(relative=rel,source=s)
    if s['kind']in ['file','link']:
        assert s['kind']==b[rel]['kind']
        path=providers.get(rel,str(pathlib.Path(g.KEEP)/rel));x['provider']=dict(path=path,metadata=g.metadata(path))
        if s['kind']=='file':x['sha256']=hashes[str(pathlib.Path(g.TARGET)/rel)];assert g.sha(path)==x['sha256']if rel in diff else True
        else:assert s['target']==b[rel]['target']
    rows.append(x)
ledger=PRIVATE/'npx-retirement-nodes.json.gz'
with gzip.open(ledger,'wt')as f:json.dump(rows,f,separators=(',',':'))
checks=g.consumers();time.sleep(2);assert g.tree(g.TARGET)==a and g.tree(g.KEEP)==b
m=dict(version=1,status='PROPOSED_NOT_AUTHORIZED',deletion_authorized=False,authority_message_id='1571894881096310825',thread_id=g.THREAD,target=g.TARGET,retained_root=g.KEEP,nodes=len(rows),files=len(files),directories_including_root=sum(s['kind']=='directory'for s in a.values()),symlinks=sum(s['kind']=='link'for s in a.values()),allocated_reclaim_bytes=sum(s['allocated']for s in a.values()),logical_file_bytes=sum(s['size']for s in a.values()if s['kind']=='file'),private_ledger=str(ledger),private_ledger_sha256=g.sha(ledger),protected_helpers={str(g.WRAPPER):g.sha(g.WRAPPER)},identical_retained_regular_providers=len(files)-len(diff),private_metadata_overrides=len(diff),consumer_scan=checks,coherent_two_pass_freeze=True,originals_unchanged=True,current_security_wrapper_uses_retained_tree=True,recovery_contract='All original regular bytes and file metadata can be reconstructed using surviving NPX tree plus three preserved JSON metadata files; directories/symlink layout kept in manifest. Current tool path stays. Future explicit-version npx may download again or require offline reconstruction first. Not credential, authentication or Security scan recovery.',at=datetime.datetime.now().astimezone().isoformat())
g.scope(m,rows);(OUT/'npx-retirement-manifest.json').write_text(json.dumps(m,indent=2)+'\n')
(OUT/'npx-retirement-manifest.sha256').write_text(g.sha(OUT/'npx-retirement-manifest.json')+'  npx-retirement-manifest.json\n')
(OUT/'npx-gate.sha256').write_text(g.sha(OUT/'npx-gate.py')+'  npx-gate.py\n')
r=g.verify(m,rows);(OUT/'npx-preflight.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps({k:m[k]for k in ['files','directories_including_root','symlinks','allocated_reclaim_bytes','logical_file_bytes','identical_retained_regular_providers','private_metadata_overrides']}));print('PREFLIGHT',json.dumps(r))

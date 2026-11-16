"""Read-only UV inode inventory and source-derived prune projection."""
import pathlib,os,stat,json,gzip,subprocess,collections,datetime,time,urllib.request,re
os.umask(0o077)
OUT=pathlib.Path(__file__).parent
PRIVATE=pathlib.Path('/root/.hermes/secure-backups/storage-uv-1571959754081837281')
CACHE=pathlib.Path('/root/.cache/uv')
SOURCE='https://raw.githubusercontent.com/astral-sh/uv/0.12.1/crates/uv-cache/src/lib.rs'
def sha(p):return subprocess.check_output(['sha256sum','--',str(p)],text=True).split()[0]
def snapshot(name):
    rows=[];errors=[];device=CACHE.stat().st_dev;stack=[str(CACHE)]
    while stack:
        p=stack.pop()
        try:
            s=os.lstat(p)
            if s.st_dev!=device:raise RuntimeError('mount boundary in UV cache')
            kind='file'if stat.S_ISREG(s.st_mode)else'directory'if stat.S_ISDIR(s.st_mode)else'link'if stat.S_ISLNK(s.st_mode)else'other'
            rel=os.path.relpath(p,CACHE);parts=pathlib.PurePosixPath(rel).parts;bucket=parts[0]if parts else'.';archive=parts[1]if bucket=='archive-v0'and len(parts)>1 else None
            row=dict(relative=rel,bucket=bucket,archive=archive,kind=kind,dev=s.st_dev,ino=s.st_ino,size=s.st_size,allocated=s.st_blocks*512,nlink=s.st_nlink,mode=stat.S_IMODE(s.st_mode),uid=s.st_uid,gid=s.st_gid,mtime_ns=s.st_mtime_ns,ctime_ns=s.st_ctime_ns)
            if kind=='link':row['target']=os.readlink(p)
            rows.append(row)
            if kind=='directory':
                with os.scandir(p)as entries:stack.extend(x.path for x in entries)
        except OSError as e:errors.append(dict(path=p,error=type(e).__name__))
    assert not errors,errors[:3];rows.sort(key=lambda x:x['relative'])
    file=PRIVATE/(name+'.jsonl.gz') if name is not None else None;h=subprocess.Popen(['sha256sum'],stdin=subprocess.PIPE,stdout=subprocess.PIPE);assert h.stdin and h.stdout
    if file is not None:
        with gzip.open(file,'wb')as f:
            for row in rows:
                line=(json.dumps(row,sort_keys=True,separators=(',',':'))+'\n').encode();f.write(line);h.stdin.write(line)
    else:
        for row in rows:h.stdin.write((json.dumps(row,sort_keys=True,separators=(',',':'))+'\n').encode())
    h.stdin.close();digest=h.stdout.read().decode().split()[0];assert h.wait()==0
    return rows,dict(path=str(file) if file is not None else None,compressed_sha256=sha(file) if file is not None else None,normalized_plain_sha256=digest,node_count=len(rows))
def references():
    refs=collections.defaultdict(list);env=[];errors=[]
    for bucket in ['sdists-v9','wheels-v6','environments-v2']:
        for d,ds,fs in os.walk(CACHE/bucket,followlinks=False):
            ds[:]=[n for n in ds if n not in {'src','.lock','.gitignore'}]
            for n in ds+fs:
                p=pathlib.Path(d)/n
                if n in {'src','.lock','.gitignore'}or p.suffix.lower()in {'.lock','.whl','.http','.rev','.msgpack'}:continue
                if not p.is_symlink():continue
                try:target=str(p.resolve(strict=True))
                except OSError as e:errors.append(dict(path=str(p),error=type(e).__name__));continue
                row=dict(path=str(p),target=target)
                if bucket=='environments-v2':env.append(row)
                else:refs[target].append(str(p))
    assert not errors,errors[:3]
    return dict(refs),env
if __name__=='__main__':
    assert not PRIVATE.exists();PRIVATE.mkdir(mode=0o700)
    source=PRIVATE/'uv-cache-0.12.1-lib.rs';source.write_bytes(urllib.request.urlopen(SOURCE,timeout=30).read())
    text=source.read_text();pairs=re.findall(r'Self::(\w+)\s*=>\s*"([a-z0-9-]+)"',text)
    current=set(v for k,v in pairs);assert {'archive-v0','wheels-v6','sdists-v9','simple-v24','environments-v2'}<=current
    rows,first=snapshot('metadata-first');refs,env=references();time.sleep(2);rows2,second=snapshot('metadata-second');assert first['normalized_plain_sha256']==second['normalized_plain_sha256'],'cache changed between metadata passes'
    archives={str(x):x.name for x in(CACHE/'archive-v0').iterdir()};orphans={p for p in archives if p not in refs};outdated=[str(x)for x in CACHE.iterdir()if x.is_dir()and x.name not in current]
    targets=sorted(set(outdated+[str(x)for x in(CACHE/'environments-v2').iterdir()]+list(orphans)))
    def targeted(relative):
        p=str(CACHE/relative);return any(p==t or p.startswith(t+'/')for t in targets)
    inodes={};buckets=collections.defaultdict(lambda:dict(files=0,directories=0,links=0,logical_file_bytes=0,unique_allocated_bytes=0));archive_stats=collections.defaultdict(lambda:dict(files=0,directories=0,links=0,logical_file_bytes=0,allocated_naive_bytes=0,single_link_file_bytes=0))
    for row in rows:
        u=buckets[row['bucket']];u[dict(file='files',directory='directories',link='links').get(row['kind'],'other')]=u.get(dict(file='files',directory='directories',link='links').get(row['kind'],'other'),0)+1
        if row['kind']=='file':u['logical_file_bytes']+=row['size']
        if row['archive']:
            a=archive_stats[row['archive']];a[dict(file='files',directory='directories',link='links').get(row['kind'],'other')]=a.get(dict(file='files',directory='directories',link='links').get(row['kind'],'other'),0)+1;a['allocated_naive_bytes']+=row['allocated']
            if row['kind']=='file':a['logical_file_bytes']+=row['size'];a['single_link_file_bytes']+=row['allocated']if row['nlink']==1 else 0
        key=(row['dev'],row['ino']);selected=targeted(row['relative'])
        if key not in inodes:inodes[key]=dict(bucket=row['bucket'],kind=row['kind'],allocated=row['allocated'],seen=1,nlink=row['nlink'],selected_seen=int(selected));u['unique_allocated_bytes']+=row['allocated']
        else:
            n=inodes[key];n['seen']+=1;n['selected_seen']+=int(selected)
            if n['bucket']!=row['bucket']and n['bucket']!='__shared__':buckets[n['bucket']]['unique_allocated_bytes']-=n['allocated'];buckets['__shared__']['unique_allocated_bytes']+=n['allocated'];n['bucket']='__shared__'
    exact_cache=sum(n['allocated']for n in inodes.values());outside=sum(n['allocated']for n in inodes.values()if n['kind']=='file'and n['nlink']>n['seen'])
    full_reclaim=sum(n['allocated']for n in inodes.values()if n['kind']!='file'or n['nlink']==n['seen'])
    projected=sum(n['allocated']for n in inodes.values()if n['selected_seen']and(n['kind']!='file'or n['nlink']==n['selected_seen']))
    for p in orphans:archive_stats[archives[p]]['native_orphan']=True
    for p in refs:
        if p in archives:archive_stats[archives[p]]['native_orphan']=False
    detail=dict(archive_stats=dict(archive_stats),native_refs=refs,environment_links=env,native_prune_targets=targets,current_bucket_names=sorted(current),outdated_buckets=outdated)
    with gzip.open(PRIVATE/'classification.json.gz','wt')as f:json.dump(detail,f,separators=(',',':'))
    result=dict(status='READONLY_UV_INVENTORY_AND_NATIVE_SOURCE_MODEL',authority_message_id='1571959754081837281',thread_id='1569928464033783862',uv_binary='/root/.local/bin/uv',uv_version=subprocess.check_output(['/root/.local/bin/uv','--version'],text=True).strip(),uv_binary_sha256=sha('/root/.local/bin/uv'),source_url=SOURCE,source_sha256=sha(source),metadata_first=first,metadata_second=second,coherent_two_pass_freeze=True,node_counts=dict(collections.Counter(x['kind']for x in rows)),unique_allocated_cache_bytes=exact_cache,cache_inode_blocks_with_external_hardlinks_bytes=outside,whole_cache_deletion_physical_upper_bound_bytes=full_reclaim,whole_cache_deletion_not_proposed=True,buckets=dict(buckets),archive_count=len(archives),native_wheel_sdist_referenced_archives=len(set(archives)&set(refs)),native_orphan_archives=len(orphans),environment_link_count=len(env),outdated_bucket_count=len(outdated),outdated_buckets=outdated,native_prune_predicted_top_targets=len(targets),native_prune_physical_upper_bound_bytes=projected,native_prune_not_executed=True,projection_is_not_native_dry_run=True,consumer_and_recovery_classification_pending=True,private_classification=str(PRIVATE/'classification.json.gz'),source_files_deleted=0,observed_savings_bytes=0,at=datetime.datetime.now().astimezone().isoformat())
    (OUT/'inventory.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k]for k in ['status','node_counts','unique_allocated_cache_bytes','cache_inode_blocks_with_external_hardlinks_bytes','whole_cache_deletion_physical_upper_bound_bytes','archive_count','native_wheel_sdist_referenced_archives','native_orphan_archives','environment_link_count','outdated_buckets','native_prune_predicted_top_targets','native_prune_physical_upper_bound_bytes','native_prune_not_executed']}))
    print('ORPHAN_LARGEST',json.dumps(sorted([dict(id=k,**v)for k,v in archive_stats.items()if v.get('native_orphan')],key=lambda x:-x['allocated_naive_bytes'])[:8]))

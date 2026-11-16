"""Read-only work/cache inventory; hardlink-aware, no secret payload reads."""
import os, stat, json, pathlib, gzip, collections, datetime, subprocess
os.umask(0o077)
OUT=pathlib.Path(__file__).parent
PRIVATE=pathlib.Path('/root/.hermes/secure-backups/storage-followup-1571894881096310825')
ROOTS=['/root/mgs-agent/work','/root/.cache','/root/.npm','/root/.hermes/profiles/zeus/cache','/root/.hermes/profiles/ares/cache','/root/.hermes/profiles/atena/cache','/var/cache/apt/archives']
def group(path,root):
    rel=os.path.relpath(path,root)
    return root if rel=='.' else root+'/'+rel.split('/')[0]
def scan(roots,ledger):
    units=collections.defaultdict(lambda:dict(files=0,directories=0,links=0,other=0,logical_bytes=0,allocated_unique_bytes=0,single_link_file_bytes=0,newest_mtime_ns=0))
    inodes={};errors=[];excluded=[];pg=[];counts=collections.Counter();largest=[]
    with gzip.open(ledger,'wt') as output:
        for root in roots:
            if not os.path.lexists(root):
                excluded.append(dict(path=root,reason='absent'));continue
            device=os.lstat(root).st_dev;stack=[root]
            while stack:
                p=stack.pop()
                try:
                    s=os.lstat(p)
                    if s.st_dev!=device:
                        excluded.append(dict(path=p,reason='mount_boundary'));continue
                    kind='file' if stat.S_ISREG(s.st_mode) else 'directory' if stat.S_ISDIR(s.st_mode) else 'link' if stat.S_ISLNK(s.st_mode) else 'other'
                    unit=group(p,root);key=(s.st_dev,s.st_ino);allocated=s.st_blocks*512
                    row=dict(path=p,unit=unit,kind=kind,dev=s.st_dev,ino=s.st_ino,size=s.st_size,allocated=allocated,nlink=s.st_nlink,mode=stat.S_IMODE(s.st_mode),uid=s.st_uid,gid=s.st_gid,mtime_ns=s.st_mtime_ns,ctime_ns=s.st_ctime_ns)
                    if kind=='link':row['target']=os.readlink(p)
                    output.write(json.dumps(row,separators=(',',':'))+'\n')
                    counts[kind]+=1;u=units[unit];u[dict(file='files',directory='directories',link='links',other='other')[kind]]+=1;u['newest_mtime_ns']=max(u['newest_mtime_ns'],s.st_mtime_ns)
                    if key not in inodes:
                        inodes[key]=dict(unit=unit,allocated=allocated,seen=1,nlink=s.st_nlink,kind=kind);u['allocated_unique_bytes']+=allocated
                    else:
                        prev=inodes[key];prev['seen']+=1
                        if prev['unit']!=unit and prev['unit']!='__shared_hardlinks__':
                            units[prev['unit']]['allocated_unique_bytes']-=prev['allocated'];units['__shared_hardlinks__']['allocated_unique_bytes']+=prev['allocated'];prev['unit']='__shared_hardlinks__'
                    if kind=='directory':
                        with os.scandir(p) as it:stack.extend(x.path for x in it)
                        if os.path.isfile(p+'/PG_VERSION') and os.path.isdir(p+'/base') and os.path.isdir(p+'/global'):pg.append(p)
                    elif kind=='file':
                        u['logical_bytes']+=s.st_size
                        if s.st_nlink==1:u['single_link_file_bytes']+=allocated
                        if allocated>=10*1024**2:largest.append(dict(path=p,unit=unit,allocated=allocated,logical_bytes=s.st_size,nlink=s.st_nlink))
                except (OSError,ValueError) as e:errors.append(dict(path=p,error=type(e).__name__))
    unseen=sum(x['allocated'] for x in inodes.values() if x['kind']=='file' and x['seen']<x['nlink'])
    closed=sum(x['allocated'] for x in inodes.values() if x['kind']=='file' and x['seen']==x['nlink'])
    return dict(status='PASS' if not errors else 'PARTIAL',node_counts=dict(counts),units=dict(units),unique_allocated_bytes=sum(x['allocated_unique_bytes']for x in units.values()),file_blocks_with_links_outside_review=unseen,file_blocks_link_closed_inside_review=closed,errors=errors,exclusions=excluded,postgres_cluster_roots=pg,largest_files=sorted(largest,key=lambda x:-x['allocated'])[:30])
def fixture():
    base=pathlib.Path(os.environ['TMPDIR'])/'storage-followup-accounting-fixture-1571894881096310825';base.mkdir(mode=0o700,exist_ok=False)
    for n in ['a','b','outside']:(base/n).mkdir()
    (base/'a/shared').write_bytes(b'x'*8192);os.link(base/'a/shared',base/'b/shared')
    (base/'a/external').write_bytes(b'y'*12288);os.link(base/'a/external',base/'outside/held')
    os.symlink(str(base/'outside'),base/'a/link')
    r=scan([str(base/'a'),str(base/'b')],base/'fixture-ledger.jsonl.gz')
    assert not r['errors'] and r['node_counts']['file']==3 and r['node_counts']['link']==1
    assert r['units']['__shared_hardlinks__']['allocated_unique_bytes']==os.stat(base/'a/shared').st_blocks*512
    assert r['file_blocks_with_links_outside_review']==os.stat(base/'a/external').st_blocks*512
    return dict(status='PASS',path=str(base),analysis_created=True,external_link_not_counted_as_reclaim=True,outward_link_not_followed=True,cross_unit_inode_counted_once=True)
if __name__=='__main__':
    assert not PRIVATE.exists();PRIVATE.mkdir(mode=0o700)
    f=fixture();r=scan(ROOTS,PRIVATE/'metadata.jsonl.gz');r.update(authority_message_id='1571894881096310825',thread_id='1569928464033783862',roots=ROOTS,private_ledger=str(PRIVATE/'metadata.jsonl.gz'),fixture=f,source_files_deleted=0,proven_deletion_reclaim_bytes=0,scope='Work and named caches only; not whole VPS; metadata alone does not certify disposal',at=datetime.datetime.now().astimezone().isoformat())
    (OUT/'metadata-summary.json').write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({k:r[k]for k in ['status','node_counts','unique_allocated_bytes','file_blocks_with_links_outside_review','source_files_deleted','fixture']},ensure_ascii=False))
    print('TOP_UNITS',json.dumps(sorted([dict(path=k,**v)for k,v in r['units'].items()],key=lambda x:-x['allocated_unique_bytes'])[:16]))

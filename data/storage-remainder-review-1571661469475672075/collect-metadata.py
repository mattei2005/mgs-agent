"""Read-only bounded maintenance/work metadata inventory; no deletions."""
import os, stat, json, gzip, pathlib, collections, datetime, time
from typing import Any
os.umask(0o077)
ROOTS = ['/root/mgs-agent', '/root/mgs-agent-backups', '/root/zeus-vps-maintenance-1565730926233657347']
OUT = pathlib.Path(__file__).parent
SCRATCH = pathlib.Path(os.environ['TMPDIR']) / 'storage-remainder-1571661469475672075'
PRIVATE = pathlib.Path('/root/.hermes/secure-backups/storage-remainder-review-1571661469475672075')
SCRATCH.mkdir(mode=0o700, exist_ok=False)
PRIVATE.mkdir(mode=0o700, exist_ok=False)
PRUNE = ['/root/mgs-agent/.git', str(OUT)]
start = time.monotonic()
def disk():
    s = os.statvfs('/')
    return dict(total=s.f_blocks*s.f_frsize, used=(s.f_blocks-s.f_bfree)*s.f_frsize, available=s.f_bavail*s.f_frsize)
def unit(path, root):
    rel = os.path.relpath(path, root)
    parts = rel.split('/')
    if root == '/root/mgs-agent' and parts[0] in ['work','data','reports'] and len(parts)>1:
        return root + '/' + '/'.join(parts[:2])
    return root if rel == '.' else root + '/' + parts[0]
def classify(path):
    parts = path.split('/')
    if 'node_modules' in parts or '.venv' in parts or 'venv' in parts or '__pycache__' in parts:
        return 'dependencies_or_generated_code'
    n = parts[-1].lower()
    if n.endswith(('.tar.gz','.tar.xz','.tgz','.zip','.tar','.xz','.gz','.deb','.dump','.sql','.sql.gz')):
        return 'archive_dump_or_installer'
    if n.endswith(('.sqlite','.sqlite3','.db','.db-wal','.db-shm')) or n == 'PG_VERSION':
        return 'database_indicator'
    if n.endswith(('.png','.jpg','.jpeg','.webp','.mp4','.mov','.mp3','.wav','.pdf','.xlsx','.csv')):
        return 'media_or_business_input'
    return 'code_configuration_or_evidence'
units: dict[str, dict[str, Any]] = collections.defaultdict(lambda:dict(files=0, directories=0, links=0, other=0, logical_bytes=0, allocated_unique_bytes=0, newest_mtime_ns=0, classes=collections.Counter()))
inodes: dict[tuple[int,int], dict[str, Any]] = {}
errors: list[dict[str, str]] = []
exclusions: list[dict[str, str]] = []
counts: collections.Counter[str] = collections.Counter()
largest: list[dict[str, Any]] = []
pg_clusters: list[str] = []
b=disk()
ledger=SCRATCH/'metadata.jsonl.gz'
with gzip.open(ledger,'wt') as out:
    for root in ROOTS:
        device=os.lstat(root).st_dev
        stack=[root]
        while stack:
            path=stack.pop()
            if any(path==p or path.startswith(p+'/') for p in PRUNE):
                exclusions.append(dict(path=path,reason='institutional_git_or_current_analysis'))
                continue
            try:
                s=os.lstat(path)
                if s.st_dev != device:
                    exclusions.append(dict(path=path,reason='mount_boundary'))
                    continue
                kind='file' if stat.S_ISREG(s.st_mode) else 'directory' if stat.S_ISDIR(s.st_mode) else 'link' if stat.S_ISLNK(s.st_mode) else 'other'
                group=unit(path,root)
                row=dict(path=path,unit=group,kind=kind,mode=s.st_mode,uid=s.st_uid,gid=s.st_gid,size=s.st_size,blocks=s.st_blocks,dev=s.st_dev,ino=s.st_ino,nlink=s.st_nlink,mtime_ns=s.st_mtime_ns,ctime_ns=s.st_ctime_ns)
                if kind=='link': row['target']=os.readlink(path)
                out.write(json.dumps(row,separators=(',',':'))+'\n')
                counts[kind]+=1; u=units[group]
                u['newest_mtime_ns']=max(u['newest_mtime_ns'],s.st_mtime_ns)
                u[dict(file='files',directory='directories',link='links',other='other')[kind]]+=1
                key=(s.st_dev,s.st_ino)
                if key not in inodes:
                    inodes[key]=dict(group=group,blocks=s.st_blocks,links_seen=1,nlink=s.st_nlink,kind=kind)
                    u['allocated_unique_bytes']+=s.st_blocks*512
                else:
                    prev=inodes[key];prev['links_seen']+=1
                    if prev['group']!=group and prev['group']!='__shared__':
                        units[prev['group']]['allocated_unique_bytes']-=prev['blocks']*512
                        units['__shared__']['allocated_unique_bytes']+=prev['blocks']*512
                        prev['group']='__shared__'
                if kind=='directory':
                    with os.scandir(path) as entries:
                        stack.extend(entry.path for entry in entries)
                    if os.path.isfile(path+'/PG_VERSION') and os.path.isdir(path+'/base') and os.path.isdir(path+'/global'):
                        pg_clusters.append(path)
                elif kind=='file':
                    u['logical_bytes']+=s.st_size;u['classes'][classify(path)]+=s.st_blocks*512
                    if s.st_blocks*512>=10*2**20:largest.append(dict(path=path,unit=group,logical_bytes=s.st_size,allocated_bytes=s.st_blocks*512,nlink=s.st_nlink,kind=classify(path)))
            except (OSError,ValueError) as exc:
                errors.append(dict(path=path,error=type(exc).__name__))
final_ledger=PRIVATE/'metadata.jsonl.gz'
os.replace(ledger,final_ledger)
external=sum(v['blocks']*512 for v in inodes.values() if v['kind']=='file' and v['links_seen']<v['nlink'] and v['nlink']>1)
result=dict(status='PASS' if not errors else 'PARTIAL',authority_message_id='1571661469475672075',thread_id='1569928464033783862',roots=ROOTS,scope='Bounded repository sources/work/data/reports plus two legacy maintenance/site-backup roots; not whole VPS',exclusions=exclusions,errors=errors,node_counts=dict(counts),inode_unique_allocated_bytes=sum(x['allocated_unique_bytes']for x in units.values()),inodes_with_unseen_links_allocated_bytes=external,units=dict(units),largest_files=sorted(largest,key=lambda x:-x['allocated_bytes']),postgres_cluster_roots=pg_clusters,private_ledger=str(final_ledger),disk_before=b,disk_after=disk(),elapsed_seconds=round(time.monotonic()-start,2),at=datetime.datetime.now(datetime.timezone.utc).isoformat(),deletions=0)
(OUT/'metadata-inventory.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(status=result['status'],node_counts=result['node_counts'],errors=len(errors),units=len(units),allocated_bytes=result['inode_unique_allocated_bytes'],postgres_clusters=len(pg_clusters),elapsed_seconds=result['elapsed_seconds'],top_units=sorted([dict(path=k,allocated_bytes=v['allocated_unique_bytes'],files=v['files'])for k,v in units.items()],key=lambda x:-int(x['allocated_bytes']))[:18])))

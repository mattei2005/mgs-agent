"""Read-only duplicate/proc classifier; source contents stay private."""
import os, pathlib, json, gzip, collections, subprocess, stat, datetime
from typing import Any
os.umask(0o077)
OUT=pathlib.Path(__file__).parent
D=json.load(open(OUT/'metadata-inventory.json'))
PRIVATE=pathlib.Path(D['private_ledger']).parent
PREFIXES=['/root/mgs-agent/work','/root/mgs-agent/artifacts','/root/mgs-agent/tmp','/root/mgs-agent/reports/meta-manual-payments-runs','/root/mgs-agent-backups','/root/zeus-vps-maintenance-1565730926233657347']
def inside(p,r):return p==r or p.startswith(r+'/')
files: list[dict[str,Any]] = []
size_groups: dict[int,list[dict[str,Any]]] = collections.defaultdict(list)
unit_details: dict[str,dict[str,int]] = collections.defaultdict(lambda:dict(files=0,logical_bytes=0,allocated_naive_bytes=0))
with gzip.open(D['private_ledger'],'rt')as stream:
    for line in stream:
        r=json.loads(line)
        if r['kind']=='file' and any(inside(r['path'],p)for p in PREFIXES):
            files.append(r);size_groups[r['size']].append(r)
            rel=r['path'];u=r['unit'];unit_details[u]['files']+=1;unit_details[u]['logical_bytes']+=r['size'];unit_details[u]['allocated_naive_bytes']+=r['blocks']*512
selected=[r for size,rows in size_groups.items()if size>=32768 and len({(x['dev'],x['ino'])for x in rows})>1 for r in rows]
selected_map={r['path']:r for r in selected}
payload=b''.join(os.fsencode(r['path'])+b'\0'for r in selected)
result=subprocess.run(['xargs','-0','-r','sha256sum','--zero','--'],input=payload,capture_output=True,timeout=180)
assert result.returncode==0,'hash command failed'
hashes={};groups=collections.defaultdict(list)
for record in result.stdout.split(b'\0'):
    if not record:continue
    digest=record[:64].decode();path=os.fsdecode(record[66:]);assert path in selected_map
    r=selected_map[path];s=os.lstat(path)
    assert (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)==(r['dev'],r['ino'],r['size'],r['mtime_ns'],r['ctime_ns']),'source drift'
    hashes[path]=digest;groups[(r['size'],digest)].append(r)
duplicates=[]
for (size,digest),rows in groups.items():
    by_inode={}
    for r in rows:by_inode.setdefault((r['dev'],r['ino']),r)
    if len(by_inode)<2:continue
    # Potential only: one physical representative survives; no pathname disposal inferred.
    physical=list(by_inode.values());single=[r for r in physical if r['nlink']==1]
    potential=sum(r['blocks']*512 for r in single)
    if len(single)==len(physical):potential-=min(r['blocks']*512 for r in single)
    duplicates.append(dict(size=size,sha256=digest,paths=[r['path']for r in rows],physical_copies=len(physical),potential_upper_bound_bytes=potential))
# Process reference checks, not ownership or recovery proof.
ancestors=set();pid=os.getpid()
while pid>1:
    ancestors.add(pid)
    try:pid=int(pathlib.Path('/proc',str(pid),'stat').read_text().rsplit(')',1)[1].split()[1])
    except OSError:break
hits=[];checked=0;errors=[]
for proc in pathlib.Path('/proc').iterdir():
    if not proc.name.isdigit()or int(proc.name)in ancestors:continue
    try:
        checked+=1;cmd=(proc/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')
        for root in PREFIXES:
            if root in cmd:hits.append(dict(pid=int(proc.name),root=root,reference='command'))
        for q in [proc/'cwd',proc/'exe',*(proc/'fd').iterdir()]:
            try:target=os.readlink(q)
            except OSError:continue
            for root in PREFIXES:
                if inside(target,root):hits.append(dict(pid=int(proc.name),root=root,path=target,reference=q.name))
    except (FileNotFoundError,ProcessLookupError):continue
    except PermissionError:errors.append(dict(pid=int(proc.name),error='PermissionError'))
private=dict(files=files,hashes=hashes,duplicates=duplicates,process_hits=hits)
with gzip.open(PRIVATE/'duplicate-and-reference-ledger.json.gz','wt')as stream:json.dump(private,stream)
receipt: dict[str,Any] = dict(status='PASS',prefixes=PREFIXES,source_regular_files=len(files),hashes_checked=len(hashes),hash_source_metadata_stable=True,duplicate_payload_groups=len(duplicates),duplicate_physical_copies=sum(x['physical_copies']for x in duplicates),duplicate_potential_upper_bound_bytes=sum(x['potential_upper_bound_bytes']for x in duplicates),duplicate_potential_is_not_eligible_reclaim=True,processes_checked=checked,process_reference_hits=hits,process_scan_errors=errors,unit_details=dict(unit_details),largest_duplicate_groups=sorted(duplicates,key=lambda x:-x['potential_upper_bound_bytes'])[:15],private_ledger=str(PRIVATE/'duplicate-and-reference-ledger.json.gz'),deletions=0,at=datetime.datetime.now(datetime.timezone.utc).isoformat())
(OUT/'duplicate-and-reference-review.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:receipt[k]for k in ['status','source_regular_files','hashes_checked','duplicate_payload_groups','duplicate_physical_copies','duplicate_potential_upper_bound_bytes','processes_checked','process_reference_hits','process_scan_errors']}))
print('top_groups',json.dumps(receipt['largest_duplicate_groups'][:6],ensure_ascii=False))

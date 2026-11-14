import pathlib,os,stat,json,gzip,subprocess,datetime,argparse
p=argparse.ArgumentParser();p.add_argument('--batch',type=int,required=True);a=p.parse_args()
OUT=pathlib.Path('/root/mgs-agent/data/storage-runtime-review-1571217101597712496');SEC=pathlib.Path('/root/.hermes/secure-backups/runtime-review/20261114-1571217101597712496');SEC.mkdir(parents=True,mode=0o700,exist_ok=True)
roots=sorted(p for p in pathlib.Path('/root/.hermes').glob('hermes-agent*') if p.is_dir());selected=roots[:3] if a.batch==1 else roots[3:];result=[];os.umask(0o077)
for root in selected:
 ledger=SEC/(root.name+'-metadata.jsonl.gz');errors=[];counts={'regular_files':0,'directories':0,'symlinks':0};alloc=0;dev=root.stat().st_dev;seen=set();top={}
 with gzip.open(ledger,'wt') as f:
  stack=[str(root)]
  while stack:
   path=stack.pop()
   try:s=os.lstat(path)
   except OSError as e:errors.append({'path':path,'error':type(e).__name__});continue
   if s.st_dev!=dev:errors.append({'path':path,'error':'mount_boundary'});continue
   rel=os.path.relpath(path,root);kind='regular_files' if stat.S_ISREG(s.st_mode) else 'directories' if stat.S_ISDIR(s.st_mode) else 'symlinks' if stat.S_ISLNK(s.st_mode) else 'other';counts[kind]=counts.get(kind,0)+1
   row={'path':rel,'mode':s.st_mode,'size':s.st_size,'mtime_ns':s.st_mtime_ns,'ctime_ns':s.st_ctime_ns,'dev':s.st_dev,'ino':s.st_ino,'nlink':s.st_nlink,'allocated':s.st_blocks*512}
   if stat.S_ISLNK(s.st_mode):row['link_target']=os.readlink(path)
   f.write(json.dumps(row,ensure_ascii=False,separators=(',',':'))+'\n')
   key=(s.st_dev,s.st_ino)
   if key not in seen:
    seen.add(key);alloc+=row['allocated'];t=rel.split('/')[0];top[t]=top.get(t,0)+row['allocated']
   if stat.S_ISDIR(s.st_mode):
    try:
     with os.scandir(path) as entries:stack.extend(e.path for e in entries)
    except OSError as e:errors.append({'path':path,'error':type(e).__name__})
 sha=subprocess.run(['sha256sum',str(ledger)],capture_output=True,text=True,check=True).stdout.split()[0]
 result.append({'path':str(root),'ledger':str(ledger),'ledger_sha256':sha,'counts':counts,'allocated_unique_within_root':alloc,'errors':errors,'top_allocations':dict(sorted(top.items(),key=lambda x:-x[1])[:10])})
(OUT/f'metadata-batch-{a.batch}.json').write_text(json.dumps({'roots':result,'observed_at':datetime.datetime.now().astimezone().isoformat()},indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False))

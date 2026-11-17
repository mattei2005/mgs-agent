"""Bounded, resumable shell hashing of the frozen same-size selection; never discard payloads."""
import pathlib,json,gzip,os,stat,subprocess,time,argparse
O=pathlib.Path(__file__).parent;P=pathlib.Path(json.loads((O/'metadata-summary.json').read_text())['own_analysis_excluded'][1]);rows=json.load(gzip.open(P/'size-selected-duplicates.json.gz','rt'));out=P/'selected-hash-readback.jsonl';done={}
if out.exists():
 for line in out.read_text().splitlines():
  r=json.loads(line);assert r['path']not in done;done[r['path']]=r
assert set(done)<={r['p']for r in rows}
def meta(p):
 s=os.lstat(p);assert stat.S_ISREG(s.st_mode);return dict(dev=s.st_dev,ino=s.st_ino,size=s.st_size,blocks=s.st_blocks,nlink=s.st_nlink,mtime_ns=s.st_mtime_ns,ctime_ns=s.st_ctime_ns,mode=s.st_mode,uid=s.st_uid,gid=s.st_gid)
def original_equal(r,m):return(r['d'],r['i'],r['s'],r['b'],r['n'],r['t'],r['m'],r['u'],r['g'])==(m['dev'],m['ino'],m['size'],m['blocks']*512,m['nlink'],m['mtime_ns'],stat.S_IMODE(m['mode']),m['uid'],m['gid'])
ap=argparse.ArgumentParser();ap.add_argument('--limit',type=int,default=1000);args=ap.parse_args();todo=[r for r in rows if r['p']not in done][:args.limit];start=time.monotonic();new=0
for offset in range(0,len(todo),40):
 if time.monotonic()-start>110:break
 batch=todo[offset:offset+40];before={};results={}
 for r in batch:
  try:
   m=meta(r['p'])
   if not original_equal(r,m):results[r['p']]={'path':r['p'],'status':'changed_since_metadata_observation'}
   else:before[r['p']]=m
  except OSError as e:results[r['p']]={'path':r['p'],'status':'unavailable','error_type':type(e).__name__}
 hashes={}
 if before:
  p=subprocess.run(['nice','-n','10','sha256sum','--zero','--',*before],capture_output=True)
  for item in p.stdout.split(b'\0'):
   if item:hashes[os.fsdecode(item[66:])]=item[:64].decode()
 for path,m in before.items():
  try:stable=meta(path)==m
  except OSError:stable=False
  results[path]={'path':path,'status':'PASS'if stable and path in hashes else'changed_or_failed_hash_read','sha256':hashes.get(path),'metadata':m}
 with out.open('a')as f:
  for r in batch:record=results[r['p']];f.write(json.dumps(record)+'\n');done[r['p']]=record;new+=1
  f.flush();os.fsync(f.fileno())
print(json.dumps({'newly_classified_hash_reads':new,'verified_or_disclosed_total':len(done),'expected':len(rows),'remaining':len(rows)-len(done),'passed':sum(r['status']=='PASS'for r in done.values()),'unstable_or_unavailable':sum(r['status']!='PASS'for r in done.values()),'source_files_deleted':0}))

"""Retained-only regular-file recovery for the proposed copied JSON subset; zero source reads."""
import pathlib,json,os,stat,subprocess,datetime
O=pathlib.Path(__file__).parent

def recover(row,payload):
 m=row['metadata'];assert len(payload)==m['size'];fd=os.memfd_create('mgs-consolidated-retained-file',flags=0)
 try:
  v=memoryview(payload);i=0
  while i<len(v):i+=os.write(fd,v[i:i+1048576])
  v.release();os.fchown(fd,m['uid'],m['gid']);os.fchmod(fd,stat.S_IMODE(m['mode']));os.utime(fd,ns=(m['mtime_ns'],m['mtime_ns']));s=os.fstat(fd);assert s.st_size==m['size']and s.st_uid==m['uid']and s.st_gid==m['gid']and stat.S_IMODE(s.st_mode)==stat.S_IMODE(m['mode'])and s.st_mtime_ns==m['mtime_ns'];actual=subprocess.check_output(['sha256sum',f'/proc/self/fd/{fd}'],pass_fds=(fd,),text=True).split()[0];assert actual==row['sha256']
 finally:os.close(fd)
 return actual

def run(manifest,stage='prepare'):
 rows=[r for r in manifest['targets']if r['kind']=='copied_finance_JSON'];cache={};proof=[]
 for row in rows:
  p=row['retained_provider'];assert p not in{r['path']for r in manifest['targets']};available=int(next(line.split()[1]for line in pathlib.Path('/proc/meminfo').read_text().splitlines()if line.startswith('MemAvailable:')))*1024;assert available>4*row['metadata']['size']+2*1024**3
  if p not in cache:cache[p]=pathlib.Path(p).read_bytes()
  actual=recover(row,cache[p]);proof.append({'path':row['path'],'provider':p,'materialized_sha256':actual,'size':row['metadata']['size'],'source_payload_reads':0,'persistent_payload_copies':0})
 return {'status':'PASS','stage':stage,'files_recovered_in_RAM':len(proof),'unique_retained_providers':len(cache),'proof':proof,'at':datetime.datetime.now().astimezone().isoformat()}

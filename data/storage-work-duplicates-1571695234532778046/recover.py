"""Recover twelve historical files solely from their retained byte-identical copies.
No source target is opened; --ram reconstructs each actual file independently.
"""
import os,stat,json,pathlib,subprocess,argparse
OLD=pathlib.Path('/root/mgs-agent/work/finance-reaudit-20260905')
NAMES=sorted(n+s for n in ['principal','kelly','isliago','george','nicolas','joe']for s in ['.json','-metadata.json'])
def sha(p):return subprocess.check_output(['sha256sum','--',str(p)],text=True).split()[0]
def metadata(p):
 s=os.lstat(p);assert stat.S_ISREG(s.st_mode);assert not os.listxattr(p)
 return dict(path=str(p),dev=s.st_dev,ino=s.st_ino,mode=stat.S_IMODE(s.st_mode),uid=s.st_uid,gid=s.st_gid,size=s.st_size,nlink=s.st_nlink,allocated_bytes=s.st_blocks*512,mtime_ns=s.st_mtime_ns,ctime_ns=s.st_ctime_ns)
def scoped(m):
 assert len(m['files'])==12 and m['directories']==0
 expected={str(OLD/'final'/n)for n in NAMES};actual=[x['source']['path']for x in m['files']]
 assert len(set(actual))==12 and set(actual)==expected,'target scope'
 for x in m['files']:
  p=pathlib.Path(x['source']['path']);q=pathlib.Path(x['retained']['path'])
  assert q==OLD/p.name and p.name in NAMES and q!=p,'retained mapping'
  for z in [q,*q.parents]:assert not z.is_symlink(),'retained symlink'
  assert x['source']['nlink']==1 and(x['source']['dev'],x['source']['ino'])!=(x['retained']['dev'],x['retained']['ino'])
def restore_ram(m):
 scoped(m);mem={}
 for line in open('/proc/meminfo'):
  k,v=line.split(':',1);mem[k]=int(v.strip().split()[0])*1024 if v.strip()else 0
 largest=max(x['source']['size']for x in m['files']);assert mem['MemAvailable']>largest*3+128*1024**2,'RAM reserve'
 reads=[];verified=[]
 for x in m['files']:
  retained=pathlib.Path(x['retained']['path']);before=metadata(retained)
  assert before['size']==x['source']['size']
  fd=os.memfd_create('historical-'+retained.name,flags=0)
  try:
   source_fd=os.open(retained,os.O_RDONLY|os.O_NOFOLLOW);reads.append(str(retained))
   try:
    while True:
     b=os.read(source_fd,1024*1024)
     if not b:break
     view=memoryview(b)
     while view:
      count=os.write(fd,view);assert count>0;view=view[count:]
   finally:os.close(source_fd)
   s=x['source'];os.fchown(fd,s['uid'],s['gid']);os.fchmod(fd,s['mode']);os.utime(fd,ns=(s['mtime_ns'],s['mtime_ns']))
   actual=subprocess.check_output(['sha256sum','--','/proc/self/fd/'+str(fd)],text=True,pass_fds=(fd,)).split()[0];assert actual==x['sha256'],'restored payload hash'
   a=os.fstat(fd);assert(a.st_size,stat.S_IMODE(a.st_mode),a.st_uid,a.st_gid,a.st_mtime_ns)==(s['size'],s['mode'],s['uid'],s['gid'],s['mtime_ns']),'restored metadata'
   assert metadata(retained)==before,'retained input changed during recovery'
   verified.append(dict(name=retained.name,sha256=actual,metadata_equal=True,size=a.st_size))
  finally:os.close(fd)
 assert not(set(reads)&{x['source']['path']for x in m['files']})
 return dict(status='PASS',files_materialized=len(verified),logical_bytes=sum(x['size']for x in verified),max_concurrent_payload_bytes=largest,original_source_payload_reads=len(set(reads)&{x['source']['path']for x in m['files']}),retained_input_reads=len(reads),restored_files=verified,full_application_restore=False)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--ram',action='store_true',required=True);a=p.parse_args();m=json.load(open(a.manifest));print(json.dumps(restore_ram(m)))

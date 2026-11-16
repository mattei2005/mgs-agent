"""Frozen single NPX-tree gate; retained-only recovery; read-only by default."""
import os,sys,stat,pathlib,json,gzip,subprocess,datetime,argparse
sys.dont_write_bytecode=True
OUT=pathlib.Path(__file__).parent
ROOT=pathlib.Path('/root/mgs-agent')
TARGET='/root/.npm/_npx/0d710a328f2801a9'
KEEP='/root/.npm/_npx/f4a9a6fe740fa973'
WRAPPER=pathlib.Path('/root/.hermes/profiles/zeus/codex-pilots/security_sandbox.py')
OWNER='344196393512075265';THREAD='1569928464033783862'
def sha(path):return subprocess.check_output(['sha256sum','--',str(path)],text=True).split()[0]
def digest(data):return subprocess.check_output(['sha256sum'],input=data).split()[0].decode()
def metadata(path):
    s=os.lstat(path);kind='file' if stat.S_ISREG(s.st_mode) else 'directory' if stat.S_ISDIR(s.st_mode) else 'link' if stat.S_ISLNK(s.st_mode) else 'other'
    assert kind!='other' and not os.listxattr(path,follow_symlinks=False)
    row=dict(kind=kind,dev=s.st_dev,ino=s.st_ino,size=s.st_size,allocated=s.st_blocks*512,nlink=s.st_nlink,mode=stat.S_IMODE(s.st_mode),uid=s.st_uid,gid=s.st_gid,mtime_ns=s.st_mtime_ns,ctime_ns=s.st_ctime_ns)
    if kind=='link':row['target']=os.readlink(path)
    return row
def tree(root):
    assert os.path.isdir(root)and not os.path.islink(root)and not os.path.ismount(root)
    device=os.lstat(root).st_dev;result={};stack=[root]
    while stack:
        path=stack.pop();row=metadata(path);assert row['dev']==device
        result[os.path.relpath(path,root)]=row
        if row['kind']=='directory':
            with os.scandir(path)as entries:stack.extend(x.path for x in entries)
    return dict(sorted(result.items()))
def runtime():
    pids={p:int(subprocess.check_output(['systemctl','show',p+'-gateway.service','-p','MainPID','--value'],text=True))for p in ['zeus','ares','atena']};assert all(pids.values())
    return dict(pids=pids,boot_id=pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip(),launcher=os.path.realpath('/root/.local/bin/hermes'))
def consumers():
    needles=[TARGET,'_npx/'+pathlib.Path(TARGET).name];hits=[];links=[];errors=[];seen=0
    roots=[ROOT/'scripts',ROOT/'apps',ROOT/'config',pathlib.Path('/etc/systemd/system'),pathlib.Path('/root/.local/bin'),pathlib.Path('/root/.codex/config.toml')]
    roots += [pathlib.Path('/root/.hermes/profiles')/p/n for p in ['zeus','ares','atena']for n in ['config.yaml','cron','scripts','skills']]
    roots += [WRAPPER.parent]
    exclude={'.git','node_modules','__pycache__','.venv','venv','state','snapshots','source','sandbox','candidates','results','artifacts','sdk-marketplace','private','cache','browser-profiles','media'}
    for root in roots:
        if not root.exists():continue
        if root.is_file():files=[root]
        else:
            files=[]
            for d,ds,fs in os.walk(root,followlinks=False):
                for name in ds+fs:
                    p=pathlib.Path(d)/name
                    if p.is_symlink():
                        resolved=os.path.realpath(p)
                        if resolved==TARGET or resolved.startswith(TARGET+'/'):links.append(str(p))
                ds[:]=[x for x in ds if x not in exclude and not(pathlib.Path(d)/x).is_symlink()];files.extend(pathlib.Path(d)/x for x in fs)
        for p in files:
            try:
                if p.is_symlink()or p.suffix not in {'.py','.sh','.json','.yaml','.yml','.md','.service','.timer','.js','.mjs','.cjs','.ts','.conf','.toml','.pth','.egg-link'}or p.stat().st_size>4*1024**2:continue
                seen+=1;text=p.read_text(errors='replace')
                if any(x in text for x in needles):hits.append(str(p))
            except FileNotFoundError:pass
            except OSError as e:errors.append(dict(path=str(p),error=type(e).__name__))
    cron=subprocess.run(['crontab','-l'],capture_output=True,text=True)
    assert cron.returncode in (0,1)
    if any(x in cron.stdout for x in needles):hits.append('root_crontab')
    for p in [pathlib.Path('/etc/crontab'),*pathlib.Path('/etc/cron.d').glob('*')]:
        if p.is_file() and not p.is_symlink():
            seen+=1
            if any(x in p.read_text(errors='replace')for x in needles):hits.append(str(p))
    processes=[];unreadable=[];pcount=0
    for p in pathlib.Path('/proc').iterdir():
        if not p.name.isdigit():continue
        try:
            pcount+=1;parts=[(p/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace'),os.readlink(p/'cwd'),os.readlink(p/'exe'),(p/'maps').read_text(errors='replace')]
            for fd in(p/'fd').iterdir():
                try:parts.append(os.readlink(fd))
                except (FileNotFoundError,ProcessLookupError):pass
            if any(TARGET in x for x in parts):processes.append(int(p.name))
        except (FileNotFoundError,ProcessLookupError):pass
        except PermissionError:unreadable.append(int(p.name))
    assert not hits and not links and not errors and not processes and not unreadable,'consumer unresolved'
    assert KEEP+'/node_modules' in WRAPPER.read_text(),'current Security wrapper provider changed'
    return dict(status='PASS',code_files_scanned=seen,processes_inspected=pcount,literal_hits=hits,inbound_links=links,process_matches=processes,errors=errors,scope='Local inspected code/config/schedulers and process cmdline/cwd/exe/maps/fd; future manual npx calls can recreate the retired cache')
def scope(m,rows):
    assert m['target']==TARGET and m['retained_root']==KEEP and m['directories_including_root']>0
    assert len(rows)==m['nodes'] and sum(x['source']['kind']=='file'for x in rows)==m['files']
    assert sum(x['source']['kind']=='directory'for x in rows)==m['directories_including_root']
    assert sum(x['source']['kind']=='link'for x in rows)==m['symlinks']
    assert sum(x['source']['allocated']for x in rows)==m['allocated_reclaim_bytes']
    rels=[x['relative']for x in rows];assert len(rels)==len(set(rels)) and '.' in rels
    for x in rows:
        rel=pathlib.PurePosixPath(x['relative']);assert not rel.is_absolute()and '..'not in rel.parts
        s=x['source'];q=x.get('provider')
        if s['kind']=='file':
            assert s['nlink']==1 and q and q['path']!=TARGET and not q['path'].startswith(TARGET+'/')
            assert q['path']==str(pathlib.Path(KEEP)/x['relative'])or pathlib.Path(m['private_ledger']).parent in pathlib.Path(q['path']).parents
        elif s['kind']=='link':assert q and q['path']==str(pathlib.Path(KEEP)/x['relative'])
        else:assert s['kind']=='directory'
def load():
    m=json.load(open(OUT/'npx-retirement-manifest.json'));assert sha(m['private_ledger'])==m['private_ledger_sha256'];rows=json.loads(gzip.open(m['private_ledger'],'rb').read());scope(m,rows);return m,rows
def recover(m,rows):
    scope(m,rows);files=0;links=0;bytes_restored=0;max_size=max(x['source']['size']for x in rows if x['source']['kind']=='file')
    mem=next(int(x.split()[1])*1024 for x in open('/proc/meminfo')if x.startswith('MemAvailable:'));assert mem>max_size*3+256*1024**2
    for x in rows:
        s=x['source']
        if s['kind']=='directory':continue
        q=x['provider'];assert metadata(q['path'])==q['metadata'],'retained provider drift'
        if s['kind']=='link':assert os.readlink(q['path'])==s['target'];links+=1;continue
        fd=os.memfd_create('npx-retained-recovery',flags=0)
        try:
            with open(q['path'],'rb')as f:
                while data:=f.read(1024*1024):
                    view=memoryview(data)
                    while view:n=os.write(fd,view);assert n>0;view=view[n:]
            os.fchown(fd,s['uid'],s['gid']);os.fchmod(fd,s['mode']);os.utime(fd,ns=(s['mtime_ns'],s['mtime_ns']))
            h=subprocess.check_output(['sha256sum','/proc/self/fd/'+str(fd)],pass_fds=(fd,),text=True).split()[0];st=os.fstat(fd)
            assert h==x['sha256']and(st.st_size,stat.S_IMODE(st.st_mode),st.st_uid,st.st_gid,st.st_mtime_ns)==(s['size'],s['mode'],s['uid'],s['gid'],s['mtime_ns'])
            files+=1;bytes_restored+=st.st_size
        finally:os.close(fd)
        assert metadata(q['path'])==q['metadata']
    return dict(status='PASS',regular_files_materialized_in_RAM=files,symlink_targets_validated=links,logical_bytes=bytes_restored,original_payload_reads=0,full_directory_layout_materialized=False,Security_scan_or_authentication_executed=False)
def verify(m,rows,post=False):
    scope(m,rows)
    for path,h in m['protected_helpers'].items():assert sha(path)==h,'protected helper drift'
    if post:assert not os.path.lexists(TARGET)
    else:
        assert tree(TARGET)=={x['relative']:x['source']for x in rows},'target fingerprint drift'
        expected={str(pathlib.Path(TARGET)/x['relative']):x['sha256']for x in rows if x['source']['kind']=='file'};names=list(expected)
        for i in range(0,len(names),150):
            raw=subprocess.check_output(['sha256sum','--zero','--',*names[i:i+150]])
            for part in raw.split(b'\0'):
                if part:h,n=part.split(b'  ',1);assert h.decode()==expected[os.fsdecode(n)],'target payload drift'
        assert tree(TARGET)=={x['relative']:x['source']for x in rows}
    return dict(status='PASS',post=post,consumers=consumers(),recovery=recover(m,rows),runtime=runtime())
def approval(a):
    assert a['owner_id']==OWNER and a['thread_id']==THREAD and a['native_readback_verified']is True and a['scope_expansion_authorized']is False
    assert a['manifest_sha256']==sha(OUT/'npx-retirement-manifest.json')and a['executor_sha256']==sha(__file__)
    assert a['confirmation_content'].strip().lower()=='sim'and a['confirmation_message_id'].isdigit()and a['question_message_id'].isdigit()
def envelope(action,data):
    assert data.get('owner_id',OWNER)==OWNER and data.get('thread_id',THREAD)==THREAD
    return {**data,'agent':'zeus','owner_id':OWNER,'thread_id':THREAD,'action':action,'at':datetime.datetime.now().astimezone().isoformat()}
def audit(action,data):
    row=envelope(action,data)
    with open(ROOT/'logs/events-audit.jsonl','a')as f:f.write(json.dumps(row)+'\n');f.flush();os.fsync(f.fileno())
def disk():
    s=os.statvfs('/');return dict(total=s.f_blocks*s.f_frsize,used=(s.f_blocks-s.f_bfree)*s.f_frsize,available=s.f_bavail*s.f_frsize)
def execute(m,rows):
    a=json.load(open(OUT/'npx-approval.json'));approval(a)
    assert not any((OUT/n).exists()for n in ['npx-start.json','npx-journal.jsonl','npx-filesystem-result.json'])
    before=verify(m,rows);audit('npx_retirement_start',a)
    with open(OUT/'npx-start.json','x')as f:json.dump(a,f);f.flush();os.fsync(f.fileno())
    db=disk()
    try:
        for x in sorted(rows,key=lambda r:len(pathlib.PurePosixPath(r['relative']).parts),reverse=True):
            p=str(pathlib.Path(TARGET)/x['relative']);s=x['source'];now=metadata(p)
            if s['kind']=='directory':assert all(now[k]==s[k]for k in ['kind','dev','ino','mode','uid','gid']);os.rmdir(p)
            else:assert now==s;os.unlink(p)
            with open(OUT/'npx-journal.jsonl','a')as f:f.write(json.dumps(dict(relative=x['relative'],kind=s['kind'],absent=not os.path.lexists(p)))+'\n');f.flush();os.fsync(f.fileno())
        da=disk();(OUT/'npx-disk-interval.json').write_text(json.dumps(dict(before=db,immediate_after=da,observed_global_delta_bytes=da['available']-db['available']),indent=2)+'\n')
        after=verify(m,rows,post=True);assert after['runtime']==before['runtime'];(OUT/'npx-filesystem-result.json').write_text(json.dumps(after,indent=2)+'\n');audit('npx_retirement_completed',a);print(json.dumps(after))
    except Exception as e:audit('npx_retirement_partial_failure',{**a,'error_type':type(e).__name__});raise
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--execute',action='store_true');p.add_argument('--post',action='store_true');args=p.parse_args();m,rows=load()
    if args.execute:assert not args.post;execute(m,rows)
    else:print(json.dumps(verify(m,rows,post=args.post)))

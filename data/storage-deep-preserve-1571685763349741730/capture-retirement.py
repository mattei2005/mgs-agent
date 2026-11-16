"""Exact five-file retirement verifier. Read-only unless newly confirmed."""
import pathlib,json,os,subprocess,hashlib,argparse,datetime,sys,stat
OUT=pathlib.Path(__file__).parent
ROOT=pathlib.Path('/root/mgs-agent')
PARENT=ROOT/'work/finance-reaudit-20260905'
NAMES=['F16-BR-full-post-1545874044757344417.json','F16-user-layout-pre-1545874044757344417.json','F16-feasibility-1545869802898194432.json','batch567-full-postwrite.json','batch567-full-prewrite.json']
def sha(p):return subprocess.check_output(['sha256sum','--',str(p)],text=True).split()[0]
def metadata(p) -> dict:
    s=os.lstat(p);return dict(path=str(p),mode=s.st_mode,size=s.st_size,allocated_bytes=s.st_blocks*512,uid=s.st_uid,gid=s.st_gid,mtime_ns=s.st_mtime_ns,ctime_ns=s.st_ctime_ns,dev=s.st_dev,ino=s.st_ino,nlink=s.st_nlink)
def fingerprint(rows):
    return hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def process_hits(paths):
    ancestors=set();pid=os.getpid()
    while pid>1:
        ancestors.add(pid)
        try:pid=int(pathlib.Path('/proc',str(pid),'stat').read_text().rsplit(')',1)[1].split()[1])
        except OSError:break
    hits=[]
    for proc in pathlib.Path('/proc').iterdir():
        if not proc.name.isdigit() or int(proc.name)in ancestors:continue
        try:
            command=(proc/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')
            if any(p in command for p in paths):hits.append(int(proc.name))
            for q in [proc/'cwd',proc/'exe',*(proc/'fd').iterdir()]:
                try:target=os.readlink(q)
                except OSError:continue
                if target in paths:hits.append(int(proc.name))
        except (OSError,ProcessLookupError):continue
    return sorted(set(hits))
def runtime():
    pids={}
    for profile in ['zeus','ares','atena']:
        assert subprocess.run(['systemctl','is-active','--quiet',profile+'-gateway.service']).returncode==0,'gateway inactive'
        pids[profile]=int(subprocess.check_output(['systemctl','show',profile+'-gateway.service','-p','MainPID','--value'],text=True))
    return dict(pids=pids,boot_id=pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip(),launcher=os.path.realpath('/root/.local/bin/hermes'))
def verify(m,post=False):
    expected=[str(PARENT/n)for n in NAMES]
    assert m['owner_id']=='344196393512075265'and m['thread_id']=='1569928464033783862'
    assert m['preservation_authority_message_id']=='1571685763349741730'
    assert m['executor_sha256']==sha(__file__),'executor drift'
    assert m['targets']==[dict(path=p,action='delete_file')for p in expected],'scope drift'
    assert m['file_count']==len(m['source_metadata'])==5,'count drift'
    if post:assert all(not os.path.lexists(p)for p in expected),'target still present'
    else:
        assert all(pathlib.Path(p).is_file()and not pathlib.Path(p).is_symlink()and not os.path.ismount(p)for p in expected)
        rows=[metadata(p)for p in expected]
        assert all(stat.S_ISREG(r['mode'])and r['nlink']==1 for r in rows)
        assert fingerprint(rows)==m['metadata_fingerprint'],'metadata fingerprint drift'
        assert sum(r['size']for r in rows)==m['logical_bytes'] and sum(r['allocated_bytes']for r in rows)==m['allocated_bytes'],'byte count drift'
        for row in m['original_hashes']:assert sha(row['path'])==row['sha256'],'source payload drift'
        assert not process_hits(expected),'active target consumer'
    for row in m['retained_hashes']+m['protected_hashes']:assert sha(row['path'])==row['sha256'],'retained/protected input drift'
    r=subprocess.run(['python3',m['recovery_reader'],'--ram-restore'],capture_output=True,text=True,timeout=240)
    assert r.returncode==0,'retained-only recovery failed';recovery=json.loads(r.stdout)
    assert recovery['files_verified']==recovery['ram_materializations']==5 and recovery['original_source_payload_reads']==0
    return dict(status='PASS',mode='post'if post else'preflight',file_targets=5,directories_removed=0,original_payload_reads_by_recovery=0,recovery=recovery,runtime=runtime(),deletions_by_verifier=0)
def audit(event,data):
    with open(ROOT/'logs/events-audit.jsonl','a')as f:f.write(json.dumps(dict(at=datetime.datetime.now().astimezone().isoformat(),agent='zeus',thread_id='1569928464033783862',action=event,**data))+'\n');f.flush();os.fsync(f.fileno())
def execute(m):
    approval=OUT/'capture-retirement-approval.json'
    if not approval.exists():raise RuntimeError('missing_new_critical_confirmation_no_mutation')
    a=json.load(open(approval));assert a['native_readback_verified']is True and a['owner_id']=='344196393512075265'and a['thread_id']=='1569928464033783862'
    assert a['confirmation_message_id']!=m['preservation_authority_message_id']and a['manifest_sha256']==sha(OUT/'capture-retirement-manifest.json')and a['executor_sha256']==sha(__file__)
    before=verify(m);fd=os.open(OUT/'capture-retirement-start.json',os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    with os.fdopen(fd,'w')as f:json.dump(a,f);f.flush();os.fsync(f.fileno())
    audit('historical_capture_retirement_start',a)
    try:
        for row in m['targets']:
            os.unlink(row['path'])
            assert not os.path.lexists(row['path'])
            with open(OUT/'capture-retirement-journal.jsonl','a')as f:f.write(json.dumps(dict(row,absent=True))+'\n');f.flush();os.fsync(f.fileno())
        after=verify(m,post=True);assert before['runtime']==after['runtime'],'runtime changed during retirement'
        (OUT/'capture-retirement-filesystem-result.json').write_text(json.dumps(after,indent=2)+'\n');audit('historical_capture_retirement_filesystem_completed',a);print(json.dumps(after))
    except Exception as e:audit('historical_capture_retirement_partial_failure',dict(confirmation_message_id=a['confirmation_message_id'],error_type=type(e).__name__));raise
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--post',action='store_true');p.add_argument('--execute',action='store_true');a=p.parse_args()
    try:
        path=OUT/'capture-retirement-manifest.json';assert sha(path)==(OUT/'capture-retirement-manifest.sha256').read_text().split()[0]
        m=json.load(open(path));execute(m)if a.execute else print(json.dumps(verify(m,a.post)))
    except Exception as e:print('BLOCKED: '+str(e),file=sys.stderr);raise SystemExit(1)

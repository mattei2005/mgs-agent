"""Execute only Rodolfo's confirmed, frozen restore-workspace cleanup."""
import os,sys,json,gzip,stat,hashlib,shutil,subprocess,argparse
from pathlib import Path
sys.path.insert(0,'/root/mgs-agent/scripts')
import ares_archive_bridge as b
import mgs_whole_drive_migration as m
import mgs_backup_archive as archive
APPROVAL='1562683794958450761'
TARGET=Path('/root/.hermes/profiles/zeus/cache/scratch/mgs-dr-restore-qj0i0h9c')
MANIFEST=m.DATA/'restore-temp-cleanup-candidate-1562676006119280762.json'
EXPECTED_MANIFEST_SHA='7dd2255d1c93eccf0c0fbe1eb2bf41bd29c0874d7a12bf6f727214f57db84d16'
RECEIPT=m.DATA/'restore-temp-cleanup-execution-1562683794958450761.json'

def digest(raw):return hashlib.sha256(raw).hexdigest()
def load_contract():
    raw=MANIFEST.read_bytes()
    if digest(raw)!=EXPECTED_MANIFEST_SHA:raise RuntimeError('CONFIRMED_MANIFEST_CHANGED')
    c=json.loads(raw)
    if c['target']!=str(TARGET) or c['file_count']!=203672 or c['directory_count']!=21244 or c['allocated_bytes_inode_deduplicated']!=44591214592:raise RuntimeError('CONFIRMED_SCOPE_CHANGED')
    z=(b.BASE/c['entries_gzip_path']).read_bytes()
    if digest(z)!=c['entries_gzip_sha256']:raise RuntimeError('LEDGER_COMPRESSED_HASH')
    expanded=gzip.decompress(z)
    if digest(expanded)!=c['expanded_manifest_sha256']:raise RuntimeError('LEDGER_EXPANDED_HASH')
    return c

def snapshot(root):
    if root.is_symlink() or not stat.S_ISDIR(root.lstat().st_mode) or root.resolve()!=root or os.path.ismount(root):raise RuntimeError('UNSAFE_ROOT_TYPE')
    for line in Path('/proc/self/mountinfo').read_text().splitlines():
        point=line.split()[4].replace('\\040',' ').replace('\\134','\\')
        if point==str(root) or point.startswith(str(root)+'/'):raise RuntimeError('MOUNT_IN_DELETION_SCOPE')
    rows=[];inodes=set();allocated=0;logical=0;files=0;dirs=0;links=0
    for base,ds,fs in os.walk(root,followlinks=False):
        for p in [Path(base)]+[Path(base)/n for n in fs]+[Path(base)/n for n in ds if (Path(base)/n).is_symlink()]:
            s=p.lstat();kind='directory' if stat.S_ISDIR(s.st_mode) else 'symlink' if stat.S_ISLNK(s.st_mode) else 'file' if stat.S_ISREG(s.st_mode) else 'special'
            if kind not in ['directory','file']:raise RuntimeError('UNEXPECTED_SYMLINK_OR_SPECIAL_FILE')
            rows.append({'relative_path':str(p.relative_to(root)),'type':kind,'dev':s.st_dev,'ino':s.st_ino,'mode':s.st_mode,'size':s.st_size,'mtime_ns':s.st_mtime_ns,'nlink':s.st_nlink})
            if (s.st_dev,s.st_ino) not in inodes:allocated+=s.st_blocks*512;inodes.add((s.st_dev,s.st_ino))
            if kind=='file':files+=1;logical+=s.st_size
            else:dirs+=1
    rows.sort(key=lambda x:x['relative_path'])
    return {'fingerprint_sha256':digest(b.canonical(rows)),'file_count':files,'directory_count':dirs,'symlink_count':links,'logical_file_bytes':logical,'allocated_bytes_inode_deduplicated':allocated}

def process_refs(root):
    refs=[]
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit():continue
        for p in [proc/'cwd',proc/'exe']+list((proc/'fd').glob('*')):
            try:dest=os.readlink(p).removesuffix(' (deleted)')
            except (FileNotFoundError,PermissionError,OSError):continue
            if dest==str(root) or dest.startswith(str(root)+'/'):refs.append({'pid':proc.name,'reference':str(p.relative_to(proc))})
    return refs

def protected_services():
    r=subprocess.run(['systemctl','list-units','--type=service','--all','--no-pager','--plain','--no-legend'],capture_output=True,text=True,check=True)
    names=[line.split()[0] for line in r.stdout.splitlines() if line.split() and any(x in line.split()[0] for x in ['zeus','atena','ares']) and 'gateway' in line.split()[0]]
    if len(names)!=3:raise RuntimeError('PROTECTED_GATEWAY_UNIT_SCOPE')
    states={}
    for name in names:
        p=subprocess.run(['systemctl','show',name,'--property=ActiveState,SubState,MainPID'],capture_output=True,text=True,check=True)
        states[name]=dict(line.split('=',1) for line in p.stdout.splitlines())
        if states[name]['ActiveState']!='active' or int(states[name]['MainPID'])<=0:raise RuntimeError('PROTECTED_GATEWAY_NOT_ACTIVE')
    return states

def protected_check():
    result=archive.verify_pilot(b.Drive(False))
    if result['status']!='verified' or not result['post_move_full_restore_verified']:raise RuntimeError('RETAINED_REMOTE_RECOVERY_NOT_VERIFIED')
    paths={str(m.DATA/'backup-pilot-restore-1562676006119280762.json'):True,str(MANIFEST):True}
    for agent in ['zeus','atena','ares']:
        root=Path('/root/.hermes/profiles')/agent
        if not root.is_dir():raise RuntimeError('PROTECTED_PROFILE_MISSING')
        paths[str(root)]=True
    for name in paths:
        if not Path(name).exists() or Path(name).is_relative_to(TARGET):raise RuntimeError('PROTECTED_PATH_SCOPE')
    return {'remote_backup_id':result['file_id'],'remote_backup_sha256':result['metadata']['sha256Checksum'],'isolated_restore_verified':True,'protected_paths_present':paths,'gateways':protected_services()}

def event(kind,**details):
    with (b.BASE/'logs/events-audit.jsonl').open('a') as f:
        f.write(json.dumps({'at':b.now_iso(),'agent':'zeus','event':kind,'confirmation_message_id':APPROVAL,'target':str(TARGET),'manifest_sha256':EXPECTED_MANIFEST_SHA,'executor_sha256':digest(Path(__file__).read_bytes()),**details})+'\n');f.flush();os.fsync(f.fileno())

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    c=load_contract()
    if RECEIPT.exists() and b.read_json(RECEIPT).get('status')=='completed_validated':
        if TARGET.exists():raise RuntimeError('DELETED_TARGET_REAPPEARED')
        print(json.dumps({'status':'already_completed_no_replay','receipt':str(RECEIPT)}));return
    before=snapshot(TARGET)
    if any(before[k]!=c[k] for k in before):raise RuntimeError('FROZEN_TARGET_DRIFT')
    if process_refs(TARGET):raise RuntimeError('ACTIVE_PROCESS_REFERENCES')
    retained=protected_check();free_before=shutil.disk_usage('/root').free
    pre={'status':'preflight_passed','approval_message_id':APPROVAL,'target':str(TARGET),'snapshot':before,'protected':retained,'host_free_bytes':free_before,'executor_sha256':digest(Path(__file__).read_bytes()),'verified_at':b.now_iso()}
    b.atomic_json(m.DATA/'restore-temp-cleanup-preflight-1562683794958450761.json',pre)
    if not args.apply:print(json.dumps({k:v for k,v in pre.items() if k!='protected'}));return
    # Last process guard follows the remote checks, immediately before deletion.
    if process_refs(TARGET) or TARGET.is_symlink() or os.path.ismount(TARGET):raise RuntimeError('LAST_DESTRUCTIVE_BOUNDARY_GUARD')
    event('confirmed_restore_temp_cleanup_start',snapshot=before)
    try:
        shutil.rmtree(TARGET)
        if TARGET.exists() or TARGET.is_symlink():raise RuntimeError('EXACT_TARGET_STILL_PRESENT')
        after=protected_check()
        if after['gateways']!=retained['gateways']:raise RuntimeError('PROTECTED_GATEWAY_STATE_CHANGED')
        free_after=shutil.disk_usage('/root').free
        receipt={'status':'completed_validated','approval_message_id':APPROVAL,'target':str(TARGET),'target_absent':True,'removed':before,'host_free_bytes_before':free_before,'host_free_bytes_after':free_after,'observed_free_bytes_delta':free_after-free_before,'observed_free_gib_delta':round((free_after-free_before)/(1024**3),2),'protected_before':retained,'protected_after':after,'other_scratch_and_source_outside_scope':True,'remote_backup_deleted':False,'production_profiles_deleted':False,'cleanup_policy_changed':False,'executor_sha256':digest(Path(__file__).read_bytes()),'manifest_sha256':EXPECTED_MANIFEST_SHA,'completed_at':b.now_iso()}
        b.atomic_json(RECEIPT,receipt);event('confirmed_restore_temp_cleanup_completed_validated',target_absent=True,observed_free_bytes_delta=free_after-free_before)
        print(json.dumps({k:v for k,v in receipt.items() if k not in ['protected_before','protected_after']}))
    except Exception as exc:
        b.atomic_json(RECEIPT,{'status':'partial_or_postcheck_failure','approval_message_id':APPROVAL,'target':str(TARGET),'target_absent':not TARGET.exists(),'error_type':type(exc).__name__,'error':str(exc)[:300],'at':b.now_iso()});event('confirmed_restore_temp_cleanup_partial_failure',target_absent=not TARGET.exists(),error_type=type(exc).__name__);raise
if __name__=='__main__':main()

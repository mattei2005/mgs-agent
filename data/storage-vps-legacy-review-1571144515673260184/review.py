import os, stat, json, subprocess, collections, tarfile, hashlib, gzip, datetime
from pathlib import Path
ROOT=Path('/root/.hermes/secure-backups/vps-maintenance')
OUT=Path('/root/mgs-agent/data/storage-vps-legacy-review-1571144515673260184')
OUT.mkdir(mode=0o700,parents=True,exist_ok=True)
errors=[];rows=[];sets={};dev=ROOT.stat().st_dev

def category(rel):
    name=Path(rel).name
    if name.startswith('hermes-profile-control-plane') or name=='profiles-control-plane.tar.gz':return 'historical_hermes_control_plane_archives'
    if 'events-audit' in rel or 'infra-inventory.pre-scope-drift' in rel:return 'historical_audit_inventory_state'
    if any(x in rel.split('/') for x in ['rollback-verify','installed-deb-build']):return 'expanded_package_verification'
    if name.endswith(('.deb','.tar.gz','.tgz')):return 'package_payload_and_other_recovery_archives'
    return 'compact_evidence_code_configuration'

def walk(p):
    try:s=os.lstat(p)
    except OSError as e:errors.append([str(p),type(e).__name__]);return
    if s.st_dev!=dev:errors.append([str(p),'mount_boundary']);return
    rel=os.path.relpath(p,ROOT)
    row={'relative_path':rel,'mode':s.st_mode,'size':s.st_size,'mtime_ns':s.st_mtime_ns,'ctime_ns':s.st_ctime_ns,'dev':s.st_dev,'ino':s.st_ino,'nlink':s.st_nlink,'allocated':s.st_blocks*512,'category':category(rel)}
    if stat.S_ISLNK(s.st_mode):row['link_target']=os.readlink(p)
    rows.append(row)
    if stat.S_ISDIR(s.st_mode):
        for n in sorted(os.listdir(p)):walk(p/n)
walk(ROOT)
files=[r for r in rows if stat.S_ISREG(r['mode'])]
# Hash through the shell toolchain, never expose file content.
paths=[str(ROOT/r['relative_path']) for r in files]
proc=subprocess.run(['xargs','-0','sha256sum','--zero'],input=b'\0'.join(os.fsencode(p) for p in paths)+b'\0',capture_output=True,check=True)
hashes={}
for line in proc.stdout.split(b'\0'):
    if line:hashes[os.fsdecode(line[66:])]=line[:64].decode()
for r in files:r['sha256']=hashes[str(ROOT/r['relative_path'])]
# Deduplicate inode occupancy without assigning shared blocks arbitrarily.
inodes=collections.defaultdict(list)
for r in rows:inodes[(r['dev'],r['ino'])].append(r)
classes=collections.defaultdict(lambda:{'regular_files':0,'allocated_bytes':0})
for r in files:classes[r['category']]['regular_files']+=1
for rr in inodes.values():
    cc={r['category'] for r in rr};cat=next(iter(cc)) if len(cc)==1 else 'shared_hardlinks'
    classes[cat]['allocated_bytes']+=rr[0]['allocated']
for r in rows:
    top=r['relative_path'].split('/')[0]
    if top=='.':continue
    st=sets.setdefault(top,{'regular_files':0,'directories':0,'symlinks':0,'allocated_bytes':0,'categories':collections.Counter()})
    st['regular_files']+=stat.S_ISREG(r['mode']);st['directories']+=stat.S_ISDIR(r['mode']);st['symlinks']+=stat.S_ISLNK(r['mode'])
    st['categories'][r['category']]+=stat.S_ISREG(r['mode'])
for rr in inodes.values():
    top={r['relative_path'].split('/')[0] for r in rr}
    if len(top)==1 and next(iter(top)) in sets:sets[next(iter(top))]['allocated_bytes']+=rr[0]['allocated']
# Check all compressed archives without extracting any member.
archive_checks=[]
for r in files:
    if r['relative_path'].endswith(('.tar.gz','.tgz')):
        p=ROOT/r['relative_path']
        gz=subprocess.run(['gzip','-t',str(p)],capture_output=True)
        tar=subprocess.run(['tar','-tzf',str(p)],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        archive_checks.append({'relative_path':r['relative_path'],'gzip_rc':gz.returncode,'tar_rc':tar.returncode})
# Compare historical profile member bytes with the retained November archive.
old=[r for r in files if r['category']=='historical_hermes_control_plane_archives']
retained=json.load(open('/root/mgs-agent/data/storage-backup-review-1570830889359777924/retained-archives-validation.json'))[:2]
retained_hashes=set();retained_checks=[]
def member_hashes(p):
    result=[]
    with tarfile.open(p,'r|gz') as tf:
        for m in tf:
            if m.isfile():
                h=hashlib.sha256();f=tf.extractfile(m)
                while b:=f.read(1024*1024):h.update(b)
                result.append({'member':m.name,'size':m.size,'sha256':h.hexdigest()})
    return result
for a in retained:
    h=subprocess.run(['sha256sum',a['path']],capture_output=True,text=True,check=True).stdout.split()[0]
    assert h==a['sha256'],'retained archive checksum drift'
    members=member_hashes(a['path']);retained_hashes.update(x['sha256'] for x in members)
    retained_checks.append({'path':a['path'],'sha256':h,'files_streamed':len(members),'recorded_hash_matches':True})
comparison=[];member_ledger={}
for r in old:
    mm=member_hashes(ROOT/r['relative_path']);member_ledger[r['relative_path']]=mm
    unmatched=[m for m in mm if m['sha256'] not in retained_hashes]
    comparison.append({'relative_path':r['relative_path'],'regular_members':len(mm),'matched_payloads':len(mm)-len(unmatched),'unmatched_payloads':len(unmatched),'unmatched_logical_bytes':sum(m['size'] for m in unmatched),'unmatched_classes':dict(collections.Counter('database' if m['member'].endswith(('.db','.db-wal','.sqlite','.sqlite3')) else 'configuration_auth_or_other_control_plane' for m in unmatched)),'classification':'preserve_unproven_historical_subsumption' if unmatched else 'member_payloads_covered_requires_reference_and_evidence_checks'})
# Observe exact path use, without printing unrelated processes or command lines.
refs=[];proc_errors=0
for pid in os.listdir('/proc'):
    if not pid.isdigit() or int(pid)==os.getpid():continue
    for leaf in ['cwd','exe']:
        try:
            target=os.readlink(f'/proc/{pid}/{leaf}')
            if target==str(ROOT) or target.startswith(str(ROOT)+'/'):refs.append({'pid':int(pid),'reference':leaf,'path':target})
        except OSError:pass
    try:
        for fd in os.listdir(f'/proc/{pid}/fd'):
            try:
                target=os.readlink(f'/proc/{pid}/fd/{fd}')
                if target==str(ROOT) or target.startswith(str(ROOT)+'/'):refs.append({'pid':int(pid),'reference':'fd','path':target})
            except OSError:pass
    except OSError:proc_errors+=1
# Original bytes and metadata must remain stable across read-only inspection.
drift=[]
for r in rows:
    p=ROOT/r['relative_path'];s=os.lstat(p)
    current=(s.st_mode,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_dev,s.st_ino,s.st_nlink,s.st_blocks*512)
    before=tuple(r[k] for k in ['mode','size','mtime_ns','ctime_ns','dev','ino','nlink','allocated'])
    if current!=before:drift.append(r['relative_path'])
verify=subprocess.run(['xargs','-0','sha256sum','--zero'],input=b'\0'.join(os.fsencode(p) for p in paths)+b'\0',capture_output=True,check=True)
assert verify.stdout==proc.stdout,'source byte drift during read-only review'
assert not errors and not drift, 'metadata scan error or drift'
checks_failed=[a for a in archive_checks if a['gzip_rc'] or a['tar_rc']]
v=os.statvfs('/');used=(v.f_blocks-v.f_bfree)*v.f_frsize;available=v.f_bavail*v.f_frsize
summary={'status':'classification_complete_preservation_required_before_broad_retirement','request_message_id':'1571144515673260184','thread_id':'1569928464033783862','observed_at':datetime.datetime.now().astimezone().isoformat(),'root':str(ROOT),'entries':len(sets),'directories_at_root':sum((ROOT/x).is_dir() for x in sets),'regular_files':len(files),'symlinks':sum(stat.S_ISLNK(r['mode']) for r in rows),'directories':sum(stat.S_ISDIR(r['mode']) for r in rows),'occupied_inode_unique_bytes':sum(rr[0]['allocated'] for rr in inodes.values()),'category_totals':dict(classes),'sets':sets,'archive_checks':{'checked':len(archive_checks),'failed':len(checks_failed)},'historical_profile_archive_comparison':comparison,'retained_archives':retained_checks,'process_references':refs,'process_fd_directories_unreadable':proc_errors,'scan_errors':errors,'source_metadata_drift':drift,'source_payloads_unchanged':True,'eligible_frozen_reclaim_bytes':0,'deletions':0,'retention_changed':False,'disk':{'used_bytes':used,'available_bytes':available,'used_percent':100*used/(used+available)},'scope_boundary':'Only the old VPS-maintenance root was reviewed; no new full-VPS or runtime cleanup, no SQLite connection or DB restore, no credential changes. Archive comparison proves member-byte differences against the two latest Hermes archives, not global uniqueness or loss of live history.','recommendation':'Preserve historical control-plane differences and checksum-coupled evidence before any broader old-maintenance retirement; do not treat the entire root as one redundant VPS backup. A preservation/repack proposal and a later exact deletion gate are distinct from this read-only review.'}
with gzip.open(OUT/'metadata-and-hashes.json.gz','wt',encoding='utf-8') as f:json.dump(rows,f,ensure_ascii=False)
with gzip.open(OUT/'archive-member-comparison.json.gz','wt',encoding='utf-8') as f:json.dump(member_ledger,f,ensure_ascii=False)
(OUT/'archive-checks.json').write_text(json.dumps(archive_checks,ensure_ascii=False,indent=2)+'\n')
(OUT/'review-result.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:summary[k] for k in ['status','entries','directories_at_root','regular_files','directories','symlinks','occupied_inode_unique_bytes','category_totals','archive_checks','historical_profile_archive_comparison','process_references','source_payloads_unchanged','eligible_frozen_reclaim_bytes','deletions','disk']},ensure_ascii=False))
if checks_failed:raise SystemExit('Archive integrity failure requires investigation before closure')

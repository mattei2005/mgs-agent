"""Deeper read-only coverage and native-package audit of the two roots."""
import pathlib,json,subprocess,os,stat,tarfile,hashlib,collections,datetime,gzip
os.umask(0o077)
OUT=pathlib.Path(__file__).parent
ROOTS=[pathlib.Path('/root/zeus-vps-maintenance-1565730926233657347'),pathlib.Path('/root/mgs-agent-backups')]
SOURCES=[('/root/.hermes/secure-backups/maintenance-history/20261114-1571190519713759264/source-manifest.json','/root/.hermes/secure-backups/maintenance-history/20261114-1571190519713759264/maintenance-history.tar.xz'),('/root/.hermes/secure-backups/storage-backup-remainder-1571327506374598789/site-source-manifest.json','/root/.hermes/secure-backups/storage-backup-remainder-1571327506374598789/site-backup-history.tar.xz')]
PRIVATE=pathlib.Path('/root/.hermes/secure-backups/storage-deep-review-1571685763349741730');PRIVATE.mkdir(mode=0o700,exist_ok=False)
def sha(p):return subprocess.check_output(['sha256sum','--',str(p)],text=True).split()[0]
def meta(p) -> dict:
    s=os.lstat(p);return dict(path=str(p),mode=s.st_mode,size=s.st_size,allocated=s.st_blocks*512,dev=s.st_dev,ino=s.st_ino,nlink=s.st_nlink,mtime_ns=s.st_mtime_ns,ctime_ns=s.st_ctime_ns,uid=s.st_uid,gid=s.st_gid)
files=[];nodes=[]
for root in ROOTS:
    for p in [root,*root.rglob('*')]:
        r=meta(p);assert not stat.S_ISLNK(r['mode']),'unexpected source symlink';nodes.append(r)
        if stat.S_ISREG(r['mode']):r['sha256']=sha(p);files.append(r)
# Bind the previously retained archive/manifests to original exact recovery hashes.
old=json.load(open('/root/mgs-agent/data/storage-backup-remainder-1571327506374598789/deletion-manifest.json'))
expected={x['path']:x['sha256']for x in old['recovery_hashes']}
verified_archives=[];coverage_index=collections.defaultdict(list)
for manifest_path,archive_path in SOURCES:
    assert sha(manifest_path)==expected[manifest_path] and sha(archive_path)==expected[archive_path],'retained input drift'
    m=json.load(open(manifest_path));wanted={}
    for row in m['files']:
        if stat.S_ISREG(row['mode']):
            member=pathlib.Path(m['root']).name+'/'+row['relative_path'];wanted[member]=row
    found=0
    with tarfile.open(archive_path,'r|xz')as tf:
        for member in tf:
            if not member.isfile():continue
            assert member.name in wanted,'unexpected regular archive member'
            row=wanted[member.name];stream=tf.extractfile(member);assert stream is not None;h=hashlib.sha256();size=0
            while chunk:=stream.read(1024*1024):h.update(chunk);size+=len(chunk)
            assert size==row['size'] and h.hexdigest()==row['sha256'],'retained manifest payload mismatch'
            coverage_index[(size,h.hexdigest())].append(dict(archive=archive_path,member=member.name,uid=member.uid,gid=member.gid,mode=member.mode,mtime=member.pax_headers.get('mtime',str(member.mtime))))
            found+=1
    assert found==len(wanted)
    verified_archives.append(dict(path=archive_path,regular_members_verified=found,sha256=sha(archive_path)))
for row in files:
    row['retained_exact_payload_sources']=coverage_index.get((row['size'],row['sha256']),[])
# Native package archive readability and current-version comparison only. No install.
backup=json.load(open(ROOTS[0]/'backup-result.json'));packages=[]
for row in backup['packages']:
    path=pathlib.Path(row['artifact']);assert path.exists() and sha(path)==row['sha256'],'historical rollback package drift'
    identity=subprocess.check_output(['dpkg-deb','-f',str(path),'Package','Version'],text=True).splitlines()
    current=subprocess.run(['dpkg-query','-W','-f=${Version}',row['package']],capture_output=True,text=True)
    proc=subprocess.Popen(['dpkg-deb','--fsys-tarfile',str(path)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    assert proc.stdout is not None;count=0;live_equal=0;live_different=0;live_missing=0;bytes_read=0
    with tarfile.open(fileobj=proc.stdout,mode='r|')as tf:
        for member in tf:
            if not member.isfile():continue
            stream=tf.extractfile(member);assert stream is not None;h=hashlib.sha256();size=0
            while chunk:=stream.read(1024*1024):h.update(chunk);size+=len(chunk)
            count+=1;bytes_read+=size
            relative=member.name[2:] if member.name.startswith('./') else member.name
            assert not pathlib.PurePosixPath(relative).is_absolute() and '..' not in pathlib.PurePosixPath(relative).parts,'unsafe package member'
            target=pathlib.Path('/')/relative
            if target.is_file() and not target.is_symlink():
                if target.stat().st_size==size and sha(target)==h.hexdigest():live_equal+=1
                else:live_different+=1
            else:live_missing+=1
    proc.stdout.close();stderr=proc.stderr.read()if proc.stderr is not None else b'';assert proc.wait(timeout=30)==0,'package stream failure'
    packages.append(dict(package=row['package'],historical_version=row['version'],installed_version=current.stdout.strip()if current.returncode==0 else None,same_version=current.returncode==0 and current.stdout.strip()==row['version'],archive_identity=identity,regular_payloads_streamed=count,logical_payload_bytes=bytes_read,live_equal_regular_files=live_equal,live_different_regular_files=live_different,live_missing_or_symlink=live_missing))
# The retained configuration is examined as opaque payload hashes, never printed.
config=ROOTS[0]/'system-config.tgz';members=[]
with tarfile.open(config,'r|gz')as tf:
    for member in tf:
        if member.isfile():
            stream=tf.extractfile(member);assert stream is not None;h=hashlib.sha256();size=0
            while chunk:=stream.read(1024*1024):h.update(chunk);size+=len(chunk)
            members.append(dict(member=member.name,size=size,sha256=h.hexdigest()))
# Recheck every source, not just the large candidates.
for row in files:
    assert meta(row['path'])=={k:row[k]for k in meta(row['path'])},'source metadata changed'
    assert sha(row['path'])==row['sha256'],'source payload changed'
with gzip.open(PRIVATE/'full-file-coverage.json.gz','wt')as f:json.dump(dict(nodes=nodes,files=files,config_members=members),f)
covered=[r for r in files if r['retained_exact_payload_sources']];uncovered=[r for r in files if not r['retained_exact_payload_sources']]
by_root=[]
for root in ROOTS:
    rows=[r for r in files if r['path'].startswith(str(root)+'/')]
    by_root.append(dict(root=str(root),files=len(rows),logical_bytes=sum(r['size']for r in rows),allocated_regular_bytes=sum(r['allocated']for r in rows),covered_files=sum(bool(r['retained_exact_payload_sources'])for r in rows),uncovered_files=sum(not r['retained_exact_payload_sources']for r in rows)))
result=dict(status='deep_content_review_complete_originals_preserved',authority_message_id='1571685763349741730',regular_files_hashed=len(files),source_metadata_and_bytes_unchanged=True,retained_archives=verified_archives,by_root=by_root,exact_payload_covered_files=len(covered),exact_payload_uncovered_files=len(uncovered),covered_logical_bytes=sum(r['size']for r in covered),uncovered_logical_bytes=sum(r['size']for r in uncovered),package_archives_checked=len(packages),packages=packages,configuration_archive_regular_members=len(members),payload_coverage_not_path_independence=True,missing_coverage_is_scoped_not_global_uniqueness=True,private_evidence=str(PRIVATE/'full-file-coverage.json.gz'),deletions=0,package_installs_or_changes=0,configs_applied=0,at=datetime.datetime.now(datetime.timezone.utc).isoformat())
(OUT/'maintenance-deep-review.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(status=result['status'],regular_files_hashed=len(files),by_root=by_root,packages_checked=len(packages),same_installed_version=sum(r['same_version']for r in packages),retained_config_members=len(members),covered_files=len(covered),uncovered_files=len(uncovered),originals_unchanged=True,deletions=0)))

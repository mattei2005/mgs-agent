"""Create and exercise private lossless preservation; originals remain."""
import pathlib,json,subprocess,os,stat,datetime
os.umask(0o077)
OUT=pathlib.Path(__file__).parent
ROOT=pathlib.Path('/root/mgs-agent')
PROPOSAL=ROOT/'data/storage-remainder-review-1571661469475672075/preservation-proposal.json'
BUNDLE=pathlib.Path('/root/.hermes/secure-backups/storage-captures-1571685763349741730')
def sha(path):return subprocess.check_output(['sha256sum','--',str(path)],text=True).split()[0]
def metadata(path):
    s=os.lstat(path)
    return dict(path=str(path),size=s.st_size,allocated_bytes=s.st_blocks*512,mode=s.st_mode,uid=s.st_uid,gid=s.st_gid,mtime_ns=s.st_mtime_ns,ctime_ns=s.st_ctime_ns,dev=s.st_dev,ino=s.st_ino,nlink=s.st_nlink)
def validate_sources(proposal):
    assert len(proposal['targets'])==5
    for row in proposal['targets']:
        assert metadata(row['path'])=={k:row[k]for k in metadata(row['path'])},'source metadata drift'
        assert not os.path.islink(row['path']) and stat.S_ISREG(row['mode'])
        assert not os.listxattr(row['path'],follow_symlinks=False),'source xattrs need explicit preservation'
        assert sha(row['path'])==row['sha256'],'source bytes drift'
proposal=json.load(open(PROPOSAL));validate_sources(proposal)
assert not BUNDLE.exists(),'existing preservation; reconcile before retry'
free=os.statvfs(BUNDLE.parent);available=free.f_bavail*free.f_frsize
# Archive worst case plus one-GiB persistent reserve. RAM restore is serialized.
assert available>proposal['logical_bytes']+1024**3,'disk capacity gate'
BUNDLE.mkdir(mode=0o700)
parent=pathlib.Path(proposal['targets'][0]['path']).parent
assert all(pathlib.Path(x['path']).parent==parent for x in proposal['targets'])
manifest=dict(scope_id='storage-five-captures-1571685763349741730',owner_id='344196393512075265',thread_id='1569928464033783862',authority_message_id='1571685763349741730',source_proposal_sha256=sha(PROPOSAL),source_root=str(parent),files=[dict(x,member=pathlib.Path(x['path']).name,xattrs={})for x in proposal['targets']],originals_must_remain=True,created_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
(BUNDLE/'source-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
(BUNDLE/'recover.py').write_bytes((OUT/'recover-captures.py').read_bytes())
archive=BUNDLE/'captures.tar.xz'
cmd=['tar','--format=pax','--numeric-owner','--acls','--xattrs','--xattrs-include=*','--pax-option=delete=atime,delete=ctime','-I','xz -T2 -3','-cf',str(archive),'-C',str(parent),*[pathlib.Path(x['path']).name for x in proposal['targets']]]
r=subprocess.run(cmd,capture_output=True,text=True,timeout=420)
(OUT/'archive-command-readback.json').write_text(json.dumps(dict(returncode=r.returncode,stderr=r.stderr),indent=2)+'\n');assert r.returncode==0,'archive creation failed; preserve partial evidence'
for cmd in [['xz','-t',str(archive)],['tar','-tJf',str(archive)]]:
    check=subprocess.run(cmd,capture_output=True,timeout=180);assert check.returncode==0,'archive integrity/listing failed'
sumlines=subprocess.check_output(['sha256sum','captures.tar.xz','source-manifest.json','recover.py'],cwd=BUNDLE,text=True)
(BUNDLE/'SHA256SUMS').write_text(sumlines)
reader=subprocess.run(['python3',str(BUNDLE/'recover.py'),'--ram-restore'],capture_output=True,text=True,timeout=240)
(OUT/'retained-only-replay.json').write_text(reader.stdout);assert reader.returncode==0,reader.stdout[:300]
replay=json.loads(reader.stdout);assert replay['files_verified']==replay['ram_materializations']==5 and replay['original_source_payload_reads']==0
validate_sources(proposal)
allocated=sum(p.stat().st_blocks*512 for p in BUNDLE.iterdir()if p.is_file())
result=dict(status='preserved_validated_originals_retained',authority_message_id='1571685763349741730',bundle=str(BUNDLE),source_files=5,source_logical_bytes=proposal['logical_bytes'],source_allocated_bytes=proposal['allocated_bytes'],bundle_allocated_bytes=allocated,bundle_MiB=round(allocated/2**20,2),archive_sha256=sha(archive),archive_size=archive.stat().st_size,retained_only_reader=replay,all_original_hashes_and_metadata_unchanged=True,originals_present=5,deletions=0,actual_reclaimed_bytes=0,potential_net_bytes_if_separately_authorized_original_retirement=proposal['allocated_bytes']-allocated,potential_net_GiB_if_separately_authorized_original_retirement=round((proposal['allocated_bytes']-allocated)/2**30,2),permanent_real_disk_restore_copy_created=False,real_files_restored_one_at_a_time_to_anonymous_RAM=True,full_application_restore_executed=False,financial_operations=0,source_proposal_sha256=sha(PROPOSAL),at=datetime.datetime.now(datetime.timezone.utc).isoformat())
(OUT/'preservation-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))

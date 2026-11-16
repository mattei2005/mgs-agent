"""Portable retained-only recovery of the five authorized captures."""
import argparse, pathlib, json, subprocess, tarfile, hashlib, decimal, os, stat
NAMES = {'F16-BR-full-post-1545874044757344417.json','F16-user-layout-pre-1545874044757344417.json','F16-feasibility-1545869802898194432.json','batch567-full-postwrite.json','batch567-full-prewrite.json'}

def run(bundle, ram=False, destination=None):
    bundle=pathlib.Path(bundle).resolve()
    check=subprocess.run(['sha256sum','--quiet','-c','SHA256SUMS'],cwd=bundle,capture_output=True,text=True)
    assert check.returncode==0,'bundle checksum failure'
    m=json.load(open(bundle/'source-manifest.json'))
    assert m['scope_id']=='storage-five-captures-1571685763349741730'
    rows={x['member']:x for x in m['files']}
    assert len(m['files'])==5 and set(rows)==NAMES,'scope drift'
    assert all(pathlib.PurePosixPath(n).name==n for n in rows),'unsafe member'
    dest=None
    if destination is not None:
        dest=pathlib.Path(destination).absolute()
        assert not os.path.lexists(dest),'destination already exists'
        assert str(dest)!=m['source_root'] and not str(dest).startswith(m['source_root']+'/'),'production overwrite forbidden'
        parent=dest.parent
        while parent!=parent.parent:
            assert not parent.is_symlink(),'symlink ancestor forbidden'
            parent=parent.parent
        dest.mkdir(mode=0o700)
    seen=set();total=0;ram_count=0;written=0
    with tarfile.open(bundle/'captures.tar.xz','r|xz') as tf:
        for member in tf:
            assert member.name in rows and member.name not in seen and member.isfile(),'unexpected archive member'
            row=rows[member.name]
            ns=int(decimal.Decimal(member.pax_headers.get('mtime',str(member.mtime)))*1_000_000_000)
            assert (member.size,member.mode,member.uid,member.gid,ns)==(row['size'],stat.S_IMODE(row['mode']),row['uid'],row['gid'],row['mtime_ns']),'member metadata drift'
            assert not row['xattrs'],'unsupported source xattrs'
            stream=tf.extractfile(member);assert stream is not None
            fd=None;fileobj=None
            if ram:
                available=int(next(s.split()[1]for s in pathlib.Path('/proc/meminfo').read_text().splitlines()if s.startswith('MemAvailable:')))*1024
                assert available>2*row['size']+1024**3,'RAM restore capacity gate'
                fd=os.memfd_create('mgs-retained-capture',os.MFD_CLOEXEC)
                fileobj=os.fdopen(fd,'wb',closefd=False)
            elif dest is not None:
                fd=os.open(dest/member.name,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
                fileobj=os.fdopen(fd,'wb',closefd=False)
            h=hashlib.sha256();size=0
            try:
                while chunk:=stream.read(1024*1024):
                    h.update(chunk);size+=len(chunk)
                    if fileobj is not None:fileobj.write(chunk)
                assert size==row['size'] and h.hexdigest()==row['sha256'],'recovery payload mismatch'
                if fd is not None:
                    assert fileobj is not None
                    fileobj.flush();os.fchown(fd,row['uid'],row['gid']);os.fchmod(fd,stat.S_IMODE(row['mode']));os.utime(fd,ns=(row['mtime_ns'],row['mtime_ns']))
                    s=os.fstat(fd)
                    assert (s.st_size,stat.S_IMODE(s.st_mode),s.st_uid,s.st_gid,s.st_mtime_ns)==(row['size'],stat.S_IMODE(row['mode']),row['uid'],row['gid'],row['mtime_ns'])
                    if ram:
                        actual=subprocess.check_output(['sha256sum','/proc/self/fd/'+str(fd)],pass_fds=(fd,),text=True).split()[0]
                        assert actual==row['sha256'],'materialized RAM hash mismatch';ram_count+=1
                    else:written+=1
            finally:
                if fileobj is not None:fileobj.close()
                if fd is not None:os.close(fd)
            seen.add(member.name);total+=size
    assert seen==NAMES,'missing archive member'
    if dest is not None:
        for name,row in rows.items():
            actual=subprocess.check_output(['sha256sum',str(dest/name)],text=True).split()[0]
            assert actual==row['sha256'],'disk materialization hash mismatch'
    return dict(status='PASS',files_verified=len(seen),logical_bytes_verified=total,ram_materializations=ram_count,disk_materializations=written,original_source_payload_reads=0,metadata_verified=True,original_ctime_recorded_not_recreatable=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--bundle',default=str(pathlib.Path(__file__).parent));p.add_argument('--ram-restore',action='store_true');p.add_argument('--destination');a=p.parse_args()
    try:print(json.dumps(run(a.bundle,a.ram_restore,a.destination)))
    except Exception as exc:print(json.dumps(dict(status='BLOCKED',error_type=type(exc).__name__,reason=str(exc))));raise SystemExit(1)

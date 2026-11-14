#!/usr/bin/env python3
"""Verify immutable maintenance history or restore to a NEW isolated directory."""
import argparse,hashlib,json,os,pathlib,stat,subprocess,tarfile
from decimal import Decimal

def verify(base):
    subprocess.run(['sha256sum','--status','-c','SHA256SUMS'],cwd=base,check=True)
    manifest=json.loads((base/'source-manifest.json').read_text())
    prefix=pathlib.Path(manifest['root']).name
    expected={prefix+('' if r['relative_path']=='.' else '/'+r['relative_path']):r for r in manifest['files']}
    seen=set();payloads={};counts={'files':0,'directories':0,'symlinks':0}
    with tarfile.open(base/'maintenance-history.tar.xz','r|xz') as tf:
        for m in tf:
            name=m.name.rstrip('/')
            assert name in expected and name not in seen,'Unexpected or duplicate archive member'
            assert not pathlib.PurePosixPath(name).is_absolute() and '..' not in pathlib.PurePosixPath(name).parts
            r=expected[name];seen.add(name)
            assert m.mode==stat.S_IMODE(r['mode']) and m.uid==r['uid'] and m.gid==r['gid'],'Ownership/mode mismatch'
            assert abs(int(Decimal(m.pax_headers.get('mtime',str(m.mtime)))*1000000000)-r['mtime_ns'])<=1,'Timestamp mismatch'
            if stat.S_ISDIR(r['mode']):assert m.isdir();counts['directories']+=1
            elif stat.S_ISLNK(r['mode']):assert m.issym() and m.linkname==r['link_target'];counts['symlinks']+=1
            elif stat.S_ISREG(r['mode']):
                if m.islnk():assert m.linkname in payloads;h,n=payloads[m.linkname]
                else:
                    assert m.isfile();hsh=hashlib.sha256();n=0;stream=tf.extractfile(m)
                    while chunk:=stream.read(1024*1024):hsh.update(chunk);n+=len(chunk)
                    h=hsh.hexdigest()
                assert h==r['sha256'] and n==r['size'],'Payload mismatch'
                payloads[name]=(h,n);counts['files']+=1
            else:raise AssertionError('Unsupported source type')
    assert seen==set(expected),'Incomplete archive'
    # No member may descend through an archived symlink.
    for name in expected:
        for parent in pathlib.PurePosixPath(name).parents:
            row=expected.get(str(parent))
            assert row is None or not stat.S_ISLNK(row['mode']),'Symlink traversal in archive'
    return manifest,counts

def restore(base,destination,manifest):
    destination=destination.expanduser().absolute()
    assert not destination.exists() and not destination.is_symlink(),'Destination must not exist'
    resolved=destination.resolve();scratch=pathlib.Path('/root/.hermes/profiles/zeus/cache/scratch').resolve()
    if not resolved.is_relative_to(scratch):
        assert not any(resolved.is_relative_to(pathlib.Path(p)) or pathlib.Path(p).is_relative_to(resolved) for p in ['/etc','/usr','/boot','/root/.hermes','/root/mgs-agent']), 'Use a new isolated scratch destination, never a live path'
    os.umask(0o077);destination.mkdir(mode=0o700,parents=True)
    subprocess.run(['tar','-xJf',str(base/'maintenance-history.tar.xz'),'--xattrs','--xattrs-include=*','--acls','--same-owner','--same-permissions','-C',str(destination)],check=True)
    root=destination/pathlib.Path(manifest['root']).name
    for r in manifest['files']:
        p=root/r['relative_path'];s=os.lstat(p)
        assert s.st_mode==r['mode'] and s.st_uid==r['uid'] and s.st_gid==r['gid'] and s.st_mtime_ns==r['mtime_ns'],'Restored metadata mismatch'
        if stat.S_ISREG(s.st_mode):
            h=subprocess.run(['sha256sum',str(p)],capture_output=True,text=True,check=True).stdout.split()[0]
            assert h==r['sha256'] and s.st_size==r['size'],'Restored bytes mismatch'
        if stat.S_ISLNK(s.st_mode):assert os.readlink(p)==r['link_target']
        assert {k:os.getxattr(p,k,follow_symlinks=False).hex() for k in os.listxattr(p,follow_symlinks=False)}==r['xattrs'],'Restored xattrs mismatch'
    return str(root)

def main():
    p=argparse.ArgumentParser();p.add_argument('--base',type=pathlib.Path,default=pathlib.Path(__file__).resolve().parent);p.add_argument('--restore-to',type=pathlib.Path);a=p.parse_args()
    manifest,counts=verify(a.base)
    result={'status':'verified','self_contained':True,'counts':counts}
    if a.restore_to:result.update(status='restored_verified',isolated_root=restore(a.base,a.restore_to,manifest))
    print(json.dumps(result))
if __name__=='__main__':main()

"""Pure fail-closed core: only exact approved gzip dumps, no credential handling."""
import pathlib,os,json,stat,fcntl,subprocess,datetime

def run(plan,now,apply=False,guard=lambda: False):
    assert now.tzinfo is not None,'aware_clock_required'
    assert now >= datetime.datetime.fromisoformat(plan['not_before']),'retention_not_complete'
    assert guard(),'instruction_or_hold_block'
    root=pathlib.Path(plan['backup_root']);assert root.is_dir() and not root.is_symlink() and root.resolve()==root,'root_changed'
    rs=root.stat();assert rs.st_uid==0 and stat.S_IMODE(rs.st_mode)==0o700,'private_root_changed'
    targets=plan['files'];assert len(targets)==2 and len({x['path'] for x in targets})==2,'exact_two_targets_required'
    receipt=root/'authorized-dump-purge-receipt.json';prior=json.loads(receipt.read_text()) if receipt.exists() else None
    if prior:assert prior['plan_sha256']==plan['plan_sha256'] and prior['confirmation_message_id']==plan['confirmation_message_id'],'prior_receipt_drift'
    resolved=[]
    for t in targets:
        p=pathlib.Path(t['path']);assert p.parent==root and p.parent.resolve()==root and not p.is_symlink(),'path_or_symlink_changed'
        if not p.exists():
            assert prior and any(x['path']==str(p) and x['sha256']==t['sha256'] for x in prior.get('validated',[])),'unattributed_missing_dump'
            resolved.append({'path':str(p),'sha256':t['sha256'],'bytes':t['bytes'],'already_absent':True});continue
        st=p.lstat();assert stat.S_ISREG(st.st_mode) and st.st_uid==0 and stat.S_IMODE(st.st_mode)==0o600 and st.st_nlink==1 and st.st_size==t['bytes'],'private_dump_or_bytes_changed'
        fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW)
        try:
            fs=os.fstat(fd);assert (fs.st_dev,fs.st_ino)==(st.st_dev,st.st_ino),'inode_race'
            digest=subprocess.check_output(['sha256sum','/proc/self/fd/'+str(fd)],text=True,pass_fds=(fd,)).split()[0];assert digest==t['sha256'],'dump_hash_changed'
            assert subprocess.run(['gzip','-t','/proc/self/fd/'+str(fd)],pass_fds=(fd,),capture_output=True).returncode==0,'gzip_invalid'
        finally:os.close(fd)
        resolved.append({'path':str(p),'sha256':digest,'bytes':st.st_size,'inode':st.st_ino,'device':st.st_dev,'mtime_ns':st.st_mtime_ns,'already_absent':False})
    others={str(p):p.stat().st_size for p in root.iterdir() if str(p) not in {x['path'] for x in targets} and p!=receipt}
    result={'status':'dry_run_validated' if not apply else 'prepared','plan_sha256':plan['plan_sha256'],'manifest_sha256':plan['manifest_sha256'],'confirmation_message_id':plan['confirmation_message_id'],'utc':now.astimezone(datetime.timezone.utc).isoformat(),'validated':resolved,'removed_or_verified_absent':[],'untouched_other_artifacts':others}
    if not apply:return result
    def save():
        tmp=root/'authorized-dump-purge-receipt.tmp';fd=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        with os.fdopen(fd,'w') as f:json.dump(result,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
        os.replace(tmp,receipt);df=os.open(root,os.O_RDONLY|os.O_DIRECTORY);os.fsync(df);os.close(df)
    save()
    for t in resolved:
        assert guard(),'instruction_or_hold_block'
        p=pathlib.Path(t['path'])
        if not t['already_absent']:
            st=p.lstat();assert not p.is_symlink() and (st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns)==(t['device'],t['inode'],t['bytes'],t['mtime_ns']),'unlink_target_drift'
            p.unlink()
        assert not p.exists() and not p.is_symlink(),'unlink_readback_failed'
        result['removed_or_verified_absent'].append(t['path']);result['status']='partial' if len(result['removed_or_verified_absent'])<2 else 'completed';save()
    assert {str(p):p.stat().st_size for p in root.iterdir() if str(p) not in {x['path'] for x in targets} and p!=receipt}==others,'unrelated_artifact_changed'
    assert all(not pathlib.Path(x['path']).exists() for x in targets) and json.loads(receipt.read_text())==result,'exact_post_readback_failed'
    return result

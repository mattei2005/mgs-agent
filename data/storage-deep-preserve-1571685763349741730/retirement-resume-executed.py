"""Bounded recovery after audit serialization failed before any deletion.
The approved manifest and its frozen validator are not edited or relaxed.
"""
import pathlib,json,os,subprocess,sys,datetime,importlib.util,argparse
sys.dont_write_bytecode=True
OUT=pathlib.Path(__file__).parent
ROOT=pathlib.Path('/root/mgs-agent')
MANIFEST_SHA='4ae58340cef7628339f7a9d005b9f5901cc115035d99832854a72e120407f534'
FROZEN_EXECUTOR_SHA='69932098c1f051bb44bb011de3bfcf91aac42e8dc4b9b00c7101c2f4c58ac80f'
OWNER='344196393512075265';THREAD='1569928464033783862';CONFIRMATION='1571691667516424224'
def sha(p):return subprocess.check_output(['sha256sum','--',str(p)],text=True).split()[0]
def envelope(action,data):
    assert data.get('thread_id',THREAD)==THREAD,'audit thread conflict'
    assert data.get('owner_id',OWNER)==OWNER,'audit owner conflict'
    return {**data,'at':datetime.datetime.now().astimezone().isoformat(),'agent':'zeus','thread_id':THREAD,'action':action}
def audit(action,data):
    payload=envelope(action,data)
    with open(ROOT/'logs/events-audit.jsonl','a')as f:
        f.write(json.dumps(payload)+'\n');f.flush();os.fsync(f.fileno())
def disk():
    s=os.statvfs('/')
    return dict(total=s.f_blocks*s.f_frsize,used=(s.f_blocks-s.f_bfree)*s.f_frsize,available=s.f_bavail*s.f_frsize,at=datetime.datetime.now().astimezone().isoformat())
def preflight():
    assert sha(OUT/'capture-retirement-manifest.json')==MANIFEST_SHA
    assert sha(OUT/'capture-retirement.py')==FROZEN_EXECUTOR_SHA
    m=json.load(open(OUT/'capture-retirement-manifest.json'))
    a=json.load(open(OUT/'capture-retirement-approval.json'))
    assert a['native_readback_verified']is True and a['owner_id']==OWNER and a['thread_id']==THREAD and a['confirmation_message_id']==CONFIRMATION
    assert a['manifest_sha256']==MANIFEST_SHA and a['executor_sha256']==FROZEN_EXECUTOR_SHA
    assert json.load(open(OUT/'capture-retirement-start.json'))==a,'original reservation drift'
    failure=json.load(open(OUT/'retirement-execution-output.json'))
    assert failure['returncode']==1 and "dict() got multiple values for keyword argument 'thread_id'"in failure['stderr'],'different failure requires diagnosis'
    assert not(OUT/'capture-retirement-journal.jsonl').exists() and not(OUT/'capture-retirement-filesystem-result.json').exists(),'prior filesystem effects; do not replay'
    assert all(os.path.lexists(x['path'])for x in m['targets']),'partial absence requires different recovery'
    spec=importlib.util.spec_from_file_location('approved_frozen_capture_gate',OUT/'capture-retirement.py');assert spec and spec.loader
    gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)
    checked=gate.verify(m)
    # Exercise audit payload construction with the exact native approval shape.
    sample=envelope('capture_retirement_resume_start',a)
    assert sample['thread_id']==THREAD and sample['confirmation_message_id']==CONFIRMATION
    try:envelope('fixture',dict(a,thread_id='wrong'))
    except AssertionError:pass
    else:raise RuntimeError('audit conflict accepted')
    return m,a,gate,checked
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--resume',action='store_true');args=p.parse_args()
    m,a,gate,checked=preflight()
    proof=dict(status='PASS',cause='Duplicate thread_id in audit envelope; original reservation created but audit failed before unlink loop.',targets_present=5,journal_absent=True,source_scope_unchanged=True,frozen_manifest_sha256=MANIFEST_SHA,frozen_executor_sha256=FROZEN_EXECUTOR_SHA,frozen_validator_unchanged=True,verification=checked,audit_envelope_exact_approval_test='PASS',audit_conflicting_thread_negative='PASS',recovery_adapter_sha256=sha(__file__))
    if not args.resume:print(json.dumps(proof));raise SystemExit(0)
    fd=os.open(OUT/'retirement-recovery-start.json',os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    with os.fdopen(fd,'w')as f:json.dump(dict(proof=proof,approval=a),f);f.flush();os.fsync(f.fileno())
    audit('historical_capture_retirement_recovered_start',{**a,'recovery_adapter_sha256':proof['recovery_adapter_sha256'],'original_reservation_preserved':True,'frozen_validator_unchanged':True})
    before=disk();(OUT/'retirement-recovered-disk-before.json').write_text(json.dumps(before,indent=2)+'\n')
    expected={r['path']:r for r in m['source_metadata']}
    try:
        for row in m['targets']:
            assert row['action']=='delete_file' and gate.metadata(row['path'])==expected[row['path']],'target metadata changed after preflight'
            os.unlink(row['path']);assert not os.path.lexists(row['path'])
            with open(OUT/'capture-retirement-journal.jsonl','a')as f:f.write(json.dumps(dict(row,absent=True))+'\n');f.flush();os.fsync(f.fileno())
        after_disk=disk();(OUT/'retirement-recovered-disk-immediate-after.json').write_text(json.dumps(after_disk,indent=2)+'\n')
        after=gate.verify(m,post=True);assert after['runtime']==checked['runtime'],'runtime changed'
        (OUT/'capture-retirement-filesystem-result.json').write_text(json.dumps(after,indent=2)+'\n')
        audit('historical_capture_retirement_filesystem_completed',{**a,'recovered_audit_serialization':True})
        result=dict(status='PASS',targets_absent=5,journal_entries=5,scope_unchanged=True,frozen_validator_unchanged=True,post=after,observed_immediate_delta_bytes=after_disk['available']-before['available'],source_directories_removed=0,original_failed_attempt_source_deletions=0)
        (OUT/'retirement-recovery-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
    except Exception as exc:
        audit('historical_capture_retirement_recovery_partial_failure',dict(confirmation_message_id=CONFIRMATION,error_type=type(exc).__name__))
        raise

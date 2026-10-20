"""Isolated native-Ares engineering canary. Never a production lineage or campaign input."""
from pathlib import Path
import json,io,os,subprocess
import ares_archive_bridge as bridge
class SelftestError(RuntimeError):pass

def validate_selftest_identity(test,raw,clean,raw_sha):
    if test.get('schema')!='mgs.intake.selftest.v1' or test.get('validation_only') is not True or test.get('run_id')!='1562188030205362227':raise SelftestError('SELFTEST_SCOPE')
    if raw.get('id')!=test['raw_source_id'] or raw.get('parents')!=[test['legacy_parent_id']] or clean.get('id')==raw.get('id') or clean.get('parents')!=[test['ready_parent_id']] or raw_sha!=test['raw_sha256']:raise SelftestError('SELFTEST_IDENTITY')
    if any(x.get('properties',{}).get('mgsArchiveType')!='intake_test_media' for x in [raw,clean]):raise SelftestError('SELFTEST_MEDIA_MARKER')
    return True

def finish(d,clean_id):
    from PIL import Image
    path=bridge.DATA/'intake-selftest-1562188030205362227.json';test=bridge.read_json(path);assert isinstance(test,dict)
    if test.get('status')!='pending':return {'status':test['status'],'archive_job_id':test.get('archive_job_id')}
    raw=d.meta(test['raw_source_id']);clean=d.meta(clean_id);bridge.require_publisher(raw,bridge.CANONICAL_SA);bridge.require_publisher(clean,bridge.CANONICAL_SA)
    rh=d.hashes(raw['id']);ch=d.hashes(clean['id']);validate_selftest_identity(test,raw,clean,rh['sha256'])
    for m in [raw,clean]:
        if m.get('driveId')!=bridge.SOURCE_DRIVE or m.get('trashed') or not m.get('name','').startswith('MGS_INTAKE_TEST_ONLY_'):raise SelftestError('SELFTEST_PHYSICAL_SCOPE')
        if d.relative_parent(m['parents'][0],bridge.config_load()['control_folder_id'])[:1]!=['TEST_INPUTS_INTAKE_AUTOMATION']:raise SelftestError('SELFTEST_CONTROL_ONLY')
    raw_bytes=d.raw(raw['id']);clean_bytes=d.raw(clean['id']);one=Image.open(io.BytesIO(raw_bytes)).convert('RGB');two=Image.open(io.BytesIO(clean_bytes)).convert('RGB')
    if one.size!=two.size or one.tobytes()!=two.tobytes():raise SelftestError('SELFTEST_LOSSLESS_PIXEL_QA')
    scratch=Path(os.environ.get('TMPDIR','/root/.hermes/profiles/ares/cache/scratch'))/'intake-selftest-1562188030205362227';scratch.mkdir(parents=True,exist_ok=True);download=scratch/'verified-clean.png';download.write_bytes(clean_bytes)
    check=subprocess.run(['python3',str(bridge.BASE/'scripts/clean-creative-metadata.py'),'verify',str(download),'--json'],capture_output=True,text=True,timeout=90)
    if check.returncode!=0 or json.loads(check.stdout).get('clean') is not True:raise SelftestError('SELFTEST_SANITIZER_VERIFY')
    rows=[json.loads(l) for l in (bridge.BASE/'data/ares/creative-ops/inventory/assets.jsonl').read_text().splitlines() if l.strip()]
    if any(r.get(k) in [raw['id'],clean['id']] for r in rows for k in ['source_drive_id','asset_drive_id']):raise SelftestError('SELFTEST_CONTAMINATED_INVENTORY')
    with bridge.queue_lock():
        c=bridge.config_load();assets=[bridge.asset_snapshot(d,c,raw['id'],'original'),bridge.asset_snapshot(d,c,clean['id'],'clean')];job=bridge.make_request(c,assets,kind='lineage',lineage_id='INTAKE-TECHNICAL-SELFTEST-1562188030205362227',validation_only=True);result=bridge.enqueue(d,c,job)
    test.update(status='processed_waiting_archive',processed_at=bridge.now_iso(),clean_source_id=clean['id'],clean_sha256=ch['sha256'],clean_md5=ch['md5'],raw_legacy_verified=True,clean_ready_verified=True,lossless_pixels_verified=True,sanitizer_clean_verified=True,primary_inventory_isolated=True,archive_job_id=result['jobId'],archive_request_file_id=result['requestFileId']);bridge.atomic_json(path,test)
    return {'status':test['status'],'archive_job_id':result['jobId'],'validationOnly':True,'primary_inventory_written':False,'pixels_equal':True,'metadata_clean':True}

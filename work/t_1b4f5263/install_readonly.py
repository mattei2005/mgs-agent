"""CAS install of the bounded read-only consumer, under archive/inventory locks."""
import sys,fcntl,hashlib,json,os,tempfile
from pathlib import Path
ROOT=Path('/root/mgs-agent');sys.path.insert(0,str(ROOT/'scripts'))
import ares_archive_bridge as b
H=b.DATA/'consumer-recovery-t_1b4f5263';W=ROOT/'work/t_1b4f5263'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
baseline=b.read_json(H/'baseline.json');backup=H/'installation-backup';backup.mkdir(exist_ok=True)
files=['ares_archive_readonly_reconciliation.py','ares_archive_storage.py']
with b.queue_lock():
 with (ROOT/'data/ares/creative-ops/inventory/assets.jsonl.lock').open('a+') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX)
  with (H/'.install.lock').open('a+') as maint:
   fcntl.flock(maint,fcntl.LOCK_EX|fcntl.LOCK_NB)
   for rel,expected in baseline['file_sha256'].items():assert sha(ROOT/rel)==expected,rel
   inv=ROOT/'data/ares/creative-ops/inventory/assets.jsonl';rows=[json.loads(x) for x in inv.read_text().splitlines() if x.strip()]
   for row in baseline['inventory_rows']:assert [r for r in rows if r['asset_id']==row['asset_id']]==[row]
   assert not (ROOT/'scripts'/files[0]).exists(),'new_module_already_present_reconcile_first'
   manifest={'task_id':'t_1b4f5263','installed_at':b.now_iso(),'before':{},'after':{},'inventory_sha256':sha(inv),'binding_sha256':sha(H/'approved-readonly-binding.json')}
   for name in files:
    target=ROOT/'scripts'/name;source=W/name
    if target.exists():
     assert not (backup/name).exists();(backup/name).write_bytes(target.read_bytes());manifest['before'][str(target.relative_to(ROOT))]=sha(target)
    else:manifest['before'][str(target.relative_to(ROOT))]=None
    temp=target.with_suffix('.t_1b4f5263.new');assert not temp.exists();temp.write_bytes(source.read_bytes());os.chmod(temp,0o644);os.replace(temp,target)
    assert sha(target)==sha(source);manifest['after'][str(target.relative_to(ROOT))]=sha(target)
   b.atomic_json(H/'installation-receipt.json',manifest)
   print(json.dumps(manifest))

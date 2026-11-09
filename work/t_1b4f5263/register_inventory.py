"""Record only this installation in infra inventory; preserve concurrent state."""
import fcntl,hashlib,json,os,sys
from pathlib import Path
from datetime import datetime
ROOT=Path('/root/mgs-agent');sys.path.insert(0,str(ROOT/'scripts'))
import ares_archive_bridge as b
H=b.DATA/'consumer-recovery-t_1b4f5263';ip=ROOT/'data/infra-inventory.json'
with (ROOT/'data/.infra-inventory.lock').open('a+') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX)
 with (ROOT/'data/infra-inventory.json.lock').open('a+') as other:
  fcntl.flock(other,fcntl.LOCK_EX)
  before=ip.read_bytes();value=json.loads(before)
  backup=H/'infra-inventory-before-installation.json'
  if not backup.exists():backup.write_bytes(before)
  receipt=b.read_json(H/'installation-receipt.json')
  for rel,digest in receipt['after'].items():
   p=ROOT/rel;st=p.stat();record={'path':str(p),'size_bytes':st.st_size,'modified_at':datetime.fromtimestamp(st.st_mtime).astimezone().isoformat(timespec='seconds')}
   matches=[i for i,item in enumerate(value['scripts']) if item.get('path')==str(p)]
   assert len(matches)<=1
   if matches:value['scripts'][matches[0]]=record
   else:value['scripts'].append(record)
  artifact={'id':'ares-readonly-pairs-t_1b4f5263','agent':'ares','type':'exact_pair_readonly_consumer_reconciliation','status':'installed_native_34_of_34_verified','authority_message_id':'1569458720050516030','confirmation_message_id':'1569459090634047609','request_id':'shein-1569454008337301577','evidence':str(H/'canonical-consumers-accepted.json'),'installation_sha256':receipt['after'],'binding':str(H/'approved-readonly-binding.json'),'tests_installed':193,'native_negative_guards':2,'media_writes':0,'meta_calls':0,'frozen_records_preserved':True,'skill_reference_sha256':hashlib.sha256(Path('/root/.hermes/profiles/ares/skills/growth/creative-operations-mgs/references/drive-meta-asset-identity-and-manager-reservation.md').read_bytes()).hexdigest(),'updated_at':b.now_iso()}
  hits=[i for i,r in enumerate(value['runtime_artifacts']) if r.get('id')==artifact['id']];assert len(hits)<=1
  if hits:value['runtime_artifacts'][hits[0]]=artifact
  else:value['runtime_artifacts'].append(artifact)
  assert ip.read_bytes()==before,'infra_inventory_CAS'
  b.atomic_json(ip,value)
  assert next(r for r in b.read_json(ip)['runtime_artifacts'] if r.get('id')==artifact['id'])==artifact
  b.atomic_json(H/'inventory-registration-receipt.json',{'artifact':artifact,'before_sha256':hashlib.sha256(before).hexdigest(),'after_sha256':hashlib.sha256(ip.read_bytes()).hexdigest()})
  print(json.dumps({'inventory_artifact_id':artifact['id'],'readback':True}))

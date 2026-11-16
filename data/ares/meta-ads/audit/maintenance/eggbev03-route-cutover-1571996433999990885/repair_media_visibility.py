"""Scoped media-layer repair through canonical pre-stage; never campaign writes."""
import sys,json,hashlib,shutil
from pathlib import Path
sys.path.insert(0,'/root/mgs-agent/scripts')
R=Path('/root/mgs-agent');RID='eggbev03-c212-replacement-1571894746719330377';AID='1481815942722118';H=R/'data/ares/meta-ads/audit/eggbev/same-account'/RID/'execution';D=H/'media-visibility-repair';D.mkdir(exist_ok=True)
from ares_campaign_v3 import eggbev_same_account_replacement as same
from ares_campaign_v3.media_registry import MediaRegistry
from ares_campaign_v3.prestage import PrestageService,OnDemandMediaPipeline
from ares_campaign_v3.coordination import AccountWriterLeaseStore
from request_serialization import request_lock
runner=same.importlib.util if False else None
import importlib.util
s=importlib.util.spec_from_file_location('canonical_target_media_runner',R/'scripts/ares-eggbev-target-clone.py');runner=importlib.util.module_from_spec(s);s.loader.exec_module(runner)
q=same.request_load(R/'data/ares/meta-ads/requests'/(RID+'.json'));same.admit(q);cfg=same.load(runner.CONFIG);common,meta,sb,token=same.runtime(runner,cfg);same.live_request(q,common);same.verify_advertiser(meta,token)
proof=same.load(H/'current-main-account-video-reconciliation.json');assert proof['complete'] and proof['exact_id_matches']==0 and proof['approved_video_count']==30
selected=same.load(H/'selected-assets.json');inventory=[json.loads(x) for x in runner.INVENTORY.read_text().splitlines() if x.strip()];byid={x['asset_id']:x for x in inventory};count=int(sys.argv[1]) if len(sys.argv)>1 else 1;assert 1<=count<=15;selected=selected[:count]
work=Path('/root/.hermes/profiles/ares/cache/scratch')/RID/'media-visibility-repair';work.mkdir(parents=True,exist_ok=True)
creation=runner.module('canonical_clean_verifier',R/'scripts/ares-eggbev-creation.py');paths={};manifest=[]
for asset in selected:
 current=byid[asset['asset_id']];assert current['clean_checksum']==asset['clean_checksum'] and current.get('reservation_request_id')==RID
 row={'asset_id':asset['asset_id'],'canonical_filename':asset['canonical_filename'],'clean_checksum':asset['clean_checksum'],'variants':{}}
 for variant in ['vertical','square']:
  target=work/(asset['asset_id']+'-'+variant+'.mp4')
  if not target.exists():
   source=Path('/root/.hermes/profiles/ares/cache/scratch/eggbev03-cross-account-1571623835822858352')/target.name
   assert source.exists();shutil.copy2(source,target)
  checksum=creation.verify_clean(target)
  if variant=='vertical':assert checksum==asset['clean_checksum']
  row['variants'][variant]={'sha256':checksum,'bytes':target.stat().st_size,'exact_existing_bytes_reused':True}
 paths[asset['asset_id']]={'vertical_path':str(work/(asset['asset_id']+'-vertical.mp4')),'square_path':str(work/(asset['asset_id']+'-square.mp4'))}
 manifest.append(row)
runner.save(D/'byte-verification.json',{'request_id':RID,'assets':manifest,'canonical_registry_changed':False})
lease=AccountWriterLeaseStore(cfg['state_root']);lease.claim(AID,RID,status='PRESTAGING_MISSING_MEDIA_RECOVERY')
try:
 with request_lock(Path(cfg['state_root'])/'locks',RID+'-media-visibility-repair'):
  service=PrestageService(MediaRegistry(D/'candidate-registry.json'),runner.TargetAccountUploader(common=meta,user_token=token,account_id=AID))
  result=OnDemandMediaPipeline(service,max_workers=3).run(account_id=AID,assets=selected,prepare_asset=lambda asset:paths[asset['asset_id']])
  runner.save(D/('prestage-'+str(count)+'.json'),result);print(json.dumps({'status':'MEDIA_PRESTAGE_VERIFIED','assets':len(result['assets']),'videos':sum(bool(a['registry'].get(k)) for a in result['assets'] for k in ['vertical_video_id','square_video_id']),'original_manifest_and_production_registry_preserved':True}))
finally:lease.mark(AID,RID,'RECOVERY_PENDING')

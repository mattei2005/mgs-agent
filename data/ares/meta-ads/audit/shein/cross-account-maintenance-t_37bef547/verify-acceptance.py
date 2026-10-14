"""Maintenance verification: live GETs + explicitly fake offline media/core.
Never upload/reserve/call the live Engine writer. Persist safe proofs only.
"""
import copy
import hashlib
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, '/root/mgs-agent/scripts')
from ares_campaign_v3 import shein_single_clone as driver, shein_reference as reference, shein_general as compiler
from ares_campaign_v3.shein_grouped_media import manager_folder
from ares_campaign_v3.shein_media_handoff import _ops
from ares_campaign_v3.media_registry import MediaRegistry
from ares_campaign_v3.prevalidation import prevalidate_payload, validate_account_policy
from ares_campaign_v3.schema import Manifest
from ares_campaign_v3.engine import CampaignEngine
from ares_campaign_v3.transport import FakeBatchTransport

BASE=Path('/root/mgs-agent');OUT=Path(__file__).resolve().parent

def main():
    request=json.loads((OUT/'reference-request.json').read_text())
    intent=json.loads((BASE/'data/ares/meta-ads/audit/shein/campaigns/intake'/request['request_id']/'blocked-intent.json').read_text())
    assert request['request_id']==intent['request_id'] and request['website_url']==intent['website_url'] and request['primary_text']==intent['primary_text']
    assert request['campaign_groups'][0]['files']==intent['files_ordered']
    config=json.loads((BASE/'data/ares/meta-ads/engine-v3/config.json').read_text())
    operation=json.loads((BASE/'data/ares/meta-ads/operations/SHEIN-US-DIRECT.json').read_text())
    profiles=json.loads((BASE/'data/ares/meta-ads/operations/SHEIN-US-DIRECT-profiles.json').read_text())['profiles']
    target=copy.deepcopy(profiles[intent['target_account_id']]);target['channel_authorization_policy']=operation['channel_authorization_policy']
    target,source_profile=reference.configure(request,target,profiles,operation,driver.lookup_account);target['reference_profile']=source_profile
    common=driver.ReadOnlyClient(driver._load_common())
    token,_=common.common.get_token_from_1password(config['accounts'][target['account_id']]['token_item'])
    marker=driver.CURRENT_PROFILE.set(target)
    try:prepared,_=driver._prepare(request,config,common,token,reference_only=True)
    finally:driver.CURRENT_PROFILE.reset(marker)
    ops=_ops(BASE);drive_token,identity=ops.drive_runtime_token()
    folder=manager_folder(request,target,BASE,ops,drive_token)
    inventory=[json.loads(line) for line in (BASE/'data/ares/creative-ops/inventory/assets.jsonl').read_text().splitlines() if line.strip()]
    selected=[];files=[]
    for name in request['campaign_groups'][0]['files']:
        matches=[r for r in inventory if r.get('canonical_filename')==name];assert len(matches)==1
        row=matches[0];file=ops.drive_file_readback(drive_token,row['asset_drive_id'])
        assert file['driveId']=='0AEwt4Ye690ocUk9PVA' and file['parents']==[folder['id']] and file['name']==name and not file.get('trashed')
        files.append(file)
        selected.append({'asset_id':row['asset_id'],'checksum':row['clean_checksum'],'canonical_filename':name,'language':row['language'],
                         'vertical_video_id':'OFFLINE-NOT-UPLOADED-'+str(len(selected)+1),'thumbnail_url':'https://example.test/offline-not-real.jpg',
                         'ready':True,'association_verified':True,'upload_edge':'ad_account_advideos'})
    resolved=prepared['resolved_request'];resolved['_resolved_assets']=selected
    source=prepared['source'];source_before=copy.deepcopy(source)
    draft=compiler.build(resolved,source,prepared['number'],prepared['compiler_config'])
    assert source==source_before and draft['campaigns'][0]['account_id']==intent['target_account_id']
    assert len(draft['campaigns'][0]['ads'])==2 and draft['campaigns'][0]['campaign_create']['daily_budget']=='5000'
    assert draft['campaigns'][0]['adset_create']['bid_amount']=='90'
    validate_account_policy(Manifest.from_dict(draft),config)
    with tempfile.TemporaryDirectory() as raw:
        root=Path(raw);registry=MediaRegistry(root/'OFFLINE-registry.json')
        for asset in selected:
            registry.register(account_id=target['account_id'],asset_id=asset['asset_id'],checksum=asset['checksum'],vertical_video_id=asset['vertical_video_id'],square_video_id=None,ready=True,upload_edge='ad_account_advideos',association_verified=True)
        payload,target_manifest,barrier=driver.seal_creation_pair(draft,config,registry);manifest=Manifest.from_dict(payload)
        offline_config=copy.deepcopy(config)
        offline_config.update(state_root=str(root/'state'),audit_root=str(root/'audit'),shein_execution_sla={'enabled':False})
        transport=FakeBatchTransport(target['account_id']);engine=CampaignEngine(offline_config,transport_factory=lambda aid:transport)
        plan=engine.dry_run(manifest)
        # Explicit OFFLINE transport: these IDs are simulated, never Meta IDs.
        result=engine.execute(manifest)
    proof={'task_id':'t_37bef547','verified_at':datetime.now(timezone.utc).isoformat(),'live_mode':'READ_ONLY',
           'request_id':request['request_id'],'source_account_id':source['campaign']['account_id'],'source_campaign_id':source['campaign']['id'],
           'target_account_id':target['account_id'],'source_account':prepared['reference_account'],'target_account':prepared['account'],
           'source_ad_ids':[a['id'] for a in source['ads']], 'page_id':prepared['page_id'],'pixel_id':source['adset']['promoted_object']['pixel_id'],
           'next_target_number':prepared['number'],'budget_minor':draft['campaigns'][0]['campaign_create']['daily_budget'],'bid_minor':draft['campaigns'][0]['adset_create']['bid_amount'],
           'ads_order':[a['canonical_filename'] for a in selected],'literal_url_preserved':True,'literal_copy_preserved':True,
           'drive_files':files,'drive_identity':identity,'source_local_snapshot_unchanged':source==source_before,
           'offline_media_is_synthetic':True,'offline_engine_status':result['status'],'offline_only_simulated_campaign_count':len(result['campaign_ids']),
           'source_mutations':0,'live_campaign_writes':0,'live_media_uploads':0,'inventory_reservations':0,'drive_writes':0,
           'live_api_acceptance_verified':False,'serving_verified':False,'original_message_id':request['source_message_id'],
           'late_recovery_review_required_before_activation':True,'plan':plan['plan']}
    # No signed source thumbnail/preview URLs or Page tokens are persisted.
    driver.atomic_json(OUT/'acceptance-proof.json',proof)
    draft['maintenance_offline_only']=True;draft['prevalidated']=False
    driver.atomic_json(OUT/'OFFLINE-template-NOT-EXECUTABLE.json',draft)
    print(json.dumps({k:proof[k] for k in ['task_id','live_mode','request_id','next_target_number','budget_minor','bid_minor','offline_engine_status','live_campaign_writes','live_media_uploads','inventory_reservations','serving_verified']},indent=2))

if __name__=='__main__':
    try:main()
    except Exception as exc:
        print(json.dumps({'status':'MAINTENANCE_VERIFICATION_FAILED','error_type':type(exc).__name__}));raise SystemExit(1)

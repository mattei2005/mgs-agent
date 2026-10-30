"""Read-only REAL 16-image validation; prohibit all campaign/Drive mutations."""
import copy,hashlib,json,os,sys
from pathlib import Path
from datetime import datetime,timezone
B=Path('/root/mgs-agent');W=B/'work/t_8364ae25';installed='--installed' in sys.argv
sys.path[:0]=([] if installed else [str(W/'stage')])+[str(B/'scripts')]
assert Path(os.environ['HERMES_HOME'])==Path('/root/.hermes/profiles/ares')
from ares_campaign_v3 import image_prestage as ip,image_identity as identity,shein_media_handoff as handoff
from ares_campaign_v3 import shein_single_clone as route,shein_continuation as central,shein_reviewed_targeting as reviewed,shein_reviewed_img as img
from ares_campaign_v3.shein_channel_authority import _get
from ares_campaign_v3 import shein_request_queue as queue
from ares_campaign_v3.media_registry import MediaRegistry,MediaNotReady
R='shein-1565747351543480374';A='937846586033361';proofdir=B/'data/ares/meta-ads/audit/shein/campaigns/intake'/R
baseline=json.loads((W/'baseline-state-hashes.json').read_text())
def unchanged():
 assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in baseline.items())
unchanged()
s=json.loads((B/'data/ares/meta-ads/state/shein-campaigns/single-clone'/R/'state.json').read_text())
c=json.loads((B/'data/ares/meta-ads/engine-v3/state/checkpoints'/(R+'-'+A+'.json')).read_text())
dp=B/'data/ares/meta-ads/audit/shein/campaigns/continuations'/(R+'-review-1565779731440468199.json');d=json.loads(dp.read_text())
assert hashlib.sha256(dp.read_bytes()).hexdigest()==json.loads((B/'work/t_fc58be96/deployment-receipt.json').read_text())['descriptor_sha256']
assert s['phase']=='POSTPROCESS_PENDING' and not s.get('qa_proof') and not s.get('media_postprocess_complete') and not s.get('activation_result')
auth=queue.authorize_queue_request(s['request'],B)
proof=central.validate_descriptor(d,s,c,get_message=_get)
context={'descriptor':d,'state':s,'checkpoint':c,'verified':proof}
config=json.loads((B/'data/ares/meta-ads/engine-v3/config.json').read_text());account=config['accounts'][A]
common=route._load_common();token,_=common.get_token_from_1password(account['token_item']);client=route.ReadOnlyClient(common)
http,act,_=client.graph_get('act_'+A,token,{'fields':'id,account_id,currency,timezone_name'})
assert http==200 and act['account_id']==A and act['currency']=='USD' and act['timezone_name']=='America/New_York'
assets=s['new_media_assets'];registry=MediaRegistry(B/'data/ares/meta-ads/engine-v3/media-registry.json')
library=ip.read_account_images(client,token,A,hashes=[a['image_hash'] for a in assets]);rows=[];negative=0
prepared=json.loads((proofdir/'media-preparation.json').read_text())['assets']
for a in assets:
 record=registry.require_ready(A,a['asset_id'],a['checksum'],media_type='image')
 row=identity.require_prepared_image(library,a['image_hash'],account_id=A,asset=a,registry_record=record,proof_dir=proofdir)
 assert row['name']==ip.image_title(a['asset_id'],a['checksum'],a['canonical_filename'])+'_105'
 p=next(x for x in prepared if x['asset_id']==a['asset_id']);raw=Path(p['vertical_file']).read_bytes()
 rows.append({'asset_id':a['asset_id'],'sha256':hashlib.sha256(raw).hexdigest(),'md5':hashlib.md5(raw).hexdigest(),'bytes':len(raw),'image_hash':a['image_hash'],'dimensions':[row['original_width'],row['original_height']],'observed_name':row['name'],'registry_source':record['source']})
 for k,v in {'account_id':'999','image_hash':'f'*32,'checksum':'f'*64,'asset_id':'other','association_verified':False}.items():
  try:identity.require_prepared_image(library,a['image_hash'],account_id=A,asset=a,registry_record={**record,k:v},proof_dir=proofdir)
  except MediaNotReady:negative+=1
  else:raise AssertionError('real binding negative accepted')
# Exact same cache-hit path as pre-stage, with a hard no-write transport.
class ReadOnlyUploader:
 def inventory(self,hashes=None):return ip.read_account_images(client,token,A,hashes=hashes)
 def upload(self,*args):raise AssertionError('upload prohibited')
def no_write(*args):raise AssertionError('registry/intent write prohibited')
reg_before=registry.path.read_bytes()
hits=ip.prestage_images(prepared,account_id=A,registry=registry,uploader=ReadOnlyUploader(),proof_dir=proofdir,atomic_json=no_write)
assert hits['registry_hits']==16 and registry.path.read_bytes()==reg_before
# Full production handoff function: Drive metadata + MD5 + exact account association, GET only.
from unittest.mock import patch
ops=handoff._ops(B);original_readback=ops.drive_file_readback;drive_checked=[]
by_drive={a['asset_drive_id']:a for a in assets}
def drive_readback(t,fid):
 result=original_readback(t,fid)
 if fid in by_drive:
  a=by_drive[fid];p=next(x for x in prepared if x['asset_id']==a['asset_id']);raw=Path(p['vertical_file']).read_bytes()
  assert result['md5Checksum']==hashlib.md5(raw).hexdigest() and int(result['size'])==len(raw)
  drive_checked.append(fid)
 return result
ops.drive_file_readback=drive_readback
with patch.object(handoff,'_ops',return_value=ops):
 loaded=handoff.load_ready_assets(s['request'],account['shein_profile'],B,client,token)
assert len(set(drive_checked))==16
assert len(loaded)==16 and {(a['asset_id'],a['checksum'],a['image_hash']) for a in loaded}=={(a['asset_id'],a['checksum'],a['image_hash']) for a in assets}
marker=central.APPROVED_RESUME.set(context);trees=[]
http,source,_=client.graph_get(s['source']['adset']['id'],token,{'fields':'id,targeting,bid_amount'})
assert http==200 and source['targeting']==s['source']['adset']['targeting'] and source['bid_amount']==90
try:
 for slot in d['reviewed_targeting']['slots']:
  tree=route._readback(client,token,slot['campaign_id']);reviewed.validate_tree(reviewed.active_context(),tree);reviewed.validate_activation_tree(tree)
  assert all(x['status']=='PAUSED' for x in [tree['campaign']]+tree['adsets']['data']+tree['ads']['data'])
  trees.append({'campaign_id':tree['campaign']['id'],'status':tree['campaign']['status'],'adset_id':tree['adsets']['data'][0]['id'],'ad_ids':[x['id'] for x in tree['ads']['data']]})
finally:central.APPROVED_RESUME.reset(marker)
history=[]
for cid in ['120250921178510629','120250921178500629']:
 h,v,_=client.graph_get(cid,token,{'fields':'id,status'});assert h==200 and v['status']=='PAUSED';history.append(v)
assert len(s.get('media_qa') or {})==8
unchanged()
result={'at':datetime.now(timezone.utc).isoformat(),'installed':installed,'profile_home':os.environ['HERMES_HOME'],'module_origin':identity.__file__,'request_id':R,'account_id':A,'descriptor_sha256':hashlib.sha256(dp.read_bytes()).hexdigest(),'binding_digest':img.BINDING_DIGEST,'authority_live':True,'descriptor_live_verified':True,'images':rows,'image_count':len(rows),'prestage_readonly_registry_hits':hits['registry_hits'],'handoff_load_ready_real':len(loaded),'campaigns':trees,'campaign_count':len(trees),'ad_count':sum(len(t['ad_ids']) for t in trees),'historical':history,'negative_count':negative,'all_paused':True,'meta_gets':client.http_requests,'meta_writes':0,'drive_writes':0,'uploads':0,'reservations':0,'state_core_manifests_registry_intents_unchanged':True,'qa_proof_fabricated':False,'postprocess_executed':False,'activation_executed':False,'serving_verified':False}
(W/('real-readonly-installed.json' if installed else 'real-readonly-stage.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:result[k] for k in ['installed','profile_home','image_count','prestage_readonly_registry_hits','handoff_load_ready_real','campaign_count','ad_count','negative_count','meta_gets','state_core_manifests_registry_intents_unchanged','serving_verified']}))

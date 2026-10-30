"""Offline manager delivery safety and same-ID CAS recovery; network forbidden."""
import contextlib,copy,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import ares_manager_delivery as m
class ManagerDeliveryTests(unittest.TestCase):
 def setUp(self):
  self.row={'asset_id':'assetOffline001','asset_drive_id':'cleanOffline001','source_drive_id':'rawOffline001','clean_checksum':'a'*64,'original_checksum':'b'*64,'source_manager':'Nicolas','requested_by_discord_id':'1055570806945620030','metadata_clean':True,'reservation_status':'RESERVADO_PELO_GESTOR','ares_eligible':False,'used_by':None,'operation':'CC_US_EN','format':'VID','canonical_filename':'CC_US_EN_VID_AVAILABLE_LIMIT_PV_001.mp4'}
  self.entry={'role':'clean','sourceId':'cleanOffline001','lineageId':'assetOffline001','sha256':'a'*64,'md5':'c'*32,'size':'10','relativeParent':['CC_US_EN','VID','01_READY'],'verified':True,'stockTransferredToArchive':True,'archiveId':'providerOffline001','stockShortcutId':'shortcutOffline001','jobId':'jobOffline001'}
  self.req={'requester_id':'1055570806945620030','thread_id':'1565540543457534103','message_id':'1565545194852454471'}
  self.auth=patch.object(m,'policy',return_value={'standing_approval':True});self.auth.start();self.addCleanup(self.auth.stop)
  self.registry=patch.object(m.b,'read_json',return_value={'agents':{'ares':{'authorized_user_discord_ids':['1055570806945620030']}}});self.registry.start();self.addCleanup(self.registry.stop)
 def test_authorized_clean_identity(self):self.assertTrue(m.validate_identity(self.row,self.entry,self.req))
 def deny(self,table,key,value):
  table[key]=value
  with self.assertRaises(m.DeliveryError):m.validate_identity(self.row,self.entry,self.req)
 def test_raw_never_moved(self):self.deny(self.entry,'role','original')
 def test_unverified_blocks(self):self.deny(self.entry,'verified',False)
 def test_stock_transfer_required(self):self.deny(self.entry,'stockTransferredToArchive',False)
 def test_changed_hash_blocks(self):self.deny(self.entry,'sha256','d'*64)
 def test_wrong_lineage_blocks(self):self.deny(self.entry,'lineageId','otherOffline001')
 def test_wrong_logical_id_blocks(self):self.deny(self.entry,'sourceId','otherOffline001')
 def test_only_ready_is_manager_dispatch_source(self):self.deny(self.entry,'relativeParent',['CC_US_EN','VID','02_TESTING'])
 def test_not_clean_blocks(self):self.deny(self.row,'metadata_clean',False)
 def test_unknown_manager_blocks(self):self.deny(self.row,'source_manager','Arbitrary folder')
 def test_eligibility_never_promoted(self):self.deny(self.row,'ares_eligible',True)
 def test_used_asset_blocks(self):self.deny(self.row,'used_by',['campaignOffline001'])
 def test_reservation_required(self):self.deny(self.row,'reservation_status','AVAILABLE')
 def test_other_requester_blocks(self):self.deny(self.req,'requester_id','344196393512075265')
 def test_malformed_origin_blocks(self):self.deny(self.req,'thread_id','malformed')
 def test_ready_plan_unchanged(self):self.assertTrue(m.verify_plan(object(),{},[],{}))
 def test_manager_plan_cannot_silently_use_READY(self):
  with self.assertRaises(m.DeliveryError):m.verify_plan(object(),{'requested_manager_final_parent':'managerOffline001','manager':'Nicolas','items':[{'id':'rawOffline001'}]},[self.row],{})
 def receipt(self):return {'schema':'mgs.manager.delivery.receipt.v1','authority_message_id':m.AUTHORITY,'status':'verified','asset_id':self.row['asset_id'],'logical_id':self.row['asset_drive_id'],'raw_source_id':self.row['source_drive_id'],'provider_id':self.entry['archiveId'],'stock_file_id':self.entry['stockShortcutId'],'sha256':self.entry['sha256'],'job_id':self.entry['jobId'],'manager':'Nicolas','request':self.req}
 def test_exact_receipt_binding(self):self.assertTrue(m.receipt_binding(self.row,self.entry,self.receipt()))
 def test_receipt_cannot_expand_folder_manager(self):
  r=self.receipt();r['manager']='Kelly'
  with self.assertRaises(m.DeliveryError):m.receipt_binding(self.row,self.entry,r)
 def test_receipt_wrong_authority_blocks(self):
  r=self.receipt();r['authority_message_id']='1565545194852454471'
  with self.assertRaises(m.DeliveryError):m.receipt_binding(self.row,self.entry,r)
 def test_changed_stock_id_blocks(self):
  r=self.receipt();r['stock_file_id']='otherOffline001'
  with self.assertRaises(m.DeliveryError):m.receipt_binding(self.row,self.entry,r)
 def test_retirement_manager_stock_requires_exact_receipt(self):
  import ares_archive_retirement as retirement
  asset={**self.entry,'name':self.row['canonical_filename'],'mimeType':'video/mp4'}
  physical={'parents':['providerReadyOffline001'],'permissions':[{'role':'writer','emailAddress':email} for email in retirement.WRITERS|{m.b.CANONICAL_SA}]}
  record={'name':asset['name'],'mimeType':'video/mp4','provider_metadata':physical,'stock_metadata':{'parents':['managerOffline001']},'capabilities':{'canDownload':True}}
  class Drive:
   def relative_parent(s,*args):return ['CC_US_EN','VID','01_READY']
   def hashes(s,*args):return {k:asset[k] for k in ['size','md5','sha256']}
  with patch.object(m.storage,'meta',return_value={}),patch.object(m.storage,'media_record',return_value=record),patch.object(m.loc,'stock_parent',return_value=['Nicolas']),patch.object(m,'verify_delivered',return_value=record) as proof:
   self.assertEqual(retirement.check_copy(Drive(),asset,self.entry),record);proof.assert_called_once()
  with patch.object(m.storage,'meta',return_value={}),patch.object(m.storage,'media_record',return_value=record),patch.object(m.loc,'stock_parent',return_value=['Nicolas']),patch.object(m,'verify_delivered',side_effect=m.DeliveryError('MISSING_RECEIPT')):
   with self.assertRaises(m.DeliveryError):retirement.check_copy(Drive(),asset,self.entry)
 def test_retirement_RAW_cannot_use_manager_receipt(self):
  import ares_archive_retirement as retirement
  asset={**self.entry,'role':'original','name':self.row['canonical_filename'],'mimeType':'video/mp4'}
  record={'name':asset['name'],'mimeType':'video/mp4','provider_metadata':{'parents':['providerOffline001']},'stock_metadata':{'parents':['managerOffline001']}}
  class Drive:
   def relative_parent(s,*args):return asset['relativeParent']
  with patch.object(m.storage,'meta',return_value={}),patch.object(m.storage,'media_record',return_value=record),patch.object(m.loc,'stock_parent',return_value=['Nicolas']),patch.object(m,'verify_delivered') as proof:
   with self.assertRaises(retirement.RetirementError):retirement.check_copy(Drive(),asset,self.entry)
   proof.assert_not_called()
 def test_same_id_move_and_verified_replay_no_second_PATCH(self):self.delivery_roundtrip(False)
 def test_lost_PATCH_response_reconciles_intent_without_replay(self):self.delivery_roundtrip(True)
 def delivery_roundtrip(self,lost_response):
  # All fixture objects are offline; this test must not instantiate real auth.
  self.registry.stop()
  with tempfile.TemporaryDirectory() as temp,contextlib.ExitStack() as stack:
   base=Path(temp);inv=base/'assets.jsonl';inv.write_text(json.dumps(self.row)+'\n');receipts=base/'receipts'
   raw={**self.entry,'role':'original','sourceId':'rawOffline001','archiveId':'rawProviderOffline001','stockShortcutId':'rawShortcutOffline001','sha256':'b'*64,'relativeParent':['CC_US_EN','VID','99_LEGACY']}
   index={'mappings':{self.entry['sourceId']:self.entry,raw['sourceId']:raw}}
   original_read=m.b.read_json
   def read(path,default=None):
    if str(path).endswith('archive-index.json'):return copy.deepcopy(index)
    if str(path).endswith('authorized-users.json'):return {'agents':{'ares':{'authorized_user_discord_ids':[self.req['requester_id']]}}}
    return original_read(path,default)
   class FakeDrive:
    parent='readyOffline001';patches=0
    def one(s,*a):return {'id':'ackOffline001'}
    def meta(s,fid):return {}
    def raw(s,fid):return json.dumps({'schema':'mgs.archive.ack.v1','status':'verified','kind':'lineage','jobId':'jobOffline001','assets':[self.entry,raw]}).encode()
    def hashes(s,fid):return {'size':'10','md5':'c'*32,'sha256':'a'*64}
    def api(s,method,path,params,payload):
     assert method=='PATCH' and path=='files/shortcutOffline001';assert params['removeParents']==s.parent;s.parent=params['addParents'];s.patches+=1
     if lost_response and s.patches==1:raise TimeoutError('offline lost PATCH response after server-side move')
     return {'id':'shortcutOffline001','parents':[s.parent]}
   drive=FakeDrive()
   def record(entry,*args):return {'parents':['legacyOffline001'] if entry['role']=='original' else [drive.parent],'name':self.row['canonical_filename'],'stock_file_id':entry['stockShortcutId']}
   def verify(d,row,entry,receipt,**kwargs):
    self.assertEqual(d.parent,'managerOffline001');self.assertEqual(receipt['stock_file_id'],'shortcutOffline001');return {'stock_file_id':'shortcutOffline001'}
   stack.enter_context(patch.object(m,'INVENTORY',inv));stack.enter_context(patch.object(m,'RECEIPTS',receipts));stack.enter_context(patch.object(m.b,'BASE',base));stack.enter_context(patch.object(m.b,'read_json',side_effect=read));stack.enter_context(patch.object(m.b,'queue_lock',return_value=contextlib.nullcontext()));stack.enter_context(patch.object(m.b,'Drive',return_value=drive));stack.enter_context(patch.object(m.b,'config_load',return_value={'requests_folder_id':'requestsOffline001'}));stack.enter_context(patch.object(m.b,'require_publisher'))
   stack.enter_context(patch.object(m,'exact_folder'));stack.enter_context(patch.object(m.storage,'meta',return_value={}));stack.enter_context(patch.object(m.storage,'media_record',side_effect=record));stack.enter_context(patch.object(m.storage,'require_registered_mapping'));stack.enter_context(patch.object(m.loc,'stock_parent',side_effect=lambda d,p:['CC_US_EN','VID','99_LEGACY' if p=='legacyOffline001' else '01_READY']));stack.enter_context(patch.object(m,'verify_receipt',side_effect=verify));stack.enter_context(patch.object(m,'verify_delivered'))
   import ares_autonomous_intake as intake
   stack.enter_context(patch.object(intake,'assert_source_writer'));stack.enter_context(patch('urllib.request.urlopen',side_effect=AssertionError('OFFLINE_NETWORK_FORBIDDEN')))
   if lost_response:
    with self.assertRaises(TimeoutError):m.deliver(self.row['asset_id'],'managerOffline001',self.req,True)
    intent=json.loads((receipts/'delivery-cleanOffline001.json').read_text());self.assertEqual(intent['status'],'intent');self.assertEqual(json.loads(inv.read_text())['asset_drive_id'],self.row['asset_drive_id'])
   first=m.deliver(self.row['asset_id'],'managerOffline001',self.req,True);second=m.deliver(self.row['asset_id'],'managerOffline001',self.req,True)
   self.assertEqual(drive.patches,1);self.assertEqual(first['stock_file_id'],second['stock_file_id']);after=json.loads(inv.read_text());self.assertEqual(after['asset_drive_id'],self.row['asset_drive_id']);self.assertFalse(after['ares_eligible']);self.assertEqual(after['reservation_status'],'RESERVADO_PELO_GESTOR')
if __name__=='__main__':unittest.main()

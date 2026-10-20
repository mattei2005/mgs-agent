"""Offline queue reconciliation boundaries; not provider execution evidence."""
import unittest, importlib.util, sys, json, copy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
def load_module(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/(name+'.py'))
    assert spec is not None and spec.loader is not None
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module)
    return module
b=load_module('ares_archive_bridge')
api=load_module('ares_archive_automation')

class FakeDrive:
    def __init__(self,c,job):
        self.c=c;self.job=job;self.calls=0;self.files={};self.texts={};self.req='requestOffline';self.rec='receiptOffline';self.ack='ackOffline'
        self.files[self.req]={'id':self.req,'parents':[c['requests_folder_id']],'driveId':b.SOURCE_DRIVE,'version':'1','lastModifyingUser':{'permissionId':'07414359829876449782'},'properties':{'mgsArchiveKey':'request:'+job['jobId'],'mgsArchiveType':'request','mgsArchiveState':'queued','sha256':api.hashlib.sha256(b.canonical(job)).hexdigest()}}
        self.texts[self.req]=b.canonical(job)
        a=job['assets'][0];self.files[a['sourceId']]={'id':a['sourceId'],'version':'12','size':a['size'],'md5Checksum':a['md5'],'parents':[a['sourceParentId']],'driveId':b.SOURCE_DRIVE,'trashed':False}
        self.files['archiveOffline']={'id':'archiveOffline','version':'1','size':a['size'],'md5Checksum':a['md5'],'parents':[c['archive_root_id']],'trashed':False,'owners':[{'emailAddress':b.ACCOUNT}],'permissions':[]}
    def add_receipt(self,status='copied'):
        self.files[self.rec]={'id':self.rec,'parents':[self.c['receipts_folder_id']],'driveId':b.SOURCE_DRIVE,'version':'1','lastModifyingUser':{'permissionId':'03783617840924670288'},'properties':{'mgsArchiveKey':'receipt:'+self.job['jobId'],'mgsArchiveType':'receipt'}}
        a=self.job['assets'][0];self.texts[self.rec]=b.canonical({'schema':'mgs.archive.receipt.v1','jobId':self.job['jobId'],'kind':'canary','status':status,'reason':'SOURCE_CHANGED','deleteSource':False,'assets':[{'sourceId':a['sourceId'],'archiveId':'archiveOffline','role':a['role']}]})
    def one(self,parent,key):
        hits=[m for m in self.files.values() if m.get('parents')==[parent] and m.get('properties',{}).get('mgsArchiveKey')==key]
        if len(hits)>1:raise b.ArchiveError('DUPLICATE_QUEUE_OBJECT')
        return copy.deepcopy(hits[0]) if hits else None
    def meta(self,fid):return copy.deepcopy(self.files[fid])
    def raw(self,fid):return self.texts[fid]
    def verify(self,d,c,jid,apply=False):
        assert d is self and apply;self.calls+=1
        self.files[self.req]['properties']['mgsArchiveState']='verified';self.files[self.req]['version']='2'
        self.files[self.ack]={'id':self.ack,'parents':[c['requests_folder_id']],'driveId':b.SOURCE_DRIVE,'version':'1','lastModifyingUser':{'permissionId':'07414359829876449782'},'properties':{'mgsArchiveKey':'ack:'+jid,'mgsArchiveType':'ack'}}
        self.texts[self.ack]=b.canonical({'schema':'mgs.archive.ack.v1','jobId':jid,'kind':'canary','status':'verified','deleteSource':False})
        return {'status':'verified','jobId':jid,'assets':[]}

class ReconcileTests(unittest.TestCase):
    def setUp(self):
        self.c={'account':b.ACCOUNT,'source_drive_id':b.SOURCE_DRIVE,'source_root_id':b.SOURCE_ROOT,'archive_root_id':b.ARCHIVE_ROOT,'delete_source':False,'effective_after':'2026-10-20T14:00:00Z','requests_folder_id':'requestsFolder123','receipts_folder_id':'receiptsFolder123'}
        a={'role':'clean','sourceId':b.PILOT,'sourceParentId':'sourceFolder123','name':'test.mp4','mimeType':'video/mp4','size':'5375929','md5':b.PILOT_MD5,'sha256':b.PILOT_SHA,'version':'12','relativeParent':[],'sourceCreatedTime':'2026-10-20T09:00:00Z'}
        self.job=b.make_request(self.c,[a],kind='canary',lineage_id='OFFLINE-ONLY');self.d=FakeDrive(self.c,self.job);self.state={}
    def run_cycle(self,apply=True):return api.reconcile_jobs(self.d,self.c,[self.job],self.state,apply,self.d.verify)
    def test_missing_receipt_is_pending_without_write(self):
        out=self.run_cycle();self.assertEqual(out['pending'],[self.job['jobId']]);self.assertEqual(self.d.calls,0)
    def test_new_copied_receipt_independently_reconciled(self):
        self.d.add_receipt();out=self.run_cycle();self.assertEqual(out['verified'],[self.job['jobId']]);self.assertEqual(self.d.calls,1)
    def test_verified_unchanged_cache_prevents_repeated_full_downloads(self):
        self.d.add_receipt();self.run_cycle();out=self.run_cycle();self.assertEqual(out['cached'],[self.job['jobId']]);self.assertEqual(self.d.calls,1)
    def test_changed_archive_invalidates_cache(self):
        self.d.add_receipt();self.run_cycle();self.d.files['archiveOffline']['version']='2';self.run_cycle();self.assertEqual(self.d.calls,2)
    def test_changed_source_invalidates_cache(self):
        self.d.add_receipt();self.run_cycle();self.d.files[b.PILOT]['version']='13';self.run_cycle();self.assertEqual(self.d.calls,2)
    def test_blocked_receipt_not_acked(self):
        self.d.add_receipt('blocked');out=self.run_cycle();self.assertEqual(len(out['blocked']),1);self.assertEqual(self.d.calls,0)
    def test_wrong_receipt_native_publisher_blocked(self):
        self.d.add_receipt();self.d.files[self.d.rec]['lastModifyingUser']['permissionId']='unknown';out=self.run_cycle();self.assertEqual(len(out['blocked']),1);self.assertEqual(self.d.calls,0)
    def test_wrong_request_native_publisher_blocked(self):
        self.d.add_receipt();self.d.files[self.d.req]['lastModifyingUser']['permissionId']='unknown';out=self.run_cycle();self.assertEqual(len(out['blocked']),1);self.assertEqual(self.d.calls,0)
    def test_edited_request_body_blocked(self):
        self.d.add_receipt();self.d.texts[self.d.req]=b'edited';out=self.run_cycle();self.assertEqual(len(out['blocked']),1);self.assertEqual(self.d.calls,0)
    def test_dry_run_does_not_verify_write_or_cache(self):
        self.d.add_receipt();out=self.run_cycle(False);self.assertEqual(out['planned'],[self.job['jobId']]);self.assertEqual(self.d.calls,0);self.assertEqual(self.state,{})
    def test_wrong_ack_publisher_does_not_count_as_cache_hit(self):
        self.d.add_receipt();self.run_cycle();self.d.files[self.d.ack]['lastModifyingUser']['permissionId']='unknown';out=self.run_cycle();self.assertEqual(len(out['blocked']),1);self.assertEqual(self.d.calls,1)
    def test_unknown_verifier_result_never_cached(self):
        self.d.add_receipt();out=api.reconcile_jobs(self.d,self.c,[self.job],self.state,True,lambda *a,**k:{'status':'pending'});self.assertEqual(len(out['blocked']),1);self.assertEqual(self.state.get('verified',{}),{})
    def test_failure_of_one_job_does_not_hide_another(self):
        self.d.add_receipt();bad={**self.job,'jobId':'0'*32};out=api.reconcile_jobs(self.d,self.c,[bad,self.job],self.state,True,self.d.verify);self.assertEqual(len(out['blocked']),1);self.assertEqual(out['verified'],[self.job['jobId']])

if __name__=='__main__':unittest.main()

"""Offline automation tests; fixtures are NOT real Google receipts."""
import unittest, importlib.util, sys, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
bridge_spec=importlib.util.spec_from_file_location('ares_archive_bridge',ROOT/'scripts/ares_archive_bridge.py')
assert bridge_spec is not None and bridge_spec.loader is not None
bridge=importlib.util.module_from_spec(bridge_spec);bridge_spec.loader.exec_module(bridge)

class AutomationTests(unittest.TestCase):
    def setUp(self):
        spec=importlib.util.spec_from_file_location('ares_archive_automation',ROOT/'scripts/ares_archive_automation.py')
        assert spec is not None and spec.loader is not None
        self.api=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.api)
        self.c={'account':bridge.ACCOUNT,'source_drive_id':bridge.SOURCE_DRIVE,'source_root_id':bridge.SOURCE_ROOT,'archive_root_id':bridge.ARCHIVE_ROOT,'effective_after':'2026-10-20T14:23:41+00:00','delete_source':False,'queue_enabled':False,'requests_folder_id':'requestsFolder123','receipts_folder_id':'receiptsFolder123'}
        self.row={'asset_id':'asset_offline','first_seen_at':'2026-10-20T15:00:00+00:00','metadata_clean':True,'source_drive_id':'sourceOffline123','asset_drive_id':'cleanOffline123','original_checksum':'a'*64,'clean_checksum':'b'*64,'reservation_status':'RESERVADO_PELO_GESTOR','ares_eligible':False}
    def test_post_cutoff_clean_pair_selected_without_changing_reservation(self):
        before=json.dumps(self.row,sort_keys=True);selected,excluded=self.api.select_inventory([self.row],self.c)
        self.assertEqual([r['asset_id'] for r in selected],['asset_offline']);self.assertEqual(json.dumps(self.row,sort_keys=True),before)
    def test_historical_excluded(self):
        self.row['first_seen_at']='2026-10-20T09:00:00Z';self.assertEqual(self.api.select_inventory([self.row],self.c)[0],[])
    def test_missing_timestamp_not_invented(self):
        del self.row['first_seen_at'];self.assertEqual(self.api.select_inventory([self.row],self.c)[0],[])
    def test_naive_timestamp_excluded(self):
        self.row['first_seen_at']='2026-10-20T15:00:00';self.assertEqual(self.api.select_inventory([self.row],self.c)[0],[])
    def test_nonclean_excluded(self):
        self.row['metadata_clean']=False;self.assertEqual(self.api.select_inventory([self.row],self.c)[0],[])
    def test_trashed_excluded(self):
        self.row['source_drive_trashed']=True;self.assertEqual(self.api.select_inventory([self.row],self.c)[0],[])
    def test_superseded_excluded(self):
        self.row['superseded_by_asset_id']='new_lineage';self.assertEqual(self.api.select_inventory([self.row],self.c)[0],[])
    def test_missing_hash_excluded(self):
        del self.row['original_checksum'];self.assertEqual(self.api.select_inventory([self.row],self.c)[0],[])
    def test_same_raw_clean_id_excluded(self):
        self.row['asset_drive_id']=self.row['source_drive_id'];self.assertEqual(self.api.select_inventory([self.row],self.c)[0],[])
    def test_duplicate_lineage_id_fails_closed(self):
        with self.assertRaises(bridge.ArchiveError):self.api.select_inventory([self.row,dict(self.row)],self.c)
    def test_reservation_changes_do_not_create_second_archive_identity(self):
        first=self.api.lineage_fingerprint(self.row);self.row.update(status='TESTING',ares_eligible=True,reservation_status='LIBERADO')
        self.assertEqual(first,self.api.lineage_fingerprint(self.row))
    def test_changed_content_changes_lineage_fingerprint(self):
        first=self.api.lineage_fingerprint(self.row);self.row['clean_checksum']='c'*64;self.assertNotEqual(first,self.api.lineage_fingerprint(self.row))
    def test_disabled_queue_never_enqueues(self):
        calls=[];out=self.api.enqueue_ready([self.row],self.c,{},True,lambda row:calls.append(row))
        self.assertEqual(calls,[]);self.assertEqual(out['queued'],[])
    def test_dry_run_never_enqueues_or_mutates_state(self):
        self.c['queue_enabled']=True;state={};calls=[];out=self.api.enqueue_ready([self.row],self.c,state,False,lambda row:calls.append(row))
        self.assertEqual(calls,[]);self.assertEqual(state,{});self.assertEqual(out['planned'],['asset_offline'])
    def test_enqueued_lineage_not_enqueued_twice(self):
        self.c['queue_enabled']=True;state={};calls=[]
        def publish(row):calls.append(row);return {'jobId':'a'*32,'requestFileId':'offlineRequest123'}
        self.api.enqueue_ready([self.row],self.c,state,True,publish);self.api.enqueue_ready([self.row],self.c,state,True,publish);self.assertEqual(len(calls),1)
    def test_changed_enqueued_content_is_blocked_not_replaced(self):
        self.c['queue_enabled']=True;state={};publish=lambda row:{'jobId':'a'*32,'requestFileId':'offlineRequest123'}
        self.api.enqueue_ready([self.row],self.c,state,True,publish);self.row['clean_checksum']='c'*64
        out=self.api.enqueue_ready([self.row],self.c,state,True,lambda row:self.fail('must not publish changed lineage'));self.assertEqual(out['blocked'][0]['reason'],'ENQUEUED_LINEAGE_CHANGED')
    def test_job_limit_defers_remaining_not_drops(self):
        self.c['queue_enabled']=True;other={**self.row,'asset_id':'asset_second'};state={};calls=[]
        out=self.api.enqueue_ready([self.row,other],self.c,state,True,lambda row:(calls.append(row) or {'jobId':'a'*32,'requestFileId':'offlineRequest123'}),limit=1)
        self.assertEqual(len(calls),1);self.assertEqual(out['deferred'],1)

if __name__=='__main__':unittest.main()

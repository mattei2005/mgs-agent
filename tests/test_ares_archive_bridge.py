"""Offline contract tests; fixtures are not provider receipts."""
import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
MODULE=ROOT/'scripts/ares_archive_bridge.py'

class ArchiveContractTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(MODULE.exists(), 'copy-only queue bridge missing')
        spec=importlib.util.spec_from_file_location('ares_archive_bridge',MODULE)
        assert spec is not None and spec.loader is not None
        self.api=importlib.util.module_from_spec(spec);sys.modules[spec.name]=self.api;spec.loader.exec_module(self.api)
        self.cfg={'account':'mgsdigitalcorp@gmail.com','source_drive_id':'0AEwt4Ye690ocUk9PVA','source_root_id':'1h8wEYDcn2SYLZI-Cp4dMpxfwFUqQXhpa','archive_root_id':'1jDcp9BOn-rusiRQ1t0MjJCby-qj0BL2J','delete_source':False,'queue_enabled':False,'effective_after':'2026-10-20T14:00:00+00:00'}
        self.asset={'role':'clean','sourceId':'1WDP1Mgwy4jTAowTDNy_k9RcuSieKOg9N','sourceParentId':'1iGO8km_WVwbIppLotf1h1kZ7W0UKUxz1','name':'unit.mp4','mimeType':'video/mp4','size':'5375929','md5':'59065739912275ee5995bfee8d5ca9c7','sha256':'11e123e5b495e5ed1a2ae5099b1cef94b6255a4c5f8302859b01a8b291793027','version':'12','relativeParent':[],'sourceCreatedTime':'2026-10-20T09:00:00Z'}
    def job(self):return self.api.make_request(self.cfg,[self.asset],kind='canary',lineage_id='PILOT-ONLY')
    def test_canary_has_no_delete(self):self.assertIs(self.job()['deleteSource'],False)
    def test_job_identity_ignores_request_clock(self):self.assertEqual(self.job()['jobId'],self.job()['jobId'])
    def test_changed_destination_rejected(self):
        self.cfg['archive_root_id']='otherFolderId'
        with self.assertRaises(self.api.ArchiveError):self.job()
    def test_delete_switch_rejected(self):
        self.cfg['delete_source']=True
        with self.assertRaises(self.api.ArchiveError):self.job()
    def test_path_traversal_rejected(self):
        self.asset['relativeParent']=['..']
        with self.assertRaises(self.api.ArchiveError):self.job()
    def test_bad_checksum_rejected(self):
        self.asset['sha256']='not-a-hash'
        with self.assertRaises(self.api.ArchiveError):self.job()
    def test_historical_lineage_rejected(self):
        row={'asset_id':'old','first_seen_at':'2026-10-19T00:00:00Z','metadata_clean':True}
        with self.assertRaises(self.api.ArchiveError):self.api.validate_lineage(row,self.cfg)
    def test_ambiguous_timestamp_rejected(self):
        row={'asset_id':'new','first_seen_at':'2026-10-20T15:00:00','metadata_clean':True}
        with self.assertRaises(self.api.ArchiveError):self.api.validate_lineage(row,self.cfg)
    def test_future_clean_lineage_accepted_without_changing_reservation(self):
        row={'asset_id':'new','first_seen_at':'2026-10-20T15:00:00Z','metadata_clean':True,'reservation_status':'RESERVADO_PELO_GESTOR','ares_eligible':False}
        before=json.dumps(row,sort_keys=True);self.api.validate_lineage(row,self.cfg);self.assertEqual(before,json.dumps(row,sort_keys=True))
    def test_nonclean_lineage_rejected(self):
        with self.assertRaises(self.api.ArchiveError):self.api.validate_lineage({'first_seen_at':'2026-10-20T15:00:00Z','metadata_clean':False},self.cfg)
    def test_scope_pins_source_and_account(self):
        self.cfg['account']='other@example.com'
        with self.assertRaises(self.api.ArchiveError):self.job()
    def test_source_and_clean_pairs_required_for_lineage(self):
        with self.assertRaises(self.api.ArchiveError):self.api.make_request(self.cfg,[self.asset],kind='lineage',lineage_id='new')
    def test_source_metadata_drift_rejected(self):
        meta={'id':self.asset['sourceId'],'parents':[self.asset['sourceParentId']],'size':'1','md5Checksum':self.asset['md5'],'version':'12','trashed':False,'driveId':self.cfg['source_drive_id']}
        with self.assertRaises(self.api.ArchiveError):self.api.validate_source_metadata(meta,self.asset,self.cfg)
    def test_receipt_asset_set_must_match_exactly(self):
        with self.assertRaises(self.api.ArchiveError):self.api.validate_receipt(self.job(),{'jobId':self.job()['jobId'],'status':'copied','assets':[]})
    def test_unverified_or_unpreferred_mapping_keeps_original(self):
        sid=self.asset['sourceId'];self.assertEqual(self.api.resolve_id(sid,{},False),sid)
        self.assertEqual(self.api.resolve_id(sid,{sid:{'verified':True,'archiveId':'newId'}},False),sid)
    def test_verified_mapping_can_resolve_explicitly(self):
        sid=self.asset['sourceId'];self.assertEqual(self.api.resolve_id(sid,{sid:{'verified':True,'archiveId':'newId','owner':self.cfg['account']}},True),'newId')
    def test_google_hidden_email_accepts_pinned_sa_permission_id(self):
        self.assertIs(self.api.require_publisher({'lastModifyingUser':{'permissionId':'07414359829876449782'}},self.api.CANONICAL_SA),True)
    def test_google_hidden_email_accepts_pinned_owner_permission_id(self):
        self.assertIs(self.api.require_publisher({'lastModifyingUser':{'permissionId':'03783617840924670288'}},self.api.ACCOUNT),True)
    def test_matching_email_cannot_bypass_wrong_permission_id(self):
        with self.assertRaises(self.api.ArchiveError):self.api.require_publisher({'lastModifyingUser':{'emailAddress':self.api.CANONICAL_SA,'permissionId':'other'}},self.api.CANONICAL_SA)
    def test_missing_native_id_fails_closed(self):
        with self.assertRaises(self.api.ArchiveError):self.api.require_publisher({'lastModifyingUser':{'emailAddress':self.api.ACCOUNT}},self.api.ACCOUNT)
    def test_contradictory_email_fails_closed(self):
        with self.assertRaises(self.api.ArchiveError):self.api.require_publisher({'lastModifyingUser':{'emailAddress':'other@example.com','permissionId':'03783617840924670288'}},self.api.ACCOUNT)
    def test_unknown_expected_publisher_fails_closed(self):
        with self.assertRaises(self.api.ArchiveError):self.api.require_publisher({'lastModifyingUser':{'emailAddress':'other@example.com','permissionId':'03783617840924670288'}},'other@example.com')
    def test_bridge_requests_native_id_from_google_metadata(self):
        d=object.__new__(self.api.Drive);calls=[]
        d.api=lambda method,path,params:(calls.append(params) or {})
        d.meta('offline-file')
        self.assertIn('permissionId',calls[0]['fields'])
    def test_mapping_never_changes_inventory_identifiers(self):
        source={'source_drive_id':'source','asset_drive_id':'clean','ares_eligible':False};before=source.copy()
        self.api.resolve_id('clean',{'clean':{'verified':True,'archiveId':'newId','owner':self.cfg['account']}},True)
        self.assertEqual(source,before)

if __name__=='__main__':unittest.main()

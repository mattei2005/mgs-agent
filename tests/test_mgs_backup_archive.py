"""Offline backup-archive validation tests; not proof of Google transfer."""
import copy
import importlib
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))

class BackupArchiveTests(unittest.TestCase):
    def setUp(self):
        self.a=importlib.import_module('mgs_backup_archive')
        self.root='corporateRoot123'
        self.folders=[{'id':'archiveRoot123','name':'_DISASTER_RECOVERY','mimeType':self.a.b.FOLDER,'parents':[self.root],'trashed':False,'owners':[{'emailAddress':self.a.b.ACCOUNT}]}]+[{'id':'tierFolder'+n,'name':n,'mimeType':self.a.b.FOLDER,'parents':['archiveRoot123'],'trashed':False,'owners':[{'emailAddress':self.a.b.ACCOUNT}]} for n in self.a.TIERS]
        self.contract={'file_id':'backupFile123','name':'mgs-dr-weekly-20261018T081508Z.zip.gpg','mime_type':'application/pgp-encrypted','source_parent_id':'sourceWeekly123','destination_parent_id':'tierFolderweekly','size':'1234','md5':'a'*32,'sha256':'b'*64,'created_time':'2026-10-18T08:27:35.200Z','source_version':'1','tier':'weekly','mode':'full','expected_owner':self.a.b.ACCOUNT}
        self.meta={'id':self.contract['file_id'],'name':self.contract['name'],'mimeType':self.contract['mime_type'],'parents':['sourceWeekly123'],'driveId':self.a.b.SOURCE_DRIVE,'trashed':False,'size':'1234','md5Checksum':'a'*32,'sha256Checksum':'b'*64,'createdTime':self.contract['created_time'],'version':'1','appProperties':{'mgs_dr':'true','tier':'weekly','mode':'full','sha256':'b'*64},'capabilities':{'canDownload':True}}
    def test_layout_accepts_exact_owner_parents_and_five_folders(self):
        self.assertEqual(set(self.a.validate_layout(self.folders,self.root)),set(self.a.TIERS)|{'root'})
    def test_duplicate_tier_is_rejected(self):
        self.folders[-1]['name']=self.folders[-2]['name']
        with self.assertRaises(self.a.b.ArchiveError):self.a.validate_layout(self.folders,self.root)
    def test_wrong_owner_is_rejected(self):
        self.folders[-1]['owners']=[{'emailAddress':'other@example.invalid'}]
        with self.assertRaises(self.a.b.ArchiveError):self.a.validate_layout(self.folders,self.root)
    def test_wrong_folder_parent_is_rejected(self):
        self.folders[-1]['parents']=['otherParent123']
        with self.assertRaises(self.a.b.ArchiveError):self.a.validate_layout(self.folders,self.root)
    def test_extra_folder_is_rejected(self):
        self.folders.append(copy.deepcopy(self.folders[-1]))
        with self.assertRaises(self.a.b.ArchiveError):self.a.validate_layout(self.folders,self.root)
    def test_source_native_backup_is_accepted(self):
        self.a.validate_pilot_metadata(self.meta,self.contract,moved=False)
    def test_move_accepts_same_id_and_gmail_owner(self):
        self.meta.pop('driveId');self.meta.update(parents=['tierFolderweekly'],owners=[{'emailAddress':self.a.b.ACCOUNT}],version='2')
        self.a.validate_pilot_metadata(self.meta,self.contract,moved=True)
    def test_wrong_checksum_is_rejected(self):
        self.meta['sha256Checksum']='c'*64
        with self.assertRaises(self.a.b.ArchiveError):self.a.validate_pilot_metadata(self.meta,self.contract,moved=False)
    def test_missing_private_dr_marker_is_rejected(self):
        self.meta['appProperties'].pop('mgs_dr')
        with self.assertRaises(self.a.b.ArchiveError):self.a.validate_pilot_metadata(self.meta,self.contract,moved=False)
    def test_missing_native_sha_is_not_silently_replaced_by_editable_property(self):
        self.meta.pop('sha256Checksum')
        with self.assertRaises(self.a.b.ArchiveError):self.a.validate_pilot_metadata(self.meta,self.contract,moved=False)
    def test_changed_source_version_blocks_release(self):
        self.meta['version']='2'
        with self.assertRaises(self.a.b.ArchiveError):self.a.validate_pilot_metadata(self.meta,self.contract,moved=False)
    def test_wrong_move_owner_is_rejected(self):
        self.meta.pop('driveId');self.meta.update(parents=['tierFolderweekly'],owners=[{'emailAddress':'other@example.invalid'}],version='2')
        with self.assertRaises(self.a.b.ArchiveError):self.a.validate_pilot_metadata(self.meta,self.contract,moved=True)
    def test_unexpected_move_parent_is_rejected(self):
        self.meta.pop('driveId');self.meta.update(parents=['otherParent123'],owners=[{'emailAddress':self.a.b.ACCOUNT}],version='2')
        with self.assertRaises(self.a.b.ArchiveError):self.a.validate_pilot_metadata(self.meta,self.contract,moved=True)
    def test_folder_key_is_deterministic_and_parent_bound(self):
        x=self.a.folder_key('d'*64,'parent123','weekly')
        self.assertEqual(x,self.a.folder_key('d'*64,'parent123','weekly'));self.assertNotEqual(x,self.a.folder_key('d'*64,'parent456','weekly'))
    def retired_staging(self,*,proof_ok=True,nonempty=False,wrong_owner=False):
        from unittest.mock import patch,Mock
        loc=importlib.import_module('ares_archive_locations')
        a=self.a;binding={'source_root_id':'legacyRoot123','corporate_root_id':self.root,'archive_root_id':'archiveRoot123','tiers':{t:{'source_id':'source'+t,'archive_id':'tierFolder'+t} for t in a.TIERS}}
        pilot={**self.contract,'schema':'mgs.corporate.backup.native.move.pilot.v1'}
        moved={**self.meta,'parents':['tierFolderweekly'],'owners':[{'emailAddress':a.b.ACCOUNT}],'version':'2'};moved.pop('driveId')
        legacy={'id':'legacyRoot123','name':'_DR_LEGADO','mimeType':a.b.FOLDER,'parents':[self.root],'trashed':False,'owners':[{'emailAddress':'other' if wrong_owner else a.b.ACCOUNT}]}
        meta={x['id']:x for x in self.folders};meta[moved['id']]=moved;meta[legacy['id']]=legacy
        for t in a.TIERS:meta['source'+t]={'id':'source'+t,'name':t,'parents':['legacyRoot123'],'trashed':False,'owners':[{'emailAddress':a.b.ACCOUNT}]}
        proof={'backup_staging_same_ids_retired_privately':proof_ok,'backup_staging_retired_parent_id':self.root,'backup_staging_retired_name':'_DR_LEGADO'}
        def read(path,default=None):return pilot if path==a.PILOT else proof if str(path)=='proof' else {}
        with patch.object(a,'load_binding',return_value=binding),patch.object(a.b,'read_json',side_effect=read),patch.object(a.b,'atomic_json'),patch.object(a,'native_meta',side_effect=lambda d,fid:meta[fid]),patch.object(a.corporate,'load_plan',return_value=({},{})),patch.object(a.corporate,'check_acl'),patch.object(a.corporate,'desired',return_value={}),patch.object(a.corporate.h,'permissions',return_value=[]),patch.object(a,'children',return_value=[{'id':'unexpected'}] if nonempty else []),patch.object(loc,'active',return_value={'acceptance_proof':'proof'}):return a.verify_pilot(Mock())
    def test_retired_staging_same_ids_in_private_corporate_archive(self):
        result=self.retired_staging();self.assertTrue(result['source_staging_same_ids_retired_privately']);self.assertFalse(result['source_staging_unchanged'])
    def test_retired_staging_needs_accepted_proof(self):
        with self.assertRaises(self.a.b.ArchiveError):self.retired_staging(proof_ok=False)
    def test_retired_staging_cannot_hide_unmigrated_backup(self):
        with self.assertRaises(self.a.b.ArchiveError):self.retired_staging(nonempty=True)
    def test_retired_staging_owner_must_remain_pinned(self):
        with self.assertRaises(self.a.b.ArchiveError):self.retired_staging(wrong_owner=True)
if __name__=='__main__':unittest.main()

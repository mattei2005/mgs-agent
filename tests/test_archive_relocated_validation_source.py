"""Offline checks: migrated test controls are not a general media bypass."""
import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import ares_archive_bridge as b

class RelocatedValidationSource(unittest.TestCase):
    def setUp(self):
        self.asset = dict(sourceId='SOURCE', sourceParentId='OLD', name='test.png',
                          mimeType='image/png', size='10', md5='a'*32, sha256='b'*64,
                          sourceCreatedTime='CREATED', version='1')
        self.c = dict(source_drive_id=b.SOURCE_DRIVE, control_folder_id='ROOT',
                      archive_root_id=b.ARCHIVE_ROOT)
        self.job = dict(validationOnly=True, kind='lineage')
        self.meta = dict(id='SOURCE', parents=['NEW'], name='test.png', mimeType='image/png',
                         size='10', md5Checksum='a'*32, sha256Checksum='b'*64,
                         createdTime='CREATED', version='3', trashed=False,
                         owners=[dict(emailAddress=b.ACCOUNT)], permissions=[],
                         properties=dict(mgsArchiveType='archive_test_media', sha256='b'*64),
                         lastModifyingUser=dict(permissionId=b.PUBLISHER_PERMISSION_IDS[b.CANONICAL_SA]))
        self.binding = dict(schema='mgs.private.control.binding.v1', production_enabled=True,
                            migration_pending=False, approval_message_id='1562972150455992431',
                            root_id='ROOT', parent_ids=['NEW'], folder_map={'OLD':'NEW'},
                            cutover_verified_at='TIME')
        self.row = dict(id='SOURCE', old_parent='OLD', new_parent='NEW', name='test.png',
                        mime='image/png', size='10', sha256='b'*64, verification_kind='full_bytes',
                        publisher_permission_id=b.PUBLISHER_PERMISSION_IDS[b.CANONICAL_SA],
                        properties=copy.deepcopy(self.meta['properties']))
        self.snapshot = dict(schema='mgs.private.control.cutover.snapshot.v1',
                             approval_message_id='1562972150455992431', new_control_root='ROOT',
                             files=[self.row])
        self.verified = dict(schema='mgs.private.control.cutover.files.v1', files=[
            dict(id='SOURCE', new_parent='NEW', sha256='b'*64, verified=True, publisher_preserved=True)])
        self.root = dict(id='ROOT', parents=[b.ARCHIVE_ROOT], mimeType=b.FOLDER,
                         trashed=False, owners=[dict(emailAddress=b.ACCOUNT)], permissions=[])
        obj=self
        class D:
            def meta(self, fid):
                if fid != 'ROOT': raise AssertionError(fid)
                return obj.root
            def relative_parent(self, parent, root):
                if (parent,root) != ('NEW','ROOT'): raise AssertionError((parent,root))
                return ['TEST_INPUTS']
        self.d=D()
    def validate(self):
        def read(path, default=None):
            return {'binding.json':self.binding, 'source-snapshot.json':self.snapshot,
                    'verified-files.json':self.verified}[Path(path).name]
        with patch.object(b,'read_json',side_effect=read):
            return b.validate_reconciliation_source(self.d,self.meta,self.asset,self.c,self.job)
    def test_verified_test_control_accepted(self): self.assertTrue(self.validate())
    def test_live_media_not_relaxed(self):
        self.job['validationOnly']=False
        with self.assertRaises(b.ArchiveError):self.validate()
    def test_missing_or_duplicate_manifest_membership(self):
        for rows in [[],[self.row,self.row]]:
            self.snapshot['files']=rows
            with self.subTest(rows=len(rows)),self.assertRaises(b.ArchiveError):self.validate()
    def test_rejects_each_drift(self):
        for key,value in [('id','OTHER'),('name','renamed'),('parents',['OTHER']),
                          ('size','11'),('md5Checksum','c'*32),('sha256Checksum','c'*64),
                          ('mimeType','image/jpeg'),('createdTime','OTHER'),('trashed',True),
                          ('version','0'),('owners',[dict(emailAddress='other')]),
                          ('permissions',[dict(type='anyone')]),('properties',{})]:
            old=copy.deepcopy(self.meta);self.meta[key]=value
            with self.subTest(key=key),self.assertRaises(b.ArchiveError):self.validate()
            self.meta=old
    def test_unaccepted_or_disabled_binding_rejected(self):
        for key,value in [('production_enabled',False),('migration_pending',True),
                          ('approval_message_id','OTHER'),('root_id','OTHER'),
                          ('cutover_verified_at',None),('folder_map',{})]:
            old=copy.deepcopy(self.binding);self.binding[key]=value
            with self.subTest(key=key),self.assertRaises(b.ArchiveError):self.validate()
            self.binding=old
    def test_verification_receipt_required(self):
        for key,value in [('verified',False),('publisher_preserved',False),('sha256','c'*64)]:
            old=copy.deepcopy(self.verified);self.verified['files'][0][key]=value
            with self.subTest(key=key),self.assertRaises(b.ArchiveError):self.validate()
            self.verified=old
    def test_native_publisher_required(self):
        self.meta['lastModifyingUser']={'permissionId':'OTHER'}
        with self.assertRaises(b.ArchiveError):self.validate()
    def test_root_scope_required(self):
        self.root['parents']=['FOREIGN']
        with self.assertRaises(b.ArchiveError):self.validate()
    def test_shared_drive_default_unchanged(self):
        self.meta.update(parents=['OLD'],driveId=b.SOURCE_DRIVE)
        self.job['validationOnly']=False
        self.assertTrue(self.validate())

    def test_unknown_control_media_type_rejected(self):
        self.meta['properties']['mgsArchiveType']='production_media'
        self.row['properties']=copy.deepcopy(self.meta['properties'])
        with self.assertRaises(b.ArchiveError):self.validate()

class RelocatedIntakeValidationSource(RelocatedValidationSource):
    def setUp(self):
        super().setUp()
        self.meta['properties']['mgsArchiveType']='intake_test_media'
        self.row['properties']=copy.deepcopy(self.meta['properties'])

if __name__=='__main__':unittest.main()

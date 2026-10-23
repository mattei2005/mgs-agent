"""Explicit stock/staging location contract for the whole-Drive cutover.

Inactive until an independently verified same-ID stock move is accepted. This
module never authenticates, copies, moves, changes permissions or deletes.
"""
from __future__ import annotations
import re
from pathlib import Path
import ares_archive_bridge as b
BINDING=b.DATA/'owner-connector'/'stock-layout-binding.json'
APPROVAL='1562972150455992431'
UPLOAD='1ARBvLammWUHuAclNmcriwkkgeedKryBd'

def validate(value):
    if not isinstance(value,dict) or value.get('schema')!='mgs.archive.stock.layout.v1' or value.get('approval_message_id')!=APPROVAL:
        raise b.ArchiveError('STOCK_LAYOUT_AUTHORITY')
    expected={'source_drive_id':b.SOURCE_DRIVE,'staging_root_id':b.SOURCE_ROOT,'archive_root_id':b.ARCHIVE_ROOT,'upload_root_id':UPLOAD,'owner':b.ACCOUNT}
    if any(value.get(k)!=v for k,v in expected.items()):raise b.ArchiveError('STOCK_LAYOUT_PIN')
    stock=value.get('stock_root_id')
    if not isinstance(stock,str) or not re.fullmatch('[A-Za-z0-9_-]{8,}',stock) or stock in set(expected.values()):raise b.ArchiveError('STOCK_LAYOUT_ROOT')
    if type(value.get('active')) is not bool:raise b.ArchiveError('STOCK_LAYOUT_ACTIVE_TYPE')
    if value['active'] and (value.get('same_ids_verified') is not True or value.get('consumer_canary_verified') is not True or not value.get('acceptance_proof')):
        raise b.ArchiveError('STOCK_LAYOUT_ACCEPTANCE_REQUIRED')
    return value

def binding():
    value=b.read_json(BINDING)
    return validate(value) if value is not None else None

def active():
    value=binding()
    if value and value.get('phase')=='transition':raise b.ArchiveError('STOCK_LAYOUT_TRANSITION')
    return value if value and value['active'] else None

def token_drive(token):
    from mgs_google_workspace_auth import api_json
    d=b.Drive.__new__(b.Drive);d.token=token;d.api_json=api_json;d.base='https://www.googleapis.com/drive/v3/'
    return d

def creatives_for_token(token):
    return verify_stock_root(token_drive(token))

def assert_stock_file(d,fid,expected_parent=None):
    meta=d.meta(fid)
    if not stock_metadata_allowed(meta) or len(meta.get('parents',[]))!=1 or (expected_parent is not None and meta['parents']!=[expected_parent]):raise b.ArchiveError('STOCK_FILE_SCOPE')
    stock_parent(d,meta['parents'][0])
    return meta

def stock_root():
    value=active()
    return value['stock_root_id'] if value else b.SOURCE_ROOT

def upload_parent():
    return b.SOURCE_DRIVE if active() else b.SOURCE_ROOT

def stock_metadata_allowed(meta):
    """Metadata half of the gate; callers must also prove exact stock ancestry."""
    if meta.get('trashed') is not False:return False
    value=active()
    if not value:return meta.get('driveId')==b.SOURCE_DRIVE
    return not meta.get('driveId') and any(x.get('emailAddress')==b.ACCOUNT for x in meta.get('owners',[])) and not any(x.get('type') in ['anyone','domain'] for x in meta.get('permissions',[]))

def verify_stock_root(d):
    value=active();fid=stock_root();meta=d.meta(fid)
    if not value:
        if meta.get('driveId')!=b.SOURCE_DRIVE or meta.get('trashed') is not False:raise b.ArchiveError('STOCK_ROOT_SHARED_SCOPE')
    elif not stock_metadata_allowed(meta) or meta.get('parents')!=[b.ARCHIVE_ROOT] or meta.get('mimeType')!=b.FOLDER or meta.get('name')!='CRIATIVOS':
        raise b.ArchiveError('STOCK_ROOT_ARCHIVE_SCOPE')
    return meta

def stock_parent(d,parent):
    if active():verify_stock_root(d)
    return d.relative_parent(parent,stock_root())

def staging_relative_parent(d,parent):
    return d.relative_parent(parent,b.SOURCE_ROOT)

def verify_staging_root(d):
    meta=d.meta(b.SOURCE_ROOT);value=active()
    expected_parent=UPLOAD if value else b.SOURCE_DRIVE
    if meta.get('driveId')!=b.SOURCE_DRIVE or meta.get('parents')!=[expected_parent] or meta.get('trashed') is not False or meta.get('mimeType')!=b.FOLDER:
        raise b.ArchiveError('STAGING_ROOT_SCOPE')
    return meta

def stock_folder_for_path(d,names):
    """Lookup only; no quota fallback or implicit folder creation in My Drive."""
    parent=stock_root();verify_stock_root(d)
    for name in names:
        if not isinstance(name,str) or name in ['', '.', '..'] or '/' in name or '\\' in name:raise b.ArchiveError('STOCK_PATH_COMPONENT')
        rows=[x for x in d.listing(parent) if x.get('name')==name and x.get('mimeType')==b.FOLDER]
        if len(rows)!=1:raise b.ArchiveError('STOCK_PATH_NOT_UNIQUE')
        meta=d.meta(rows[0]['id'])
        if meta.get('parents')!=[parent] or not stock_metadata_allowed(meta):raise b.ArchiveError('STOCK_PATH_NATIVE_SCOPE')
        parent=meta['id']
    return parent

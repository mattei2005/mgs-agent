#!/usr/bin/env python3
"""Explicit approved physical namespace and legacy metadata reconciliation.

Frozen requests/ACKs remain unchanged. Only exact native IDs and unchanged
checksums receive a separately approved location/display reconciliation.
"""
from __future__ import annotations
import hashlib,json
import ares_archive_bridge as b
SCHEMA='mgs.archive.physical.namespace.v1'
AUTHORITY='1566510979838255326'
PATH=b.DATA/'legacy-consolidation'/'binding.json'
PARENTS=PATH.parent/'provider-parent-bindings.json'
_CACHE={}
class NamespaceError(b.ArchiveError):pass

def require(value,reason):
 if not value:raise NamespaceError(reason)
def validate_binding(value):
 require(value.get('schema')==SCHEMA and value.get('authority_message_id')==AUTHORITY and value.get('phase') in ['prepared','active'],'NAMESPACE_AUTHORITY')
 require(value.get('archive_root_id')==b.ARCHIVE_ROOT and value.get('provider_root_id') not in [None,b.ARCHIVE_ROOT,value.get('stock_root_id')],'NAMESPACE_ROOT_BINDING')
 require(isinstance(value.get('files'),dict) and isinstance(value.get('stock_moves'),dict) and isinstance(value.get('legacy_manager_folders'),dict),'NAMESPACE_SCHEMA');return value
def binding():
 if not PATH.exists():return None
 plan_path=PATH.parent/'plan.json'
 signature=(PATH.stat().st_ino,PATH.stat().st_mtime_ns,PATH.stat().st_size,plan_path.stat().st_mtime_ns if plan_path.exists() else None,PARENTS.stat().st_mtime_ns if PARENTS.exists() else None)
 if _CACHE.get('signature')==signature:return _CACHE['value']
 value=b.read_json(PATH,{})
 if value.get('phase')!='active':return None
 validate_binding(value);plan=b.read_json(plan_path,{})
 require(plan.get('authority_message_id')==AUTHORITY and value.get('plan_sha256')==hashlib.sha256(b.canonical(plan)).hexdigest(),'NAMESPACE_PLAN_DIGEST')
 expected={**plan.get('namespace',{}),'phase':'active','plan_sha256':value['plan_sha256']};parents={}
 if value.get('provider_parent_bindings_sha256'):
  native=b.read_json(PARENTS,{})
  require(hashlib.sha256(b.canonical(native)).hexdigest()==value['provider_parent_bindings_sha256'] and native.get('schema')=='mgs.archive.provider.parents.v1' and native.get('authority_message_id')==AUTHORITY and native.get('plan_sha256')==value['plan_sha256'],'NAMESPACE_NATIVE_PARENT_BINDING')
  parents=native.get('bindings',{});require(set(parents)==set(value['files']),'NAMESPACE_NATIVE_PARENT_MEMBERSHIP');expected['provider_parent_bindings_sha256']=value['provider_parent_bindings_sha256']
 require(value==expected,'NAMESPACE_PLAN_MEMBERSHIP')
 result={**value,'accepted_provider_parents':parents};_CACHE.update(signature=signature,value=result);return result

def provider_root(d):
 value=binding()
 if not value:return b.ARCHIVE_ROOT
 fid=value['provider_root_id'];m=d.meta(fid);stock=d.meta(value['stock_root_id'])
 for meta,name,parent in [(m,'_ARQUIVO_FISICO',value['stock_root_id']),(stock,'CRIATIVOS',b.ARCHIVE_ROOT)]:
  require(meta.get('mimeType')==b.FOLDER and meta.get('name')==name and meta.get('parents')==[parent] and meta.get('trashed') is False and not meta.get('driveId') and any(o.get('emailAddress')==b.ACCOUNT for o in meta.get('owners',[])) and not any(p.get('type') in ['domain','anyone'] for p in meta.get('permissions',[])),'NAMESPACE_NATIVE_ROOT')
 return fid

def is_provider_boundary(current,root):
 value=binding();return bool(value and root==b.ARCHIVE_ROOT and current==value['provider_root_id'])

def override(entry):
 value=binding()
 if not value:return None
 rec=value['files'].get(entry.get('archiveId'))
 if not rec:return None
 require(all(rec.get(a)==entry.get(c) for a,c in [('archive_id','archiveId'),('source_id','sourceId'),('sha256','sha256'),('md5','md5'),('size','size')]),'NAMESPACE_FROZEN_IDENTITY_MISMATCH')
 parent=value.get('accepted_provider_parents',{}).get(entry['archiveId'])
 if parent:
  require(parent.get('source_id')==entry['sourceId'] and parent.get('sha256')==entry['sha256'] and isinstance(parent.get('parent_id'),str),'NAMESPACE_PROVIDER_PARENT_IDENTITY');return {**rec,'provider_parent_id':parent['parent_id']}
 return rec

def effective_path(entry):
 rec=override(entry);return rec['provider_relative_parent'] if rec else entry['relativeParent']
def expected_provider_name(entry,original):
 rec=override(entry);return rec['provider_name'] if rec else original

def names_match(entry,physical,stock):
 rec=override(entry)
 if not rec:return stock.get('name')==physical.get('name')
 return physical.get('id')==rec['archive_id'] and physical.get('name')==rec['provider_name'] and stock.get('id')==rec['stock_id'] and stock.get('name')==rec['stock_name']

def catalogue_name(entry,stock):
 rec=override(entry)
 if not rec:return stock['name']
 require(stock.get('id')==rec['stock_id'] and stock.get('name')==rec['stock_name'],'NAMESPACE_STOCK_LABEL_CHANGED')
 return rec.get('catalogue_name') or stock['name']

def native_stock_label(logical_id,stock_id,catalogue_label):
 value=binding()
 if not value:return catalogue_label
 records=[r for r in value['files'].values() if r['source_id']==logical_id and r['stock_id']==stock_id and r.get('catalogue_name')==catalogue_label]
 require(len(records)<=1,'NAMESPACE_DUPLICATE_LABEL_BINDING')
 return records[0]['stock_name'] if records else catalogue_label

def stock_move(entry):
 value=binding()
 if not value:return None
 rec=value['stock_moves'].get(entry.get('stockShortcutId') or entry.get('approvedStockId') or entry.get('sourceId'))
 if rec:require(rec.get('source_id')==entry.get('sourceId') and rec.get('sha256')==entry.get('sha256'),'NAMESPACE_STOCK_MOVE_BINDING')
 return rec

def effective_stock_parent(entry,old):
 rec=stock_move(entry)
 return rec['to_parent'] if rec and rec['from_parent']==old else old

def legacy_manager_folder(d,manager,fid):
 value=binding();rec=value['legacy_manager_folders'].get(fid) if value else None
 if not rec:return None
 require(rec['manager']==manager,'NAMESPACE_LEGACY_MANAGER_PARTITION')
 m=d.meta(fid)
 require(m.get('id')==fid and m.get('mimeType')==b.FOLDER and m.get('name')==rec.get('native_name',manager) and m.get('parents')==[rec['parent_id']] and m.get('trashed') is False and any(x.get('emailAddress')==b.ACCOUNT for x in m.get('owners',[])),'NAMESPACE_LEGACY_FOLDER_NATIVE')
 require(d.relative_parent(rec['parent_id'],b.ARCHIVE_ROOT)==rec.get('parent_relative_path',['_ESTRUTURAS_ANTIGAS']),'NAMESPACE_LEGACY_FOLDER_ANCESTRY');return m

def project_historical(entry):
 """Use the verified provider itself as the view for a missing old stock ID.
 The native historical ACK still binds the original source and exact bytes.
 No new media, fabricated source object, or replacement logical ID is created.
 """
 rec=override(entry)
 if not rec or not rec.get('provider_parent_id'):return entry
 require(entry.get('mapping_kind')=='historical_verified','NAMESPACE_PROVIDER_VIEW_BINDING')
 projected={**entry,'frozenArchiveParentId':entry['archiveParentId'],'archiveParentId':rec['provider_parent_id'],'namespace_authority':AUTHORITY}
 if rec.get('representation')=='provider_as_stock':
  require(rec['stock_id']==entry['archiveId'],'NAMESPACE_PROVIDER_VIEW_STOCK_ID');projected['approvedStockId']=entry['archiveId']
 return projected

def verify_migrated_delivery(d,row,entry,receipt):
 """Preserve old delivery receipt while proving its exact same-ID relocation."""
 import ares_archive_storage as storage
 import ares_manager_storage_standard as standard
 rec=stock_move(entry);require(rec is not None,'NAMESPACE_DELIVERY_MIGRATION_REQUIRED');assert rec is not None
 require(rec.get('inventory_asset_id')==row.get('asset_id') and rec.get('to_parent')==row.get('manager_media_folder_id'),'NAMESPACE_DELIVERY_INVENTORY')
 require(receipt.get('schema')=='mgs.manager.delivery.receipt.v1' and receipt.get('status')=='verified' and receipt.get('authority_message_id')=='1565546229914411133' and receipt.get('logical_id')==entry['sourceId'] and receipt.get('stock_file_id')==rec['stock_id'] and receipt.get('provider_id')==entry['archiveId'] and receipt.get('sha256')==entry['sha256'] and receipt.get('destination_parent_id')==rec['from_parent'],'NAMESPACE_ORIGINAL_DELIVERY_RECEIPT')
 standard.validate_folder(d,rec['to_parent'],manager=rec['manager_code'],state=rec['state'])
 record=storage.resolve_media(entry['sourceId'],getattr(d,'token',None));require(record is not None,'NAMESPACE_MIGRATED_MEDIA');assert record is not None
 require(record['parents']==[rec['to_parent']] and record['sha256Checksum']==entry['sha256'] and record['name']==row['canonical_filename'],'NAMESPACE_MIGRATED_DELIVERY_READBACK')
 require(d.hashes(entry['archiveId'])=={k:entry[k] for k in ['size','md5','sha256']},'NAMESPACE_MIGRATED_DELIVERY_BYTES');return record

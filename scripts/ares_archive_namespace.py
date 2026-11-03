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
SOURCES=PATH.parent/'source-metadata-bindings.json'
HISTORICAL=b.DATA/'legacy-reconciliation-1566533058130088158'/'provider-metadata.json'
HISTORICAL_AUTHORITY='1566533058130088158'
_CACHE={}
class NamespaceError(b.ArchiveError):pass

def require(value,reason):
 if not value:raise NamespaceError(reason)
def validate_binding(value):
 require(value.get('schema')==SCHEMA and value.get('authority_message_id')==AUTHORITY and value.get('phase') in ['prepared','active'],'NAMESPACE_AUTHORITY')
 require(value.get('archive_root_id')==b.ARCHIVE_ROOT and value.get('provider_root_id') not in [None,b.ARCHIVE_ROOT,value.get('stock_root_id')],'NAMESPACE_ROOT_BINDING')
 require(isinstance(value.get('files'),dict) and isinstance(value.get('stock_moves'),dict) and isinstance(value.get('legacy_manager_folders'),dict),'NAMESPACE_SCHEMA');return value
def historical_reconciliation(value,plan):
 if not value.get('historical_reconciliation_sha256'):return {}
 extra=b.read_json(HISTORICAL,{})
 require(hashlib.sha256(b.canonical(extra)).hexdigest()==value['historical_reconciliation_sha256'] and extra.get('schema')=='mgs.archive.historical.metadata.reconciliation.v1' and extra.get('authority_message_id')==HISTORICAL_AUTHORITY and extra.get('original_plan_sha256')==value['plan_sha256'] and extra.get('phase')=='active','NAMESPACE_HISTORICAL_RECONCILIATION_AUTHORITY')
 files=extra.get('files',{});expected={r['stock_id'] for r in plan.get('usage_unproven_preserved',[])}
 require(expected and len(files)==len(expected) and {r.get('stock_id') for r in files.values()}==expected and not (set(files)&set(value['files'])),'NAMESPACE_HISTORICAL_RECONCILIATION_MEMBERSHIP')
 proof=b.read_json(HISTORICAL.parent/'native-verification.json',{})
 require(proof.get('schema')=='mgs.legacy.historical.native.verification.v1' and proof.get('authority_message_id')==HISTORICAL_AUTHORITY and proof.get('all_passed') is True and hashlib.sha256(b.canonical(proof)).hexdigest()==extra.get('verification_sha256'),'NAMESPACE_HISTORICAL_NATIVE_PROOF')
 records={r['archive_id']:r for r in proof.get('records',[])}
 require(set(records)==set(files),'NAMESPACE_HISTORICAL_NATIVE_PROOF_MEMBERSHIP')
 for fid,rec in files.items():
  native=records[fid]
  require(native.get('full_bytes_and_native_ack_verified') is True and all(native.get(k)==rec.get(k) for k in ['source_id','archive_id','stock_id','sha256','md5','size','provider_parent_id']) and rec.get('reconciliation_authority')==HISTORICAL_AUTHORITY,'NAMESPACE_HISTORICAL_NATIVE_PROOF_IDENTITY')
 return files

def binding():
 if not PATH.exists():return None
 plan_path=PATH.parent/'plan.json'
 signature=(PATH.stat().st_ino,PATH.stat().st_mtime_ns,PATH.stat().st_size,plan_path.stat().st_mtime_ns if plan_path.exists() else None,PARENTS.stat().st_mtime_ns if PARENTS.exists() else None,SOURCES.stat().st_mtime_ns if SOURCES.exists() else None,HISTORICAL.stat().st_mtime_ns if HISTORICAL.exists() else None,(HISTORICAL.parent/'native-verification.json').stat().st_mtime_ns if (HISTORICAL.parent/'native-verification.json').exists() else None)
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
 sources={}
 if value.get('source_metadata_bindings_sha256'):
  source=b.read_json(SOURCES,{})
  require(hashlib.sha256(b.canonical(source)).hexdigest()==value['source_metadata_bindings_sha256'] and source.get('schema')=='mgs.archive.source.metadata.v1' and source.get('authority_message_id')==AUTHORITY and source.get('plan_sha256')==value['plan_sha256'],'NAMESPACE_SOURCE_BINDING_DIGEST')
  sources=source.get('bindings',{});require(set(sources)<={r['source_id'] for r in value['files'].values()},'NAMESPACE_SOURCE_BINDING_MEMBERSHIP');expected['source_metadata_bindings_sha256']=value['source_metadata_bindings_sha256']
 historical=historical_reconciliation(value,plan)
 if historical:expected['historical_reconciliation_sha256']=value['historical_reconciliation_sha256']
 require(value==expected,'NAMESPACE_PLAN_MEMBERSHIP')
 result={**value,'files':{**value['files'],**historical},'accepted_provider_parents':parents,'accepted_source_metadata':sources};_CACHE.update(signature=signature,value=result);return result

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
 import ares_archive_stock_labels as labels
 approved=labels.names_match(entry,physical,stock)
 if approved is not None:return approved
 rec=override(entry)
 if not rec:return stock.get('name')==physical.get('name')
 return physical.get('id')==rec['archive_id'] and physical.get('name')==rec['provider_name'] and stock.get('id')==rec['stock_id'] and stock.get('name')==rec['stock_name']

def catalogue_name(entry,stock):
 import ares_archive_stock_labels as labels
 approved=labels.catalogue_name(entry,stock)
 if approved is not None:return approved
 rec=override(entry)
 if not rec:return stock['name']
 require(stock.get('id')==rec['stock_id'] and stock.get('name')==rec['stock_name'],'NAMESPACE_STOCK_LABEL_CHANGED')
 return rec.get('catalogue_name') or stock['name']

def native_stock_label(logical_id,stock_id,catalogue_label):
 import ares_archive_stock_labels as labels
 approved=labels.native_stock_label(logical_id,stock_id,catalogue_label)
 if approved is not None:return approved
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

def verify_reconciled_source(d,meta,asset,c,job):
 """Read-only location acceptance; destructive retirement stays unchanged."""
 value=binding();rec=value.get('accepted_source_metadata',{}).get(asset['sourceId']) if value else None
 if not rec:return False
 require(rec['job_id']==job['jobId'] and rec['snapshot_sha256']==hashlib.sha256(b.canonical(asset)).hexdigest(),'NAMESPACE_SOURCE_FROZEN_JOB')
 expected={'id':asset['sourceId'],'name':asset['name'],'mimeType':asset['mimeType'],'size':asset['size'],'md5Checksum':asset['md5'],'sha256Checksum':asset['sha256'],'driveId':c['source_drive_id'],'parents':[rec['parent_id']],'trashed':False}
 if asset.get('sourceCreatedTime'):expected['createdTime']=asset['sourceCreatedTime']
 require(all(meta.get(k)==v for k,v in expected.items()),'NAMESPACE_SOURCE_NATIVE_IDENTITY')
 from ares_archive_locations import UPLOAD
 root=d.meta(UPLOAD);require(root.get('driveId')==c['source_drive_id'] and root.get('mimeType')==b.FOLDER and root.get('trashed') is False,'NAMESPACE_SOURCE_INTAKE_ROOT')
 require(d.relative_parent(rec['parent_id'],UPLOAD)==rec['relative_parent'] and len(rec['relative_parent'])==2 and rec['relative_parent'][0]==asset['relativeParent'][0],'NAMESPACE_SOURCE_INTAKE_PARTITION')
 current=meta.get('version');frozen=asset.get('version');require(isinstance(current,str) and isinstance(frozen,str) and current.isdigit() and frozen.isdigit() and int(current)>=int(frozen),'NAMESPACE_SOURCE_VERSION')
 return True

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
 projected={**entry,'frozenArchiveParentId':entry['archiveParentId'],'archiveParentId':rec['provider_parent_id'],'namespace_authority':rec.get('reconciliation_authority',AUTHORITY)}
 if rec.get('representation')=='provider_as_stock':
  require(rec['stock_id']==entry['archiveId'],'NAMESPACE_PROVIDER_VIEW_STOCK_ID');projected['approvedStockId']=entry['archiveId']
 return projected

def verify_migrated_delivery(d,row,entry,receipt):
 """Preserve old delivery receipt while proving its exact same-ID relocation."""
 import ares_archive_storage as storage
 import ares_manager_storage_standard as standard
 rec=stock_move(entry);require(rec is not None,'NAMESPACE_DELIVERY_MIGRATION_REQUIRED');assert rec is not None
 require(rec.get('inventory_asset_id')==row.get('asset_id'),'NAMESPACE_DELIVERY_INVENTORY')
 target=row.get('manager_media_folder_id');state=rec['state']
 if target!=rec['to_parent']:
  found=standard.find_slot(rec['to_parent']);require(found is not None and found[1]=='exclusive','NAMESPACE_DELIVERY_USE_CHAIN_SOURCE');assert found is not None;slot,_=found
  request_id=row.get('manager_use_request_id');require(isinstance(request_id,str) and target==slot['used_id'],'NAMESPACE_DELIVERY_USE_CHAIN_TARGET')
  key=hashlib.sha256(b.canonical([request_id,row['asset_drive_id']])).hexdigest();use=b.read_json(standard.HOME/('use-'+key+'.json'),{})
  expected={'schema':'mgs.manager.standard.use.v1','authority_message_id':standard.AUTHORITY,'status':'verified','request_id':request_id,'asset_id':row['asset_id'],'logical_id':entry['sourceId'],'stock_file_id':rec['stock_id'],'source_id':rec['to_parent'],'folder_id':target,'sha256':entry['sha256'],'manager_code':rec['manager_code']}
  require(all(use.get(k)==v for k,v in expected.items()),'NAMESPACE_DELIVERY_USE_CHAIN_PROOF');assignment=use.get('assignment',{});standard.validate_assignment(assignment)
  require(assignment['campaign_id']==row.get('used_by') and assignment['ad_id']==row.get('meta_ad_id') and assignment['creative_id']==row.get('meta_creative_id'),'NAMESPACE_DELIVERY_USE_CHAIN_ASSIGNMENT');state='used'
 if not receipt and rec.get('classification_basis')=='native_historical_use_verified':
  # These READY assets were assigned before manager delivery existed. Their
  # digest-bound consolidation proves usage/relocation, not a nonexistent
  # original delivery. Never synthesize a receipt or admit unproven legacy.
  require(rec.get('state')=='used' and target==rec['to_parent'] and row.get('legacy_consolidation_authority')==AUTHORITY and row.get('legacy_usage_classification')==rec['classification_basis'] and row.get('manager_storage_state')=='used' and row.get('manager_storage_code')==rec['manager_code'],'NAMESPACE_NATIVE_USED_CONSOLIDATION')
  require(row.get('asset_id')==entry.get('lineageId') and row.get('asset_drive_id')==entry['sourceId'] and row.get('clean_checksum')==entry['sha256'] and all(isinstance(row.get(k),str) and row[k].isdigit() for k in ['used_by','meta_ad_id','meta_creative_id']),'NAMESPACE_NATIVE_USED_IDENTITY')
 else:
  require(receipt.get('schema')=='mgs.manager.delivery.receipt.v1' and receipt.get('status')=='verified' and receipt.get('authority_message_id')=='1565546229914411133' and receipt.get('logical_id')==entry['sourceId'] and receipt.get('stock_file_id')==rec['stock_id'] and receipt.get('provider_id')==entry['archiveId'] and receipt.get('sha256')==entry['sha256'] and receipt.get('destination_parent_id')==rec['from_parent'],'NAMESPACE_ORIGINAL_DELIVERY_RECEIPT')
 standard.validate_folder(d,target,manager=rec['manager_code'],state=state)
 record=storage.resolve_media(entry['sourceId'],getattr(d,'token',None));require(record is not None,'NAMESPACE_MIGRATED_MEDIA');assert record is not None
 require(record['parents']==[target] and record['sha256Checksum']==entry['sha256'] and record['name']==row['canonical_filename'],'NAMESPACE_MIGRATED_DELIVERY_READBACK')
 require(d.hashes(entry['archiveId'])=={k:entry[k] for k in ['size','md5','sha256']},'NAMESPACE_MIGRATED_DELIVERY_BYTES');return record

#!/usr/bin/env python3
"""Bind the approved empty Gmail backup layout and validate one native move.

No source move, upload, delete/trash, retention change, activation or credential
fallback. The old uploader/staging and its policy remain unchanged. A successful
metadata check does not claim an actual post-move restore drill.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import ares_archive_bridge as b
import mgs_whole_drive_migration as m
import mgs_corporate_archive as corporate
TIERS=('hourly','daily','weekly','monthly')
DATA=m.DATA
LAYOUT_PROOF=DATA/'backup-empty-layout-verification-1562665022910500936.json'
BINDING=DATA/'backup-archive-binding.json'
PILOT=DATA/'backup-native-move-pilot.json'
BACKUP_CONFIG=b.BASE/'config/backup/mgs-offsite-backup.json'
BACKUP_STATE=b.BASE/'data/mgs-offsite-backup-state.json'
META_FIELDS='id,name,mimeType,parents,driveId,owners(emailAddress,permissionId),createdTime,size,md5Checksum,sha256Checksum,trashed,appProperties,properties,version,capabilities(canDownload,canEdit,canTrash,canDelete)'


def folder_key(plan_sha,parent,name):
    return 'corporate-folder:'+hashlib.sha256(json.dumps([plan_sha,parent,name],ensure_ascii=False,separators=(',',':')).encode()).hexdigest()


def validate_layout(folders,corporate_root):
    if len(folders)!=5 or len({x.get('id') for x in folders})!=5:raise b.ArchiveError('BACKUP_LAYOUT_COUNT')
    roots=[x for x in folders if x.get('name')=='_DISASTER_RECOVERY']
    if len(roots)!=1:raise b.ArchiveError('BACKUP_LAYOUT_ROOT')
    root=roots[0];tiers={x.get('name'):x for x in folders if x is not root}
    if set(tiers)!=set(TIERS) or root.get('parents')!=[corporate_root]:raise b.ArchiveError('BACKUP_LAYOUT_NAMES_OR_ROOT_PARENT')
    for x in folders:
        if x.get('mimeType')!=b.FOLDER or x.get('driveId') or x.get('trashed') is not False or not any(o.get('emailAddress')==b.ACCOUNT for o in x.get('owners',[])):raise b.ArchiveError('BACKUP_LAYOUT_OWNER_OR_TYPE')
        if x is not root and x.get('parents')!=[root['id']]:raise b.ArchiveError('BACKUP_LAYOUT_TIER_PARENT')
    return {'root':root,**tiers}


def native_meta(d,fid):
    return d.api('GET','files/'+fid,{'supportsAllDrives':'true','fields':META_FIELDS})


def children(d,fid,managed=False):
    q="'"+fid+"' in parents and trashed=false"
    if managed:q+=" and appProperties has { key='mgs_dr' and value='true' }"
    out=[];page=None
    while True:
        params={'q':q,'supportsAllDrives':'true','includeItemsFromAllDrives':'true','fields':'nextPageToken,files('+META_FIELDS+')','pageSize':1000}
        if page:params['pageToken']=page
        result=d.api('GET','files',params);out.extend(result.get('files',[]));page=result.get('nextPageToken')
        if len(out)>2000:raise b.ArchiveError('BACKUP_LAYOUT_SCOPE_LIMIT')
        if not page:return out


def load_binding():
    value=b.read_json(BINDING,{})
    if value.get('schema')!='mgs.corporate.backup.archive.binding.v1' or value.get('account')!=b.ACCOUNT or value.get('source_drive_id')!=b.SOURCE_DRIVE or set(value.get('tiers',{}))!=set(TIERS):raise b.ArchiveError('BACKUP_BINDING_REQUIRED')
    if hashlib.sha256(BACKUP_CONFIG.read_bytes()).hexdigest()!=value['backup_config_sha256']:raise b.ArchiveError('BACKUP_CONFIGURATION_CHANGED')
    return value


def bind_layout(d):
    p,s=corporate.load_plan();proof=b.read_json(LAYOUT_PROOF,{})
    if proof.get('status')!='verified' or proof.get('source_message_id')!='1562665022910500936' or s.get('production_moves_enabled') is not False:raise b.ArchiveError('BACKUP_LAYOUT_APPROVED_PREFLIGHT_REQUIRED')
    cfg=b.read_json(BACKUP_CONFIG,{})
    if not isinstance(cfg,dict) or cfg.get('schema_version')!=1 or cfg.get('drive_root_id')!=b.SOURCE_DRIVE or cfg.get('drive_folder_name')!='_DISASTER_RECOVERY':raise b.ArchiveError('BACKUP_SOURCE_CONFIGURATION')
    about=d.api('GET','about',{'fields':'user(emailAddress,permissionId)'})
    if about.get('user',{}).get('permissionId')!='07414359829876449782' or about['user'].get('emailAddress')!=b.CANONICAL_SA:raise b.ArchiveError('BACKUP_CANONICAL_ACTOR')
    folders=[native_meta(d,x['id']) for x in proof['folders']];layout=validate_layout(folders,s['root_id'])
    corporate.check_acl(corporate.h.permissions(d,s['root_id']),corporate.desired(p))
    if len(children(d,layout['root']['id']))!=4 or any(children(d,layout[t]['id']) for t in TIERS):raise b.ArchiveError('BACKUP_LAYOUT_NOT_EMPTY_NO_ADOPTION')
    for meta in folders:
        corporate.check_acl(corporate.h.permissions(d,meta['id']),corporate.desired(p))
        wanted={'mgsArchiveKey':folder_key(s['plan_sha256'],meta['parents'][0],meta['name']),'mgsArchiveType':'corporate_folder'};props=dict(meta.get('properties') or {})
        if any(k in props and props[k]!=v for k,v in wanted.items()):raise b.ArchiveError('BACKUP_LAYOUT_PROPERTY_CONFLICT')
        if any(props.get(k)!=v for k,v in wanted.items()):
            if meta.get('capabilities',{}).get('canEdit') is not True:raise b.ArchiveError('BACKUP_LAYOUT_NOT_EDITABLE')
            d.api('PATCH','files/'+meta['id'],{'supportsAllDrives':'true','fields':'id,properties'},{'properties':{**props,**wanted}})
        observed=native_meta(d,meta['id'])
        if any(observed.get('properties',{}).get(k)!=v for k,v in wanted.items()) or observed.get('parents')!=meta['parents'] or not any(x.get('emailAddress')==b.ACCOUNT for x in observed.get('owners',[])):raise b.ArchiveError('BACKUP_LAYOUT_TAG_READBACK')
        corporate.check_acl(corporate.h.permissions(d,meta['id']),corporate.desired(p))
    source=next(x for x in p['allowedSourceRoots'] if x['name']=='_DISASTER_RECOVERY');sm=native_meta(d,source['id'])
    if cfg['drive_root_id']!=b.SOURCE_DRIVE or cfg['drive_folder_name']!='_DISASTER_RECOVERY' or sm.get('parents')!=[b.SOURCE_DRIVE] or sm.get('driveId')!=b.SOURCE_DRIVE or sm.get('name')!='_DISASTER_RECOVERY':raise b.ArchiveError('BACKUP_SOURCE_STAGING_CHANGED')
    source_tiers=children(d,source['id']);byname={x['name']:x for x in source_tiers}
    if len(source_tiers)!=4 or set(byname)!=set(TIERS) or any(x['mimeType']!=b.FOLDER for x in source_tiers):raise b.ArchiveError('BACKUP_SOURCE_TIER_LAYOUT')
    result={'schema':'mgs.corporate.backup.archive.binding.v1','status':'layout_bound_archive_activation_pending','account':b.ACCOUNT,'authorization_message_id':m.AUTH,'source_message_id':'1562665022910500936','source_drive_id':b.SOURCE_DRIVE,'source_root_id':source['id'],'corporate_root_id':s['root_id'],'archive_root_id':layout['root']['id'],'tiers':{t:{'source_id':byname[t]['id'],'archive_id':layout[t]['id']} for t in TIERS},'backup_config_sha256':hashlib.sha256(BACKUP_CONFIG.read_bytes()).hexdigest(),'retention_count':cfg['retention_count'],'source_staging_unchanged':True,'owner_code_folder_tags_verified':True,'archive_activation_performed':False,'retention_mutation_performed':False,'verified_at':b.now_iso()}
    b.atomic_json(BINDING,result);return result


def validate_pilot_metadata(meta,contract,*,moved):
    exact={'id':'file_id','name':'name','mimeType':'mime_type','size':'size','md5Checksum':'md5','sha256Checksum':'sha256','createdTime':'created_time'}
    if any(str(meta.get(k))!=str(contract[v]) for k,v in exact.items()) or meta.get('trashed') is not False or meta.get('capabilities',{}).get('canDownload') is not True:raise b.ArchiveError('BACKUP_PILOT_IDENTITY_OR_BYTES')
    props=meta.get('appProperties') or {}
    if props.get('mgs_dr')!='true' or props.get('tier')!=contract['tier'] or props.get('mode')!=contract['mode'] or props.get('sha256')!=contract['sha256']:raise b.ArchiveError('BACKUP_PILOT_MANAGED_PROPERTIES')
    version=meta.get('version','')
    if not re.fullmatch('[1-9][0-9]*',str(version)):raise b.ArchiveError('BACKUP_PILOT_VERSION')
    if moved:
        if meta.get('parents')!=[contract['destination_parent_id']] or meta.get('driveId') or int(version)<int(contract['source_version']) or not any(x.get('emailAddress')==contract['expected_owner'] for x in meta.get('owners',[])):raise b.ArchiveError('BACKUP_PILOT_DESTINATION')
    elif meta.get('parents')!=[contract['source_parent_id']] or meta.get('driveId')!=b.SOURCE_DRIVE or str(version)!=contract['source_version']:raise b.ArchiveError('BACKUP_PILOT_SOURCE_CHANGED')
    return True


def prepare_pilot(d):
    binding=load_binding();prior=b.read_json(PILOT)
    if prior:
        validate_pilot_metadata(native_meta(d,prior['file_id']),prior,moved=False);return prior
    state=b.read_json(BACKUP_STATE,{});restore=state.get('last_restore_test',{})
    if restore.get('status')!='PASS' or restore.get('bundle_mode')!='full':raise b.ArchiveError('BACKUP_PRIOR_FULL_RESTORE_REQUIRED')
    meta=native_meta(d,restore['remote_file_id']);tier=(meta.get('appProperties') or {}).get('tier')
    if tier not in TIERS or meta.get('sha256Checksum')!=restore.get('download_sha256') or int(meta.get('size',0))!=restore.get('remote_size_bytes') or not re.fullmatch('mgs-dr-'+tier+'-[0-9]{8}T[0-9]{6}Z\\.zip\\.gpg',meta.get('name','')):raise b.ArchiveError('BACKUP_PILOT_PRIOR_RESTORE_BINDING')
    p,s=corporate.load_plan();corporate.check_acl(corporate.h.permissions(d,meta['id']),corporate.desired(p,True))
    managed=sorted(children(d,binding['tiers'][tier]['source_id'],managed=True),key=lambda x:x['createdTime'],reverse=True);keep=binding['retention_count'][tier]
    if meta['id'] not in {x['id'] for x in managed[:keep]}:raise b.ArchiveError('BACKUP_PILOT_NOT_IN_RETAINED_SET')
    if sum(x.get('name')==meta['name'] for x in managed)!=1:raise b.ArchiveError('BACKUP_PILOT_SOURCE_NAME_AMBIGUOUS')
    result={'schema':'mgs.corporate.backup.native.move.pilot.v1','status':'awaiting_owner_single_native_move','authorization_message_id':m.AUTH,'source_message_id':'1562665022910500936','file_id':meta['id'],'name':meta['name'],'mime_type':meta['mimeType'],'source_parent_id':binding['tiers'][tier]['source_id'],'destination_parent_id':binding['tiers'][tier]['archive_id'],'size':meta['size'],'md5':meta['md5Checksum'],'sha256':meta['sha256Checksum'],'created_time':meta['createdTime'],'source_version':meta['version'],'tier':tier,'mode':'full','expected_owner':b.ACCOUNT,'prior_full_restore_pass_at':restore['tested_at_utc'],'prior_full_restore_components':restore['components_validated'],'source_selected_in_retained_set':True,'metadata_before':meta,'bytes_downloaded_by_this_preflight':False,'archive_automatic_activation_performed':False,'source_root_must_remain':True,'post_move_restore_required':True,'prepared_at':b.now_iso()}
    validate_pilot_metadata(meta,result,moved=False);b.atomic_json(PILOT,result);return result


def verify_pilot(d):
    binding=load_binding();pilot=b.read_json(PILOT,{})
    if pilot.get('schema')!='mgs.corporate.backup.native.move.pilot.v1':raise b.ArchiveError('BACKUP_PILOT_REQUIRED')
    meta=native_meta(d,pilot['file_id']);validate_pilot_metadata(meta,pilot,moved=True);p,s=corporate.load_plan();corporate.check_acl(corporate.h.permissions(d,meta['id']),corporate.desired(p))
    staging=native_meta(d,binding['source_root_id'])
    if staging.get('driveId')!=b.SOURCE_DRIVE or staging.get('parents')!=[b.SOURCE_DRIVE] or staging.get('name')!='_DISASTER_RECOVERY' or staging.get('trashed') is not False:raise b.ArchiveError('BACKUP_SOURCE_STAGING_CHANGED')
    for tier,ids in binding['tiers'].items():
        st=native_meta(d,ids['source_id'])
        if st.get('driveId')!=b.SOURCE_DRIVE or st.get('parents')!=[binding['source_root_id']] or st.get('name')!=tier or st.get('trashed') is not False:raise b.ArchiveError('BACKUP_SOURCE_TIER_CHANGED')
    archive_root=native_meta(d,binding['archive_root_id']);archive_tier=native_meta(d,pilot['destination_parent_id'])
    if archive_root.get('parents')!=[binding['corporate_root_id']] or archive_root.get('name')!='_DISASTER_RECOVERY' or archive_root.get('driveId') or archive_tier.get('parents')!=[binding['archive_root_id']] or archive_tier.get('name')!=pilot['tier'] or archive_tier.get('driveId'):raise b.ArchiveError('BACKUP_ARCHIVE_HIERARCHY_CHANGED')
    for item in [archive_root,archive_tier]:
        if item.get('mimeType')!=b.FOLDER or item.get('trashed') is not False or not any(x.get('emailAddress')==b.ACCOUNT for x in item.get('owners',[])):raise b.ArchiveError('BACKUP_ARCHIVE_FOLDER_OWNER_OR_TYPE')
        corporate.check_acl(corporate.h.permissions(d,item['id']),corporate.desired(p))
    path=DATA/'backup-native-move-pilot-verification.json';previous=b.read_json(path,{})
    first=previous.get('native_move_first_verified_at') or b.now_iso();restore=b.read_json(BACKUP_STATE,{}).get('last_restore_test',{})
    restored=restore.get('status')=='PASS' and restore.get('remote_file_id')==pilot['file_id'] and restore.get('download_sha256')==pilot['sha256'] and bool(restore.get('tested_at_utc')) and b.timestamp(restore['tested_at_utc'])>=b.timestamp(first)
    result={'schema':'mgs.corporate.backup.native.move.verification.v1','status':'verified' if restored else 'native_move_verified_restore_pending','file_id':meta['id'],'name':meta['name'],'same_id':True,'same_native_size_md5_sha256':True,'same_managed_properties':True,'owner_and_acl_verified':True,'source_staging_unchanged':True,'native_move_first_verified_at':first,'post_move_full_restore_verified':restored,'restore_proof':restore if restored else None,'archive_sa_capabilities':meta.get('capabilities'),'archive_retention_activation_performed':False,'archive_retention_status':'not_proven_by_this_check','metadata':meta,'verified_at':b.now_iso(),'full_migration_complete':False};b.atomic_json(path,result);return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['bind-layout','prepare-pilot','verify-pilot']);args=parser.parse_args()
    with b.queue_lock():
        d=b.Drive(args.action=='bind-layout');result={'bind-layout':bind_layout,'prepare-pilot':prepare_pilot,'verify-pilot':verify_pilot}[args.action](d)
    print(json.dumps(result,ensure_ascii=False))
    return 2 if args.action=='verify-pilot' and result.get('status')!='verified' else 0
if __name__=='__main__':raise SystemExit(main())

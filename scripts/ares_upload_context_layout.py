#!/usr/bin/env python3
"""Approved additive upload context layout; no moves, deletes, ACL or campaign writes."""
from __future__ import annotations
import re
FOLDER='application/vnd.google-apps.folder'
MANAGERS={'g001':'Ícaro','g002':'Geizian','g003':'Isliago','g004':'Joe','g005':'Kelly','g006':'Nicolas'}
OPERATION=re.compile(r'(CC|CAR|GAME|JOBS|SHEIN)_[A-Z]{2}_[A-Z]{2}')
class LayoutError(RuntimeError):pass

def plan(operations,managers):
    if not managers or any(MANAGERS.get(k)!=v for k,v in managers.items()):raise LayoutError('UNKNOWN_MANAGER')
    selected=[x for x in operations if x.get('mimeType')==FOLDER and OPERATION.fullmatch(x.get('name',''))]
    if len({x['name'] for x in selected})!=len(selected):raise LayoutError('DUPLICATE_OPERATION')
    return [{'operation':x['name'],'source_operation_folder_id':x['id'],'manager_code':code,'manager_name':name} for x in sorted(selected,key=lambda x:x['name']) for code,name in sorted(managers.items())]

def check_folder(d,c,fid,parent,name):
    m=d.meta(fid)
    if any(m.get(k)!=v for k,v in {'id':fid,'mimeType':FOLDER,'parents':[parent],'name':name,'driveId':c['source_drive_id'],'trashed':False}.items()):raise LayoutError('FOLDER_SCOPE_CHANGED')
    if m.get('capabilities',{}).get('canAddChildren') is not True:raise LayoutError('FOLDER_NOT_WRITABLE')
    return m

def find(d,parent,name):
    matches=[x for x in d.listing(parent) if x.get('name')==name]
    if len(matches)>1:raise LayoutError('AMBIGUOUS_EXISTING_FOLDER')
    if matches and matches[0].get('mimeType')!=FOLDER:raise LayoutError('NAME_OCCUPIED_BY_NONFOLDER')
    return matches[0] if matches else None

def ensure(d,c,parent,name,key):
    previous=find(d,parent,name)
    if previous:fid=previous['id']
    else:
        payload={'name':name,'mimeType':FOLDER,'parents':[parent],'properties':{'mgsIntakeSchema':'mgs.upload.context.v1','mgsIntakeKey':key,'mgsIntakeAuthority':c['authority_message_id']}}
        try:fid=d.api('POST','files',{'supportsAllDrives':'true','fields':'id'},payload)['id']
        except Exception:
            # Reconcile ambiguous POST; never blindly create a second folder.
            landed=find(d,parent,name)
            if not landed or landed.get('properties',{}).get('mgsIntakeKey')!=key:raise LayoutError('FOLDER_CREATE_AMBIGUOUS_NO_REPLAY')
            fid=landed['id']
    check_folder(d,c,fid,parent,name);return fid

def validate_slot(d,c,slot):
    check_folder(d,c,c['upload_root_id'],c['source_root_id'],'UPLOAD MANUAL')
    check_folder(d,c,slot['source_operation_folder_id'],c['source_root_id'],slot['operation'])
    check_folder(d,c,slot['operation_upload_folder_id'],c['upload_root_id'],slot['operation'])
    check_folder(d,c,slot['folder_id'],slot['operation_upload_folder_id'],slot['manager_name'])
    if MANAGERS.get(slot['manager_code'])!=slot['manager_name']:raise LayoutError('SLOT_MANAGER_CHANGED')
    return {'operation':slot['operation'],'manager_code':slot['manager_code'],'manager_name':slot['manager_name']}

def apply_layout(d,c,rows):
    check_folder(d,c,c['upload_root_id'],c['source_root_id'],'UPLOAD MANUAL')
    if len({(r['operation'],r['manager_code']) for r in rows})!=len(rows):raise LayoutError('DUPLICATE_SLOT')
    for r in rows:
        if not OPERATION.fullmatch(r['operation']) or MANAGERS.get(r['manager_code'])!=r['manager_name']:raise LayoutError('UNREGISTERED_SLOT')
    for op in sorted({r['operation'] for r in rows}):
        candidates=[r['source_operation_folder_id'] for r in rows if r['operation']==op]
        if len(set(candidates))!=1:raise LayoutError('AMBIGUOUS_SOURCE_OPERATION')
        check_folder(d,c,candidates[0],c['source_root_id'],op)
    # Validate every pre-existing target before the first additive write.
    for op in sorted({r['operation'] for r in rows}):
        existing=find(d,c['upload_root_id'],op)
        if existing:
            check_folder(d,c,existing['id'],c['upload_root_id'],op)
            for r in [x for x in rows if x['operation']==op]:
                slot=find(d,existing['id'],r['manager_name'])
                if slot:check_folder(d,c,slot['id'],existing['id'],r['manager_name'])
    opids={};slots=[]
    for row in rows:
        op=row['operation']
        if op not in opids:opids[op]=ensure(d,c,c['upload_root_id'],op,'operation:'+op)
        fid=ensure(d,c,opids[op],row['manager_name'],'slot:'+op+':'+row['manager_code'])
        slot={**row,'operation_upload_folder_id':opids[op],'folder_id':fid};validate_slot(d,c,slot);slots.append(slot)
    return {'schema':'mgs.upload.context.layout.v1','authority_message_id':c['authority_message_id'],'source_root_id':c['source_root_id'],'source_drive_id':c['source_drive_id'],'upload_root_id':c['upload_root_id'],'slots':slots,'auto_treatment_enabled':False,'campaign_actions_enabled':False,'delete_source':False}

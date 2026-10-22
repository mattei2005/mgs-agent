#!/usr/bin/env python3
"""Publish an immutable efficiency revision; deliberate owner repin remains mandatory."""
from __future__ import annotations
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import ares_archive_bridge as b
import mgs_backup_automation as a
AUTH='1562859075107164270'
BASE_SHA='23b3953232921ac91d5efeeed2cecda70043c7563b6c2513e14f427c65b2e948'
BASE=b.BASE/'integrations/creative-archive-30tb/WorkerBackupArchiveMaxQuota.js'
EXTENSION=b.BASE/'integrations/creative-archive-30tb/ArchiveEfficiencyExtension.js'
TARGET=b.BASE/'integrations/creative-archive-30tb/WorkerArchiveEfficient.js'
ROLLBACK=a.m.DATA/('efficiency-rollback-'+AUTH+'.json')

def sha(raw):return hashlib.sha256(raw).hexdigest()
def build(raw,extension):
 if sha(raw)!=BASE_SHA:raise b.ArchiveError('EFFICIENCY_BASE_CHANGED')
 text=raw.decode()
 changes=[
 ("  var start=Date.now(),props=PropertiesService.getScriptProperties(),ledger=[],budgetReady=false;\n  try {\n    var about=Drive.About.get", "  var start=Date.now(),props=PropertiesService.getScriptProperties(),ledger=[],budgetReady=false;\n  try {\n    var admission=mgsArchiveFastAdmit(props,start);ledger=admission.ledger;budgetReady=true;\n    if(!admission.admitted)return mgsArchiveFastPause(c,admission.runtime);\n    var about=Drive.About.get"),
 ("    var priorLedger=JSON.parse(props.getProperty('MGS_ARCHIVE_RUNTIME_24H') || '[]');\n    if(!Array.isArray(priorLedger) || priorLedger.some(function(p){return !Array.isArray(p) || p.length!==2 || !isFinite(p[0]) || !isFinite(p[1]) || p[1]<0;}))throw new Error('RUNTIME_BUDGET_CORRUPT');\n    ledger=priorLedger.filter(function(p){return p[0]>start-86400000;});budgetReady=true;\n    if(ledger.length>=350 || ledger.reduce(function(n,p){return n+p[1];},0)>=mgsArchiveBulkRuntimeLimit()) {\n      var paused={status:'runtime_budget_paused',deleteSource:false};mgsArchiveWriteHeartbeat(c,paused);return paused;\n    }", "    // Production budget was checked before any Drive call; real ledger retained."),
 ("    if(summary.canaryAcknowledged)summary.backfillTree=mgsArchiveBackfillTree(c,start);", "    if(summary.canaryAcknowledged)summary.backfillTree={status:'on_demand_only'};"),
 ("summary.copied.length+summary.blocked.length<2 && Date.now()-start<210000", "summary.copied.length+summary.blocked.length<8 && mgsArchiveFastCanWork(15000)"),
 ("      } catch(error) {\n        var reason=String(error && error.message || error).slice(0,240);", "      } catch(error) {\n        if(error.mgsArchiveCooperativeYield){summary.yielded=true;break;}\n        var reason=String(error && error.message || error).slice(0,240);"),
 ("  var page=Drive.Files.list({q:q,pageSize:2,fields:'nextPageToken,files(id)'});", "  var page=mgsArchiveFastRead(function(){return Drive.Files.list({q:q,pageSize:2,fields:'nextPageToken,files(id)'});});"),
 ("    mgsArchiveWriteHeartbeat(c,summary);console.log(JSON.stringify(summary));return summary;", "    if(!rows.length && !summary.blocked.length && summary.canaryAcknowledged)summary.backfillTree=mgsArchiveFastFinalizeTree(c,summary,start);\n    if(summary.blocked.length)summary.status='blocked';\n    mgsArchiveWriteHeartbeat(c,summary);console.log(JSON.stringify(summary));return summary;"),
 ("  var f=mgsArchiveOne(c.requestsFolderId,'backup-activation:'+MGS_BACKUP_PINS.planSha256);if(!f)return out;\n  var act=mgsCorporateSaObject(c,f,'backup-activation:'+MGS_BACKUP_PINS.planSha256,'backup_activation').body;", "  var activationKey='backup-activation-v2:'+mgsArchiveHash(MGS_BACKUP_PINS.planSha256+'|'+c.workerSha256);\n  var f=mgsArchiveOne(c.requestsFolderId,activationKey);if(!f){out.status='awaiting_sa_reacceptance';return out;}\n  var act=mgsCorporateSaObject(c,f,activationKey,'backup_activation').body;")]
 for old,new in changes:
  if text.count(old)!=1:raise b.ArchiveError('EFFICIENCY_REPLACEMENT_COUNT:'+old[:80])
  text=text.replace(old,new)
 return text.encode()+b'\n'+extension

def prepare():
 raw=build(BASE.read_bytes(),EXTENSION.read_bytes())
 if TARGET.exists() and TARGET.read_bytes()!=raw:
  stage=b.read_json(a.STAGE,{})
  if stage.get('worker_sha256')==sha(TARGET.read_bytes()):raise b.ArchiveError('EFFICIENCY_IMMUTABLE_SOURCE_CHANGED')
 TARGET.write_bytes(raw);subprocess.run(['node','--check',str(TARGET)],capture_output=True,check=True)
 return {'authorization_message_id':AUTH,'worker_sha256':sha(raw),'worker_source_path':str(TARGET.relative_to(b.BASE)),'status':'prepared_not_owner_deployed','base_worker_sha256':BASE_SHA}

def sync_whole(s):
 whole=b.read_json(a.m.DATA/'stage.json',{})
 if whole.get('worker_sha256') not in [BASE_SHA,s['worker_sha256']]:raise b.ArchiveError('EFFICIENCY_WHOLE_STAGE_DRIFT')
 whole.update(worker_file_id=s['worker_file_id'],worker_sha256=s['worker_sha256'],worker_source_path=s['worker_source_path'],previous_active_worker_file_id=s['previous_active_worker_file_id'],previous_active_worker_sha256=BASE_SHA,status=s['status'],owner_repin_confirmed=s.get('owner_accepted') is True,efficiency_authorization_message_id=AUTH)
 b.atomic_json(a.m.DATA/'stage.json',whole)

def publish():
 prepared=prepare()
 with b.queue_lock():
  plan,s=a.load();c=b.config_load();d=b.Drive(True)
  if s.get('worker_sha256')==prepared['worker_sha256']:
   if s.get('efficiency_revision',{}).get('authorization_message_id')!=AUTH or d.raw(s['worker_file_id'])!=TARGET.read_bytes():raise b.ArchiveError('EFFICIENCY_REPLAY_READBACK')
   b.require_publisher(d.meta(s['worker_file_id']),b.CANONICAL_SA);sync_whole(s);return s
  if s.get('worker_sha256')!=BASE_SHA or c.get('worker_sha256')!=BASE_SHA or s.get('owner_accepted') is not True:raise b.ArchiveError('EFFICIENCY_ACTIVE_BASE_NOT_ACCEPTED')
  if sha(d.raw(c['worker_file_id']))!=BASE_SHA:raise b.ArchiveError('EFFICIENCY_REMOTE_BASE_DRIFT')
  b.preflight(d,c)
  if not ROLLBACK.exists():b.atomic_json(ROLLBACK,{'authorization_message_id':AUTH,'saved_at':b.now_iso(),'backup_stage':s,'whole_stage':b.read_json(a.m.DATA/'stage.json'),'active_config':c,'historical_stage':b.read_json(a.historical.location()/'stage.json')})
  s['efficiency_revision']={**prepared,'previous_active_worker_file_id':c['worker_file_id'],'rollback_path':str(ROLLBACK.relative_to(b.BASE))};b.atomic_json(a.STAGE,s)
  fid=a.staged_blob(d,s,c['control_folder_id'],'worker:'+prepared['worker_sha256'],'worker_source',TARGET.read_bytes(),'worker-efficient-'+prepared['worker_sha256']+'.js','application/javascript')
  b.require_publisher(d.meta(fid),b.CANONICAL_SA)
  if d.raw(fid)!=TARGET.read_bytes():raise b.ArchiveError('EFFICIENCY_NATIVE_BYTES_READBACK')
  s.update(worker_file_id=fid,worker_sha256=prepared['worker_sha256'],worker_source_path=prepared['worker_source_path'],previous_active_worker_file_id=c['worker_file_id'],previous_active_worker_sha256=BASE_SHA,previous_activation_file_id=s.get('activation_file_id'),owner_accepted=False,automatic_archive_enabled=s.get('automatic_archive_enabled') is True,heartbeat_samples=[],status='efficiency_revision_awaiting_owner_repin',published_at=b.now_iso())
  s['efficiency_revision'].update(status=s['status'],worker_file_id=fid,backup_activation_key_versioned=True)
  b.atomic_json(a.STAGE,s);sync_whole(s)
  if b.config_load()!=c:raise b.ArchiveError('EFFICIENCY_ACTIVE_CONFIG_CHANGED')
  return s
if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['prepare','publish']);args=parser.parse_args();print(json.dumps({'prepare':prepare,'publish':publish}[args.action](),ensure_ascii=False))

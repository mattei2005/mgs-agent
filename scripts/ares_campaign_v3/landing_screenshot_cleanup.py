"""Delete only attributable completed-observer screenshots, never audit JSON."""
from __future__ import annotations
import hashlib
import json
import re
from pathlib import Path
from . import landing_followup as core
from .landing_reliability import policy

IMAGE_ROOTS=(Path('/root/.hermes/profiles/ares/artifacts/landing-followup'),Path('/root/.hermes/profiles/ares/cache/images'))
SUFFIXES={'.png','.jpg','.jpeg','.webp'}


def image_paths(value):
    result=set()
    if isinstance(value,dict):
        for x in value.values():result.update(image_paths(x))
    elif isinstance(value,list):
        for x in value:result.update(image_paths(x))
    elif isinstance(value,str):
        if value.startswith('/') and Path(value).suffix.lower() in SUFFIXES:result.add(value)
        for p in re.findall(r'/root/[^\s"<>\\]+\.(?:png|jpg|jpeg|webp)',value):result.add(p)
    return result


def allowed(path):
    p=Path(path)
    return p.suffix.lower() in SUFFIXES and not p.is_symlink() and any(p.is_relative_to(root) and p.resolve().is_relative_to(root.resolve()) for root in IMAGE_ROOTS)


def references(q,key):
    refs=set();owners=set()
    for r in q.db.execute('SELECT evidence FROM links WHERE job=?',(key,)):
        refs.update(image_paths(json.loads(r['evidence'] or '{}')))
    for r in q.db.execute('SELECT detail FROM events WHERE job=?',(key,)):
        d=json.loads(r['detail']);refs.update(image_paths(d))
        if isinstance(d,dict) and isinstance(d.get('owner'),str):owners.add(d['owner'])
    for owner in owners:
        folder=q.root/'runs'/owner
        if not folder.is_relative_to(q.root/'runs') or not folder.resolve().is_relative_to((q.root/'runs').resolve()):continue
        for file in folder.rglob('*.json'):
            try:refs.update(image_paths(json.loads(file.read_text())))
            except (OSError,ValueError):continue
        log=folder/'worker.log'
        if log.is_file():refs.update(image_paths(log.read_text(errors='replace')))
    root=IMAGE_ROOTS[0]/key
    if root.is_dir():refs.update(str(p) for p in root.rglob('*') if p.suffix.lower() in SUFFIXES)
    return {p for p in refs if allowed(p)}


def prune_completed(q,apply=False):
    cfg=policy()
    if not cfg.get('delete_screenshots_after_complete'):return {'state':'DISABLED','files':0,'bytes':0}
    candidates=[];protected=set();eligible=[]
    for row in q.db.execute('SELECT key,state FROM jobs').fetchall():
        j=q.job(row['key']);links=j['links'];success=q.db.execute('SELECT state FROM messages WHERE key=?',(q.success_key(j['key']),)).fetchone()
        complete=j['state']=='COMPLETE' and links and all(l['state']=='PASSED' for l in links) and success and success['state']=='VERIFIED'
        if not complete:protected.update(references(q,j['key']));continue
        if all(json.loads(l['evidence'] or '{}').get('screenshots_purged') is True for l in links):continue
        # Retain a verifiable result receipt for every passed URL before removal.
        receipts=[]
        for link in links:
            passed=None
            for event in q.db.execute("SELECT seq,at,detail FROM events WHERE job=? AND kind='observation_result' ORDER BY seq DESC",(j['key'],)):
                d=json.loads(event['detail'])
                if d.get('idx')==link['idx'] and d.get('result')=='PASS':passed=(event,d);break
            e=json.loads(link['evidence'] or '{}')
            if not passed or e.get('network_ad_confirmed') is not True or e.get('tab_closed_verified') is not True or e.get('other_tabs_preserved') is not True:
                receipts=[];break
            event,d=passed;receipts.append({'idx':link['idx'],'pass_event_seq':event['seq'],'validated_at':event['at'],'ad_description':e.get('ad_description'),'sample_metadata':[{k:s.get(k) for k in ['monotonic_seconds','screenshot','screenshot_sha256','screenshot_captured_at','ad_visible','tab_active']} for s in e.get('samples',[])]})
        if len(receipts)!=len(links):protected.update(references(q,j['key']));continue
        eligible.append((j,receipts));candidates.extend(references(q,j['key']))
    files=[]
    for path in sorted(set(candidates)-protected):
        p=Path(path)
        if p.is_file() and allowed(p):
            stat=p.stat();files.append({'path':str(p),'size':stat.st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    summary={'state':'PLAN','files':len(files),'bytes':sum(f['size'] for f in files),'eligible_jobs':len(eligible)}
    if not apply:return summary
    if not eligible:return {'state':'NO_ELIGIBLE_COMPLETED_JOB','files':0,'bytes':0}
    # Exclude a live claimant for eligible rows before irreversible deletion.
    for j,_ in eligible:
        current=q.job(j['key'])
        if current['state']!='COMPLETE':raise ValueError('completion changed; purge aborted before delete')
    with q.tx():q.event(None,'screenshot_purge_intent',{'files':files,'jobs':[j['key'] for j,_ in eligible],'retains_validation_receipts':True})
    deleted=[];skipped=[]
    for f in files:
        p=Path(f['path'])
        if not p.exists():continue
        if not allowed(p) or p.stat().st_size!=f['size'] or hashlib.sha256(p.read_bytes()).hexdigest()!=f['sha256']:
            skipped.append(f['path']);continue
        p.unlink();assert not p.exists();deleted.append(f)
    with q.tx():
        for j,receipts in eligible:
            q.event(j['key'],'validated_screenshot_retention_receipt',{'links':receipts,'binary_images_removed_after_complete':True,'json_events_and_utm_lineage_preserved':True})
            for link in j['links']:
                e=json.loads(link['evidence'] or '{}');e['screenshots_purged']=not bool(skipped);e['screenshot_retention']='PURGED_AFTER_VERIFIED_COMPLETE' if not skipped else 'PURGE_PARTIAL_RETRY_REQUIRED'
                q.db.execute('UPDATE links SET evidence=? WHERE job=? AND idx=?',(json.dumps(e,ensure_ascii=False),j['key'],link['idx']))
        q.event(None,'screenshot_purge_complete',{'deleted_files':deleted,'skipped_changed_files':skipped,'bytes_freed':sum(f['size'] for f in deleted)})
    return {'state':'PURGED','files':len(deleted),'bytes':sum(f['size'] for f in deleted),'eligible_jobs':len(eligible),'skipped_changed':len(skipped)}

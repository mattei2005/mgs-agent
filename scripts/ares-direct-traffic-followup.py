#!/usr/bin/env python3
"""Post-response landing follow-up control plane. All diagnostics stay local."""
from __future__ import annotations
import argparse
import fcntl
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import time
import uuid
from pathlib import Path
from ares_campaign_v3.landing_followup import Queue, Discord, ROOT, BASE, publish_creation, worker_prompt
from ares_campaign_v3 import landing_followup as core
from ares_campaign_v3.landing_intake import Intake, native_busy
from ares_campaign_v3.landing_followup_reporting import cycle as report_progress


def require_pc1_lease(session_id):
    if not session_id or session_id!=os.environ.get('HERMES_SESSION_ID'):
        raise ValueError('real current observer session ID required')
    r=subprocess.run([sys.executable,str(BASE/'scripts/mgs-pc1-computer-use-lock.py'),'status'],capture_output=True,text=True,timeout=20)
    state=json.loads(r.stdout) if r.returncode==0 else {}
    if not state.get('locked') or state.get('agent')!='ares' or state.get('session_id')!=session_id:
        raise ValueError('exclusive physical PC1 lease not held by this observer')


def evidence_arguments(parser):
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--evidence',type=Path)
    group.add_argument('--evidence-json',help='Compact actual evidence; avoid a separate narrative file')


def load_evidence(args):
    return json.loads(args.evidence_json) if args.evidence_json is not None else json.loads(args.evidence.read_text())


def flush(q,discord):
    # All observation/recovery evidence is already persisted before outbox work.
    for row in q.db.execute("SELECT key FROM jobs WHERE state='OBSERVED'").fetchall():
        with q.tx():q.prepare_success_if_complete(row['key'])
    for row in q.db.execute("SELECT key FROM messages WHERE state IN ('PREPARED','INTENT') ORDER BY created").fetchall():
        try:
            message=discord.deliver(q,row['key'])
            if row['key'].endswith(':creation'):
                q.acknowledge(row['key'].removesuffix(':creation'),message,discord.bot_id)
        except Exception as e:
            # Never dump transport data into the operational thread. The outbox
            # retains exact IDs/intent and will be reconciled on the next tick.
            with q.tx():q.event(None,'notification_deferred',{'key':row['key'],'reason':str(e)[:120]})
    for row in q.db.execute("SELECT key FROM jobs WHERE state='WAITING_CREATION_REPLY'").fetchall():
        out=q.db.execute('SELECT * FROM messages WHERE key=?',(row['key']+':creation',)).fetchone()
        if out and out['state']=='VERIFIED':
            try:q.acknowledge(row['key'],discord.deliver(q,out['key']),discord.bot_id)
            except Exception:pass
    for row in q.db.execute("SELECT key FROM jobs WHERE state='OBSERVED'").fetchall():
        out=q.db.execute('SELECT state FROM messages WHERE key=?',(q.success_key(row['key']),)).fetchone()
        if out and out['state']=='VERIFIED':
            with q.tx():
                q.db.execute("UPDATE jobs SET state='COMPLETE' WHERE key=?",(row['key'],))
                q.event(row['key'],'completed',{'landing_observation':True,'gam_registration':'NOT_VERIFIED'})


def observer_process_alive(session_id,query_file=None):
    marker=('HERMES_SESSION_ID='+session_id).encode()
    for p in Path('/proc').iterdir():
        if not p.name.isdigit():continue
        try:
            if marker in (p/'environ').read_bytes().split(b'\0'):return True
            argv=(p/'cmdline').read_bytes().split(b'\0')
            if session_id.encode() in argv or (query_file and str(query_file).encode() in argv):return True
        except (FileNotFoundError,ProcessLookupError):continue
        except (PermissionError,OSError):return True
    return False


def orphan_observer_lease(q,state):
    """Release only an ended Ares observer's proven orphan; never another task."""
    sid=state.get('session_id')
    if not state.get('locked') or state.get('agent')!='ares' or not sid or observer_process_alive(sid):return False
    try:
        from ares_campaign_v3.landing_intake import readonly,NATIVE_DB
        with readonly(NATIVE_DB) as c:
            row=c.execute("SELECT source FROM sessions WHERE id=?",(sid,)).fetchone()
            if not row or row['source']!='tool':return False
            first=c.execute("SELECT content FROM messages WHERE session_id=? AND role='user' ORDER BY id LIMIT 1",(sid,)).fetchone()
        if not first:return False
        data=json.loads(first['content'].rsplit('\n',1)[-1])
        key=data['queue_key'];j=q.job(key)
        if j['state']!='NEEDS_RECONCILIATION':return False
        last=q.db.execute("SELECT detail FROM events WHERE job=? AND kind IN ('claimed','recovery_claimed') ORDER BY seq DESC LIMIT 1",(key,)).fetchone()
        if not last or json.loads(last['detail']).get('owner')!=data.get('owner'):return False
        # --pass-session-id can be set after process startup; /proc/environ of
        # the still-live CLI need not contain it. Check its exact query-file too.
        if observer_process_alive(sid,q.root/'runs'/data['owner']/'input.txt'):return False
    except (ValueError,KeyError,TypeError,AttributeError,OSError,sqlite3.Error):return False
    r=subprocess.run([sys.executable,str(BASE/'scripts/mgs-pc1-computer-use-lock.py'),'release','--agent','ares','--session-id',sid],capture_output=True,text=True,timeout=20)
    if r.returncode:return False
    result=json.loads(r.stdout)
    if result.get('locked') is not False:return False
    with q.tx():q.event(key,'orphan_pc1_lease_released',{'session_id':sid,'previous_owner_process_alive':False,'automatic_navigation':False})
    return True


def prepare_recovery_proof(q,job,idx,directory):
    """Freeze already-reconciled facts, not a new browser result or a PASS."""
    target=job['links'][idx]
    for row in q.db.execute("SELECT detail FROM events WHERE job=? AND kind='reconciled_no_ad' ORDER BY seq DESC",(job['key'],)):
        d=json.loads(row['detail'])
        if d.get('idx')!=idx or d.get('attempt')!=target['attempt']:continue
        e=d.get('evidence') or {}
        try:
            core.validate_closure(e)
            if e.get('network_ad_confirmed') is not False or not e.get('visual_review'):continue
            url=core.urllib.parse.urlsplit(e['observed_url']);source=core.urllib.parse.urlsplit(job['payload']['links'][idx]['effective_campaign_url'])
            if url.hostname!=source.hostname or url.query!=source.query:continue
            core.scope(e['observed_url'])
            observed=core.file_evidence(e['observation_screenshot'])['captured_at']
            opened=[json.loads(x['detail'])|{'at':x['at']} for x in q.db.execute("SELECT at,detail FROM events WHERE job=? AND kind='open_intent' ORDER BY seq",(job['key'],)) if json.loads(x['detail']).get('idx')==idx]
            if not opened or observed<opened[-1]['at'] or core.file_evidence(e['closed_screenshot'])['captured_at']<observed:continue
        except (ValueError,KeyError,TypeError,OSError):continue
        p=directory/'recovery-evidence.json';p.write_text(json.dumps(e,ensure_ascii=False));os.chmod(p,0o600)
        job['recovery_evidence_path']=str(p);job['confirmed_no_ads']=q.no_ad_count(job['key'],idx)
        return True
    return False


def tick(q):
    try:report_progress(q,Discord)
    except Exception as e:
        with q.tx():q.event(None,'progress_delivery_deferred',{'reason':type(e).__name__,'retry_owner':'ares'})
    # Existing native turns have absolute priority; this adds nothing to them.
    if native_busy():return {'state':'WAITING_NATIVE_TURN','creation_path_unchanged':True}
    # Independent flock spans the entire local observer subprocess. Losing the
    # scheduler does not authorize a second worker while the first survives.
    with (q.root/'dispatcher.lock').open('a+') as guard:
        try:fcntl.flock(guard,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return {'state':'DISPATCHER_BUSY'}
        q.recover_expired()
        from ares_campaign_v3 import landing_retry_policy as finite
        finite.maintain(q)
        pending=q.db.execute("SELECT 1 FROM messages WHERE state IN ('PREPARED','INTENT')").fetchone()
        waiting=q.db.execute("SELECT 1 FROM jobs WHERE state IN ('WAITING_CREATION_REPLY','OBSERVED')").fetchone()
        if pending or waiting:
            # Do not even resolve the bot token when there is no notification.
            try:flush(q,Discord())
            except Exception as e:
                with q.tx():q.event(None,'notification_transport_deferred',{'reason':str(e)[:120]})
        due=q.db.execute("SELECT 1 FROM jobs j JOIN links l ON l.job=j.key WHERE j.state='READY' AND l.state IN ('READY','WAIT_RETRY') AND l.due<=?",(q.now(),)).fetchone()
        recovery=q.db.execute("SELECT 1 FROM jobs WHERE state IN ('NEEDS_RECONCILIATION','ATTENTION') AND (lease_until IS NULL OR lease_until<=?)",(q.now(),)).fetchone()
        if not due and not recovery:return {'state':'IDLE'}
        check=subprocess.run([sys.executable,str(BASE/'scripts/mgs-pc1-computer-use-lock.py'),'status'],capture_output=True,text=True,timeout=20)
        if check.returncode:return {'state':'WAITING_PC1'}
        lock=json.loads(check.stdout)
        if lock.get('locked') and not orphan_observer_lease(q,lock):return {'state':'WAITING_PC1'}
        owner='landing-observer-'+uuid.uuid4().hex
        j=q.claim_recovery(owner) or q.claim(owner)
        if not j:return {'state':'IDLE'}
        repairing=j['state']=='RECONCILING'
        j['defer_c121_until_others']=q.target_waits_for_others(j['key'])
        idx=next(x['idx'] for x in j['links'] if x['state'] in ({'OPEN_INTENT','ATTENTION','READY','WAIT_RETRY'} if repairing else {'READY','WAIT_RETRY'}) and (repairing or x['due']<=q.now()))
        j['final_retry']=bool(finite.policy() and finite.final_start(q,j['key'],idx))
        directory=q.root/'runs'/owner;directory.mkdir(parents=True,mode=0o700)
        if repairing:prepare_recovery_proof(q,j,idx,directory)
        prompt=directory/'input.txt';prompt.write_text(worker_prompt(j['key'],owner,idx,j));os.chmod(prompt,0o600)
        env=dict(os.environ)
        for name in ('HERMES_SESSION_ID','HERMES_KANBAN_TASK','HERMES_KANBAN_BOARD'):
            env.pop(name,None)
        env['HERMES_HOME']='/root/.hermes/profiles/ares'
        env['HERMES_CUA_DRIVER_CMD']=str(BASE/'scripts/mgs-pc1-cua-driver-ssh.sh')
        policy=json.loads((BASE/'data/ares/meta-ads/policies/direct-traffic-landing-followup.json').read_text())
        if policy.get('provider')!='openai-codex':raise ValueError('approved OAuth worker provider unavailable')
        executable=shutil.which('hermes')
        with (directory/'worker.log').open('w') as log:
            try:
                if not executable:raise RuntimeError('Hermes CLI unavailable')
                completed=subprocess.run([executable,'-p','ares','chat','--query-file',str(prompt),
                    '--provider',policy['provider'],'--model',policy['model'],
                    '--source','tool','--max-turns','80','--run-budget','480','--oneshot','-Q','--pass-session-id'],
                    env=env,cwd=BASE,stdout=log,stderr=subprocess.STDOUT,timeout=540)
                rc=completed.returncode
            except Exception as e:
                log.write('worker_terminated '+type(e).__name__+'\n');rc=-1
        j=q.job(j['key'])
        if j['state'] in {'RUNNING','RECONCILING'}:
            with q.tx():q.db.execute('UPDATE jobs SET lease_until=? WHERE key=?',(q.now()-1,j['key']))
            q.recover_expired()
        try:flush(q,Discord())
        except Exception as e:
            with q.tx():q.event(j['key'],'notification_transport_deferred',{'reason':str(e)[:120]})
        return {'state':q.job(j['key'])['state'],'worker_returncode':rc}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=ROOT)
    s=p.add_subparsers(dest='command',required=True)
    a=s.add_parser('stage');a.add_argument('--input',type=Path,required=True)
    a=s.add_parser('publish-creation');a.add_argument('--key',required=True);a.add_argument('--message-file',type=Path,required=True)
    a=s.add_parser('show');a.add_argument('--key',required=True)
    s.add_parser('status');s.add_parser('tick');s.add_parser('intake');s.add_parser('activate-intake')
    a=s.add_parser('reconcile');a.add_argument('--key',required=True);a.add_argument('--index',type=int,required=True)
    a.add_argument('--pc1-session-id',required=True);evidence_arguments(a)
    a.add_argument('--resume',action='store_true',help='Resume technical failure only after verified closure, never PASS')
    a=s.add_parser('need-action');a.add_argument('--key',required=True);a.add_argument('--owner',required=True)
    a.add_argument('--pc1-session-id',required=True);evidence_arguments(a)
    for command in ('begin','defer','result'):
        a=s.add_parser(command);a.add_argument('--key',required=True);a.add_argument('--owner',required=True)
        if command!='defer':
            a.add_argument('--index',type=int,required=True)
            a.add_argument('--pc1-session-id',required=True)
        if command=='result':
            a.add_argument('--result',choices=['PASS','NO_AD','ERROR'],required=True)
            evidence_arguments(a)
            a.add_argument('--use-captured-samples',action='store_true')
            a.add_argument('--use-captured-closure',action='store_true')
            a.add_argument('--frames-reviewed',action='store_true',help='Explicit agent confirmation: every captured sample shows ad visible and tab active')
            a.add_argument('--recovered',action='store_true',help='Validate saved proof of the last real attempt without another visit')
    args=p.parse_args();q=Queue(args.root)
    if args.command in {'stage','publish-creation'}:
        return {'state':'RETIRED_CREATION_ROUTE_UNCHANGED','side_effect':'none'}
    if args.command in {'tick','intake','activate-intake'}:
        policy=json.loads((BASE/'data/ares/meta-ads/policies/direct-traffic-landing-followup.json').read_text())
        if policy.get('status')!='ACTIVE_FOR_NEW_REQUESTS' or policy.get('approval_message_id')!='1559951763019145247':
            return {'state':'POLICY_DISABLED','side_effect':'none'}
    if args.command=='stage':return {'key':q.stage(json.loads(args.input.read_text())),'state':'WAITING_CREATION_REPLY'}
    if args.command=='publish-creation':return publish_creation(q,args.key,args.message_file.read_text().strip(),Discord())
    if args.command=='show':return q.job(args.key)
    if args.command=='status':return {'jobs':[dict(x) for x in q.db.execute('SELECT state,count(*) AS count FROM jobs GROUP BY state')], 'pending_notifications':q.db.execute("SELECT count(*) FROM messages WHERE state IN ('PREPARED','INTENT')").fetchone()[0]}
    if args.command=='tick':return tick(q)
    if args.command=='activate-intake':return {'activation_epoch':Intake(q).activate(),'backfill':False}
    if args.command=='intake':
        with (q.root/'intake.lock').open('a+') as guard:
            try:fcntl.flock(guard,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:return {'state':'INTAKE_BUSY'}
            result=Intake(q).tick()
            try:result['progress_reporting']=report_progress(q,Discord)
            except Exception as e:
                with q.tx():q.event(None,'progress_delivery_deferred',{'reason':type(e).__name__,'retry_owner':'ares'})
            return result
    if args.command in {'begin','result','reconcile','need-action'}:require_pc1_lease(args.pc1_session_id)
    if args.command=='need-action':
        q.request_human(args.key,args.owner,load_evidence(args))
        return {'state':q.job(args.key)['state']}
    if args.command=='reconcile':
        q.reconcile(args.key,args.index,load_evidence(args),resume=args.resume)
        job=q.job(args.key)
        return {'state':job['state'],'link_state':job['links'][args.index]['state'],'resumed':job['links'][args.index]['state']=='WAIT_RETRY','observation_success':False}
    if args.command=='begin':q.begin(args.key,args.owner,args.index)
    elif args.command=='defer':q.deferred(args.key,args.owner)
    elif args.command=='result':
        evidence=load_evidence(args)
        if args.use_captured_closure:
            captured=json.loads((q.root/'runs'/args.owner/'capture-series.json').read_text())
            closure=captured.get('closure') or {}
            if closure.get('state')!='CLOSED_NOT_PASS':raise ValueError('verified exact owned-window closure required')
            for field in ('new_tab_identity','tab_closed_verified','other_tabs_preserved','closed_screenshot'):
                evidence[field]=closure[field]
        if args.use_captured_samples:
            captured=json.loads((q.root/'runs'/args.owner/'capture-series.json').read_text())
            if captured.get('state')!='CAPTURED_NOT_PASS' or not args.frames_reviewed or evidence.get('network_ad_confirmed') is not True:
                raise ValueError('cadence plus explicit review of ad visibility and active tab required')
            evidence['samples']=[{**x,'ad_visible':True,'tab_active':True} for x in captured['samples']]
        q.result(args.key,args.owner,args.index,args.result,evidence,recovered=args.recovered)
    return {'state':q.job(args.key)['state']}


if __name__=='__main__':
    try:print(json.dumps(main(),ensure_ascii=False))
    except Exception as e:
        # This CLI is local; no credentials, raw API payloads or stack traces.
        print(json.dumps({'state':'ERROR','reason':str(e)[:200]},ensure_ascii=False));sys.exit(1)

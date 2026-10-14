#!/usr/bin/env python3
"""Post-response landing follow-up control plane. All diagnostics stay local."""
from __future__ import annotations
import argparse
import fcntl
import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path
from ares_campaign_v3.landing_followup import Queue, Discord, ROOT, BASE, publish_creation, worker_prompt
from ares_campaign_v3.landing_intake import Intake, native_busy


def require_pc1_lease(session_id):
    if not session_id or session_id!=os.environ.get('HERMES_SESSION_ID'):
        raise ValueError('real current observer session ID required')
    r=subprocess.run([sys.executable,str(BASE/'scripts/mgs-pc1-computer-use-lock.py'),'status'],capture_output=True,text=True,timeout=20)
    state=json.loads(r.stdout) if r.returncode==0 else {}
    if not state.get('locked') or state.get('agent')!='ares' or state.get('session_id')!=session_id:
        raise ValueError('exclusive physical PC1 lease not held by this observer')


def flush(q,discord):
    for row in q.db.execute("SELECT key FROM messages WHERE state!='VERIFIED' ORDER BY created").fetchall():
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
        out=q.db.execute('SELECT state FROM messages WHERE key=?',(row['key']+':success',)).fetchone()
        if out and out['state']=='VERIFIED':
            with q.tx():
                q.db.execute("UPDATE jobs SET state='COMPLETE' WHERE key=?",(row['key'],))
                q.event(row['key'],'completed',{'landing_observation':True,'gam_registration':'NOT_VERIFIED'})


def tick(q):
    # Existing native turns have absolute priority; this adds nothing to them.
    if native_busy():return {'state':'WAITING_NATIVE_TURN','creation_path_unchanged':True}
    # Independent flock spans the entire local observer subprocess. Losing the
    # scheduler does not authorize a second worker while the first survives.
    with (q.root/'dispatcher.lock').open('a+') as guard:
        try:fcntl.flock(guard,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return {'state':'DISPATCHER_BUSY'}
        q.recover_expired()
        pending=q.db.execute("SELECT 1 FROM messages WHERE state!='VERIFIED'").fetchone()
        waiting=q.db.execute("SELECT 1 FROM jobs WHERE state IN ('WAITING_CREATION_REPLY','OBSERVED')").fetchone()
        if pending or waiting:
            # Do not even resolve the bot token when there is no notification.
            try:flush(q,Discord())
            except Exception as e:
                with q.tx():q.event(None,'notification_transport_deferred',{'reason':str(e)[:120]})
        due=q.db.execute("SELECT 1 FROM jobs j JOIN links l ON l.job=j.key WHERE j.state='READY' AND l.state IN ('READY','WAIT_RETRY') AND l.due<=?",(q.now(),)).fetchone()
        if not due:return {'state':'IDLE'}
        check=subprocess.run([sys.executable,str(BASE/'scripts/mgs-pc1-computer-use-lock.py'),'status'],capture_output=True,text=True,timeout=20)
        if check.returncode or json.loads(check.stdout).get('locked'):return {'state':'WAITING_PC1'}
        owner='landing-observer-'+uuid.uuid4().hex
        j=q.claim(owner)
        if not j:return {'state':'IDLE'}
        idx=next(x['idx'] for x in j['links'] if x['state'] in {'READY','WAIT_RETRY'} and x['due']<=q.now())
        directory=q.root/'runs'/owner;directory.mkdir(parents=True,mode=0o700)
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
                    '--source','tool','--max-turns','40','--run-budget','480','--oneshot','-Q','--pass-session-id'],
                    env=env,cwd=BASE,stdout=log,stderr=subprocess.STDOUT,timeout=540)
                rc=completed.returncode
            except Exception as e:
                log.write('worker_terminated '+type(e).__name__+'\n');rc=-1
        j=q.job(j['key'])
        if j['state']=='RUNNING':
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
    a.add_argument('--pc1-session-id',required=True);a.add_argument('--evidence',type=Path,required=True)
    for command in ('begin','defer','result'):
        a=s.add_parser(command);a.add_argument('--key',required=True);a.add_argument('--owner',required=True)
        if command!='defer':
            a.add_argument('--index',type=int,required=True)
            a.add_argument('--pc1-session-id',required=True)
        if command=='result':
            a.add_argument('--result',choices=['PASS','NO_AD','ERROR'],required=True)
            a.add_argument('--evidence',type=Path,required=True)
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
    if args.command=='status':return {'jobs':[dict(x) for x in q.db.execute('SELECT state,count(*) AS count FROM jobs GROUP BY state')], 'pending_notifications':q.db.execute("SELECT count(*) FROM messages WHERE state!='VERIFIED'").fetchone()[0]}
    if args.command=='tick':return tick(q)
    if args.command=='activate-intake':return {'activation_epoch':Intake(q).activate(),'backfill':False}
    if args.command=='intake':return Intake(q).tick()
    if args.command in {'begin','result','reconcile'}:require_pc1_lease(args.pc1_session_id)
    if args.command=='reconcile':
        q.reconcile(args.key,args.index,json.loads(args.evidence.read_text()))
        return {'state':q.job(args.key)['state'],'observation_success':False}
    if args.command=='begin':q.begin(args.key,args.owner,args.index)
    elif args.command=='defer':q.deferred(args.key,args.owner)
    elif args.command=='result':q.result(args.key,args.owner,args.index,args.result,json.loads(args.evidence.read_text()))
    return {'state':q.job(args.key)['state']}


if __name__=='__main__':
    try:print(json.dumps(main(),ensure_ascii=False))
    except Exception as e:
        # This CLI is local; no credentials, raw API payloads or stack traces.
        print(json.dumps({'state':'ERROR','reason':str(e)[:200]},ensure_ascii=False));sys.exit(1)

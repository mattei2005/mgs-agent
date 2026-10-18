"""Durable post-reply landing observation queue; never a Meta/GAM writer.

The observer is Ares in a bounded local-only CLI run, not an unverified DOM
heuristic. A successful observation requires durable screenshots and measured
visibility, and an acknowledged creation message precedes every PC1 action.
"""
from __future__ import annotations
import contextlib
import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE = Path('/root/mgs-agent')
ROOT = BASE / 'data/ares/meta-ads/landing-followup'
INCIDENT_THREAD = '1559932317861158993'
MIN_VISIBLE_SECONDS = 10
SUCCESS = 'Todas as landing pages deste pedido foram abertas, com anúncios identificados.'
TERMINAL = {'COMPLETE', 'COMPLETE_PAUSED', 'COMPLETE_FUTURE_ACTIVE', 'COMPLETED'}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def identifier(value):
    if not re.fullmatch(r'[0-9]{15,20}', str(value)):
        raise ValueError('exact technical identifier required')
    return str(value)


def scope(url):
    p = urllib.parse.urlsplit(url)
    if p.scheme != 'https' or not p.hostname or p.username or p.password or p.fragment:
        raise ValueError('approved HTTPS URL required')
    if any(k.lower() in {'token', 'access_token', 'password', 'key', 'signature', 'auth'} for k, _ in urllib.parse.parse_qsl(p.query)):
        raise ValueError('credential-bearing URL refused')
    r = subprocess.run([sys.executable, str(BASE/'scripts/mgs-domain-scope.py'), 'check', '--agent', 'ares', url], capture_output=True, timeout=20)
    if r.returncode:
        raise ValueError('domain outside approved operational scope')
    return True


def validate_payload(p, check_scope=scope):
    if p.get('strategy_family') != 'DIRECT_TRAFFIC' or p.get('creation_status') not in TERMINAL:
        raise ValueError('only completed direct-traffic requests; BOT/Messenger excluded')
    for field in ('account_id', 'source_thread_id', 'source_channel_id'):
        identifier(p[field])
    for field in ('request_id', 'operation'):
        if not re.fullmatch(r'[A-Za-z0-9_.-]{1,160}', p.get(field, '')):
            raise ValueError('literal request/operation identifier required')
    if not p.get('campaign_ids') or len(p['campaign_ids']) != len(set(p['campaign_ids'])):
        raise ValueError('exact confirmed campaign IDs required')
    for cid in p['campaign_ids']:
        identifier(cid)
    proof = Path(p['creation_proof'])
    # Scoped local readback files, never arbitrary private profile/credential files.
    allowed = BASE/'data/ares/meta-ads'
    if not proof.is_relative_to(allowed) or not proof.resolve().is_relative_to(allowed.resolve()) or not proof.is_file():
        raise ValueError('canonical campaign readback file required')
    if hashlib.sha256(proof.read_bytes()).hexdigest() != p.get('creation_proof_sha256'):
        raise ValueError('creation readback digest mismatch')
    recorded=json.loads(proof.read_text())
    recorded_request=(recorded.get('request_id') or (recorded.get('request') or {}).get('request_id')
        or (recorded.get('manifest') or {}).get('request_id') or (recorded.get('final') or {}).get('request_id'))
    recorded_status={recorded.get('phase'),recorded.get('status'),recorded.get('stage'),
        (recorded.get('final') or {}).get('status'),(recorded.get('summary') or {}).get('status')}
    if recorded_request!=p['request_id'] or not recorded_status.intersection(TERMINAL):
        raise ValueError('creation proof is not terminal for this exact request')
    manifest=recorded.get('manifest') or {}
    if not manifest and recorded.get('manifest_path'):
        manifest_path=Path(recorded['manifest_path'])
        canonical_manifest_roots=(allowed,Path('/root/.hermes/profiles/ares/work'))
        if not any(manifest_path.resolve().is_relative_to(root.resolve()) for root in canonical_manifest_roots):
            raise ValueError('manifest outside canonical campaign evidence')
        manifest=json.loads(manifest_path.read_text())
    manifest_accounts={str(c['account_id']) for c in manifest.get('campaigns',[])}
    proof_account=recorded.get('account_id') or (recorded.get('summary') or {}).get('account_id')
    accounts=manifest_accounts or ({str(proof_account)} if proof_account else set())
    if accounts!={p['account_id']}:raise ValueError('readback account does not match queue partition')
    recorded_origin=recorded.get('request') or {}
    for field in ('source_channel_id','source_thread_id'):
        if recorded_origin.get(field) and str(recorded_origin[field])!=p[field]:raise ValueError('creation origin does not match queue partition')
    recorded_ids=set(str(x) for x in recorded.get('campaign_ids',[]))
    for field in ('engine_result','activation_result','final','summary'):
        entry=recorded.get(field) or {}
        recorded_ids.update(str(x) for x in entry.get('campaign_ids',[]))
        recorded_ids.update(str(x.get('campaign_id')) for x in entry.get('campaigns',[]))
    for tree in recorded.get('final_readback',[]):recorded_ids.add(str(tree['campaign']['id']))
    if not set(p['campaign_ids']).issubset(recorded_ids):
        raise ValueError('campaign IDs missing from terminal creation evidence')
    links = p.get('links')
    if not isinstance(links, list) or not links:
        raise ValueError('complete campaign/adgroup URL coverage required')
    seen = set()
    for link in links:
        cid = identifier(link['campaign_id'])
        if cid not in p['campaign_ids']:
            raise ValueError('link belongs to another campaign')
        source = link['effective_campaign_url']
        if any(c in urllib.parse.unquote(source) for c in '{}'):
            raise ValueError('unresolved URL macros require real same-ad readback')
        check_scope(source)
        query = urllib.parse.parse_qsl(urllib.parse.urlsplit(source).query, keep_blank_values=True)
        names = [k for k, _ in query]
        if any(names.count(k) != 1 for k in ('utm_campaign', 'utm_adgroup')):
            raise ValueError('unique literal campaign/adgroup parameters required')
        q = dict(query)
        if not re.fullmatch(r'b[0-9]+fb[0-9]+c[0-9]+', q['utm_campaign']) or not re.fullmatch(re.escape(q['utm_campaign'])+r'g[0-9]+', q['utm_adgroup']):
            raise ValueError('literal tracking wrapper invalid')
        # Do not infer a landing from a quiz slug. Mapping may be resolved by the
        # observer from canonical sources AFTER the creation reply, without delay.
        landing = link.get('landing_url')
        if landing:
            check_scope(landing)
            if not link.get('mapping_source') or link.get('destination_kind') != 'LANDING_PAGE':
                raise ValueError('explicit landing mapping evidence required')
            lp = urllib.parse.urlsplit(landing)
            if re.search(r'/(quiz|chat)(/|$)', lp.path, re.I):
                raise ValueError('quiz/chat cannot be the observation destination')
            if lp.query != urllib.parse.urlsplit(source).query:
                raise ValueError('preserve exact query bytes and all approved parameters')
        key = (landing or source, q['utm_campaign'], q['utm_adgroup'])
        if key in seen:
            raise ValueError('deduplicate exact landing/UTM combinations before enqueue')
        seen.add(key)
    if {x['campaign_id'] for x in links} != set(p['campaign_ids']):
        raise ValueError('campaign URL coverage incomplete')
    return p


class Queue:
    def __init__(self, root=ROOT, *, now=time.time):
        self.root = Path(root); self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.now = now
        self.db = sqlite3.connect(self.root/'queue.sqlite3', timeout=30)
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS jobs(key TEXT PRIMARY KEY,payload TEXT NOT NULL,digest TEXT NOT NULL,
            state TEXT NOT NULL,created REAL NOT NULL,reply_id TEXT,owner TEXT,lease_until REAL);
        CREATE TABLE IF NOT EXISTS links(job TEXT NOT NULL,idx INTEGER NOT NULL,state TEXT NOT NULL,
            attempt INTEGER NOT NULL DEFAULT 0,due REAL NOT NULL DEFAULT 0,evidence TEXT,
            PRIMARY KEY(job,idx));
        CREATE TABLE IF NOT EXISTS messages(key TEXT PRIMARY KEY,thread TEXT NOT NULL,content TEXT NOT NULL,
            nonce TEXT NOT NULL,state TEXT NOT NULL,message_id TEXT,created REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS events(seq INTEGER PRIMARY KEY,at REAL NOT NULL,job TEXT,kind TEXT NOT NULL,detail TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS native_intake(id TEXT PRIMARY KEY,updated REAL NOT NULL,state TEXT NOT NULL,detail TEXT,job_key TEXT);
        CREATE TABLE IF NOT EXISTS native_receipts(job_key TEXT PRIMARY KEY,receipt TEXT NOT NULL);
        ''')
        os.chmod(self.root/'queue.sqlite3', 0o600)

    @contextlib.contextmanager
    def tx(self):
        self.db.execute('BEGIN IMMEDIATE')
        try:
            yield
            self.db.commit()
        except BaseException:
            self.db.rollback(); raise

    def event(self, key, kind, detail):
        self.db.execute('INSERT INTO events(at,job,kind,detail) VALUES(?,?,?,?)', (self.now(),key,kind,json.dumps(detail,ensure_ascii=False)))

    def stage(self, payload, check_scope=scope):
        validate_payload(payload,check_scope)
        key = digest([payload['operation'],payload['account_id'],payload['request_id']])
        with self.tx():
            old = self.db.execute('SELECT * FROM jobs WHERE key=?',(key,)).fetchone()
            if old:
                if old['digest'] != digest(payload):
                    raise ValueError('immutable request changed; reconcile, never replay')
                return key
            self.db.execute('INSERT INTO jobs VALUES(?,?,?,?,?,?,?,?)',(key,json.dumps(payload,ensure_ascii=False),digest(payload),'WAITING_CREATION_REPLY',self.now(),None,None,None))
            for idx in range(len(payload['links'])):
                self.db.execute('INSERT INTO links(job,idx,state) VALUES(?,?,?)',(key,idx,'READY'))
            self.event(key,'staged',{'links':len(payload['links']),'meta_writes':0})
        return key

    def job(self,key):
        r=self.db.execute('SELECT * FROM jobs WHERE key=?',(key,)).fetchone()
        if not r: raise ValueError('unknown queue request')
        d=dict(r);d['payload']=json.loads(d['payload']);d['links']=[dict(x) for x in self.db.execute('SELECT * FROM links WHERE job=? ORDER BY idx',(key,))]
        return d

    def acknowledge(self,key,message,bot_id):
        j=self.job(key);p=j['payload']
        if (str(message.get('channel_id')) != p['source_thread_id'] or
            str((message.get('author') or {}).get('id')) != str(bot_id) or not message.get('content')):
            raise ValueError('creation response readback identity mismatch')
        mid=identifier(message['id'])
        with self.tx():
            current=self.job(key)
            if current['reply_id']:
                if current['reply_id'] != mid: raise ValueError('creation acknowledgement cannot change')
                return
            # A dedicated wrapper sends this exact completion content after the
            # creation proof. An arbitrary older bot message cannot arm the queue.
            out=self.db.execute('SELECT * FROM messages WHERE key=?',(key+':creation',)).fetchone()
            if not out or out['state']!='VERIFIED' or out['message_id']!=mid or out['content']!=message['content']:
                raise ValueError('creation completion outbox readback required')
            self.db.execute('UPDATE jobs SET state=?,reply_id=? WHERE key=?',('READY',mid,key))
            self.event(key,'creation_reply_verified',{'message_id':mid,'thread_id':p['source_thread_id']})

    def target_waits_for_others(self,key):
        try:rule=json.loads((BASE/'data/ares/meta-ads/policies/direct-traffic-landing-followup.json').read_text()).get('current_priority') or {}
        except (OSError,ValueError):return False
        if rule.get('mode')!='OTHER_CURRENT_WORK_BEFORE_C121' or rule.get('target_job')!=key:return False
        own=self.db.execute('SELECT state FROM links WHERE job=? AND idx=?',(key,rule['target_index'])).fetchone()
        if not own or own['state']=='PASSED':return False
        for peer in rule.get('cohort_jobs',[]):
            row=self.db.execute('SELECT state FROM jobs WHERE key=?',(peer,)).fetchone()
            # OBSERVED peers cannot become COMPLETE until this same human
            # request's deferred C121 passes, so do not deadlock on its notice.
            if row and row['state'] not in {'COMPLETE','OBSERVED','WAITING_HUMAN'}:return True
        return False

    def claim_recovery(self,owner,ttl=600):
        """Claim repair work, never a second navigation or a second writer."""
        with self.tx():
            if self.db.execute("SELECT 1 FROM jobs WHERE state='WAITING_HUMAN_UNCLOSED'").fetchone():return None
            if self.db.execute("SELECT 1 FROM jobs WHERE state IN ('RUNNING','RECONCILING','REPAIRING') AND lease_until>?",(self.now(),)).fetchone():return None
            self.activate_authorized_return()
            rows=self.db.execute("SELECT * FROM jobs WHERE state IN ('NEEDS_RECONCILIATION','ATTENTION','TECHNICAL_REPAIR') AND (lease_until IS NULL OR lease_until<=?) ORDER BY CASE WHEN state='NEEDS_RECONCILIATION' THEN 0 ELSE 1 END,created,key",(self.now(),)).fetchall()
            # Closed diagnostic work must not repeatedly consume the only
            # desktop lane while due observations are waiting. Uncertain tabs
            # still have absolute recovery priority; no proof means no bypass.
            due=self.db.execute("SELECT 1 FROM jobs j JOIN links l ON l.job=j.key WHERE j.state='READY' AND j.reply_id IS NOT NULL AND l.state IN ('READY','WAIT_RETRY') AND l.due<=?",(self.now(),)).fetchone()
            def already_closed(key):
                outstanding=self.db.execute("SELECT state,evidence FROM links WHERE job=? AND state!='PASSED'",(key,)).fetchall()
                if not outstanding:return False
                for link in outstanding:
                    if link['state']!='ATTENTION':return False
                    try:
                        e=json.loads(link['evidence'] or '{}')
                        if e.get('no_tab_opened') is True:
                            if e.get('browser_inputs_zero_verified') is not True or not e.get('diagnosis'):return False
                        else:validate_closure(e)
                    except (ValueError,KeyError,TypeError,OSError):return False
                return True
            row=next((r for r in rows if r['state']=='NEEDS_RECONCILIATION' or
                (r['state']=='TECHNICAL_REPAIR' and not due) or
                (r['state']!='TECHNICAL_REPAIR' and not self.target_waits_for_others(r['key']) and not (due and already_closed(r['key'])))),None)
            if not row:return None
            key=row['key']
            phase='REPAIRING' if row['state']=='TECHNICAL_REPAIR' else 'RECONCILING'
            self.db.execute("UPDATE jobs SET state=?,owner=?,lease_until=? WHERE key=?",(phase,owner,self.now()+ttl,key))
            detail={'owner':owner,'same_request':True,'automatic_navigation':False}
            if phase=='REPAIRING':detail['idx']=self.db.execute("SELECT idx FROM links WHERE job=? AND state='TECHNICAL_REPAIR' ORDER BY idx LIMIT 1",(key,)).fetchone()['idx']
            self.event(key,'technical_repair_claimed' if phase=='REPAIRING' else 'recovery_claimed',detail)
            return self.job(key)

    def no_ad_count(self,key,idx):
        from . import landing_retry_policy as finite
        if finite.policy():
            final_count=finite.count(self,key,idx)
            if final_count is not None:return final_count
        cutoff=0
        for r in self.db.execute("SELECT seq,detail FROM events WHERE job=? AND kind='priority_retry_cycle_started' ORDER BY seq DESC",(key,)):
            if json.loads(r['detail']).get('idx')==idx:cutoff=r['seq'];break
        attempts=set()
        for r in self.db.execute("SELECT seq,detail FROM events WHERE job=? AND seq>? AND kind IN ('observation_result','reconciled_no_ad')",(key,cutoff)):
            d=json.loads(r['detail'])
            confirmed=d.get('result')=='NO_AD' or (not d.get('result') and d.get('state') in {'WAIT_RETRY','ATTENTION'} and not (d.get('evidence') or {}).get('diagnosis'))
            if d.get('idx')==idx and confirmed:attempts.add(d.get('attempt',('event',r['seq'])))
        return len(attempts)

    def activate_authorized_return(self):
        # Runs only inside the existing claim transaction, after every peer is
        # processed. Historical attempts stay intact; a new cycle needs its
        # own explicit user instruction, not an automatic technical retry.
        try:rule=json.loads((BASE/'data/ares/meta-ads/policies/direct-traffic-landing-followup.json').read_text()).get('current_priority') or {}
        except (OSError,ValueError):return False
        permission=rule.get('authorized_new_observation_cycle') or rule.get('authorized_new_observation_cycle_after_peers') or {}
        generation=permission.get('authority_message_id');key=rule.get('target_job');idx=rule.get('target_index')
        if rule.get('mode') not in {'OTHER_CURRENT_WORK_BEFORE_C121','C121_FIRST_THEN_FIFO'} or permission.get('enabled') is not True or not re.fullmatch(r'[0-9]{15,20}',str(generation or '')) or permission.get('maximum_no_ad_attempts',2)!=2 or not key or self.target_waits_for_others(key):return False
        row=self.db.execute('SELECT * FROM links WHERE job=? AND idx=?',(key,idx)).fetchone();job=self.db.execute('SELECT state FROM jobs WHERE key=?',(key,)).fetchone()
        if not row or not job or row['state']!='ATTENTION' or job['state']!='ATTENTION':return False
        for r in self.db.execute("SELECT detail FROM events WHERE job=? AND kind='priority_retry_cycle_started'",(key,)):
            if json.loads(r['detail']).get('authority_message_id')==generation:return False
        evidence=json.loads(row['evidence'] or '{}')
        try:validate_closure(evidence)
        except (ValueError,KeyError,OSError):return False
        self.event(key,'priority_retry_cycle_started',{'idx':idx,'authority_message_id':generation,'previous_attempt_count_preserved':row['attempt'],'maximum_no_ad_attempts':2,'new_visit_not_yet_started':True})
        self.db.execute("UPDATE links SET state='WAIT_RETRY',due=? WHERE job=? AND idx=?",(self.now()+60,key,idx))
        self.db.execute("UPDATE jobs SET state='READY',owner=NULL,lease_until=NULL WHERE key=?",(key,))
        return True

    def claim(self,owner,ttl=600):
        with self.tx():
            # One active observer globally, regardless of account/channel. Other
            # campaign writers remain independent and are never locked by PC1.
            if self.db.execute("SELECT 1 FROM jobs WHERE state IN ('RUNNING','RECONCILING','REPAIRING','NEEDS_RECONCILIATION','WAITING_HUMAN_UNCLOSED')").fetchone(): return None
            try:priority=json.loads((BASE/'data/ares/meta-ads/policies/direct-traffic-landing-followup.json').read_text()).get('current_priority') or {}
            except (OSError,ValueError):priority={}
            target=priority.get('target_job') if priority.get('mode')=='C121_FIRST_THEN_FIFO' else None
            from .landing_reliability import policy as execution_policy
            fair=bool(execution_policy())
            if fair:
                r=self.db.execute("SELECT j.key FROM jobs j JOIN links l ON l.job=j.key WHERE j.state='READY' AND j.reply_id IS NOT NULL AND l.state IN ('READY','WAIT_RETRY') AND l.due<=? ORDER BY CASE WHEN j.key=? THEN 0 ELSE 1 END,j.created,j.key,l.idx LIMIT 1",(self.now(),target)).fetchone()
            else:r=self.db.execute("SELECT key FROM jobs WHERE state='READY' AND reply_id IS NOT NULL ORDER BY CASE WHEN key=? THEN 0 ELSE 1 END,created,key LIMIT 1",(target,)).fetchone()
            if not r:return None
            key=r['key']
            first=self.db.execute("SELECT * FROM links WHERE job=? AND state IN ('READY','WAIT_RETRY','OPEN_INTENT')"+(' AND due<=?' if fair else '')+" ORDER BY idx LIMIT 1",(key,self.now()) if fair else (key,)).fetchone()
            if not first or first['due']>self.now():return None
            if first['state']=='OPEN_INTENT':raise ValueError('uncertain prior tab requires reconciliation')
            self.db.execute("UPDATE jobs SET state='RUNNING',owner=?,lease_until=? WHERE key=?",(owner,self.now()+ttl,key))
            self.event(key,'claimed',{'owner':owner,'idx':first['idx']})
            return self.job(key)

    def owned(self,key,owner,allow_recovery=False):
        j=self.job(key)
        if j['state'] not in ({'RUNNING','RECONCILING'} if allow_recovery else {'RUNNING'}) or j['owner']!=owner or j['lease_until']<self.now():raise ValueError('observer lease expired or owner mismatch')
        return j

    def begin(self,key,owner,idx):
        with self.tx():
            self.owned(key,owner)
            r=self.db.execute('SELECT * FROM links WHERE job=? AND idx=?',(key,idx)).fetchone()
            from . import landing_retry_policy as finite
            from .landing_reliability import needs_repair
            if needs_repair(self,key,idx):raise ValueError('technical-repair gate: verified repair probe required before another opening')
            if not r or r['state'] not in {'READY','WAIT_RETRY'} or r['due']>self.now() or self.no_ad_count(key,idx)>=finite.limit(self,key,idx):
                raise ValueError('attempt not due; no replay of ambiguous open')
            self.db.execute("UPDATE links SET state='OPEN_INTENT',attempt=attempt+1 WHERE job=? AND idx=?",(key,idx))
            self.event(key,'open_intent',{'idx':idx,'attempt':r['attempt']+1})

    def deferred(self,key,owner):
        with self.tx():
            j=self.job(key)
            if j['state']=='REPAIRING':
                if j['owner']!=owner or j['lease_until']<self.now():raise ValueError('repair owner mismatch')
                probe=self.db.execute("SELECT detail FROM events WHERE job=? AND kind='technical_probe_intent' ORDER BY seq DESC LIMIT 1",(key,)).fetchone()
                if probe:
                    d=json.loads(probe['detail'])
                    if d.get('owner')==owner:
                        proof=json.loads(Path(d['probe_file']).read_text())
                        safe=(proof.get('closure') or {}).get('state')=='CLOSED_NOT_PASS' or proof.get('no_new_window_verified') is True or proof.get('tests_returncode') not in {0,None}
                        if not safe:raise ValueError('technical probe window uncertain; reconcile before defer')
                self.db.execute("UPDATE jobs SET state='TECHNICAL_REPAIR',owner=NULL,lease_until=? WHERE key=?",(self.now()+60,key))
                self.event(key,'technical_repair_deferred',{'owner':owner,'ordinary_opening_blocked':True})
                return
            if j['state']=='RECONCILING':
                if j['owner']!=owner or j['lease_until']<self.now():raise ValueError('recovery owner mismatch')
                self.db.execute("UPDATE jobs SET state='NEEDS_RECONCILIATION',owner=NULL,lease_until=? WHERE key=?",(self.now()+60,key))
                self.event(key,'recovery_deferred',{'owner':owner,'retry_after_seconds':60,'recovery_owner':'ares'})
                return
            self.owned(key,owner)
            if self.db.execute("SELECT 1 FROM links WHERE job=? AND state='OPEN_INTENT'",(key,)).fetchone():
                raise ValueError('cannot defer an uncertain tab; reconcile or report ERROR')
            self.db.execute("UPDATE jobs SET state='READY',owner=NULL,lease_until=NULL WHERE key=?",(key,))

    def result(self,key,owner,idx,result,evidence,recovered=False):
        if result not in {'PASS','NO_AD','ERROR'}:raise ValueError('unknown result')
        if recovered and result not in {'PASS','NO_AD'}:raise ValueError('recovered result requires actual PASS or NO_AD evidence')
        j=self.owned(key,owner,allow_recovery=recovered);link=j['payload']['links'][idx]
        if result=='PASS': validate_observation(evidence,link)
        elif result=='NO_AD':
            validate_closure(evidence)
            from .landing_reliability import policy as execution_policy
            if evidence.get('observation_mode')=='LEAN_NORMAL_NEW_TAB':
                from .landing_lean import validate_lean_observation
                validate_lean_observation(evidence,link,negative=True)
            elif execution_policy():
                if evidence.get('network_ad_confirmed') is not False or not evidence.get('visual_review'):
                    raise ValueError('NO_AD requires actual negative visual review; technical capture failure is ERROR')
                observed=file_evidence(evidence['observation_screenshot'])['captured_at']
                opened=[x['at'] for x in self.db.execute("SELECT at,detail FROM events WHERE job=? AND kind='open_intent' ORDER BY seq",(key,)) if json.loads(x['detail']).get('idx')==idx]
                if not opened or observed<opened[-1] or file_evidence(evidence['closed_screenshot'])['captured_at']<observed:
                    raise ValueError('NO_AD screenshot must belong to the current opening and precede verified closure')
        else:
            if not evidence.get('diagnosis'):raise ValueError('exact safe diagnosis required')
            if evidence.get('tab_closed_verified') is True:validate_closure(evidence)
        if recovered:
            opened=[json.loads(x['detail'])|{'at':x['at']} for x in self.db.execute("SELECT at,detail FROM events WHERE job=? AND kind='open_intent' ORDER BY seq",(key,)) if json.loads(x['detail']).get('idx')==idx]
            if result=='NO_AD' and (evidence.get('network_ad_confirmed') is not False or not evidence.get('visual_review')):
                raise ValueError('recovered absence requires explicit visual review and actual screenshot')
            if evidence.get('observation_mode')=='LEAN_NORMAL_NEW_TAB':
                if not opened or evidence['opened_at']<opened[-1]['at'] or evidence['closed_at']<evidence['opened_at']:raise ValueError('normal receipt is not from the latest opening')
            else:
                frames=[file_evidence(x['screenshot'])['captured_at'] for x in evidence['samples']] if result=='PASS' else [file_evidence(evidence['observation_screenshot'])['captured_at']]
                if not opened or min(frames)<opened[-1]['at'] or file_evidence(evidence['closed_screenshot'])['captured_at']<max(frames):
                    raise ValueError('recovered proof is not from the latest actual open or lacks later closure')
        with self.tx():
            self.owned(key,owner,allow_recovery=recovered)
            row=self.db.execute('SELECT * FROM links WHERE job=? AND idx=?',(key,idx)).fetchone()
            if row['state']!='OPEN_INTENT':raise ValueError('no matching open intent')
            previous=json.loads(row['evidence']) if row['evidence'] else {}
            if previous.get('new_tab_identity') and previous['new_tab_identity']==evidence.get('new_tab_identity'):
                raise ValueError('a retry must use a different new tab identity')
            # Cache is not durable evidence. Preserve only the reviewed images,
            # with real timestamp/hash, under protected Ares artifacts.
            evidence=preserve_evidence(evidence,key,idx,row['attempt'])
            safe_error=result=='ERROR' and not evidence.get('human_action_required') and (evidence.get('no_tab_opened') is True or evidence.get('tab_closed_verified') is True)
            from . import landing_retry_policy as finite
            from . import landing_reliability as reliability
            finite_enabled=bool(finite.policy())
            retry_no_ad=result=='NO_AD' and self.no_ad_count(key,idx)+1<finite.limit(self,key,idx)
            state='PASSED' if result=='PASS' else ('WAIT_RETRY' if safe_error or retry_no_ad else 'ATTENTION')
            if result=='NO_AD' and finite_enabled and not retry_no_ad:state=finite.exhausted_state(self,key,idx)
            if safe_error and reliability.policy() and reliability.technical_errors(self,key,idx)+1>=int(reliability.policy().get('technical_error_limit',3)):state='TECHNICAL_REPAIR'
            delay=reliability.technical_delay() if safe_error else reliability.no_ad_delay()
            self.db.execute('UPDATE links SET state=?,due=?,evidence=? WHERE job=? AND idx=?',(state,self.now()+delay if state=='WAIT_RETRY' else 0,json.dumps(evidence,ensure_ascii=False),key,idx))
            self.event(key,'observation_result',{'idx':idx,'attempt':row['attempt'],'result':result,'state':state,'evidence':evidence})
            if safe_error:self.event(key,'technical_repair_required' if state=='TECHNICAL_REPAIR' else 'recoverable_retry_scheduled',{'idx':idx,'retry_after_seconds':delay,'recovery_owner':'ares','human_action_required':False,'ordinary_opening_blocked':state=='TECHNICAL_REPAIR'})
            remaining=self.db.execute("SELECT state FROM links WHERE job=?",(key,)).fetchall()
            all_pass=all(x['state']=='PASSED' for x in remaining)
            pending=any(x['state'] in {'READY','WAIT_RETRY','OPEN_INTENT'} for x in remaining)
            status='OBSERVED' if all_pass else ('READY' if pending else 'ATTENTION')
            if result=='ERROR' and not evidence.get('no_tab_opened') and evidence.get('tab_closed_verified') is not True:
                status='NEEDS_RECONCILIATION'
            if evidence.get('human_action_required') is True and isinstance(evidence.get('required_action'),str) and evidence['required_action'].strip():
                status='WAITING_HUMAN_UNCLOSED' if status=='NEEDS_RECONCILIATION' else 'WAITING_HUMAN'
            self.db.execute('UPDATE jobs SET state=?,owner=NULL,lease_until=NULL WHERE key=?',(status,key))
            if (finite_enabled or reliability.policy()) and status not in {'NEEDS_RECONCILIATION','WAITING_HUMAN','WAITING_HUMAN_UNCLOSED'}:
                finite.refresh(self,key)
            if state in {'DEFERRED_NO_AD','REVIEW_REQUIRED'}:
                self.event(key,'finite_no_ad_exhausted',{'idx':idx,'state':state,'new_visit_not_yet_started':False})
            if state=='ATTENTION':
                diagnosis='Anúncio ausente também na segunda tentativa, após o intervalo de 1 minuto.' if result=='NO_AD' else evidence['diagnosis']
                url=link.get('landing_url') or link['effective_campaign_url']
                scope(url)  # fail closed before mentioning any operational target
                self.prepare_problem(key,key+f':incident:{idx}',
                    f"Acompanhamento de landing page — pedido {j['payload']['request_id']} · conta {j['payload']['account_id']}.\n{url}\n{diagnosis}",evidence)
            if all_pass:self.prepare_success_if_complete(key)
            from .landing_followup_reporting import prepare_item
            prepare_item(self,key,idx,result)

    def success_group(self,key):
        own=self.db.execute('SELECT receipt FROM native_receipts WHERE job_key=?',(key,)).fetchone()
        if not own:return [key],True
        obligation=json.loads(own['receipt']).get('native_obligation_id')
        if not obligation:return [key],False
        keys={r['job_key'] for r in self.db.execute('SELECT job_key,receipt FROM native_receipts')
              if json.loads(r['receipt']).get('native_obligation_id')==obligation}
        ordered=[r['key'] for r in self.db.execute('SELECT key FROM jobs ORDER BY created,key') if r['key'] in keys]
        intake=self.db.execute('SELECT state FROM native_intake WHERE id=?',('native:'+obligation,)).fetchone()
        return ordered,bool(intake and intake['state']=='READY')

    def success_key(self,key):
        group,_=self.success_group(key)
        return (group[0] if group else key)+':success'

    def prepare_success_if_complete(self,key):
        # A single human reply can contain several technical clone jobs. Never
        # tell that manager "all pages" after only its first sub-job passed.
        group,enumerated=self.success_group(key)
        if not enumerated or not group:return False
        jobs=[self.job(k) for k in group]
        if len({j['payload']['source_thread_id'] for j in jobs})!=1:return False
        if any(j['state'] not in {'OBSERVED','COMPLETE'} or any(l['state']!='PASSED' for l in j['links']) for j in jobs):return False
        evidence=[json.loads(l['evidence']) if isinstance(l.get('evidence'),str) else (l.get('evidence') or {}) for j in jobs for l in j['links']]
        all_mobile=bool(evidence) and all(e.get('mobile_emulation',{}).get('verified') is True and 20<=float(e.get('observation_seconds',e.get('tab_open_seconds',0)))<=30 for e in evidence)
        all_articles=all_mobile and all(e.get('article_verified') is True and e.get('scroll_visual_changed') is True for e in evidence)
        modern=bool(evidence) and all((e.get('mobile_emulation',{}).get('verified') is True or e.get('desktop_view',{}).get('verified') is True) and e.get('article_verified') is True and e.get('scroll_visual_changed') is True and 20<=float(e.get('observation_seconds',0))<=30 for e in evidence)
        all_desktop=modern and all(e.get('device_mode')=='DESKTOP' for e in evidence)
        content=('Todas as landing pages deste pedido foram abertas em modo desktop e tiveram anúncios identificados, com observação de 20 a 30 segundos após a liberação do artigo e a rolagem.' if all_desktop else 'Todas as landing pages deste pedido foram abertas e tiveram anúncios identificados, com observação de 20 a 30 segundos após a liberação do artigo e a rolagem.' if modern and not all_articles else 'Todas as landing pages deste pedido foram abertas em modo mobile e tiveram anúncios identificados, com observação de 20 a 30 segundos após a liberação do artigo e a rolagem.' if all_articles else ('Todas as landing pages deste pedido foram abertas em modo mobile, com anúncios identificados.' if all_mobile else SUCCESS))
        self.prepare_message(self.success_key(key),jobs[0]['payload']['source_thread_id'],content)
        return True

    def prepare_message(self,key,thread,content):
        identifier(thread)
        if not content or len(content)>1900:raise ValueError('message outside safe content limits')
        nonce=str(int(hashlib.sha256(key.encode()).hexdigest()[:15],16))
        existing=self.db.execute('SELECT * FROM messages WHERE key=?',(key,)).fetchone()
        if existing:
            if existing['thread']!=thread or existing['content']!=content:raise ValueError('immutable notification changed')
            return
        self.db.execute('INSERT INTO messages VALUES(?,?,?,?,?,?,?)',(key,thread,content,nonce,'PREPARED',None,self.now()))

    def request_human(self,key,owner,evidence):
        action=evidence.get('required_action')
        if evidence.get('human_action_required') is not True or not isinstance(action,str) or not action.strip() or not isinstance(evidence.get('diagnosis'),str) or not evidence['diagnosis'].strip():
            raise ValueError('exact indispensable human action and diagnosis required')
        if evidence.get('tab_closed_verified') is True:validate_closure(evidence)
        with self.tx():
            j=self.job(key)
            if j['state'] not in {'RUNNING','RECONCILING','REPAIRING'} or j['owner']!=owner or j['lease_until']<self.now():raise ValueError('active recovery owner required')
            safe=evidence.get('tab_closed_verified') is True or (evidence.get('no_tab_opened') is True and evidence.get('browser_inputs_zero_verified') is True)
            if safe and self.target_waits_for_others(key):
                opened=[l for l in j['links'] if l['state']=='OPEN_INTENT']
                if len(opened)>1:raise ValueError('multiple uncertain tabs require individual reconciliation')
                if opened:
                    l=opened[0];saved=preserve_evidence(evidence,key,l['idx'],l['attempt'])
                    self.db.execute("UPDATE links SET state='ATTENTION',evidence=? WHERE job=? AND idx=?",(json.dumps(saved,ensure_ascii=False),key,l['idx']))
                self.db.execute("UPDATE jobs SET state='ATTENTION',owner=NULL,lease_until=NULL WHERE key=?",(key,))
                self.event(key,'c121_diagnosis_deferred_by_explicit_order',{'required_action':action.strip(),'diagnosis':evidence['diagnosis'],'safe_cleanup_verified':True,'contact_not_sent':True})
                return
            self.db.execute('UPDATE jobs SET state=?,owner=NULL,lease_until=NULL WHERE key=?',('WAITING_HUMAN' if safe else 'WAITING_HUMAN_UNCLOSED',key))
            self.prepare_problem(key,key+':human-action',f"Acompanhamento — pedido {j['payload']['request_id']}.\n{evidence['diagnosis']}",evidence)

    def prepare_problem(self,job,key,content,evidence):
        # Rodolfo: recover within scope, speak here only if HIS action is needed.
        # Expiry, technical errors and missing evidence are not human gates.
        action=evidence.get('required_action')
        if evidence.get('human_action_required') is not True or not isinstance(action,str) or not action.strip():
            self.event(job,'problem_kept_local',{'notification_key':key,'recovery_owner':'ares','human_action_required':False})
            return False
        self.prepare_message(key,INCIDENT_THREAD,content+'\nAção necessária de Rodolfo: '+action.strip())
        self.event(job,'human_action_requested',{'notification_key':key,'required_action':action.strip()})
        return True

    def recover_expired(self):
        with self.tx():
            for j in self.db.execute("SELECT * FROM jobs WHERE state IN ('RUNNING','RECONCILING','REPAIRING') AND lease_until<?",(self.now(),)).fetchall():
                # Never auto-reopen/reclose an uncertain tab. Escalate the exact
                # request here and leave its intent for browser reconciliation.
                self.db.execute("UPDATE jobs SET state='NEEDS_RECONCILIATION',owner=NULL,lease_until=? WHERE key=?",(self.now()+60,j['key']))
                p=json.loads(j['payload'])
                active=self.db.execute("SELECT idx FROM links WHERE job=? AND state='OPEN_INTENT' ORDER BY idx LIMIT 1",(j['key'],)).fetchone()
                selected=active['idx'] if active else 0
                if not active:
                    claim=self.db.execute("SELECT detail FROM events WHERE job=? AND kind IN ('claimed','technical_repair_claimed') ORDER BY seq DESC LIMIT 1",(j['key'],)).fetchone()
                    if claim:selected=json.loads(claim['detail']).get('idx',0) or 0
                affected=p['links'][selected]
                url=affected.get('landing_url') or affected['effective_campaign_url']
                scope(url)
                self.prepare_problem(j['key'],j['key']+':worker-expired',
                    f"Acompanhamento interrompido — pedido {p['request_id']} · conta {p['account_id']}.\n{url}\nA execução não confirmou o fechamento/resultado; preservada para reconciliação, sem repetir navegação ou criação.",{})
                self.event(j['key'],'worker_expired',{'automatic_reopen':False,'idx':selected,'phase':j['state']})

    def reconcile(self,key,idx,evidence,resume=False):
        # Recovery is readback-first, under the same physical PC1 lease. It
        # never promotes an unobserved URL to PASSED or replays an uncertain view.
        if evidence.get('no_tab_opened') is not True:validate_closure(evidence)
        elif evidence.get('browser_inputs_zero_verified') is not True or not evidence.get('diagnosis'):
            raise ValueError('no-tab recovery requires actual session input readback and diagnosis')
        from .landing_reliability import policy as execution_policy,latest_probe_for_cleanup
        if execution_policy() and evidence.get('no_tab_opened') is not True:
            opened=[r['at'] for r in self.db.execute("SELECT at,detail FROM events WHERE job=? AND kind='open_intent' ORDER BY seq",(key,)) if json.loads(r['detail']).get('idx')==idx]
            latest=opened[-1] if opened else 0
            probe_file=latest_probe_for_cleanup(self,key,idx)
            if probe_file:
                probe=json.loads(Path(probe_file).read_text());target=(probe.get('opening') or {}).get('target')
                if target:
                    actual=evidence.get('new_tab_identity');text=json.dumps(actual) if isinstance(actual,dict) else str(actual)
                    if not all(re.search(r'\b'+re.escape(str(target[k]))+r'\b',text) for k in ('pid','window_id')):
                        raise ValueError('closure does not identify the current technical probe window')
                for event in self.db.execute("SELECT at,detail FROM events WHERE job=? AND kind='technical_probe_intent' ORDER BY seq DESC",(key,)):
                    if json.loads(event['detail']).get('idx')==idx:latest=max(latest,event['at']);break
            closed_at=float(evidence['closed_at']) if evidence.get('observation_mode')=='LEAN_NORMAL_NEW_TAB' else file_evidence(evidence['closed_screenshot'])['captured_at']
            if closed_at<latest:
                raise ValueError('closure receipt predates the latest actual opening')
        with self.tx():
            j=self.job(key)
            if j['state'] not in {'NEEDS_RECONCILIATION','RECONCILING','ATTENTION'}:raise ValueError('request is not awaiting reconciliation')
            row=self.db.execute('SELECT * FROM links WHERE job=? AND idx=?',(key,idx)).fetchone()
            if not row or row['state'] not in {'OPEN_INTENT','ATTENTION','READY','WAIT_RETRY','TECHNICAL_REPAIR'}:raise ValueError('exact affected URL required')
            from . import landing_retry_policy as finite
            finite_enabled=bool(finite.policy())
            exhausted=self.no_ad_count(key,idx)>=finite.limit(self,key,idx)
            if resume and exhausted:
                resume=False
                self.event(key,'resume_suppressed_after_two_no_ads',{'idx':idx,'automatic_navigation':False,'continue_other_links_after_verified_closure':True})
            saved=preserve_evidence(evidence,key,idx,row['attempt'])
            from .landing_reliability import technical_delay
            self.db.execute("UPDATE links SET state=?,due=?,evidence=? WHERE job=? AND idx=?",('WAIT_RETRY' if resume else 'ATTENTION',self.now()+technical_delay() if resume else 0,json.dumps(saved,ensure_ascii=False),key,idx))
            pending=self.db.execute("SELECT 1 FROM links WHERE job=? AND state IN ('READY','WAIT_RETRY')",(key,)).fetchone()
            self.db.execute('UPDATE jobs SET state=?,owner=NULL,lease_until=? WHERE key=?',('READY' if pending else 'ATTENTION',None if pending else self.now()+60,key))
            if finite_enabled and self.no_ad_count(key,idx)>0:
                state=finite.exhausted_state(self,key,idx) if exhausted else 'WAIT_RETRY'
                from .landing_reliability import no_ad_delay
                self.db.execute('UPDATE links SET state=?,due=? WHERE job=? AND idx=?',(state,self.now()+no_ad_delay() if state=='WAIT_RETRY' else 0,key,idx))
                finite.refresh(self,key)
            from .landing_reliability import needs_repair,policy as execution_policy
            if execution_policy() and not resume and self.no_ad_count(key,idx)==0:
                self.event(key,'technical_repair_required',{'idx':idx,'reason':'closed technical attempt without a reusable observation result; stop repeated reconciliation','ordinary_opening_blocked':True})
            if needs_repair(self,key,idx):
                self.db.execute("UPDATE links SET state='TECHNICAL_REPAIR',due=0 WHERE job=? AND idx=?",(key,idx))
                finite.refresh(self,key)
            self.event(key,'uncertain_tab_closed_by_readback',{'idx':idx,'observation_success':False,'evidence':saved})


def file_evidence(path):
    p=Path(path)
    if not p.is_relative_to(Path('/root/.hermes/profiles/ares')) or not p.resolve().is_relative_to(Path('/root/.hermes/profiles/ares').resolve()) or not p.is_file():
        raise ValueError('protected real Ares screenshot required')
    if p.suffix.lower() not in {'.png','.jpg','.jpeg','.webp'} or p.stat().st_size<100:
        raise ValueError('image evidence missing')
    return {'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'captured_at':p.stat().st_mtime}


def preserve_evidence(e,key,idx,attempt):
    e=json.loads(json.dumps(e))
    destination=Path('/root/.hermes/profiles/ares/artifacts/landing-followup')/key/str(idx)/str(attempt)
    paths=[]
    for field in ('closed_screenshot','observation_screenshot','current_browser_screenshot','gate_screenshot','article_screenshot'):
        if e.get(field):paths.append((e,field))
    paths.extend((x,'screenshot') for x in e.get('samples',[]))
    if paths:destination.mkdir(parents=True,exist_ok=True,mode=0o700)
    for number,(container,field) in enumerate(paths):
        item=file_evidence(container[field]);original=Path(item['path'])
        target=destination/(f'{number:03d}-'+item['sha256']+original.suffix.lower())
        if not target.exists():shutil.copy2(original,target)
        os.chmod(target,0o600)
        if hashlib.sha256(target.read_bytes()).hexdigest()!=item['sha256']:raise ValueError('durable evidence copy mismatch')
        container[field]=str(target);container[field+'_sha256']=item['sha256']
        container[field+'_captured_at']=item['captured_at']
    return e


def validate_closure(e):
    if e.get('observation_mode')=='LEAN_NORMAL_NEW_TAB':
        from .landing_lean import validate_lean_closure
        return validate_lean_closure(e)
    if e.get('tab_closed_verified') is not True or e.get('other_tabs_preserved') is not True or not e.get('new_tab_identity'):
        raise ValueError('exact new-tab ownership and verified closure required')
    file_evidence(e['closed_screenshot'])


def validate_observation(e,link):
    if e.get('observation_mode')=='LEAN_NORMAL_NEW_TAB':
        from .landing_lean import validate_lean_observation
        return validate_lean_observation(e,link)
    validate_closure(e)
    url=link.get('landing_url') or e.get('resolved_landing_url')
    if not url or e.get('observed_url')!=url or not (link.get('mapping_source') or e.get('mapping_source')):
        raise ValueError('exact evidenced landing mapping required')
    scope(url)
    p=urllib.parse.urlsplit(url)
    if re.search(r'/(quiz|chat)(/|$)',p.path,re.I) or p.query != urllib.parse.urlsplit(link['effective_campaign_url']).query:
        raise ValueError('quiz or mutated tracking refused')
    samples=e.get('samples') or []
    if len(samples)<3 or any(x.get('ad_visible') is not True or x.get('tab_active') is not True for x in samples):
        raise ValueError('actual visible network ad + active tab samples required')
    times=[float(x['monotonic_seconds']) for x in samples]
    if any(b<=a or b-a>10 for a,b in zip(times,times[1:])) or times[-1]-times[0]<MIN_VISIBLE_SECONDS:
        raise ValueError(f'{MIN_VISIBLE_SECONDS} continuous measured seconds with bounded samples required')
    paths=[x['screenshot'] for x in samples]
    if len(set(paths))!=len(paths):raise ValueError('fresh distinct screenshots required')
    actual=[file_evidence(sample['screenshot']) for sample in samples]
    capture_times=[x['captured_at'] for x in actual]
    if capture_times[-1]-capture_times[0]<MIN_VISIBLE_SECONDS or any(b<=a or b-a>12 for a,b in zip(capture_times,capture_times[1:])):
        raise ValueError('real screenshot timestamps do not cover the observation')
    if e.get('network_ad_confirmed') is not True or not e.get('ad_description'):
        raise ValueError('rendered network creative, not empty slot/CTA, required')


class Discord:
    def __init__(self):
        self.token=None
        for raw in Path('/root/.hermes/profiles/ares/.env').read_text().splitlines():
            k,sep,v=raw.partition('=')
            if sep and k.strip()=='DISCORD_BOT_TOKEN':self.token=v.strip().strip('\"').strip("'")
        if not self.token:raise ValueError('Ares notification identity unavailable')
        self.bot_id=str(self.get('/users/@me')['id'])

    def request(self,method,path,body=None):
        assert self.token is not None
        headers={'Authorization':'Bot '+self.token,'User-Agent':'MGS-Ares-Landing-Followup/1.0'}
        data=None
        if body is not None:headers['Content-Type']='application/json';data=json.dumps(body,ensure_ascii=False).encode()
        req=urllib.request.Request('https://discord.com/api/v10'+path,data=data,method=method,headers=headers)
        try:
            with urllib.request.urlopen(req,timeout=20) as r:return json.load(r)
        except urllib.error.HTTPError as e:raise ValueError('Discord transport HTTP '+str(e.code)) from None
        except Exception:raise ValueError('Discord transport unavailable') from None

    def get(self,path):return self.request('GET',path)

    def deliver(self,q,key):
        row=q.db.execute('SELECT * FROM messages WHERE key=?',(key,)).fetchone()
        if not row:raise ValueError('missing durable notification')
        if row['state']=='CANCELLED_BEFORE_SEND':raise ValueError('notification_cancelled_before_send')
        if row['thread']==INCIDENT_THREAD:
            from .landing_followup_reporting import origin_notification_content
            row=dict(row);row['content']=origin_notification_content(q,row,self)
        if row['thread']==INCIDENT_THREAD and row['state']=='PREPARED':
            authorized=any(json.loads(e['detail']).get('notification_key')==key
                for e in q.db.execute("SELECT detail FROM events WHERE kind IN ('human_action_requested','progress_update_authorized','finite_review_report_authorized','completion_notice_authorized')"))
            if not authorized:
                # Fence legacy queued alerts, not ambiguous or delivered posts.
                with q.tx():
                    q.db.execute("UPDATE messages SET state='CANCELLED_BEFORE_SEND' WHERE key=? AND state='PREPARED'",(key,))
                    q.event(None,'problem_kept_local',{'notification_key':key,'recovery_owner':'ares','human_action_required':False})
                raise ValueError('recoverable_problem_kept_local')
        thread=row['thread'];mid=row['message_id']
        if not mid and row['state']=='INTENT':
            # Ambiguous POST: read back by stable nonce before any retry. Never
            # blindly replay a post which may have reached Discord.
            messages=self.get('/channels/'+thread+'/messages?limit=100')
            found=[m for m in messages if str(m.get('nonce'))==row['nonce'] and str((m.get('author') or {}).get('id'))==self.bot_id]
            if len(found)!=1:raise ValueError('notification outcome uncertain; preserve outbox for reconciliation')
            mid=str(found[0]['id'])
        if not mid:
            with q.tx():
                changed=q.db.execute("UPDATE messages SET state='INTENT' WHERE key=? AND state='PREPARED'",(key,)).rowcount
                if changed!=1:raise ValueError('notification_intent_changed_reconcile_before_send')
            body=self.request('POST','/channels/'+thread+'/messages',{'content':row['content'],'allowed_mentions':{'parse':[]},'nonce':row['nonce'],'enforce_nonce':True})
            mid=identifier(body['id'])
        with q.tx():q.db.execute("UPDATE messages SET message_id=? WHERE key=?",(mid,key))
        check=self.get('/channels/'+thread+'/messages/'+mid)
        if str(check.get('channel_id'))!=thread or check.get('content')!=row['content'] or str((check.get('author') or {}).get('id'))!=self.bot_id:
            raise ValueError('notification readback mismatch')
        with q.tx():q.db.execute("UPDATE messages SET state='VERIFIED' WHERE key=?",(key,))
        return check


def publish_creation(q,key,content,discord):
    j=q.job(key)
    origin=discord.get('/channels/'+j['payload']['source_thread_id'])
    if (str(origin.get('id'))!=j['payload']['source_thread_id'] or
        str(origin.get('parent_id') or origin.get('id'))!=j['payload']['source_channel_id']):
        raise ValueError('creation thread/parent readback does not match request partition')
    with q.tx():q.prepare_message(key+':creation',j['payload']['source_thread_id'],content)
    message=discord.deliver(q,key+':creation')
    q.acknowledge(key,message,discord.bot_id)
    return {'state':q.job(key)['state'],'message_id':message['id']}


def worker_prompt(key,owner,idx,job):
    from .landing_lean import lean_enabled
    if lean_enabled() and job.get('state')=='RUNNING' and job.get('batch_scope_path'):
        context={'queue_key':key,'owner':owner,'batch_scope_path':job['batch_scope_path'],'batch_jobs':job['batch_jobs'],'prepared_batch':job['prepared_batch']}
        return ('LOTE CONTINUO DO OBSERVADOR PC1. Carregue landing-followup-operations e computer-use. '
            'Preparar TODOS os destinos reais antes de qualquer input no PC1; preservar queries, acrescentar somente nocache aprovado, aplicar gate MGS. '
            'O scope congelado e os pedidos sao imutaveis. Reutilizar prepared_batch se completo; se faltar mapeamento, resolver por fonte canonica/read-only e salvar UM manifest {items:[{job,index,url,mapping_source,destination_count:1}]} com exatamente TODOS os pendentes. Nao inventar slug nem omitir destinos A/B distintos; evidencia incompleta deve ser resolvida antes de navegar. '
            'Usar o Python real do Hermes para scripts/ares-direct-traffic-batch-observe.py --scope '+job['batch_scope_path']+' --owner '+owner+' --pc1-session-id "$HERMES_SESSION_ID" [--manifest <mapa-completo>]. '
            'Um unico executor serial percorre os links, sem outro turno de modelo por URL e sem serie screenshots/galeria. ABA NOVA NORMAL MOBILE por tentativa; preset nativo verificado; CTA editorial autorizado uma vez, aguardar rewarded/liberacao do artigo, confirmar rolagem, observar20-30s sem contar espera do rewarded, capturar frame final,fechar/verificar e revisar. Nunca clicar no criativo do anuncio ou link do anunciante. '
            'O core e compartilhado com o CLI individual; backend so libera ao final do lote. Durante as visitas nao programar, investigar ou redigir. '
            'Executar o comando com stdout/stderr locais. Se usar terminal em background, notify=false; acompanhar via process_manage ate terminar, sem publicar notificacao crua e sem encerrar com processo vivo. '
            'Ausencias seguem3iniciais+1final; ao terminar a rodada, esperar60s sem ocupar PC1 e fazer1recuperacao automatica dos ainda sem anuncio; depois REVIEW_REQUIRED sem loop infinito. O prazo e o historico sao persistidos pelo controlador. '
            'MAPPING_REQUIRED nunca abriu pagina: completar o mapa antes de repetir. BATCH_TECHNICAL_DIAGNOSIS exige reparar causa local apos fechamento, sem repetir caminho inalterado; janela incerta deve ser reconciliada antes de novo input. '
            'Mensagens por item sao enfileiradas no resultado e entregues pelo consumidor independente com GET; nao aguardar Discord entre URLs. Nao postar externamente nesta sessao. Nenhum write de campanha/Meta/WP/GAM/Router/financeiro, restart ou configuracao compartilhada.\n'+json.dumps(context,ensure_ascii=False))
    if lean_enabled() and job.get('state')=='RUNNING':
        links=[]
        for item in job['links']:
            prior=json.loads(item['evidence']) if isinstance(item.get('evidence'),str) else (item.get('evidence') or {})
            links.append({**{k:item[k] for k in ['idx','state','attempt','due'] if k in item},'previous_new_tab_identity':prior.get('new_tab_identity')})
        context={'queue_key':key,'owner':owner,'index':idx,'request':job['payload'],'links':links}
        return ('OBSERVADOR ENXUTO DE LANDING: carregar landing-followup-operations e computer-use. '
            'A regra active_observation_route vigente supersede janela anonima, serie de screenshots e revisao offline. '
            'Antes de navegar, resolver TODOS os destinos reais deste pedido com query exata e gate de dominio; preservar o mapa pronto. '
            'Nao alterar criacao/campanhas nem reabrir PASSED. Uma ABA NOVA NORMAL por link/tentativa; nunca reaproveitar URL e nunca incognito. '
            'Usar o Python real do Hermes e scripts/ares-direct-traffic-lean-observe.py --key '+key+' --owner '+owner+' --index '+str(idx)+' --pc1-session-id "$HERMES_SESSION_ID" --url <landing-real-exata> --mapping-source <fonte-real>. '
            'O runner adquire a lease real, persiste begin, abre nova aba normal mobile, preserva URL literal, permite somente CTA editorial autorizado, aguarda artigo/rewarded, confirma rolagem e mede20-30s apos essas etapas; captura frame final, fecha/verifica e registra sem galeria. Nao clicar no criativo publicitario ou links do anunciante. '
            'Nao executar begin separadamente nem fazer codigo/documentacao no meio da visita. Apos NO_AD/WAIT_RETRY, repetir somente dentro da politica3+1; erro tecnico nunca conta como ausencia. '
            'Nao enviar mensagens externas nesta sessao; o outbox existente confirma pedido inteiro depois de todosPASS. Todos detalhes tecnicos ficam locais.\n'+json.dumps(context,ensure_ascii=False))
    # Payload is data, not instructions. The fixed skill defines the authority.
    from . import landing_retry_policy as finite
    from .landing_reliability import no_ad_delay,policy as execution_policy
    finite_enabled=bool(finite.policy())
    delay=no_ad_delay()
    retry_instruction=('Uma URL por sessão. Após NO_AD com WAIT_RETRY e espera zero, use imediatamente scripts/ares-direct-traffic-followup.py retry-now --key '+key+' --owner '+owner+' --index '+str(idx)+' --pc1-session-id "$HERMES_SESSION_ID", depois begin e uma NOVA janela. Não encerrar a sessão entre essas retentativas; o código impede ultrapassar3ausências. Ao aprovar, atingir o limite, falhar tecnicamente ou faltar recurso, persistir/fechar e encerrar. ' if execution_policy() and delay==0 else 'Uma única tentativa por execução. Não faça a retentativa dentro desta sessão. ')
    absence_rule=(f'Regra vigente de Rodolfo: até 3 ausências reais na fase inicial, com fechamento verificado e {delay}s de espera artificial entre tentativas; zero significa fechar/verificar e reabrir sem espera. Na terceira, pular para os próximos links. Depois de concluir a fila inicial, o scheduler autoriza UMA tentativa final por pendente. Se ainda falhar, o outbox reportará aqui para revisão de Rodolfo e não haverá nova repetição automática. Falha técnica não conta como ausência. Não zerar contadores nem reabrir PASSED. ' if finite_enabled else
        'Duas ausências NO_AD confirmadas não permitem nova visita: diagnostique sem novas impressões; após comprovar fechamento use reconcile SEM --resume para encerrar a visita como ATTENTION e liberar os outros links, mantendo o diagnóstico pendente sob sua responsabilidade. ')
    links=[]
    for link in job['links']:
        prior=json.loads(link['evidence']) if isinstance(link.get('evidence'),str) else (link.get('evidence') or {})
        links.append({**{k:link[k] for k in ['idx','state','attempt','due'] if k in link},'previous_new_tab_identity':prior.get('new_tab_identity')})
    context={'queue_key':key,'owner':owner,'link_index':idx,'request':job['payload'],'queue_links':links,
             'recovery_evidence_path':job.get('recovery_evidence_path'),'recovery_result':job.get('recovery_result'),'confirmed_no_ads':job.get('confirmed_no_ads'),
             'defer_c121_until_others':job.get('defer_c121_until_others',False),
             'no_ad_limit_this_phase':1 if job.get('final_retry') else 3 if finite_enabled else 2,
             'final_retry':job.get('final_retry',False)}
    context['stagnation_diagnosis']=job.get('stagnation_diagnosis',[])
    context['recent_technical_errors']=job.get('recent_technical_errors',[])
    context['technical_probe_evidence_path']=job.get('technical_probe_evidence_path')
    context['repeated_technical_failure']=len(context['recent_technical_errors'])>=3 and all(x.get('idx')==idx for x in context['recent_technical_errors'])
    if context['stagnation_diagnosis'] or context['repeated_technical_failure']:
        absence_rule=('DIAGNÓSTICO OBRIGATÓRIO POR ESTAGNAÇÃO: houve mais de duas mensagens equivalentes sem progresso OU três erros técnicos consecutivos do mesmo alvo. Leia os erros recentes e o estado real; não repita o helper/caminho técnico que já falhou sem diagnosticar e reparar sua causa ou usar fallback nativo permitido e comprovado. Silenciar status não resolve a pendência. Preserve request, provas, abas alheias e os limites críticos; nunca restart nem writes Meta/GAM/WordPress/Router/financeiro. Se a última abertura real já funcionou, aproveite a prova da mesma tentativa em vez de navegar novamente; só resultado validado demonstra retomada. '+absence_rule)
    if job.get('state')=='REPAIRING':
        if lean_enabled():
            return ('REPARO DO OBSERVADOR ENXUTO. Nao abrir URL de landing nem chamar begin. Carregar landing-followup-operations e computer-use. '
                'Diagnosticar e corrigir somente a camada local, apos conferir a prova da tentativa exata. '
                'Sob lease com HERMES_SESSION_ID real, usar o Python do Hermes para scripts/ares-direct-traffic-repair.py --key '+key+' --owner '+owner+' --index '+str(idx)+' --pc1-session-id "$HERMES_SESSION_ID" --repair-note <causa-e-correcao-reais>. '
                'Na rota ativa esse reparador usa SOMENTE janela vazia NORMAL e readbacks nativos de fechamento/preservacao, sem Incognito, sem serie de screenshots e sem galeria ou anuncio. '
                'Nao trocar estado para contornar o recibo. Probe incerto exige cleanup exato; nao repetir Close nem abrir outro alvo. Provas e stdout locais, sem mensagens de erro ao operador. Nenhum restart ou write de campanha/WP/GAM/Router/financeiro.\n'+json.dumps(context,ensure_ascii=False))
        return ('REPARO TÉCNICO OBRIGATÓRIO DO OBSERVADOR PC1. Não abrir URL de landing nem chamar begin: o limite técnico foi atingido e a trava é do código. '
            'Carregue landing-followup-operations e computer-use. Diagnostique os erros recentes e corrija somente a camada local do observador, sem alterar qualquer fluxo de campanha, driver compartilhado, permissões, credenciais ou reiniciar processos. '
            'Depois do reparo, adquira a lease PC1 com HERMES_SESSION_ID REAL e execute pelo Python do Hermes scripts/ares-direct-traffic-repair.py --key '+key+' --owner '+owner+' --index '+str(idx)+' --pc1-session-id "$HERMES_SESSION_ID" --repair-note <diagnostico-e-correcao-reais>. '
            'Esse runner executa testes e uma prova real de janela privada vazia, captura de10s e fechamento, sem URL/impressao. Só recibo real aprovado libera a próxima observação; não editar estados do banco para contornar. '
            'Se o probe falhar, ler a prova parcial e reconciliar o alvo exato antes de outro input. Se PC1 ocupado, defer; guardar falha/cleanup e liberar lease em finally. '
            'Sem necessidade humana presumida para falha técnica; responsabilidade de Ares até correção ou escalada indispensável comprovada.\n'+json.dumps(context,ensure_ascii=False))
    if job.get('state')=='RECONCILING':
        if lean_enabled():
            return ('RECUPERACAO DA ROTA NORMAL, MESMO REQUEST. Nao abrir URL nem repetir input incerto. Carregar landing-followup-operations e computer-use. '
                'Conferir recibo e ultima abertura exatos por job/idx/attempt; nunca selecionar o ultimo arquivo de outro item. '
                'Se recovery_evidence_path e recovery_result foram fornecidos, a prova normal compacta foi validada: sob lease real, registrar result --key '+key+' --owner '+owner+' --index '+str(idx)+' --pc1-session-id "$HERMES_SESSION_ID" --result <recovery_result> --evidence <recovery_evidence_path> --recovered, sem navegar novamente. '
                'Caso contrario, ler normal-open.json/lean-result.json da tentativa atual e fazer somente readback/cleanup do alvo proprio. Usar recibo nativo normal com identidades antes/depois e tempos; nao exigir screenshot/galeria e nao fechar janela ja ausente. '
                'Se technical_probe_evidence_path existe, reconciliar esse probe, nao uma landing antiga. Nova aba nao pode ser aberta enquanto houver fechamento incerto. '
                'Sem input, comprovar zero inputs pela sessao; nunca inventar no_tab_opened. Persistir reconcile/defer na CLI existente e liberar lease so apos fechamento seguro. '
                'Ausencia nao vira PASS; tecnica nao conta como NO_AD. Nenhuma mensagem externa nem restart ou write de campanha/WP/GAM/Router/financeiro.\n'+json.dumps(context,ensure_ascii=False))
        return ('RECUPERAÇÃO AUTÔNOMA, MESMO REQUEST. Não abrir URL, não chamar begin nem repetir input incerto. '
            'Carregue landing-followup-operations e sua referência runtime-and-recovery.md, além de computer-use. '
            'Se defer_c121_until_others=true, Rodolfo mandou fazer todos os demais antes da C121: realizar SOMENTE o readback/fechamento indispensável de eventual aba incerta, reconcile SEM --resume, liberar a lease e encerrar. Não diagnosticar nem revisitar C121 agora; ela volta após a rodada dos demais. '
            'Se recovery_evidence_path foi fornecido, é o arquivo já validado da tentativa exata: confira as imagens e o fechamento real atual, sem reextrair todo o histórico. Registre NO_AD --recovered por esse arquivo; se o resultado já está persistido, reconcilie só o fechamento e deixe o scheduler aplicar o limite vigente. Depois libere a lease e encerre. Não produzir um novo JSON narrativo. '
            'Sob lease PC1 com ID REAL da sessão, confira a sessão anterior do mesmo job via events claimed/recovery_claimed '
            'e state.db read-only. Observe o browser real e reconcilie somente abas comprovadamente pertencentes à tentativa; '
            'preserve as demais. Evidência de tentativa mais antiga não comprova fechamento da última. '
            'Se já existir evidência COMPLETA e válida da última tentativa (URL, anúncio, foco, >=10s, amostras reais e fechamento posterior), '
            'registre sem nova visita: result --key '+key+' --owner '+owner+' --index '+str(idx)+' --pc1-session-id "$HERMES_SESSION_ID" --result PASS --evidence <arquivo> --recovered. O validador exige vínculo temporal à última abertura; não preencher lacunas nem declarar visibilidade não provada. '
            'Se --recovered for aceito, libere a lease e encerre, sem reconcile adicional. SOMENTE se não houver prova completa aproveitável, depois do readback/fechamento seguro salve evidência real e execute '
            'scripts/ares-direct-traffic-followup.py reconcile --key '+key+' --index '+str(idx)+' --pc1-session-id "$HERMES_SESSION_ID" --evidence <arquivo> --resume. '
            'Quando nenhuma aba foi aberta, exija evidência da sessão anterior: no_tab_opened=true, browser_inputs_zero_verified=true e diagnosis; não invente identidade/fechamento. '
            +absence_rule+
            'Prova completa de ausência da última tentativa pode ser persistida com result --result NO_AD --recovered, sem outra visita. Não perder observações apenas porque o write do JSON original não terminou; reconstruir somente fatos verificados nos outputs/imagens reais. '
            'Somente se a solução exigir ação indispensável de Rodolfo, use need-action --key '+key+' --owner '+owner+' --pc1-session-id "$HERMES_SESSION_ID" --evidence <JSON com human_action_required=true, required_action concreta e diagnosis>. '
            'Se PC1 ocupado/indisponível, defer --key '+key+' --owner '+owner+' e libere lease. '
            'Não encerrar deixando apenas texto: persistir reconcile/defer e liberar lease em finally. '
            'Não há intervenção de Rodolfo para timeout, screenshot/cadência ou erro técnico recuperável; não enviar mensagens externas. '
            'Nenhum write Meta/GAM/WordPress/Router/financeiro, restart, alteração de campanha, billing ou credencial. '
            'Retornar após a reconciliação; a fila reexecutará a observação separadamente.\n'
            +json.dumps(context,ensure_ascii=False))
    return ('Execute somente a observação de landing do pedido já concluído abaixo. '
        'Carregue landing-followup-operations e references/runtime-and-recovery.md dessa skill. '
        'Nenhum write Meta, GAM, Router, WordPress, budget, credencial ou configuração. '
        'Nenhuma mensagem ao gestor: o outbox do runner publica somente após provas. '
        'Falhas técnicas recuperáveis são locais: resolver no mesmo request, sem pedir nova aprovação nem alertar Rodolfo; '
        'somente human_action_required=true com required_action concreta autoriza aviso. '
        'Reserve as últimas chamadas para fechar/verificar, persistir result (inclusive ERROR) e liberar a lease; '
        'Prefira result --evidence-json com metadados mínimos, sem criar um grande arquivo narrativo. Para PASS, use --use-captured-samples --frames-reviewed apenas depois de revisar todas as imagens; o CLI mescla os frames reais. Para NO_AD, exigir imagem observation_screenshot da abertura atual, visual_review explícita da ausência, network_ad_confirmed=false e fechamento posterior comprovado. Falha de captura, página não verificada ou prova incerta é ERROR, nunca NO_AD. '
        'Não reler a implementação de scripts como etapa de cada URL: os comandos e o esquema mínimo estão na skill; investigar código somente para corrigir falha concreta, após fechamento seguro. '
        'não encerrar com um texto dizendo que faltou registrar o resultado. '
        'LATÊNCIA: os 10 segundos são a janela mínima de anúncio visível, não um timer por chamada. Agrupe leituras independentes e ações com capture_after; evite recapturas/list_windows redundantes sem dúvida concreta. '
        'ABERTURA MECÂNICA: após a lease e begin, use o Python do Hermes para scripts/ares-direct-traffic-ui.py --key '+key+' --owner '+owner+' --index '+str(idx)+' --pc1-session-id "$HERMES_SESSION_ID" --url <landing real exata> --mapping-source <fonte real>. O helper faz os inputs e readbacks nativos em uma chamada, salva desktop-open.json e NÃO aprova anúncio. Não criar aba-guarda extra nem repetir o helper depois de erro: ler a prova parcial e reconciliar o mesmo alvo. '
        'Após revisar a janela nova exclusiva e confirmar anúncio/foco, acrescente --close-owned-window --exclusive-window-reviewed ao coletor abaixo. Ele salva a série antes de fechar, usa UM clique no Close nativo da janela técnica (nunca do browser original), verifica preservação e retorna closure. Não fechar novamente se closure.state=CLOSED_NOT_PASS. Depois das revisões reais, result --use-captured-closure --use-captured-samples --frames-reviewed incorpora as provas. Se a abertura foi manual ou não há desktop-open.json válido, não usar fechamento automático. '
        'Ao obter CAPTURED_NOT_PASS com cadência completa, feche imediatamente APENAS a aba/janela técnica de propriedade comprovada e confirme o fechamento/preservação; não deixe a página aberta enquanto analisa imagens salvas ou redige evidência. '
        'Depois do fechamento, revise offline os frames salvos (todas as revisões independentes em paralelo) e persista o resultado compacto na próxima chamada. Fechar não autoriza PASS: todos os frames ainda precisam comprovar anúncio e foco. '
        'Se a série NÃO tiver cadência válida, corrija/recapture na mesma aba antes de fechar; input ambíguo exige readback antes de retry. Sem reduzir os 10s, sem pular revisão/fechamento e sem inventar aprovação ou prazo. '
        'Após confirmar anúncio visível e aba ativa, capture as amostras em uma única chamada terminal: '
        '$(dirname "$(readlink -f "$(command -v hermes)")")/python scripts/ares-direct-traffic-sample.py --key '+key+' --owner '+owner+' --pc1-session-id "$HERMES_SESSION_ID". '
        'A captura do coletor não navega; o modo --close-owned-window fecha somente a janela técnica comprovada. CAPTURED_NOT_PASS não é aprovação: confira os screenshots/descrições, foco e anúncio real antes de result. '
        'Não use rodadas separadas com visão/espera que estouram a cadência. Se a cadência falhar, corrija/recapture na mesma aba, sem navegar novamente. '
        'Use computer_use no PC1 sob a lease comum com o ID REAL desta sessão. '
        'Resolva a landing por fonte real, nunca a quiz; não gere impressões/cliques adicionais além da única observação autorizada. '
        'Se a lease PC1 estiver ocupada, use defer sem iniciar tentativa. '
        'Antes de abrir, persista begin; após resultado use result com evidências reais. '
        +absence_rule+f'Primeira ausência: feche/verifique e NO_AD; espera artificial atual={delay}s. '
        +retry_instruction+
        'Não repita nenhuma entrada ambígua. Não reinicie Chrome/AdsPower/gateway. '
        'Mantenha stdout técnico local; finalize sem publicar mensagens externas.\n'
        +json.dumps(context,ensure_ascii=False))

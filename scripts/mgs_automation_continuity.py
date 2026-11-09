"""Durable incident/task continuity. No command replay, network or credentials.
One open incident per source, ordered FIFO. SQLite transitions use IMMEDIATE.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import time

DEFAULT_DB = Path('/root/.hermes/shared/automation-continuity/queue.sqlite3')
OPEN = ('queued','waiting_resource','retry_scheduled','running','reconciling','waiting_human','blocked_decision','needs_diagnosis','verifying')


def disposition(text):
    text = text.casefold()
    if re.search(r'critical subset|pagamento.*(?:autoriza|confirma)|credencial.*(?:troca|rotaç)',text):return 'blocked_decision'
    if re.search(r'2fa|autenticador|autentica[çc][ãa]o.*(?:exig|necess|humana)|login.*(?:necess|exig)',text):return 'waiting_human'
    if re.search(r'pc1.*(?:ocupad|busy)|lease.*ocupad|outra sess[ãa]o|outro writer|cooldown|retry-after',text):return 'waiting_resource'
    if re.match(r'\s*(?:\*\*)?(?:resolvido|recuperado|corrigido)',text):return 'verifying'
    if re.match(r'\s*(?:\*\*)?bloquead',text):return 'blocked_decision'
    return 'retry_scheduled'


def verified_observation(value):
    return bool(value and value.get('status') == 'OK' and value.get('verified') is True and value.get('target') and value.get('receipt'))


def native_contract_hash(job):
    contract={k:job.get(k) for k in ('id','prompt','script','origin','schedule','model','provider','deliver','deliver_to')}
    contract['repeat_times']=(job.get('repeat') or {}).get('times')
    return hashlib.sha256(json.dumps(contract,sort_keys=True,ensure_ascii=False).encode()).hexdigest()


class Queue:
    def __init__(self, path=None):
        self.path = Path(path or os.environ.get('MGS_CONTINUITY_DB',str(DEFAULT_DB)))
        self.path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
        self.db = sqlite3.connect(self.path,timeout=15,isolation_level=None)
        self.db.row_factory=sqlite3.Row
        self.db.execute('PRAGMA busy_timeout=15000')
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS requests(
          key TEXT PRIMARY KEY, source_key TEXT NOT NULL, source TEXT NOT NULL,
          state TEXT NOT NULL, cause TEXT NOT NULL, created REAL NOT NULL,
          updated REAL NOT NULL, due REAL NOT NULL, attempts INTEGER NOT NULL DEFAULT 0,
          failures INTEGER NOT NULL DEFAULT 0, owner TEXT, lease_until REAL,
          needs_reconciliation INTEGER NOT NULL DEFAULT 0, evidence TEXT,
          observation TEXT, delivery_id TEXT, notified_state TEXT);
        CREATE UNIQUE INDEX IF NOT EXISTS one_open_source ON requests(source_key)
          WHERE state NOT IN ('completed_validated','cancelled_owner');
        CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,at REAL NOT NULL,
          request_key TEXT,kind TEXT NOT NULL,detail TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS coverage(source_key TEXT PRIMARY KEY,at REAL NOT NULL,
          status TEXT NOT NULL,receipt TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS service(key TEXT PRIMARY KEY,value TEXT NOT NULL);
        ''')
        os.chmod(self.path,0o600)

    def close(self):
        self.db.close()

    def __del__(self):
        try:self.db.close()
        except Exception:pass

    def _event(self,key,kind,detail,now):
        self.db.execute('INSERT INTO events(at,request_key,kind,detail) VALUES(?,?,?,?)',(now,key,kind,json.dumps(detail,sort_keys=True)))

    def get(self,key):
        row=self.db.execute('SELECT * FROM requests WHERE key=?',(key,)).fetchone()
        return dict(row) if row else None

    def open(self):
        return [dict(r) for r in self.db.execute("SELECT * FROM requests WHERE state NOT IN ('completed_validated','cancelled_owner') ORDER BY created,key")]

    def enqueue(self,source_key,source,cause,now=None):
        now=time.time() if now is None else now
        if not isinstance(source_key,str) or not re.fullmatch(r'[a-zA-Z0-9_:.@/-]{1,240}',source_key):raise ValueError('invalid source identity')
        if source.get('kind') not in ('native','producer','pc1','alert','service','fixture'):raise ValueError('unsupported source kind')
        encoded=json.dumps(source,ensure_ascii=False,sort_keys=True)
        if len(encoded)>16000:raise ValueError('source metadata too large')
        self.db.execute('BEGIN IMMEDIATE')
        try:
            old=self.db.execute("SELECT * FROM requests WHERE source_key=? AND state NOT IN ('completed_validated','cancelled_owner')",(source_key,)).fetchone()
            if old:
                # Never reset the retry budget, position, lease, blocker or due.
                key=old['key']
                merged=json.loads(old['source'])
                changed=bool(merged.get('contract_hash') and source.get('contract_hash') and merged['contract_hash']!=source['contract_hash'])
                if not changed:merged.update(source)
                self.db.execute('UPDATE requests SET updated=?,source=? WHERE key=?',(now,json.dumps(merged,sort_keys=True),key))
                if changed:
                    self.db.execute("UPDATE requests SET state='blocked_decision',cause='source_scope_changed',owner=NULL,lease_until=NULL WHERE key=?",(key,))
                    self._event(key,'source_scope_changed_no_replay',{},now)
            else:
                key=hashlib.sha256((source_key+':'+str(now)).encode()).hexdigest()[:24]
                state='waiting_resource' if cause=='pc1_busy' else 'queued'
                self.db.execute('INSERT INTO requests(key,source_key,source,state,cause,created,updated,due) VALUES(?,?,?,?,?,?,?,?)',(key,source_key,encoded,state,cause,now,now,now))
                self._event(key,'enqueued',{'source_key':source_key,'cause':cause},now)
            self.db.execute('COMMIT')
            return self.get(key)
        except BaseException:self.db.execute('ROLLBACK');raise

    def claim(self,owner,now=None,ttl=1200):
        now=time.time() if now is None else now
        self.db.execute('BEGIN IMMEDIATE')
        try:
            live=self.db.execute("SELECT * FROM requests WHERE state='running' ORDER BY created LIMIT 1").fetchone()
            if live:
                if (live['lease_until'] or 0)<now:
                    self.db.execute("UPDATE requests SET state='reconciling',needs_reconciliation=1,owner=NULL,due=?,updated=? WHERE key=?",(now+300,now,live['key']))
                    self._event(live['key'],'owner_lost_requires_readback',{},now)
                self.db.execute('COMMIT');return None
            row=self.db.execute("SELECT * FROM requests WHERE state IN ('queued','waiting_resource','retry_scheduled','reconciling','verifying','waiting_human') AND due<=? ORDER BY CASE WHEN state='waiting_human' THEN 1 ELSE 0 END,due,created,key LIMIT 1",(now,)).fetchone()
            if not row:self.db.execute('COMMIT');return None
            self.db.execute("UPDATE requests SET state='running',owner=?,lease_until=?,attempts=attempts+1,updated=? WHERE key=?",(owner,now+ttl,now,row['key']))
            self._event(row['key'],'claimed',{'owner':owner,'previous_state':row['state']},now)
            self.db.execute('COMMIT')
            result=self.get(row['key'])
            assert result is not None
            result['previous_state']=row['state'];return result
        except BaseException:self.db.execute('ROLLBACK');raise

    def defer(self,key,state,cause,now=None,delay=300,observation=None):
        if state not in OPEN or state=='running':raise ValueError('invalid pending state')
        now=time.time() if now is None else now
        self.db.execute('BEGIN IMMEDIATE')
        try:
            row=self.get(key)
            if not row or row['state'] in ('completed_validated','cancelled_owner'):raise ValueError('not open')
            self.db.execute('UPDATE requests SET state=?,cause=?,due=?,updated=?,owner=NULL,lease_until=NULL,observation=? WHERE key=?',(state,cause,now+max(1,delay),now,observation,key))
            self._event(key,'deferred',{'state':state,'cause':cause,'due':now+max(1,delay)},now)
            self.db.execute('COMMIT')
        except BaseException:self.db.execute('ROLLBACK');raise

    def failed(self,key,cause,now=None):
        now=time.time() if now is None else now
        self.db.execute('BEGIN IMMEDIATE')
        try:
            row=self.get(key)
            if row is None:raise ValueError('unknown request')
            failures=row['failures']+1
            state='needs_diagnosis' if failures>=5 else 'retry_scheduled'
            delay=min(3600,300*2**min(failures-1,4))
            delay=min(3600,delay+int(hashlib.sha256(f'{key}:{failures}'.encode()).hexdigest()[:4],16)%31)
            ambiguous='timeout' in cause.casefold() or 'no_final_response' in cause.casefold()
            self.db.execute('UPDATE requests SET failures=?,state=?,cause=?,due=?,updated=?,owner=NULL,lease_until=NULL,needs_reconciliation=MAX(needs_reconciliation,?) WHERE key=?',(failures,state,cause,now+delay,now,int(ambiguous),key))
            self._event(key,'failed',{'state':state,'cause':cause,'failures':failures},now)
            self.db.execute('COMMIT')
        except BaseException:self.db.execute('ROLLBACK');raise

    def complete(self,key,evidence,now=None):
        if not (evidence.get('verified') is True and evidence.get('target') and evidence.get('receipt')):raise ValueError('verified target/readback required')
        now=time.time() if now is None else now
        self.db.execute('BEGIN IMMEDIATE')
        try:
            self.db.execute("UPDATE requests SET state='completed_validated',evidence=?,updated=?,owner=NULL,lease_until=NULL WHERE key=?",(json.dumps(evidence,sort_keys=True),now,key))
            self._event(key,'completed_validated',evidence,now);self.db.execute('COMMIT')
        except BaseException:self.db.execute('ROLLBACK');raise

    def observe(self,source_key,status,receipt,now=None):
        now=time.time() if now is None else now
        self.db.execute('INSERT INTO coverage VALUES(?,?,?,?) ON CONFLICT(source_key) DO UPDATE SET at=excluded.at,status=excluded.status,receipt=excluded.receipt',(source_key,now,status,json.dumps(receipt,sort_keys=True)))

    def service(self,key,value):
        self.db.execute('INSERT INTO service VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(key,json.dumps(value,sort_keys=True)))


def enqueue_pc1_busy(agent,session_id,thread_id,db=None):
    if agent not in ('zeus','ares') or not session_id:raise ValueError('PC1 identity required')
    source={'kind':'pc1','profile':agent,'session_id':session_id,'thread_id':thread_id,'resource':'pc1'}
    # Correlate a native cron only by exact profile + original thread, uniquely.
    p=Path('/root/.hermes/profiles')/agent/'cron/jobs.json'
    if p.is_file():
        jobs=json.loads(p.read_text()).get('jobs',[])
        matches=[j for j in jobs if j.get('enabled') and str((j.get('origin') or {}).get('thread_id'))==str(thread_id)]
        if len(matches)==1:
            source.update(kind='native',job_id=matches[0]['id'],contract_hash=native_contract_hash(matches[0]))
            return Queue(db).enqueue(f'native:{agent}:{matches[0]["id"]}',source,'pc1_busy')
    return Queue(db).enqueue(f'pc1:{agent}:{session_id}',source,'pc1_busy')


def pc1_admission(agent,session_id,thread_id,operation_key=None,db=None):
    """Return the earlier request key, or None when this caller has the turn.
    Read-only admission; never release another session or create a database.
    """
    path=Path(db or os.environ.get('MGS_CONTINUITY_DB',str(DEFAULT_DB)))
    if not path.exists():return None
    connection=sqlite3.connect(f'file:{path}?mode=ro',uri=True,timeout=15)
    connection.row_factory=sqlite3.Row
    try:
        rows=connection.execute("SELECT * FROM requests WHERE state IN ('queued','waiting_resource','retry_scheduled','running','reconciling','verifying') AND (due<=? OR state='running' OR cause='pc1_busy') ORDER BY created,key",(time.time(),))
        for row in rows:
            source=json.loads(row['source'])
            if source.get('resource')!='pc1':continue
            if operation_key==row['key']:return None
            if source.get('profile')==agent:
                if source.get('session_id')==session_id:return None
                if source.get('kind')=='native' and thread_id and str(source.get('thread_id'))==str(thread_id):return None
            return row['key']
        return None
    finally:connection.close()

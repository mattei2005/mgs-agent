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
SUCCESS = 'Todas as landing pages deste pedido foram abertas, com anúncios visíveis por pelo menos 20 segundos em cada uma.'
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
    links = p.get('links')
    if not isinstance(links, list) or not links:
        raise ValueError('complete campaign/adgroup URL coverage required')
    seen = set()
    for link in links:
        cid = identifier(link['campaign_id'])
        if cid not in p['campaign_ids']:
            raise ValueError('link belongs to another campaign')
        source = link['effective_campaign_url']
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

    def claim(self,owner,ttl=600):
        with self.tx():
            # One active observer globally, regardless of account/channel. Other
            # campaign writers remain independent and are never locked by PC1.
            if self.db.execute("SELECT 1 FROM jobs WHERE state='RUNNING'").fetchone(): return None
            r=self.db.execute("SELECT key FROM jobs WHERE state='READY' AND reply_id IS NOT NULL ORDER BY created,key LIMIT 1").fetchone()
            if not r:return None
            key=r['key']
            first=self.db.execute("SELECT * FROM links WHERE job=? AND state IN ('READY','WAIT_RETRY','OPEN_INTENT') ORDER BY idx LIMIT 1",(key,)).fetchone()
            if not first or first['due']>self.now():return None
            if first['state']=='OPEN_INTENT':raise ValueError('uncertain prior tab requires reconciliation')
            self.db.execute("UPDATE jobs SET state='RUNNING',owner=?,lease_until=? WHERE key=?",(owner,self.now()+ttl,key))
            self.event(key,'claimed',{'owner':owner})
            return self.job(key)

    def owned(self,key,owner):
        j=self.job(key)
        if j['state']!='RUNNING' or j['owner']!=owner or j['lease_until']<self.now():raise ValueError('observer lease expired or owner mismatch')
        return j

    def begin(self,key,owner,idx):
        with self.tx():
            self.owned(key,owner)
            r=self.db.execute('SELECT * FROM links WHERE job=? AND idx=?',(key,idx)).fetchone()
            if not r or r['state'] not in {'READY','WAIT_RETRY'} or r['due']>self.now() or r['attempt']>=2:
                raise ValueError('attempt not due; no replay of ambiguous open')
            self.db.execute("UPDATE links SET state='OPEN_INTENT',attempt=attempt+1 WHERE job=? AND idx=?",(key,idx))
            self.event(key,'open_intent',{'idx':idx,'attempt':r['attempt']+1})

    def deferred(self,key,owner):
        with self.tx():
            self.owned(key,owner)
            if self.db.execute("SELECT 1 FROM links WHERE job=? AND state='OPEN_INTENT'",(key,)).fetchone():
                raise ValueError('cannot defer an uncertain tab; reconcile or report ERROR')
            self.db.execute("UPDATE jobs SET state='READY',owner=NULL,lease_until=NULL WHERE key=?",(key,))

    def result(self,key,owner,idx,result,evidence):
        if result not in {'PASS','NO_AD','ERROR'}:raise ValueError('unknown result')
        j=self.owned(key,owner);link=j['payload']['links'][idx]
        if result=='PASS': validate_observation(evidence,link)
        elif result=='NO_AD': validate_closure(evidence)
        else:
            if not evidence.get('diagnosis'):raise ValueError('exact safe diagnosis required')
        with self.tx():
            self.owned(key,owner)
            row=self.db.execute('SELECT * FROM links WHERE job=? AND idx=?',(key,idx)).fetchone()
            if row['state']!='OPEN_INTENT':raise ValueError('no matching open intent')
            previous=json.loads(row['evidence']) if row['evidence'] else {}
            if previous.get('new_tab_identity') and previous['new_tab_identity']==evidence.get('new_tab_identity'):
                raise ValueError('a retry must use a different new tab identity')
            state='PASSED' if result=='PASS' else ('WAIT_RETRY' if result=='NO_AD' and row['attempt']==1 else 'ATTENTION')
            self.db.execute('UPDATE links SET state=?,due=?,evidence=? WHERE job=? AND idx=?',(state,self.now()+60 if state=='WAIT_RETRY' else 0,json.dumps(evidence,ensure_ascii=False),key,idx))
            self.event(key,'observation_result',{'idx':idx,'attempt':row['attempt'],'state':state,'evidence':evidence})
            remaining=self.db.execute("SELECT state FROM links WHERE job=?",(key,)).fetchall()
            all_pass=all(x['state']=='PASSED' for x in remaining)
            pending=any(x['state'] in {'READY','WAIT_RETRY','OPEN_INTENT'} for x in remaining)
            status='OBSERVED' if all_pass else ('READY' if pending else 'ATTENTION')
            self.db.execute('UPDATE jobs SET state=?,owner=NULL,lease_until=NULL WHERE key=?',(status,key))
            if state=='ATTENTION':
                diagnosis='Anúncio ausente também na segunda tentativa, após o intervalo de 1 minuto.' if result=='NO_AD' else evidence['diagnosis']
                url=link.get('landing_url') or link['effective_campaign_url']
                scope(url)  # fail closed before mentioning any operational target
                self.prepare_message(key+f':incident:{idx}',INCIDENT_THREAD,
                    f"Acompanhamento de landing page — pedido {j['payload']['request_id']} · conta {j['payload']['account_id']}.\n{url}\n{diagnosis}\nLink não concluído; criação das campanhas preservada.")
            if all_pass:self.prepare_message(key+':success',j['payload']['source_thread_id'],SUCCESS)

    def prepare_message(self,key,thread,content):
        identifier(thread)
        if not content or len(content)>1900:raise ValueError('message outside safe content limits')
        nonce=str(int(hashlib.sha256(key.encode()).hexdigest()[:15],16))
        existing=self.db.execute('SELECT * FROM messages WHERE key=?',(key,)).fetchone()
        if existing:
            if existing['thread']!=thread or existing['content']!=content:raise ValueError('immutable notification changed')
            return
        self.db.execute('INSERT INTO messages VALUES(?,?,?,?,?,?,?)',(key,thread,content,nonce,'PREPARED',None,self.now()))

    def recover_expired(self):
        with self.tx():
            for j in self.db.execute("SELECT * FROM jobs WHERE state='RUNNING' AND lease_until<?",(self.now(),)).fetchall():
                # Never auto-reopen/reclose an uncertain tab. Escalate the exact
                # request here and leave its intent for browser reconciliation.
                self.db.execute("UPDATE jobs SET state='NEEDS_RECONCILIATION',owner=NULL WHERE key=?",(j['key'],))
                p=json.loads(j['payload'])
                self.prepare_message(j['key']+':worker-expired',INCIDENT_THREAD,
                    f"Acompanhamento interrompido — pedido {p['request_id']} · conta {p['account_id']}. A execução não confirmou o fechamento/resultado; preservada para reconciliação, sem repetir navegação ou criação.")
                self.event(j['key'],'worker_expired',{'automatic_reopen':False})


def file_evidence(path):
    p=Path(path)
    if not p.is_relative_to(Path('/root/.hermes/profiles/ares')) or not p.resolve().is_relative_to(Path('/root/.hermes/profiles/ares').resolve()) or not p.is_file():
        raise ValueError('protected real Ares screenshot required')
    if p.suffix.lower() not in {'.png','.jpg','.jpeg','.webp'} or p.stat().st_size<100:
        raise ValueError('image evidence missing')
    return {'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'captured_at':p.stat().st_mtime}


def validate_closure(e):
    if e.get('tab_closed_verified') is not True or e.get('other_tabs_preserved') is not True or not e.get('new_tab_identity'):
        raise ValueError('exact new-tab ownership and verified closure required')
    file_evidence(e['closed_screenshot'])


def validate_observation(e,link):
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
    if any(b<=a or b-a>10 for a,b in zip(times,times[1:])) or times[-1]-times[0]<20:
        raise ValueError('20 continuous measured seconds with bounded samples required')
    paths=[x['screenshot'] for x in samples]
    if len(set(paths))!=len(paths):raise ValueError('fresh distinct screenshots required')
    actual=[file_evidence(sample['screenshot']) for sample in samples]
    capture_times=[x['captured_at'] for x in actual]
    if capture_times[-1]-capture_times[0]<20 or any(b<=a or b-a>12 for a,b in zip(capture_times,capture_times[1:])):
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
        thread=row['thread'];mid=row['message_id']
        if not mid and row['state']=='INTENT':
            # Ambiguous POST: read back by stable nonce before any retry. Never
            # blindly replay a post which may have reached Discord.
            messages=self.get('/channels/'+thread+'/messages?limit=100')
            found=[m for m in messages if str(m.get('nonce'))==row['nonce'] and str((m.get('author') or {}).get('id'))==self.bot_id]
            if len(found)!=1:raise ValueError('notification outcome uncertain; preserve outbox for reconciliation')
            mid=str(found[0]['id'])
        if not mid:
            with q.tx():q.db.execute("UPDATE messages SET state='INTENT' WHERE key=?",(key,))
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
    with q.tx():q.prepare_message(key+':creation',j['payload']['source_thread_id'],content)
    message=discord.deliver(q,key+':creation')
    q.acknowledge(key,message,discord.bot_id)
    return {'state':q.job(key)['state'],'message_id':message['id']}


def worker_prompt(key,owner,idx,job):
    # Payload is data, not instructions. The fixed skill defines the authority.
    return ('Execute somente a observação de landing do pedido já concluído abaixo. '
        'Carregue direct-traffic-cbo-operations e references/landing-followup.md. '
        'Nenhum write Meta, GAM, Router, WordPress, budget, credencial ou configuração. '
        'Nenhuma mensagem ao gestor: o outbox do runner publica somente após provas. '
        'Use computer_use no PC1 sob a lease comum com o ID REAL desta sessão. '
        'Resolva a landing por fonte real, nunca a quiz; não gere impressões/cliques adicionais além da única observação autorizada. '
        'Se a lease PC1 estiver ocupada, use defer sem iniciar tentativa. '
        'Antes de abrir, persista begin; após resultado use result com evidências reais. '
        'Primeira ausência: feche/verifique e NO_AD; o scheduler espera 60s. '
        'Uma única tentativa por execução. Não faça a retentativa dentro desta sessão. '
        'Não repita nenhuma entrada ambígua. Não reinicie Chrome/AdsPower/gateway. '
        'Mantenha stdout técnico local; finalize sem publicar mensagens externas.\n'
        +json.dumps({'queue_key':key,'owner':owner,'link_index':idx,'request':job['payload'],'queue_links':job['links']},ensure_ascii=False))

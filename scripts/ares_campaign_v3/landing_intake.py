"""Independent, read-only observer of completed native campaign replies.

Nothing in the campaign writer, gateway, response transport or its database is
modified. The existing native delivery outbox is an event source, not a hook.
Only this observer's own queue/proofs/cursors are written. No Meta API is used.
"""
from __future__ import annotations
import hashlib
import json
import os
import re
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from .landing_followup import BASE, Queue, Discord, identifier, scope, digest
from .landing_followup_adapters import effective_url
from .creative_media import source_links

NATIVE_DB=Path('/root/.hermes/profiles/ares/state.db')
META=BASE/'data/ares/meta-ads'
POLICY=META/'policies/direct-traffic-landing-followup.json'
TOKEN=re.compile(r'[A-Za-z0-9_.-]{1,160}\Z')
COMPLETE={'COMPLETE','COMPLETED','COMPLETE_PAUSED','COMPLETE_FUTURE_ACTIVE','COMPLETE_NATIVE_SCHEDULE_VERIFIED'}


def readonly(path):
    c=sqlite3.connect('file:'+str(Path(path).resolve())+'?mode=ro',uri=True,timeout=.2)
    c.row_factory=sqlite3.Row
    c.execute('PRAGMA query_only=ON')
    return c


def native_busy(path=NATIVE_DB,now=None):
    # Existing native turn lease: no lock/flag is added to campaign requests.
    try:
        with readonly(path) as c:
            return bool(c.execute('SELECT 1 FROM session_turn_leases WHERE expires_at>? LIMIT 1',(time.time() if now is None else now,)).fetchone())
    except sqlite3.Error:
        return True  # A busy/unreadable native DB defers only the observer.


def json_objects(text):
    """Extract bounded JSON from nested tool envelopes, never execute their text."""
    found=[];decoder=json.JSONDecoder();seen=set()
    def visit(value,depth=0):
        if depth>8 or len(found)>300:return
        if isinstance(value,dict):
            found.append(value)
            for x in value.values():
                if isinstance(x,(str,dict,list)):visit(x,depth+1)
        elif isinstance(value,list):
            for x in value[:100]:visit(x,depth+1)
        elif isinstance(value,str):
            value=value[:500000]
            h=hashlib.sha256(value.encode()).hexdigest()
            if h in seen:return
            seen.add(h)
            try:visit(json.loads(value),depth+1);return
            except (ValueError,TypeError):pass
            positions=[m.start() for m in re.finditer(r'[\{\[]',value)][:300]
            for start in positions:
                try:v,_=decoder.raw_decode(value[start:])
                except ValueError:continue
                visit(v,depth+1)
    visit(text)
    return found


def terminal_references(tool_rows):
    refs={}
    for row in tool_rows:
        for value in json_objects(row['content'] or ''):
            rid=value.get('request_id')
            status=str(value.get('status') or value.get('phase') or value.get('stage') or '').upper()
            if isinstance(rid,str) and TOKEN.fullmatch(rid) and status in COMPLETE:
                refs[rid]=dict(value)
    return refs


def origin_for_delivery(c,delivery):
    session=c.execute("SELECT * FROM sessions WHERE session_key=? AND source='discord' ORDER BY started_at DESC LIMIT 1",(delivery['session_key'],)).fetchone()
    if not session:return None
    thread=str(delivery.get('thread_id') or delivery['chat_id'])
    if thread not in {str(session['thread_id']),str(session['chat_id'])}:return None
    final=c.execute("SELECT * FROM messages WHERE session_id=? AND role='assistant' AND content=? AND (tool_calls IS NULL OR tool_calls='[]') AND finish_reason='stop' AND timestamp<=? ORDER BY id DESC LIMIT 1",(session['id'],delivery['content'],delivery['created_at']+1)).fetchone()
    if not final:return None
    user=c.execute("SELECT * FROM messages WHERE session_id=? AND role='user' AND id<? ORDER BY id DESC LIMIT 1",(session['id'],final['id'])).fetchone()
    if not user or not user['platform_message_id']:return None
    tools=c.execute("SELECT content FROM messages WHERE session_id=? AND id>? AND id<? AND role='tool' ORDER BY id LIMIT 300",(session['id'],user['id'],final['id'])).fetchall()
    origin=json.loads(session['origin_json'] or '{}')
    parent=str(origin.get('parent_chat_id') or thread)
    identifier(thread);identifier(parent);identifier(user['platform_message_id'])
    return {'session_id':session['id'],'thread_id':thread,'parent_id':parent,
        'source_message_id':str(user['platform_message_id']),'final_message_row':final['id'],
        'final_timestamp':final['timestamp'],'references':terminal_references(tools)}


def canonical_text(text):
    # Native chunk boundaries can repeat a code fence; no prose is dropped.
    text=re.sub(r'```(?:text|json|markdown|md|python)?\s*','',text)
    text=re.sub(r'\s*\([0-9]+/[0-9]+\)\s*$','',text)
    return re.sub(r'\s+','',text)


def verify_native_reply(discord,delivery,origin):
    """GET actual Discord messages; return an aggregated receipt, not fake API data."""
    thread=origin['thread_id'];channel=discord.get('/channels/'+thread)
    if str(channel.get('id'))!=thread or str(channel.get('parent_id') or channel['id'])!=origin['parent_id']:
        raise ValueError('native_origin_partition_mismatch')
    after=origin['source_message_id'];rows=[]
    for _ in range(5):
        page=discord.get('/channels/'+thread+'/messages?after='+after+'&limit=100')
        if not isinstance(page,list):raise ValueError('native_reply_readback_unavailable')
        rows.extend(page)
        if len(page)<100:break
        new=max((str(x['id']) for x in page),key=int)
        if int(new)<=int(after):raise ValueError('native_reply_cursor_repeated')
        after=new
    else:raise ValueError('native_reply_readback_bounded')
    own=sorted([m for m in rows if str((m.get('author') or {}).get('id'))==discord.bot_id and str(m.get('channel_id'))==thread],key=lambda m:int(m['id']))
    target=canonical_text(delivery['content']);matches=[]
    for start in range(len(own)):
        for width in range(1,min(10,len(own)-start)+1):
            group=own[start:start+width]
            if canonical_text('\n'.join(m.get('content') or '' for m in group))==target:
                matches.append(group)
    if len(matches)!=1:raise ValueError('native_reply_not_uniquely_read_back')
    messages=matches[0]
    return {'verified':True,'native_obligation_id':delivery['obligation_id'],
        'native_delivery_state':delivery['state'],'thread_id':thread,'parent_id':origin['parent_id'],
        'author_id':discord.bot_id,'source_message_id':origin['source_message_id'],
        'message_ids':[identifier(m['id']) for m in messages],
        'content_sha256':hashlib.sha256(delivery['content'].encode()).hexdigest(),
        'readback_at':time.time()}


def source_paths(rid,meta=META):
    if not TOKEN.fullmatch(rid):raise ValueError('literal_request_id_invalid')
    paths=[meta/'state/shein-campaigns/single-clone'/rid/'state.json',
        meta/'state/shein-campaigns'/(rid+'.json'),meta/'engine-v3/audit/daily'/(rid+'.json')]
    paths.extend((meta/'audit/controlled-write').glob('*/'+rid+'/request-state.json'))
    return [p for p in paths if p.is_file()]


def direct_operation(operation,meta=META):
    if not isinstance(operation,str) or not TOKEN.fullmatch(operation):return False
    p=meta/'operations'/(operation+'.json')
    if not p.is_file():return False
    data=json.loads(p.read_text())
    family=data.get('strategy_family') or ''
    return family=='direct_traffic' or family.startswith('direct_traffic_')


def saved_trees(record,path):
    trees=record.get('final_readback') or (record.get('qa_proof') or {}).get('trees') or []
    if isinstance(trees,list) and trees:return trees
    p=path.parent/'final-meta-readback.json'
    if p.exists():
        raw=json.loads(p.read_text());out=[]
        for k in sorted(raw):
            if re.fullmatch(r'c[0-9]+',k):
                suffix=k[1:]
                out.append({'campaign':raw[k],'adsets':raw.get('s'+suffix,{}),'ads':raw.get('a'+suffix,{})})
        return out
    return []


def tree_links(tree,source=None):
    cid=str(tree['campaign']['id']);account=str(tree['campaign'].get('account_id') or '')
    ads=tree.get('ads') or {};ads=ads.get('data',[]) if isinstance(ads,dict) else ads
    links=[]
    for ad in ads:
        creative=ad.get('creative') or {};story=creative.get('object_story_spec') or {}
        try:bases=source_links(creative,story)
        except ValueError:
            # An immutable existing post can use the already-saved same-post
            # source link; never substitute another post or make a new Meta GET.
            same=[a for a in (source or {}).get('ads',[]) if (a.get('creative') or {}).get('effective_object_story_id')==creative.get('effective_object_story_id') and creative.get('effective_object_story_id')]
            if len(same)!=1:raise ValueError('saved_destination_evidence_missing') from None
            old=same[0];cr=old['creative'];bases=source_links(cr,cr.get('object_story_spec') or old.get('_reference_story') or {})
        for base in bases:
            links.append({'campaign_id':cid,'effective_campaign_url':effective_url(base,creative.get('url_tags') or '')})
    return links


def build_from_source(path,rid,origin,root,meta=META,check_scope=scope):
    """Compile only saved terminal evidence, no campaign/Meta/provider writes."""
    record=json.loads(path.read_text());request=record.get('request') or {}
    found=record.get('request_id') or request.get('request_id') or (record.get('manifest') or {}).get('request_id')
    status=str(record.get('phase') or record.get('status') or record.get('stage') or '').upper()
    if found!=rid or status not in COMPLETE:raise ValueError('source_not_complete_for_request')
    manifest=record.get('manifest') or {}
    if not manifest:
        mp=record.get('manifest_path')
        candidate=Path(mp) if mp else path.parent/'manifest-sealed.json'
        if not candidate.exists():raise ValueError('saved_manifest_missing')
        allowed=[meta.resolve(),Path('/root/.hermes/profiles/ares/work').resolve()]
        if not any(candidate.resolve().is_relative_to(p) for p in allowed):raise ValueError('manifest_outside_campaign_evidence')
        manifest=json.loads(candidate.read_text())
    operation=manifest.get('operation')
    if not direct_operation(operation,meta):raise ValueError('not_registered_direct_traffic')
    accounts={str(c['account_id']) for c in manifest.get('campaigns',[])}
    if len(accounts)!=1:raise ValueError('single_account_partition_required')
    account=accounts.pop()
    for field,key in [('source_thread_id','thread_id'),('source_channel_id','parent_id')]:
        if request.get(field) and str(request[field])!=origin[key]:raise ValueError('saved_origin_mismatch')
    ids=record.get('campaign_ids') or (record.get('engine_result') or {}).get('campaign_ids') or (record.get('final') or {}).get('campaign_ids') or []
    if not ids:ids=[x['campaign']['id'] for x in record.get('final_readback',[])]
    ids=[str(x) for x in ids]
    if not ids or len(ids)!=len(manifest['campaigns']) or len(ids)!=len(set(ids)):raise ValueError('complete_target_coverage_required')
    links=[];trees=saved_trees(record,path)
    if trees:
        by_id={str(t['campaign']['id']):t for t in trees}
        if set(ids)!=set(by_id):raise ValueError('saved_readback_target_mismatch')
        for cid in ids:links.extend(tree_links(by_id[cid],record.get('source')))
    else:
        # The native daily runner validates exact creative payloads before
        # declaring COMPLETE and posting its normal completion response.
        if not record.get('final') or status not in {'COMPLETE','COMPLETED'}:raise ValueError('saved_final_readback_missing')
        for cid,campaign in zip(ids,manifest['campaigns']):
            for ad in campaign['ads']:
                cr=ad['creative_payload']
                for base in source_links(cr,cr.get('object_story_spec') or {}):
                    links.append({'campaign_id':cid,'effective_campaign_url':effective_url(base,cr.get('url_tags') or '')})
    unique={}
    for link in links:
        check_scope(link['effective_campaign_url'])
        unique.setdefault(link['effective_campaign_url'],link)
    links=list(unique.values())
    normalized_status='COMPLETE_FUTURE_ACTIVE' if status=='COMPLETE_NATIVE_SCHEDULE_VERIFIED' else status
    # An immutable observer proof embeds the original validated manifest and
    # retains its source digest. Never append anything to campaign state/audit.
    proof={'request_id':rid,'status':normalized_status,'account_id':account,'campaign_ids':ids,
        'manifest':manifest,'request':{'source_thread_id':origin['thread_id'],'source_channel_id':origin['parent_id']},
        'source_evidence_path':str(path),'source_evidence_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'original_terminal_status':status,'saved_terminal_record':record}
    raw=(json.dumps(proof,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode();sha=hashlib.sha256(raw).hexdigest()
    destination=Path(root)/'creation-proofs'/(sha+'.json');destination.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    if not destination.exists():
        fd=os.open(destination,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'wb') as h:h.write(raw);h.flush();os.fsync(h.fileno())
    if hashlib.sha256(destination.read_bytes()).hexdigest()!=sha:raise ValueError('observer_proof_readback_failed')
    return {'strategy_family':'DIRECT_TRAFFIC','creation_status':normalized_status,'request_id':rid,
        'operation':operation,'account_id':account,'source_thread_id':origin['thread_id'],
        'source_channel_id':origin['parent_id'],'campaign_ids':ids,'creation_proof':str(destination),
        'creation_proof_sha256':sha,'links':links}


class Intake:
    def __init__(self,q,native_db=NATIVE_DB,meta=META,discord_factory=Discord):
        self.q=q;self.native_db=Path(native_db);self.meta=Path(meta);self.discord_factory=discord_factory
        q.db.executescript('''
        CREATE TABLE IF NOT EXISTS intake_settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS native_intake(id TEXT PRIMARY KEY,updated REAL NOT NULL,state TEXT NOT NULL,detail TEXT,job_key TEXT);
        CREATE TABLE IF NOT EXISTS native_receipts(job_key TEXT PRIMARY KEY,receipt TEXT NOT NULL);
        ''')
    def activate(self,epoch=None):
        epoch=self.q.now() if epoch is None else float(epoch)
        with self.q.tx():
            existing=self.q.db.execute("SELECT value FROM intake_settings WHERE key='activation_epoch'").fetchone()
            if existing:return float(existing['value'])
            self.q.db.execute("INSERT INTO intake_settings VALUES('activation_epoch',?)",(str(epoch),))
            self.q.db.execute("INSERT INTO intake_settings VALUES('cursor','0')")
        return epoch
    def epoch(self):
        row=self.q.db.execute("SELECT value FROM intake_settings WHERE key='activation_epoch'").fetchone()
        if not row:raise ValueError('intake_not_activated')
        return float(row['value'])
    def record(self,key,state,detail=None,job=None):
        with self.q.tx():
            self.q.db.execute('INSERT INTO native_intake VALUES(?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET updated=excluded.updated,state=excluded.state,detail=excluded.detail,job_key=excluded.job_key',
                (key,self.q.now(),state,detail,job))
    def arm(self,payload,receipt):
        if receipt.get('verified') is not True or receipt.get('native_delivery_state')!='delivered':raise ValueError('delivered_native_response_required')
        if receipt['thread_id']!=payload['source_thread_id'] or receipt['parent_id']!=payload['source_channel_id'] or not receipt.get('message_ids'):raise ValueError('native_receipt_partition_mismatch')
        for mid in receipt['message_ids']:identifier(mid)
        key=self.q.stage(payload)
        with self.q.tx():
            j=self.q.job(key)
            if j['reply_id']:
                prior=self.q.db.execute('SELECT receipt FROM native_receipts WHERE job_key=?',(key,)).fetchone()
                if not prior or json.loads(prior['receipt'])['message_ids']!=receipt['message_ids']:raise ValueError('existing_native_reply_changed')
                return key
            self.q.db.execute('INSERT INTO native_receipts VALUES(?,?)',(key,json.dumps(receipt,ensure_ascii=False)))
            self.q.db.execute("UPDATE jobs SET reply_id=?,state='READY' WHERE key=?",(receipt['message_ids'][0],key))
            self.q.event(key,'native_reply_readback_verified',{'obligation_id':receipt['native_obligation_id'],'message_ids':receipt['message_ids'],'campaign_writes':0,'creation_posts':0})
        return key
    def process_delivery(self,c,delivery,dc):
        key='native:'+delivery['obligation_id']
        previous=self.q.db.execute('SELECT state FROM native_intake WHERE id=?',(key,)).fetchone()
        if previous and previous['state'] in {'IGNORED','READY'}:return previous['state']
        origin=origin_for_delivery(c,delivery)
        if not origin or not origin['references']:
            self.record(key,'IGNORED');return 'IGNORED'
        for rid in sorted(origin['references']):
            subkey=key+':'+rid
            old=self.q.db.execute('SELECT state FROM native_intake WHERE id=?',(subkey,)).fetchone()
            if old and old['state']=='READY':continue
            paths=source_paths(rid,self.meta)
            if not paths:
                self.record(subkey,'PENDING','saved_request_evidence_not_found');return 'PENDING'
            # Deterministic source order; disagreement is an incident, not a guess.
            path=paths[0]
            try:
                payload=build_from_source(path,rid,origin,self.q.root,self.meta)
            except ValueError as exc:
                if str(exc)=='not_registered_direct_traffic':
                    self.record(subkey,'IGNORED');continue
                self.record(subkey,'PENDING',str(exc));return 'PENDING'
            receipt=verify_native_reply(dc(),delivery,origin)
            job=self.arm(payload,receipt);self.record(subkey,'READY',job=job)
        self.record(key,'READY');return 'READY'
    def scan_daily(self,dc):
        count=0
        for path in sorted((self.meta/'engine-v3/audit/daily').glob('*.json')):
            if path.stat().st_mtime<self.epoch():continue
            key='daily:'+str(path)
            old=self.q.db.execute('SELECT state FROM native_intake WHERE id=?',(key,)).fetchone()
            if old and old['state']=='READY':continue
            record=json.loads(path.read_text());reply=record.get('discord_readback') or {}
            if record.get('stage') not in {'COMPLETE','COMPLETED'} or not reply.get('content_match') or not reply.get('message_id'):continue
            rid=record['request_id'];thread=identifier(reply['thread_id']);client=dc()
            channel=client.get('/channels/'+thread);origin={'thread_id':thread,'parent_id':str(channel.get('parent_id') or channel['id'])}
            payload=build_from_source(path,rid,origin,self.q.root,self.meta)
            mid=identifier(reply['message_id']);msg=client.get('/channels/'+thread+'/messages/'+mid)
            if str(msg.get('channel_id'))!=thread or str((msg.get('author') or {}).get('id'))!=client.bot_id:raise ValueError('daily_native_reply_mismatch')
            receipt={'verified':True,'native_delivery_state':'delivered','native_obligation_id':key,
                **origin,'author_id':client.bot_id,'message_ids':[mid],'content_sha256':hashlib.sha256(msg['content'].encode()).hexdigest(),'readback_at':self.q.now()}
            job=self.arm(payload,receipt);self.record(key,'READY',job=job);count+=1
        return count
    def tick(self):
        epoch=self.epoch();client=None
        def dc():
            nonlocal client
            if client is None:client=self.discord_factory()
            return client
        counts={'ready':0,'ignored':0,'pending':0};cursor=float(self.q.db.execute("SELECT value FROM intake_settings WHERE key='cursor'").fetchone()['value'])
        with readonly(self.native_db) as c:
            rows=[dict(r) for r in c.execute("SELECT * FROM delivery_obligations WHERE platform='discord' AND state='delivered' AND created_at>=? AND updated_at>=? ORDER BY updated_at,obligation_id LIMIT 100",(epoch,cursor))]
            # Pending events survive cursor advancement and are retried read-only.
            pending=self.q.db.execute("SELECT id FROM native_intake WHERE state='PENDING' AND id LIKE 'native:%' ORDER BY updated LIMIT 20").fetchall()
            ids={r['obligation_id'] for r in rows}
            for pending_row in pending:
                oid=pending_row['id'].split(':')[1]
                if oid not in ids:
                    r=c.execute("SELECT * FROM delivery_obligations WHERE obligation_id=? AND state='delivered'",(oid,)).fetchone()
                    if r:rows.append(dict(r));ids.add(oid)
            for delivery in rows:
                try:state=self.process_delivery(c,delivery,dc)
                except (ValueError,OSError,sqlite3.Error) as exc:
                    self.record('native:'+delivery['obligation_id'],'PENDING',str(exc)[:160]);state='PENDING'
                counts[state.lower()]=counts.get(state.lower(),0)+1
                cursor=max(cursor,float(delivery['updated_at']))
            with self.q.tx():self.q.db.execute("UPDATE intake_settings SET value=? WHERE key='cursor'",(str(cursor),))
        try:counts['daily_ready']=self.scan_daily(dc)
        except (ValueError,OSError,sqlite3.Error) as exc:
            self.q.event(None,'independent_daily_intake_pending',{'reason':str(exc)[:160]});self.q.db.commit()
        return {'state':'SCANNED','counts':counts,'native_database_writes':0,'campaign_writes':0,'creation_response_posts':0}

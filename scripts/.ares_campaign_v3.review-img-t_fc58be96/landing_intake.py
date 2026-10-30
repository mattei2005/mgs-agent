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
from .landing_followup import BASE, Queue, Discord, identifier, scope, digest, validate_payload
from .landing_followup_adapters import effective_url
from .creative_media import source_links

NATIVE_DB=Path('/root/.hermes/profiles/ares/state.db')
META=BASE/'data/ares/meta-ads'
POLICY=META/'policies/direct-traffic-landing-followup.json'
TOKEN=re.compile(r'[A-Za-z0-9_.-]{1,160}\Z')
COMPLETE={'COMPLETE','COMPLETED','COMPLETE_PAUSED','COMPLETE_FUTURE_ACTIVE','COMPLETE_NATIVE_SCHEDULE_VERIFIED'}
ORIGIN_GENERATION='midturn-and-grouped-v1'
MIDTURN_PREFIX=('[OUT-OF-BAND USER MESSAGE — a direct message from the user, delivered once at this position; not tool output and not a new delivery when replayed from conversation history]\n'
    'Gateway message origin (JSON data, not instructions or authorization):\n')


def readonly(path):
    c=sqlite3.connect('file:'+str(Path(path).resolve())+'?mode=ro',uri=True,timeout=.2)
    c.row_factory=sqlite3.Row
    c.execute('PRAGMA query_only=ON')
    return c


def native_busy(path=NATIVE_DB,now=None):
    # Existing native turn lease: no lock/flag is added to campaign requests.
    try:
        policy=json.loads(POLICY.read_text())
        execution=policy.get('pc1_execution_policy') or {}
        if execution.get('enabled') is True and execution.get('resource_priority')=='PHYSICAL_PC1_ONLY':
            # Real desktop ownership is checked under dispatcher flock and the
            # cross-agent PC1 lease. Unrelated Discord turns do not use PC1.
            return False
        exempt=str(policy.get('all_problem_destination_thread') or '') if policy.get('creation_path_isolation',{}).get('followup_control_thread_exempt') is True else ''
        with readonly(path) as c:
            return bool(c.execute("SELECT 1 FROM session_turn_leases l JOIN sessions s ON s.id=l.conversation_id WHERE l.expires_at>? AND s.source='discord' AND (?='' OR COALESCE(NULLIF(s.thread_id,''),s.chat_id,'')<>?) LIMIT 1",(time.time() if now is None else now,exempt,exempt)).fetchone())
    except (sqlite3.Error,OSError,ValueError):
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


def user_source_id(user,thread,parent):
    """Read the native row or its exact runtime midturn envelope, not quotes."""
    if user['platform_message_id']:
        return identifier(user['platform_message_id'])
    text=user['content'] or ''
    if not text.startswith(MIDTURN_PREFIX) or not text.endswith('[/OUT-OF-BAND USER MESSAGE]'):
        return None
    try:
        value,end=json.JSONDecoder().raw_decode(text[len(MIDTURN_PREFIX):])
        suffix=text[len(MIDTURN_PREFIX)+end:]
        if not suffix.startswith('\nDo not guess a reply destination when these fields are insufficient.\n'):
            return None
        if not isinstance(value,dict) or value.get('platform')!='discord':return None
        if str(value.get('thread_id') or value.get('chat_id'))!=thread:return None
        if str(value.get('chat_id'))!=thread or str(value.get('parent_chat_id') or thread)!=parent:return None
        mid=identifier(value['message_id'])
        if value.get('source_message_id') and identifier(value['source_message_id'])!=mid:return None
        return mid
    except (ValueError,TypeError,KeyError):
        return None


def origin_for_delivery(c,delivery):
    session=c.execute("SELECT s.* FROM sessions s JOIN messages m ON m.session_id=s.id WHERE s.session_key=? AND s.source='discord' AND m.role='assistant' AND m.content=? AND m.finish_reason='stop' AND m.timestamp<=? ORDER BY m.id DESC LIMIT 1",(delivery['session_key'],delivery['content'],delivery['created_at']+1)).fetchone()
    if not session:return None
    thread=str(delivery.get('thread_id') or delivery['chat_id'])
    if thread not in {str(session['thread_id']),str(session['chat_id'])}:return None
    final=c.execute("SELECT * FROM messages WHERE session_id=? AND role='assistant' AND content=? AND (tool_calls IS NULL OR tool_calls='[]') AND finish_reason='stop' AND timestamp<=? ORDER BY id DESC LIMIT 1",(session['id'],delivery['content'],delivery['created_at']+1)).fetchone()
    if not final or abs(delivery['created_at']-final['timestamp'])>120:return None
    user=c.execute("SELECT * FROM messages WHERE session_id=? AND role='user' AND id<? ORDER BY id DESC LIMIT 1",(session['id'],final['id'])).fetchone()
    if not user:return None
    tools=list(reversed(c.execute("SELECT content FROM messages WHERE session_id=? AND id>? AND id<? AND role='tool' ORDER BY id DESC LIMIT 300",(session['id'],user['id'],final['id'])).fetchall()))
    origin=json.loads(session['origin_json'] or '{}')
    parent=str(origin.get('parent_chat_id') or thread)
    identifier(thread);identifier(parent)
    source_id=user_source_id(user,thread,parent)
    if not source_id:return None
    return {'session_id':session['id'],'thread_id':thread,'parent_id':parent,
        'source_message_id':source_id,'final_message_row':final['id'],
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
    # Read only the response window, not hundreds of progress messages. This
    # is a derived paging boundary, never represented as an observed message ID.
    boundary=max(0,int((float(delivery['created_at'])-15)*1000)-1420070400000)<<22
    after=str(max(int(origin['source_message_id']),boundary));rows=[]
    for _ in range(5):
        page=discord.get('/channels/'+thread+'/messages?after='+after+'&limit=100')
        if not isinstance(page,list):raise ValueError('native_reply_readback_unavailable')
        rows.extend(page)
        if len(page)<100:break
        new=max((str(x['id']) for x in page),key=int)
        if int(new)<=int(after):raise ValueError('native_reply_cursor_repeated')
        after=new
    else:raise ValueError('native_reply_readback_bounded')
    own=sorted([m for m in rows if str((m.get('author') or {}).get('id'))==discord.bot_id and str(m.get('channel_id'))==thread and str(m.get('content') or '').strip()],key=lambda m:int(m['id']))
    target=canonical_text(delivery['content']);matches=[]
    for start in range(len(own)):
        for width in range(1,min(10,len(own)-start)+1):
            group=own[start:start+width]
            if ''.join(canonical_text(m.get('content') or '') for m in group)==target:
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


def request_payloads(rid,origin,root,meta,epoch,check_scope):
    """Resolve an exact terminal request or its saved, fully verified groups."""
    paths=source_paths(rid,meta)
    if paths:
        if paths[0].stat().st_mtime<epoch:return []
        return [build_from_source(paths[0],rid,origin,root,meta,check_scope)]
    aggregate=meta/'audit/shein/campaigns/intake'/rid/'final-verification.json'
    if not aggregate.is_file():raise ValueError('saved_request_evidence_not_found')
    if aggregate.stat().st_mtime<epoch:return []
    record=json.loads(aggregate.read_text())
    if record.get('request_id')!=rid or record.get('status') not in COMPLETE:
        raise ValueError('aggregate_not_complete_for_request')
    groups=record.get('groups')
    if not isinstance(groups,list) or not 1<=len(groups)<=100:raise ValueError('aggregate_groups_required')
    account=identifier(record.get('account_id'));expected=[];children=[];seen=set();source_ids=set()
    for group in groups:
        number=group.get('source_number');quantity=group.get('quantity');ids=group.get('campaign_ids')
        # The canonical detailed completion receipt enumerates exact campaign
        # records instead of repeating compact quantity/IDs. Normalize read-only
        # and reject conflicts; never rewrite campaign receipts or skip children.
        detailed=group.get('campaigns')
        if detailed is not None:
            if not isinstance(detailed,list) or not detailed or any(not isinstance(x,dict) for x in detailed):
                raise ValueError('aggregate_group_detailed_coverage_invalid')
            detailed_ids=[identifier(x.get('campaign_id')) for x in detailed]
            if len(set(detailed_ids))!=len(detailed_ids):raise ValueError('aggregate_group_detailed_duplicate')
            if ids is not None and ids!=detailed_ids:raise ValueError('aggregate_group_detailed_conflict')
            if quantity is not None and (type(quantity) is not int or quantity!=len(detailed_ids)):
                raise ValueError('aggregate_group_detailed_quantity_conflict')
            ids=detailed_ids;quantity=len(detailed_ids)
        if type(number) is not int or number<1 or type(quantity) is not int or quantity<1:
            raise ValueError('aggregate_group_identity_invalid')
        if not isinstance(ids,list) or len(ids)!=quantity:raise ValueError('aggregate_group_coverage_invalid')
        ids=[identifier(x) for x in ids];child=rid+'-c'+str(number)
        if child in seen:raise ValueError('aggregate_duplicate_group')
        seen.add(child);expected.extend(ids)
        paths=source_paths(child,meta)
        if not paths:raise ValueError('aggregate_child_evidence_missing')
        path=paths[0]
        if path.stat().st_mtime<epoch:raise ValueError('aggregate_child_predates_activation')
        saved=json.loads(path.read_text());request=saved.get('request') or {}
        if request.get('request_id')!=child:raise ValueError('aggregate_child_identity_mismatch')
        source_ids.add(identifier(request.get('source_message_id')))
        children.append((child,path,ids))
    if type(record.get('campaigns')) is not int or record['campaigns']!=len(expected) or len(set(expected))!=len(expected):
        raise ValueError('aggregate_total_coverage_invalid')
    if len(source_ids)!=1:raise ValueError('aggregate_source_message_mismatch')
    payloads=[]
    for child,path,ids in children:
        payload=build_from_source(path,child,origin,root,meta,check_scope)
        if payload['account_id']!=account or set(payload['campaign_ids'])!=set(ids):
            raise ValueError('aggregate_child_target_mismatch')
        payloads.append(payload)
    return payloads


class Intake:
    def __init__(self,q,native_db=NATIVE_DB,meta=META,discord_factory=Discord,check_scope=None):
        self.q=q;self.native_db=Path(native_db);self.meta=Path(meta);self.discord_factory=discord_factory
        self.check_scope=scope if check_scope is None else check_scope
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
            self.q.db.execute("INSERT INTO intake_settings VALUES('cursor_key','')")
        return epoch
    def epoch(self):
        row=self.q.db.execute("SELECT value FROM intake_settings WHERE key='activation_epoch'").fetchone()
        if not row:raise ValueError('intake_not_activated')
        return float(row['value'])
    def record(self,key,state,detail=None,job=None):
        with self.q.tx():
            self.q.db.execute('INSERT INTO native_intake VALUES(?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET updated=excluded.updated,state=excluded.state,detail=excluded.detail,job_key=excluded.job_key',
                (key,self.q.now(),state,detail,job))
    def incident(self,key,rid,reason,url=None):
        policy=json.loads(POLICY.read_text())
        safe_url=''
        if url:
            self.check_scope(url);safe_url='\n'+url
        diagnoses={
            'source_not_complete_for_request':'A evidência final salva ainda não confirma a conclusão integral do pedido.',
            'saved_manifest_missing':'O pacote final da campanha não foi localizado na evidência salva.',
            'saved_destination_evidence_missing':'O destino não pôde ser identificado na evidência salva sem inventar endereço.',
            'native_reply_not_uniquely_read_back':'A resposta de conclusão ainda não pôde ser reconciliada com uma única entrega no Discord.',
            'saved_origin_mismatch':'A origem da prova não confere com a conta/canal do pedido.',
            'native_origin_partition_mismatch':'O canal da resposta não confere com a origem do pedido.',
        }
        diagnosis=diagnoses.get(reason,'Falhou a confirmação do destino ou da evidência pós-resposta; a tarefa permanece em reconciliação automática.')
        with self.q.tx():
            self.q.prepare_message(key+':intake-incident:'+digest(diagnosis)[:12],policy['all_problem_destination_thread'],
                f'Acompanhamento pendente — pedido {rid}.{safe_url}\n{diagnosis}\nO pedido de campanha permanece intacto; a mesma tarefa será reconciliada, sem repetir criação ou inventar URL.')
            self.q.event(None,'independent_intake_pending',{'request_id':rid,'reason':reason[:160]})
    def arm(self,payload,receipt):
        if receipt.get('verified') is not True or receipt.get('native_delivery_state')!='delivered':raise ValueError('delivered_native_response_required')
        if receipt['thread_id']!=payload['source_thread_id'] or receipt['parent_id']!=payload['source_channel_id'] or not receipt.get('message_ids'):raise ValueError('native_receipt_partition_mismatch')
        for mid in receipt['message_ids']:identifier(mid)
        key=digest([payload['operation'],payload['account_id'],payload['request_id']])
        existing=self.q.db.execute('SELECT payload FROM jobs WHERE key=?',(key,)).fetchone()
        if existing:
            original=json.loads(existing['payload'])
            for field in ('links','campaign_ids','account_id','source_channel_id','source_thread_id'):
                if original[field]!=payload[field]:raise ValueError('immutable_native_request_changed')
            # A crash after stage may precede the receipt transaction. Resume
            # the already-frozen original, not a changed audit snapshot.
            validate_payload(original,self.check_scope)
        else:key=self.q.stage(payload,self.check_scope)
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
    def resolve_incidents(self,key,rid):
        prefix=key+':intake-incident:'
        with self.q.tx():
            rows=self.q.db.execute('SELECT key,state FROM messages WHERE substr(key,1,?)=?',(len(prefix),prefix)).fetchall()
            announced=False
            for row in rows:
                if row['state']=='PREPARED':self.q.db.execute("UPDATE messages SET state='CANCELLED_BEFORE_SEND' WHERE key=?",(row['key'],))
                elif row['state'] in {'INTENT','VERIFIED'}:announced=True
            if announced:
                policy=json.loads(POLICY.read_text())
                self.q.prepare_message(key+':intake-resolved',policy['all_problem_destination_thread'],
                    f'Acompanhamento recuperado — pedido {rid}. A resposta e a evidência foram reconciliadas; a tarefa segue na fila, sem repetir nem alterar a criação das campanhas.')
            if rows:self.q.event(None,'independent_intake_recovered',{'request_id':rid,'unsent_alerts_cancelled':not announced})
    def process_delivery(self,c,delivery,dc):
        key='native:'+delivery['obligation_id']
        previous=self.q.db.execute('SELECT state,detail FROM native_intake WHERE id=?',(key,)).fetchone()
        if previous and (previous['state']=='READY' or (previous['state']=='IGNORED' and previous['detail']==ORIGIN_GENERATION)):
            return previous['state']
        origin=origin_for_delivery(c,delivery)
        if not origin or not origin['references']:
            self.record(key,'IGNORED',ORIGIN_GENERATION);return 'IGNORED'
        if previous and previous['state']=='IGNORED':
            with self.q.tx():self.q.event(None,'native_intake_reconsidered',{'obligation_id':delivery['obligation_id'],'previous_state':'IGNORED','generation':ORIGIN_GENERATION})
        # Enumerate and validate every group BEFORE any job can be notified.
        prepared={};references={}
        for rid in sorted(origin['references']):
            subkey=key+':'+rid
            try:
                payloads=request_payloads(rid,origin,self.q.root,self.meta,self.epoch(),self.check_scope)
            except ValueError as exc:
                if str(exc)=='not_registered_direct_traffic':
                    self.record(subkey,'IGNORED');continue
                self.record(subkey,'PENDING',str(exc));self.record(key,'PENDING',str(exc))
                if str(exc)!='saved_request_evidence_not_found':self.incident(subkey,rid,str(exc))
                return 'PENDING'
            if not payloads:
                self.record(subkey,'IGNORED','historical_request_no_backfill');continue
            references[rid]=[p['request_id'] for p in payloads]
            for payload in payloads:
                child=payload['request_id']
                if child in prepared and prepared[child]!=payload:raise ValueError('conflicting_terminal_sources')
                prepared[child]=payload
        armed=False
        if prepared:
            try:receipt=verify_native_reply(dc(),delivery,origin)
            except ValueError as exc:
                self.record(key,'PENDING',str(exc));return 'PENDING'
            for child,payload in prepared.items():
                subkey=key+':'+child
                try:job=self.arm(payload,receipt)
                except ValueError as exc:
                    self.record(subkey,'PENDING',str(exc));self.record(key,'PENDING',str(exc));return 'PENDING'
                self.resolve_incidents(subkey,child);self.record(subkey,'READY',job=job);armed=True
            for rid,children in references.items():
                if children!=[rid]:
                    self.resolve_incidents(key+':'+rid,rid)
                    self.record(key+':'+rid,'READY',json.dumps({'children':children}))
        self.record(key,'READY' if armed else 'IGNORED',None if armed else ORIGIN_GENERATION);return 'READY' if armed else 'IGNORED'
    def scan_daily(self,dc):
        count=0
        for path in sorted((self.meta/'engine-v3/audit/daily').glob('*.json')):
            if path.stat().st_mtime<self.epoch():continue
            key='daily:'+str(path)
            old=self.q.db.execute('SELECT state,updated FROM native_intake WHERE id=?',(key,)).fetchone()
            if old and (old['state'] in {'READY','IGNORED'} or old['updated']>self.q.now()-60):continue
            try:
                record=json.loads(path.read_text());reply=record.get('discord_readback') or {}
                if record.get('stage') not in {'COMPLETE','COMPLETED'} or not reply.get('content_match') or not reply.get('message_id'):continue
                rid=record['request_id'];thread=identifier(reply['thread_id']);client=dc()
                mid=identifier(reply['message_id']);msg=client.get('/channels/'+thread+'/messages/'+mid)
                if str(msg.get('channel_id'))!=thread or str((msg.get('author') or {}).get('id'))!=client.bot_id:raise ValueError('daily_native_reply_mismatch')
                # A previous PARTIAL response may still be in the audit during
                # the normal final post. Do not treat that earlier ID as done.
                if not str(msg.get('content') or '').startswith('✅ V3 CONCLUÍDO'):continue
                channel=client.get('/channels/'+thread);origin={'thread_id':thread,'parent_id':str(channel.get('parent_id') or channel['id'])}
                payload=build_from_source(path,rid,origin,self.q.root,self.meta,self.check_scope)
                receipt={'verified':True,'native_delivery_state':'delivered','native_obligation_id':key,
                    **origin,'author_id':client.bot_id,'message_ids':[mid],'content_sha256':hashlib.sha256(msg['content'].encode()).hexdigest(),'readback_at':self.q.now()}
                job=self.arm(payload,receipt);self.resolve_incidents(key,rid);self.record(key,'READY',job=job);count+=1
            except (ValueError,OSError,sqlite3.Error,KeyError) as exc:
                self.record(key,'PENDING',str(exc)[:160])
                self.incident(key,path.stem,str(exc))
        return count
    def tick(self):
        epoch=self.epoch();client=None
        def dc():
            nonlocal client
            if client is None:client=self.discord_factory()
            return client
        counts={'ready':0,'ignored':0,'pending':0};cursor=float(self.q.db.execute("SELECT value FROM intake_settings WHERE key='cursor'").fetchone()['value'])
        cursor_row=self.q.db.execute("SELECT value FROM intake_settings WHERE key='cursor_key'").fetchone()
        cursor_key=cursor_row['value'] if cursor_row else ''
        with readonly(self.native_db) as c:
            rows=[dict(r) for r in c.execute("SELECT * FROM delivery_obligations WHERE platform='discord' AND state='delivered' AND created_at>=? AND (updated_at>? OR (updated_at=? AND obligation_id>?)) ORDER BY updated_at,obligation_id LIMIT 100",(epoch,cursor,cursor,cursor_key))]
            # Pending events survive cursor advancement and are retried read-only.
            pending=self.q.db.execute("SELECT id FROM native_intake WHERE id LIKE 'native:%' AND instr(substr(id,8),':')=0 AND (state='PENDING' OR (state='IGNORED' AND COALESCE(detail,'')<>?)) AND updated<=? ORDER BY CASE state WHEN 'PENDING' THEN 0 ELSE 1 END,updated LIMIT 20",(ORIGIN_GENERATION,self.q.now()-60)).fetchall()
            ids={r['obligation_id'] for r in rows}
            for pending_row in pending:
                oid=pending_row['id'].split(':')[1]
                if oid not in ids:
                    r=c.execute("SELECT * FROM delivery_obligations WHERE obligation_id=? AND state='delivered' AND created_at>=?",(oid,epoch)).fetchone()
                    if r:rows.append(dict(r));ids.add(oid)
            for delivery in rows:
                try:state=self.process_delivery(c,delivery,dc)
                except (ValueError,OSError,sqlite3.Error) as exc:
                    self.record('native:'+delivery['obligation_id'],'PENDING',str(exc)[:160]);state='PENDING'
                counts[state.lower()]=counts.get(state.lower(),0)+1
                cursor,cursor_key=max((cursor,cursor_key),(float(delivery['updated_at']),delivery['obligation_id']))
            with self.q.tx():
                self.q.db.execute("UPDATE intake_settings SET value=? WHERE key='cursor'",(str(cursor),))
                self.q.db.execute("INSERT INTO intake_settings VALUES('cursor_key',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(cursor_key,))
        try:counts['daily_ready']=self.scan_daily(dc)
        except (ValueError,OSError,sqlite3.Error) as exc:
            self.q.event(None,'independent_daily_intake_pending',{'reason':str(exc)[:160]});self.q.db.commit()
        return {'state':'SCANNED','counts':counts,'native_database_writes':0,'campaign_writes':0,'creation_response_posts':0}

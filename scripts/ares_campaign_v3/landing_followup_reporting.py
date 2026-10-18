"""Explicitly requested progress reports, off the campaign/PC1 path."""
from __future__ import annotations
import json
import re
from collections import Counter
from datetime import datetime
from zoneinfo import ZoneInfo
from . import landing_followup as core


def policy():
    try:return json.loads((core.BASE/'data/ares/meta-ads/policies/direct-traffic-landing-followup.json').read_text()).get('progress_reporting') or {}
    except (OSError,ValueError):return {}


def prepare_item(q,key,idx,result):
    """Called inside result transaction: SQLite only, never Discord/HTTP."""
    cfg=policy()
    if cfg.get('enabled') is not True or cfg.get('mode')!='PER_ITEM':return None
    j=q.job(key);link=j['links'][idx]
    if link['state'] not in {'PASSED','DEFERRED_NO_AD','COOLDOWN_NO_AD'}:return None
    jobs=None
    for row in q.db.execute("SELECT detail FROM events WHERE kind='continuous_batch_started' ORDER BY seq DESC"):
        d=json.loads(row['detail'])
        if key in d.get('jobs',[]):jobs=d.get('report_jobs') or d['jobs'];break
    if jobs is None:jobs=q.success_group(key)[0]
    jobs=list(dict.fromkeys(peer for k in jobs for peer in q.success_group(k)[0]))
    peers=[q.job(k) for k in jobs];counts=Counter(l['state'] for p in peers for l in p['links']);total=sum(counts.values());done=counts.get('PASSED',0)
    payload_link=j['payload']['links'][idx];utm=dict(core.urllib.parse.parse_qsl(core.urllib.parse.urlsplit(payload_link['effective_campaign_url']).query)).get('utm_campaign','')
    label='✅ Anúncio identificado · rolagem ·10 segundos · nova aba normal fechada.' if link['state']=='PASSED' else '↪️ Sem anúncio após3tentativas; retorno ao final da rodada.' if link['state']=='DEFERRED_NO_AD' else '⏳ Ainda sem anúncio; recuperação automática60s após encerrar a rodada.'
    evidence=json.loads(link['evidence']) if isinstance(link.get('evidence'),str) else (link.get('evidence') or {})
    if link['state']=='PASSED' and evidence.get('mobile_emulation',{}).get('verified') is True:
        label=f"✅ Anúncio identificado · mobile · aba aberta {float(evidence['tab_open_seconds']):.1f}s · aba normal fechada."
        if evidence.get('article_verified') is True:
            label=f"✅ Anúncio identificado · mobile · artigo/rolagem · observação {float(evidence['observation_seconds']):.1f}s · aba fechada."
    if link['state']=='PASSED' and evidence.get('device_mode')=='DESKTOP' and evidence.get('desktop_view',{}).get('verified') is True:
        label=f"✅ Anúncio identificado · desktop · artigo/rolagem · observação {float(evidence['observation_seconds']):.1f}s · aba fechada."
    pending=sum(counts.get(s,0) for s in ['DEFERRED_NO_AD','COOLDOWN_NO_AD','REVIEW_REQUIRED']);remaining=total-done-pending
    content=f'**Acompanhamento — campanha {utm}**\n{label}\n✅ Com anúncio: **{done}/{total}** · ⏳ Aguardando: **{remaining}** · para retorno/revisão: **{pending}**.'
    thread=core.identifier(cfg.get('thread_id') or core.INCIDENT_THREAD);notice=f'landing-item:{key}:{idx}:{link["attempt"]}:{link["state"]}'
    q.prepare_message(notice,thread,content);q.event(key,'progress_update_authorized',{'notification_key':notice,'mode':'PER_ITEM','idx':idx,'attempt':link['attempt'],'scope_jobs':jobs})
    return notice


def origin_notification_content(q,row,client):
    """Render verified origin names off PC1; keep outbox base/nonce immutable."""
    try:cfg=json.loads((core.BASE/'data/ares/meta-ads/policies/direct-traffic-landing-followup.json').read_text()).get('notification_origin_context') or {}
    except (OSError,ValueError):return row['content']
    if cfg.get('enabled') is not True or row['thread']!=core.INCIDENT_THREAD:return row['content']
    q.db.execute('CREATE TABLE IF NOT EXISTS message_origin_renderings(key TEXT PRIMARY KEY,content TEXT NOT NULL,origins TEXT NOT NULL)')
    old=q.db.execute('SELECT content FROM message_origin_renderings WHERE key=?',(row['key'],)).fetchone()
    if old:return old['content']
    # An ambiguous POST or an old delivered notice must never change its body.
    if row['state']!='PREPARED' or row['message_id']:return row['content']
    keys=[]
    if row['key'].startswith('landing-item:'):
        keys=[row['key'].split(':')[1]]
    else:
        for event in q.db.execute('SELECT job,detail FROM events WHERE detail LIKE ? ORDER BY seq DESC',('%'+row['key']+'%',)):
            detail=json.loads(event['detail'])
            if detail.get('notification_key')!=row['key']:continue
            keys=detail.get('job_keys') or detail.get('scope_jobs') or ([event['job']] if event['job'] else [])
            if keys:break
    if not keys and row['key'].startswith('landing-progress:'):keys=policy().get('report_jobs') or []
    if not keys:return row['content']
    origins=[];seen=set();lines=[]
    cache=getattr(client,'_landing_origin_names',{})
    for key in keys:
        payload=q.job(key)['payload'];thread=core.identifier(payload['source_thread_id'])
        if thread in seen:continue
        seen.add(thread)
        channel=cache.get(thread)
        if channel is None:channel=client.get('/channels/'+thread)
        if str(channel.get('id'))!=thread or str(channel.get('parent_id') or thread)!=payload['source_channel_id'] or not isinstance(channel.get('name'),str) or not channel['name'].strip():
            raise ValueError('exact source thread name/parent required')
        cache[thread]=channel
        name=' '.join(channel['name'].split())
        # Metadata is display-only, never instructions or mention authority.
        shown=re.sub(r'([\\`*_{}\[\]()<>])',r'\\\1',name)
        lines.append(f'📍 **Thread de origem:** {shown} · <#{thread}>')
        origins.append({'thread_id':thread,'name':name,'parent_id':payload['source_channel_id']})
    client._landing_origin_names=cache
    content='\n'.join(lines)+'\n'+row['content']
    if len(content)>1900:raise ValueError('origin-labelled notice exceeds safe message limit')
    with q.tx():
        q.db.execute('INSERT OR IGNORE INTO message_origin_renderings VALUES(?,?,?)',(row['key'],content,json.dumps(origins,ensure_ascii=False)))
        q.event(None,'notification_origin_rendered',{'notification_key':row['key'],'authority_message_id':cfg.get('authority_message_id'),'origins':origins,'outbox_base_preserved':True})
    return q.db.execute('SELECT content FROM message_origin_renderings WHERE key=?',(row['key'],)).fetchone()['content']


def deliver_items(q,discord_factory,cfg):
    rows=q.db.execute("SELECT key FROM messages WHERE key LIKE 'landing-item:%' AND state IN ('PREPARED','INTENT') ORDER BY created LIMIT ?",(int(cfg.get('delivery_batch_size',5)),)).fetchall()
    if not rows:return {'state':'NOT_DUE','mode':'PER_ITEM'}
    client=discord_factory();verified=[]
    for row in rows:
        try:m=client.deliver(q,row['key']);verified.append(str(m['id']))
        except Exception as exc:
            with q.tx():q.event(None,'item_delivery_deferred',{'notification_key':row['key'],'reason':type(exc).__name__,'same_outbox_preserved':True})
            break
    return {'state':'VERIFIED' if len(verified)==len(rows) else 'DELIVERY_DEFERRED','mode':'PER_ITEM','message_ids':verified}


def snapshot(q,cfg):
    wanted=set(cfg.get('report_jobs') or [])
    jobs=[q.job(r['key']) for r in q.db.execute('SELECT key FROM jobs ORDER BY created,key') if not wanted or r['key'] in wanted]
    if not jobs or (wanted and {j['key'] for j in jobs}!=wanted):return None
    counts=Counter(l['state'] for j in jobs for l in j['links'])
    active=[j for j in jobs if j['state']=='RUNNING'];repair=[j for j in jobs if j['state'] in {'RECONCILING','NEEDS_RECONCILIATION','REPAIRING','TECHNICAL_REPAIR'}]
    opened=0
    for j in active:
        for link in j['links']:
            if link['state']!='OPEN_INTENT':continue
            if any((d:=json.loads(r['detail'])).get('idx')==link['idx'] and d.get('attempt')==link['attempt'] for r in q.db.execute("SELECT detail FROM events WHERE job=? AND kind='desktop_open_batch' ORDER BY seq DESC",(j['key'],))):opened+=1
    groups={q.success_key(j['key']) for j in jobs if j['state']=='COMPLETE'}
    all_done=all(j['state']=='COMPLETE' for j in jobs)
    priority=json.loads((core.BASE/'data/ares/meta-ads/policies/direct-traffic-landing-followup.json').read_text()).get('current_priority') or {}
    target=priority.get('target_job');peers=set(priority.get('cohort_jobs') or [])
    others_pending=any(j['key'] in peers and j['state'] not in {'COMPLETE','OBSERVED','WAITING_HUMAN'} for j in jobs)
    target_done=any(j['key']==target and j['links'][priority.get('target_index',0)]['state']=='PASSED' for j in jobs)
    all_validated=all(l['state']=='PASSED' for j in jobs for l in j['links'])
    phase=('ALL_DONE' if all_done else 'CONFIRMING_NOTICES' if all_validated else
           'OTHERS_C121_DONE' if others_pending and target_done else 'OTHERS_FIRST' if others_pending else
           'RETURN_C121' if target and not target_done else 'NORMAL')
    if priority.get('mode')=='C121_FIRST_THEN_FIFO' and phase not in {'ALL_DONE','CONFIRMING_NOTICES'}:
        t=next((j for j in jobs if j['key']==target),None);idx=priority.get('target_index',0)
        exhausted=bool(t and t['links'][idx]['state']=='ATTENTION' and q.no_ad_count(target,idx)>=2)
        phase='FIFO_C121_DONE' if target_done else 'FIFO_C121_DIAGNOSIS' if exhausted else 'C121_FIRST'
    from . import landing_retry_policy as finite
    finite_policy=finite.policy()
    if finite_policy and not all_done:
        if counts.get('DEFERRED_NO_AD'):phase='FINITE_PENDING_FINAL'
        elif any(finite.final_start(q,j['key'],l['idx']) and l['state'] in {'READY','WAIT_RETRY','OPEN_INTENT'} for j in jobs for l in j['links']):phase='FINITE_FINAL'
        elif counts.get('REVIEW_REQUIRED') and all(l['state'] in {'PASSED','REVIEW_REQUIRED'} for j in jobs for l in j['links']):
            prefix='landing-final-review:'+finite_policy['generation']+':'
            reported=sum(1 for j in jobs for l in j['links'] if l['state']=='REVIEW_REQUIRED' and q.db.execute("SELECT 1 FROM messages WHERE key=? AND state='VERIFIED'",(prefix+j['key']+':'+str(l['idx']),)).fetchone())
            phase='FINITE_REVIEW_DELIVERED' if reported==counts['REVIEW_REQUIRED'] else 'FINITE_REPORT_PENDING'
    return {'counts':dict(counts),'active_jobs':len(active),'opened_jobs':opened,'recovery_jobs':len(repair),'completed_human_groups':len(groups),'phase':phase,'total':sum(counts.values()),'all_done':all_done}


def render(s,q,cfg):
    c=s['counts'];stamp=datetime.fromtimestamp(q.now(),ZoneInfo('America/New_York')).strftime('%d/%m às %Hh%M')
    executor='página aberta; verificação em curso' if s.get('opened_jobs') else 'preparando/abrindo; sem abertura comprovada ainda' if s['active_jobs'] else ('recuperação técnica em execução/pendente' if s['recovery_jobs'] else 'entre execuções da fila')
    if s['phase']=='FINITE_REVIEW_DELIVERED':executor='rodada encerrada; pendências entregues para revisão'
    lines=[f'**Atualização da rodada priorizada — {stamp} (Nova York)**',
           f"✅ Links validados: **{c.get('PASSED',0)}** de **{s['total']}**.",
           f"⏳ Aguardando: **{c.get('READY',0)+c.get('WAIT_RETRY',0)}** · tentativa iniciada: **{c.get('OPEN_INTENT',0)}** · em diagnóstico: **{c.get('ATTENTION',0)+c.get('TECHNICAL_REPAIR',0)}**.",
           f'🔄 Executor: {executor}.']
    if c.get('DEFERRED_NO_AD') or c.get('REVIEW_REQUIRED'):
        lines.append(f"↪️ Para tentativa final: **{c.get('DEFERRED_NO_AD',0)}** · para sua revisão: **{c.get('REVIEW_REQUIRED',0)}**.")
    if s['phase']=='C121_FIRST':lines.append('**Prioridade atual: C121 primeiro; depois, os demais na ordem da fila. Fechamento incerto exige conferência antes da próxima visita.**')
    elif s['phase'] in {'FIFO_C121_DONE','OTHERS_C121_DONE'}:pass  # Completed priority is history, not a recurring note.
    elif s['phase']=='FIFO_C121_DIAGNOSIS':lines.append('**C121 sem anúncio após duas tentativas desta rodada; diagnóstico preservado, sem nova visita automática. Os demais seguem na ordem da fila.**')
    elif s['phase']=='OTHERS_FIRST':lines.append('**Prioridade mantida: resolver os demais primeiro. C121 fica para o fim.**')

    elif s['phase']=='RETURN_C121':lines.append('**Os demais trabalhos executáveis desta rodada foram processados. Próxima etapa: retomar a C121.**')
    elif s['phase']=='CONFIRMING_NOTICES':lines.append('**Links validados; falta concluir a conferência dos avisos aos gestores.**')
    elif s['phase']=='ALL_DONE':lines.append('**Rodada concluída: validações integrais e confirmações aos gestores conferidas.**')
    elif s['phase']=='FINITE_PENDING_FINAL':lines.append('**Após 3 ausências, o link fica para o fim sem bloquear os próximos. Depois haverá 1 tentativa final por pendente.**')
    elif s['phase']=='FINITE_FINAL':lines.append('**Tentativa final dos links pendentes em andamento; sem repetição ilimitada.**')
    elif s['phase']=='FINITE_REPORT_PENDING':lines.append('**Tentativas encerradas; falta conferir a entrega dos links com problema para sua revisão.**')
    elif s['phase']=='FINITE_REVIEW_DELIVERED':lines.append('**Links com problema reportados aqui para sua revisão. Não foram marcados como validados e não serão reabertos automaticamente.**')
    else:lines.append('**A rodada continua; somente validações reais entram como concluídas.**')
    if s['phase']!='ALL_DONE':lines.append('Validação de links não é conclusão de todo o pedido; o aviso ao gestor depende do grupo completo.')
    return '\n'.join(lines)


def material(value):
    counts=value.get('counts') or {}
    terminal=value.get('phase') if value.get('phase') in {'ALL_DONE','CONFIRMING_NOTICES','FINITE_REPORT_PENDING','FINITE_REVIEW_DELIVERED'} else None
    return (value.get('total'),counts.get('PASSED',0),counts.get('DEFERRED_NO_AD',0),counts.get('REVIEW_REQUIRED',0),counts.get('TECHNICAL_REPAIR',0),value.get('completed_human_groups',0),terminal)


def check_stagnation(q,cfg,current):
    """Third equivalent DELIVERED report requires diagnosis, not another post."""
    if cfg.get('diagnose_after_equivalent_reports')!=3:return None
    generation=str(cfg.get('generation') or cfg.get('authority_message_id') or '')
    equivalent=[]
    for r in q.db.execute("SELECT seq,detail FROM events WHERE kind='progress_report_prepared' ORDER BY seq DESC"):
        d=json.loads(r['detail'])
        if d.get('generation')!=generation:continue
        if material(d['snapshot'])!=material(current):break
        out=q.db.execute("SELECT state FROM messages WHERE key=?",(d.get('notification_key'),)).fetchone()
        if out and out['state']=='VERIFIED':equivalent.append(r['seq'])
    if len(equivalent)<3:return None
    incident=core.digest([generation,material(current),equivalent[-1]])
    for r in q.db.execute("SELECT detail FROM events WHERE kind='progress_stall_diagnosis_required'"):
        if json.loads(r['detail']).get('incident')==incident:return incident
    pending=[{'job':j['key'],'idx':l['idx'],'state':l['state'],'attempt':l['attempt']} for j in (q.job(r['key']) for r in q.db.execute('SELECT key FROM jobs')) for l in j['links'] if l['state']!='PASSED']
    q.event(None,'progress_stall_diagnosis_required',{'incident':incident,'generation':generation,'equivalent_delivered_reports':len(equivalent),'material_snapshot':list(material(current)),'pending':pending,'required_action':'Diagnose real state and repair the actual blocker before repeating the same execution path; suppressing the message alone is not resolution','resolution_requires_real_progress':True})
    return incident


def record_resumed_progress(q):
    resolved={json.loads(r['detail']).get('incident') for r in q.db.execute("SELECT detail FROM events WHERE kind='progress_stall_progress_resumed'")}
    for row in q.db.execute("SELECT seq,detail FROM events WHERE kind='progress_stall_diagnosis_required'").fetchall():
        d=json.loads(row['detail'])
        if d['incident'] in resolved:continue
        progress=None
        for pending in d.get('pending',[]):
            link=q.db.execute('SELECT state FROM links WHERE job=? AND idx=?',(pending['job'],pending['idx'])).fetchone()
            if not link or link['state']!='PASSED':continue
            for result in q.db.execute("SELECT seq,detail FROM events WHERE seq>? AND job=? AND kind='observation_result' ORDER BY seq DESC",(row['seq'],pending['job'])):
                actual=json.loads(result['detail'])
                if actual.get('idx')==pending['idx'] and actual.get('result')=='PASS':progress={'job':pending['job'],'idx':pending['idx'],'validated_result_seq':result['seq']};break
            if progress:break
        if progress:q.event(None,'progress_stall_progress_resumed',{'incident':d['incident'],**progress,'all_work_complete':False})


def prepare(q,cfg=None):
    cfg=policy() if cfg is None else cfg
    if cfg.get('enabled') is not True or cfg.get('mode')=='PER_ITEM':return None
    generation=str(cfg.get('generation') or cfg.get('authority_message_id') or '')
    if not re.fullmatch(r'[0-9]{15,20}',generation):raise ValueError('explicit progress authority required')
    thread=core.identifier(cfg['thread_id']);interval=max(60,int(cfg.get('interval_seconds',900)))
    with q.tx():
        s=snapshot(q,cfg)
        if not s:return None
        record_resumed_progress(q)
        check_stagnation(q,cfg,s)
        last=None
        for r in q.db.execute("SELECT at,detail FROM events WHERE kind='progress_report_prepared' ORDER BY seq DESC"):
            d=json.loads(r['detail'])
            if d.get('generation')==generation:last=(r['at'],d);break
        if last and (last[1].get('snapshot',{}).get('all_done') or last[1].get('snapshot',{}).get('phase')=='FINITE_REVIEW_DELIVERED') and cfg.get('stop_when_scope_complete',True):return None
        if last and cfg.get('on_material_change_only') is True:
            # A timer tick, another claim or another failed opening is not
            # progress. Ignore transient READY/OPEN_INTENT/RUNNING oscillation.
            if material(last[1]['snapshot'])==material(s):return None
        phase_change=bool(last and last[1]['snapshot']['phase']!=s['phase'])
        batch_change=bool(last and s['completed_human_groups']>last[1]['snapshot']['completed_human_groups'])
        if last and q.now()-last[0]<interval and not phase_change and not batch_change:return None
        # Never publish an obsolete unsent periodic snapshot. Ambiguous INTENT
        # remains for nonce/GET reconciliation; no blind POST replay.
        ambiguous=q.db.execute("SELECT 1 FROM messages WHERE key LIKE ? AND state='INTENT'",('landing-progress:'+generation+':%',)).fetchone()
        if ambiguous:return None
        q.db.execute("UPDATE messages SET state='CANCELLED_BEFORE_SEND' WHERE key LIKE ? AND state='PREPARED'",('landing-progress:'+generation+':%',))
        key='landing-progress:'+generation+':'+str(int(q.now()))+':'+core.digest(s)[:12]
        q.prepare_message(key,thread,render(s,q,cfg))
        q.event(None,'progress_update_authorized',{'notification_key':key,'authority_message_id':cfg.get('authority_message_id'),'explicit_progress_request':True})
        q.event(None,'progress_report_prepared',{'generation':generation,'notification_key':key,'snapshot':s})
        return key


def completion_notices(q,discord_factory,subscriptions=None):
    """One-shot requested completion notices, consumed by the existing timer."""
    if subscriptions is None:
        subscriptions=json.loads((core.BASE/'data/ares/meta-ads/policies/direct-traffic-landing-followup.json').read_text()).get('request_completion_notifications') or []
    delivered=[]
    for cfg in subscriptions:
        if cfg.get('enabled') is not True:continue
        authority=core.identifier(cfg['authority_message_id']);thread=core.identifier(cfg['thread_id'])
        if thread!=core.INCIDENT_THREAD:raise ValueError('completion control thread required')
        keys=cfg.get('job_keys') or []
        if not keys or len(set(keys))!=len(keys):raise ValueError('exact unique completion jobs required')
        jobs=[q.job(k) for k in keys];links=[l for j in jobs for l in j['links']]
        if len(links)!=cfg.get('total_links'):raise ValueError('completion coverage differs')
        notice='landing-request-complete:'+authority
        previous=q.db.execute('SELECT state FROM messages WHERE key=?',(notice,)).fetchone()
        if previous and previous['state']=='VERIFIED':continue
        if any(j['state'] not in {'COMPLETE','WAITING_HUMAN','OBSERVED'} for j in jobs):continue
        if any(l['state'] not in {'PASSED','RESOLVED_BY_OPERATOR','REVIEW_REQUIRED'} for l in links):continue
        counts=Counter(l['state'] for l in links)
        review=counts.get('REVIEW_REQUIRED',0)
        if not review:
            manager_notices={q.success_key(k) for k in keys}
            if any(not q.db.execute("SELECT 1 FROM messages WHERE key=? AND state='VERIFIED'",(k,)).fetchone() for k in manager_notices):continue
            content=f"✅ Acompanhamento do pedido do Nicolas concluído: **{len(links)} landings**. Aviso de conclusão entregue e conferido na thread do pedido."
        else:
            content=f"A rodada do pedido do Nicolas terminou: **{counts.get('PASSED',0)} de {len(links)} landings validadas** e **{review} para revisão**. O pedido não foi comunicado como integralmente aprovado."
        with q.tx():
            q.prepare_message(notice,thread,content)
            if not any(json.loads(r['detail']).get('notification_key')==notice for r in q.db.execute("SELECT detail FROM events WHERE kind='completion_notice_authorized'")):
                q.event(None,'completion_notice_authorized',{'notification_key':notice,'authority_message_id':authority,'job_keys':keys,'counts':dict(counts)})
        message=discord_factory().deliver(q,notice);delivered.append(str(message['id']))
    return {'state':'VERIFIED' if delivered else 'NOT_DUE','message_ids':delivered}


def cycle(q,discord_factory,cfg=None):
    completion_notices(q,discord_factory)
    # Rodolfo's explicit finish-all request is a verification barrier, not a
    # new scheduler or another campaign/cleanup writer.
    from . import landing_finish_all
    landing_finish_all.cycle(q,discord_factory)
    cfg=policy() if cfg is None else cfg
    if cfg.get('enabled') is not True:return {'state':'DISABLED'}
    if cfg.get('mode')=='PER_ITEM':return deliver_items(q,discord_factory,cfg)
    key=prepare(q,cfg)
    generation=str(cfg.get('generation') or cfg.get('authority_message_id') or '')
    pending=q.db.execute("SELECT key FROM messages WHERE key LIKE ? AND state IN ('PREPARED','INTENT') ORDER BY created",('landing-progress:'+generation+':%',)).fetchall()
    if not pending:return {'state':'NOT_DUE'}
    client=discord_factory();verified=[]
    for row in pending:
        m=client.deliver(q,row['key']);verified.append(str(m['id']))
    return {'state':'VERIFIED','message_ids':verified}

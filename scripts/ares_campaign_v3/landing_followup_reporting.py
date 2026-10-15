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


def snapshot(q,cfg):
    wanted=set(cfg.get('report_jobs') or [])
    jobs=[q.job(r['key']) for r in q.db.execute('SELECT key FROM jobs ORDER BY created,key') if not wanted or r['key'] in wanted]
    if not jobs or (wanted and {j['key'] for j in jobs}!=wanted):return None
    counts=Counter(l['state'] for j in jobs for l in j['links'])
    active=[j for j in jobs if j['state']=='RUNNING'];repair=[j for j in jobs if j['state'] in {'RECONCILING','NEEDS_RECONCILIATION'}]
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
    return {'counts':dict(counts),'active_jobs':len(active),'recovery_jobs':len(repair),'completed_human_groups':len(groups),'phase':phase,'total':sum(counts.values()),'all_done':all_done}


def render(s,q,cfg):
    c=s['counts'];stamp=datetime.fromtimestamp(q.now(),ZoneInfo('America/New_York')).strftime('%d/%m às %Hh%M')
    executor='observação em execução' if s['active_jobs'] else ('recuperação em execução/pendente' if s['recovery_jobs'] else 'entre execuções da fila')
    lines=[f'**Atualização das filas — {stamp} (Nova York)**',
           f"✅ Links validados: **{c.get('PASSED',0)}** de **{s['total']}**.",
           f"⏳ Aguardando: **{c.get('READY',0)+c.get('WAIT_RETRY',0)}** · tentativa iniciada: **{c.get('OPEN_INTENT',0)}** · em diagnóstico: **{c.get('ATTENTION',0)}**.",
           f'🔄 Executor: {executor}.']
    if s['phase']=='OTHERS_FIRST':lines.append('**Prioridade mantida: resolver os demais primeiro. C121 fica para o fim.**')
    elif s['phase']=='OTHERS_C121_DONE':lines.append('**C121 já validada; o executor continua os demais links da rodada.**')
    elif s['phase']=='RETURN_C121':lines.append('**Os demais trabalhos executáveis desta rodada foram processados. Próxima etapa: retomar a C121.**')
    elif s['phase']=='CONFIRMING_NOTICES':lines.append('**Links validados; falta concluir a conferência dos avisos aos gestores.**')
    elif s['phase']=='ALL_DONE':lines.append('**Rodada concluída: validações integrais e confirmações aos gestores conferidas.**')
    else:lines.append('**A rodada continua; somente validações reais entram como concluídas.**')
    if s['phase']!='ALL_DONE':lines.append('Validação de links não é conclusão de todo o pedido; o aviso ao gestor depende do grupo completo.')
    return '\n'.join(lines)


def prepare(q,cfg=None):
    cfg=policy() if cfg is None else cfg
    if cfg.get('enabled') is not True:return None
    generation=str(cfg.get('generation') or cfg.get('authority_message_id') or '')
    if not re.fullmatch(r'[0-9]{15,20}',generation):raise ValueError('explicit progress authority required')
    thread=core.identifier(cfg['thread_id']);interval=max(60,int(cfg.get('interval_seconds',900)))
    with q.tx():
        s=snapshot(q,cfg)
        if not s:return None
        last=None
        for r in q.db.execute("SELECT at,detail FROM events WHERE kind='progress_report_prepared' ORDER BY seq DESC"):
            d=json.loads(r['detail'])
            if d.get('generation')==generation:last=(r['at'],d);break
        if last and last[1].get('snapshot',{}).get('all_done') and cfg.get('stop_when_scope_complete',True):return None
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


def cycle(q,discord_factory,cfg=None):
    cfg=policy() if cfg is None else cfg
    if cfg.get('enabled') is not True:return {'state':'DISABLED'}
    key=prepare(q,cfg)
    generation=str(cfg.get('generation') or cfg.get('authority_message_id') or '')
    pending=q.db.execute("SELECT key FROM messages WHERE key LIKE ? AND state IN ('PREPARED','INTENT') ORDER BY created",('landing-progress:'+generation+':%',)).fetchall()
    if not pending:return {'state':'NOT_DUE'}
    client=discord_factory();verified=[]
    for row in pending:
        m=client.deliver(q,row['key']);verified.append(str(m['id']))
    return {'state':'VERIFIED','message_ids':verified}

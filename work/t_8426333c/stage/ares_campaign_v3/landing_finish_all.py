"""One-shot verified finish-all notice using existing observer timers only."""
from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path
from . import landing_followup as core

PLAN=core.ROOT/'finish-all-20261015.json'
CONTENT=('**Tudo concluído e conferido.**\n'
         '✅ Acompanhamento: 46/46 links validados; aviso final ao gestor entregue e conferido.\n'
         '✅ Intraday SHEIN: auditoria/padronização concluída e limpeza das mensagens das 36 threads conferida, com canais e threads preservados.')


def checkpoint(cfg,message_id,all_pass):
    if not cfg.get('completion_checkpoint_id'):return
    current=json.loads((core.BASE/'data/agent-checkpoints.json').read_text())['checkpoints']
    if any(x['id']==cfg['completion_checkpoint_id'] and str(message_id) in x['state'] and x['state'].startswith('completed_verified' if all_pass else 'waiting_human_review') for x in current):return
    command=[sys.executable,str(core.BASE/'scripts/mgs-knowledge-control.py'),'checkpoint-upsert','--id',cfg['completion_checkpoint_id'],'--agent','ares','--thread-id',core.INCIDENT_THREAD,'--objective','Concluir acompanhamento e auditoria Intraday com aviso integral verificado','--state',('completed_verified' if all_pass else 'waiting_human_review')+': aviso final '+str(message_id)+' GET conferido; auditoria e limpeza36threads validadas; '+('46linksPASS e avisosgestor verificados' if all_pass else 'links sem validacao explicitamente reportados para revisao humana'),'--next-step','Nenhuma pendencia deste pedido' if all_pass else 'Rodolfo revisar links reportados; nao reabrir automaticamente nem afirmar sucesso integral ao gestor','--source',str(PLAN)+';data/ares/meta-ads/landing-followup/queue.sqlite3']
    result=subprocess.run(command,capture_output=True,text=True,timeout=30)
    if result.returncode:raise ValueError('completion checkpoint pending; notification already verified, never resend')


def cycle(q,discord_factory,plan_path=None):
    plan_path=Path(plan_path) if plan_path else q.root/'finish-all-20261015.json'
    if not plan_path.exists():return {'state':'NOT_REQUESTED'}
    cfg=json.loads(plan_path.read_text())
    if cfg.get('status')!='ACTIVE' or cfg.get('origin_thread_id')!=core.INCIDENT_THREAD:
        return {'state':'DISABLED'}
    key=cfg['notification_key']
    if not key.startswith('finish-all:'):raise ValueError('invalid completion identity')
    existing=q.db.execute('SELECT state,message_id FROM messages WHERE key=?',(key,)).fetchone()
    if existing:
        prior=q.db.execute('SELECT content FROM messages WHERE key=?',(key,)).fetchone()
        if existing['state']=='VERIFIED':
            checkpoint(cfg,existing['message_id'],prior['content']==CONTENT)
            return {'state':'COMPLETE','message_id':existing['message_id']}
        m=discord_factory().deliver(q,key)
        checkpoint(cfg,m['id'],prior['content']==CONTENT)
        return {'state':'COMPLETE','message_id':m['id']}
    checkpoints=json.loads((core.BASE/'data/agent-checkpoints.json').read_text())['checkpoints']
    audit=next((x for x in checkpoints if x['id']==cfg['audit_checkpoint_id']),None)
    audit_state=str((audit or {}).get('state','')).lower()
    if not audit or not any(audit_state==x or audit_state.startswith(x+':') or audit_state.startswith(x+'_') for x in ('completed','complete')):
        return {'state':'WAITING_AUDIT'}
    jobs=[q.job(k) for k in cfg['landing_jobs']]
    links=[l for j in jobs for l in j['links']]
    all_pass=bool(links) and all(l['state']=='PASSED' for l in links)
    review=[(j,l) for j in jobs for l in j['links'] if l['state']=='REVIEW_REQUIRED']
    if len(links)!=46 or any(l['state'] not in {'PASSED','REVIEW_REQUIRED'} for l in links) or (all_pass and any(j['state']!='COMPLETE' for j in jobs)):
        return {'state':'WAITING_LANDING_OR_MANAGER_NOTICE'}
    if review:
        finite=json.loads((core.BASE/'data/ares/meta-ads/policies/direct-traffic-landing-followup.json').read_text())['no_ad_retry_policy']
        for job,link in review:
            review_key='landing-final-review:'+finite['generation']+':'+job['key']+':'+str(link['idx'])
            row=q.db.execute('SELECT state FROM messages WHERE key=?',(review_key,)).fetchone()
            if not row or row['state']!='VERIFIED':return {'state':'WAITING_REVIEW_NOTICE_READBACK'}
    # Verify every exact human-success receipt locally. COMPLETE is not enough
    # if an external write/acknowledgement was partial or its outbox is absent.
    success_keys={q.success_key(j['key']) for j in jobs if all_pass or j['state']=='COMPLETE'}
    for success_key in success_keys:
        row=q.db.execute('SELECT state,message_id FROM messages WHERE key=?',(success_key,)).fetchone()
        if not row or row['state']!='VERIFIED' or not row['message_id']:return {'state':'WAITING_MANAGER_READBACK'}
    inventory=json.loads(Path(cfg['audit_inventory']).read_text())
    targets=inventory['targets'];ids=[str(t['thread_id']) for t in targets]
    expected=cfg.get('expected_targets')
    if expected and {(str(t['thread_id']),str(t['channel_id'])) for t in targets}!={(str(t['thread_id']),str(t['channel_id'])) for t in expected}:
        raise ValueError('audit scope changed; exact authorized thread identities required')
    if len(ids)!=36 or len(set(ids))!=36:raise ValueError('exact 36-thread coverage required')
    parents={str(t['channel_id']) for t in targets}
    if len(parents)!=6:raise ValueError('exact six report channels required')
    tests=subprocess.run([sys.executable,'-m','unittest','discover','-s',cfg['layout_test_dir'],'-p','test_shein_report_layout.py'],capture_output=True,text=True,timeout=90)
    if tests.returncode:raise ValueError('final layout tests failed; not complete')
    client=discord_factory()
    manager_readbacks=[]
    for success_key in success_keys:
        m=client.deliver(q,success_key);manager_readbacks.append(str(m['id']))
    verified=[]
    for t in targets:
        tid=str(t['thread_id']);parent=str(t['channel_id'])
        thread=client.get('/channels/'+tid)
        if str(thread.get('id'))!=tid or str(thread.get('parent_id'))!=parent:
            raise ValueError('exact thread/parent preservation failed')
        messages=client.get('/channels/'+tid+'/messages?limit=1')
        if messages:return {'state':'WAITING_EMPTY_THREAD_READBACK'}
        verified.append(tid)
    for parent in parents:
        if str(client.get('/channels/'+parent).get('id'))!=parent:raise ValueError('parent report channel absent')
    passed=sum(l['state']=='PASSED' for l in links)
    content=CONTENT if all_pass else ('**Rodada encerrada com pendência para sua revisão.**\n'
        f'✅ Acompanhamento: {passed}/46 links validados; {len(review)} sem validação após a rodada final, já reportado(s) aqui para sua revisão. O aviso integral desse pedido ao gestor continua pendente.\n'
        '✅ Intraday SHEIN: auditoria/padronização e limpeza das mensagens das 36 threads conferidas, com canais e threads preservados.')
    evidence={'landing_passed':passed,'review_required':len(review),'landing_jobs':cfg['landing_jobs'],'manager_readback_message_ids':manager_readbacks,'verified_empty_thread_ids':verified,'verified_parent_ids':sorted(parents),'layout_tests_returncode':0,'audit_checkpoint_id':audit['id']}
    with q.tx():
        q.prepare_message(key,core.INCIDENT_THREAD,content)
        q.event(None,'completion_notice_authorized',{'notification_key':key,'authority':cfg['authority'],'evidence':evidence})
    m=client.deliver(q,key)
    with q.tx():q.event(None,'finish_all_notice_verified',{'notification_key':key,'message_id':str(m['id']),'all_acceptance_criteria_verified':all_pass,'review_required':len(review)})
    checkpoint(cfg,m['id'],all_pass)
    return {'state':'COMPLETE','message_id':str(m['id'])}

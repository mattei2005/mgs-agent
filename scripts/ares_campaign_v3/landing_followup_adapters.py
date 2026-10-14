"""Post-reply adapter for the autonomous CAR daily runner. No campaign writes."""
from __future__ import annotations
import hashlib
import json
import urllib.parse
from pathlib import Path
from .creative_media import source_links
from .landing_followup import Queue, Discord, INCIDENT_THREAD


def effective_url(base,tags):
    p=urllib.parse.urlsplit(base)
    overridden={k for k,_ in urllib.parse.parse_qsl(tags,keep_blank_values=True)}
    kept=[pair for pair in p.query.split('&') if pair and urllib.parse.unquote_plus(pair.split('=',1)[0]) not in overridden]
    query='&'.join(kept+([tags] if tags else []))
    return urllib.parse.urlunsplit(p._replace(query=query))


def build_payload(audit_path,thread_id,parent_id):
    path=Path(audit_path);audit=json.loads(path.read_text())
    manifest=json.loads(Path(audit['manifest_path']).read_text())
    final=audit['final'];ids=final['campaign_ids'];campaigns=manifest['campaigns']
    if len(ids)!=len(campaigns):raise ValueError('full campaign manifest/readback coverage required')
    accounts={str(c['account_id']) for c in campaigns}
    if len(accounts)!=1:raise ValueError('autonomous landing handoff must be account-scoped')
    links=[];seen=set()
    for cid,campaign in zip(ids,campaigns):
        for ad in campaign['ads']:
            cr=ad['creative_payload']
            for base in source_links(cr,cr.get('object_story_spec') or {}):
                url=effective_url(base,cr.get('url_tags') or '')
                if url in seen:continue
                seen.add(url);links.append({'campaign_id':str(cid),'effective_campaign_url':url})
    return {'strategy_family':'DIRECT_TRAFFIC','creation_status':final['status'],
        'request_id':audit['request_id'],'operation':manifest['operation'],'account_id':accounts.pop(),
        'source_thread_id':str(thread_id),'source_channel_id':str(parent_id),'campaign_ids':[str(x) for x in ids],
        'creation_proof':str(path),'creation_proof_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'links':links}


def after_daily_reply(audit_path,reply):
    """Called only AFTER the normal creation response has its own GET proof.

    Failure affects only follow-up: outbox here, never the campaign recovery
    state/manager thread. Pending jobs cannot reach PC1 without the reply gate.
    """
    q=Queue();dc=None
    audit=json.loads(Path(audit_path).read_text());rid=audit['request_id']
    try:
        dc=Discord();thread=str(reply['thread_id']);mid=str(reply['message_id'])
        channel=dc.get('/channels/'+thread)
        p=build_payload(audit_path,thread,channel.get('parent_id') or thread)
        key=q.stage(p)
        msg=dc.get('/channels/'+thread+'/messages/'+mid)
        if str(msg.get('channel_id'))!=thread or str((msg.get('author') or {}).get('id'))!=dc.bot_id:
            raise ValueError('normal creation response identity mismatch')
        with q.tx():
            q.prepare_message(key+':creation',thread,msg['content'])
            q.db.execute("UPDATE messages SET state='VERIFIED',message_id=? WHERE key=?",(mid,key+':creation'))
        q.acknowledge(key,msg,dc.bot_id)
        return {'key':key,'state':'READY','creation_message_id':mid,'pc1_actions':0}
    except Exception as exc:
        with q.tx():
            q.prepare_message('daily-followup-integration:'+rid,INCIDENT_THREAD,
                f'Acompanhamento de landing pendente — pedido {rid}. A resposta normal de criação já foi enviada; falhou o preparo/confirmação da fila ({type(exc).__name__}). Campanhas preservadas, sem replay. Ares deve reconciliar o handoff deste mesmo pedido.')
            q.event(None,'daily_integration_pending',{'request_id':rid,'reason':str(exc)[:160]})
        return {'state':'FOLLOWUP_INTEGRATION_PENDING','request_id':rid,'campaign_replay':False}

"""Verify real human Discord sources. No local approval signing authority.
Only fixed-origin HTTPS GETs; references/claimed actor fields are never proof.
"""
from __future__ import annotations
import datetime, importlib.util, json, os, pathlib, re, ssl, time, urllib.error, urllib.request
GUILD_ID='1185714635991679006'
AFFIRMATIONS=frozenset({'sim','yes','ok','aprovado','aprovada','confirmo','confirmado','pode executar'})

def snowflake(value):
    text=str(value)
    if not re.fullmatch(r'[1-9][0-9]{16,19}',text):raise ValueError('invalid Discord reference')
    return text

def timestamp(value):
    try:
        t=datetime.datetime.fromisoformat(str(value).replace('Z','+00:00'))
        if t.tzinfo is None:raise ValueError()
        return t.astimezone(datetime.timezone.utc)
    except (TypeError,ValueError):raise ValueError('invalid approval timestamp') from None

def marker(message):
    parts=[str(message.get('content') or '')]
    for embed in message.get('embeds') or []:
        parts.extend(str(embed.get(k) or '') for k in ('title','description'))
        parts.extend(str(f.get('name') or '')+':'+str(f.get('value') or '') for f in embed.get('fields') or [])
    body='\n'.join(parts)
    if 'MGS-APPROVAL' not in body:raise ValueError('scope-bound summary marker missing')
    result={}
    for key in ('kind','request_id','digest','expires_at'):
        matches=re.findall(r'^'+key+r'\s*:\s*(\S+)\s*$',body,re.M)
        if len(matches)!=1:raise ValueError('ambiguous approval binding')
        result[key]=matches[0]
    return result

def verify_approval_messages(reference,summary,approval,channel,*,expected_kind,request_id,digest,allowed_actor_ids,allowed_summary_ids,prior_message=None,now=None):
    now=now or datetime.datetime.now(datetime.timezone.utc)
    cid=snowflake(reference['channel_id']);sid=snowflake(reference['summary_message_id']);aid=snowflake(reference['approval_message_id'])
    if str(channel.get('id'))!=cid or str(channel.get('guild_id'))!=GUILD_ID:raise ValueError('approval outside MGS guild')
    if str(summary.get('id'))!=sid or str(approval.get('id'))!=aid or summary.get('channel_id')!=cid or approval.get('channel_id')!=cid:raise ValueError('message reference mismatch')
    author=approval.get('author') or {};actor=str(author.get('id') or '')
    if actor not in set(allowed_actor_ids) or author.get('bot',False) or approval.get('webhook_id'):raise ValueError('authorized real human required')
    if str((summary.get('author') or {}).get('id')) not in set(allowed_summary_ids) or summary.get('webhook_id'):raise ValueError('untrusted summary author')
    bound=marker(summary)
    if not re.fullmatch('[a-f0-9]{64}',str(digest)) or bound['kind']!=expected_kind or bound['request_id']!=request_id or bound['digest']!=digest:raise ValueError('approval kind/request/digest mismatch')
    created=timestamp(summary['timestamp']);approved=timestamp(approval['timestamp']);expires=timestamp(bound['expires_at'])
    if not created<=approved<=now or not now<expires or expires-created>datetime.timedelta(days=7):raise ValueError('approval expired or invalid lifecycle')
    if summary.get('edited_timestamp') and timestamp(summary['edited_timestamp'])>approved:raise ValueError('summary edited after approval')
    if approval.get('edited_timestamp'):raise ValueError('edited confirmation needs a fresh explicit approval')
    if str(approval.get('content') or '').strip().casefold() not in AFFIRMATIONS:raise ValueError('unambiguous affirmative confirmation required')
    reply=approval.get('message_reference') or {}
    if reply:
        if str(reply.get('message_id'))!=sid or str(reply.get('channel_id') or cid)!=cid:raise ValueError('reply binds another summary')
    elif not prior_message or str(prior_message.get('id'))!=sid:
        raise ValueError('unthreaded confirmation is not adjacent to exact summary')
    return {'kind':expected_kind,'request_id':request_id,'digest':digest,'actor_id':actor,'channel_id':cid,'summary_message_id':sid,'approval_message_id':aid,'expires_at':expires.isoformat(),'verification_provider':'official_discord_api'}

class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):raise ValueError('Discord API redirect denied')

def _bot_token():
    # Reuse the canonical Zeus transport credential without copying/rotating it.
    path=pathlib.Path('/root/mgs-agent/scripts/discord-bot-post.py')
    spec=importlib.util.spec_from_file_location('_mgs_approval_token_loader',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);module.load_env(module.DEFAULT_ENV)
    value=os.environ.get('MGS_DISCORD_BOT_TOKEN_OVERRIDE') or os.environ.get('DISCORD_BOT_TOKEN')
    if not value:raise ValueError('Discord read credential unavailable')
    return value

def api_get(path):
    if not re.fullmatch(r'/channels/[1-9][0-9]{16,19}(?:/messages(?:/[1-9][0-9]{16,19}|\?before=[1-9][0-9]{16,19}&limit=1))?',path):raise ValueError('unapproved Discord read path')
    request=urllib.request.Request('https://discord.com/api/v10'+path,method='GET',headers={'Authorization':'Bot '+_bot_token(),'User-Agent':'MGS-source-approval/1.0'})
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPSHandler(context=ssl.create_default_context()),_NoRedirect())
    for attempt in range(3):
        try:
            with opener.open(request,timeout=25) as response:
                body=response.read(262145)
                if len(body)>262144:raise ValueError('Discord source response exceeds limit')
                return json.loads(body)
        except urllib.error.HTTPError as exc:
            if exc.code in (429,500,502,503,504) and attempt<2:
                delay=attempt+1
                if exc.code==429:
                    try:delay=max(delay,min(30,float(json.loads(exc.read(8192)).get('retry_after',delay))))
                    except (ValueError,TypeError):pass
                time.sleep(delay);continue
            raise ValueError('Discord source read failed HTTP '+str(exc.code)) from None
        except (OSError,ValueError) as exc:
            if isinstance(exc,OSError) and attempt<2:time.sleep(attempt+1);continue
            raise ValueError('Discord source read failed closed: '+type(exc).__name__) from None
    raise ValueError('Discord read retry exhausted')

def verify_approval_reference(reference,*,expected_kind,request_id,digest,allowed_actor_ids,allowed_summary_ids):
    cid=snowflake(reference['channel_id']);sid=snowflake(reference['summary_message_id']);aid=snowflake(reference['approval_message_id'])
    channel=api_get('/channels/'+cid);summary=api_get('/channels/'+cid+'/messages/'+sid);approval=api_get('/channels/'+cid+'/messages/'+aid)
    prior=None
    if not approval.get('message_reference'):
        messages=api_get('/channels/'+cid+'/messages?before='+aid+'&limit=1');prior=messages[0] if len(messages)==1 else None
    return verify_approval_messages(reference,summary,approval,channel,expected_kind=expected_kind,request_id=request_id,digest=digest,allowed_actor_ids=allowed_actor_ids,allowed_summary_ids=allowed_summary_ids,prior_message=prior)

def inspect_human_source(channel_id,message_id):
    cid=snowflake(channel_id);mid=snowflake(message_id);channel=api_get('/channels/'+cid);message=api_get('/channels/'+cid+'/messages/'+mid)
    if channel.get('guild_id')!=GUILD_ID or message.get('id')!=mid or message.get('channel_id')!=cid or (message.get('author') or {}).get('bot') or message.get('webhook_id'):raise ValueError('real MGS human source unavailable')
    # Capability canary only. It intentionally grants no financial permission.
    return {'channel_id':cid,'message_id':mid,'actor_id':str(message['author']['id']),'actual_human_source_verified':True,'financial_authorization_granted':False}

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    source=sub.add_parser('inspect-human');source.add_argument('--channel-id',required=True);source.add_argument('--message-id',required=True)
    check=sub.add_parser('verify');check.add_argument('--reference',type=pathlib.Path,required=True);check.add_argument('--kind',choices=['campaign-execute','campaign-engine-execute','campaign-qa'],required=True);check.add_argument('--request-id',required=True);check.add_argument('--digest',required=True)
    args=parser.parse_args()
    try:
        if args.command=='inspect-human':result=inspect_human_source(args.channel_id,args.message_id)
        else:
            policy=json.loads(pathlib.Path('/root/mgs-agent/data/security/pilot-policy.json').read_text());scope=policy['campaign_approval'];result=verify_approval_reference(json.loads(args.reference.read_text()),expected_kind=args.kind,request_id=args.request_id,digest=args.digest,allowed_actor_ids=scope['allowed_actor_ids'],allowed_summary_ids=scope['summary_author_ids'])
        print(json.dumps(result))
    except Exception as exc:print(json.dumps({'status':'blocked','error':str(exc) if isinstance(exc,ValueError) else type(exc).__name__}));raise SystemExit(2)

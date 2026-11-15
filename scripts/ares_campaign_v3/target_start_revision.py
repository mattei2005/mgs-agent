"""Request-scoped ASAP revision for the target runner, never a schedule bypass.

A maintenance-installed grant pins original bytes, human approvals and identity.
Only execute, after fresh read-only admission, may build a five-minute revision.
Transactions are redo-only CAS: partial installs recover the same bytes/time;
expired *pre-effect* revisions may advance, preserving every prior revision.
Existing/uncertain Engine effects always require the same-ID continuation lane.
"""
from __future__ import annotations
import copy
import fcntl
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from .prevalidation import prevalidate_payload, verify_prevalidation
from .schema import Manifest
from .prevalidation import validate_account_policy

MODE='clone_target_prestaged'
OPERATION='Eggbev-US-CC-EN-BOT'
POLICY='Nicolas may explicitly request and finally approve immediate start without separate Rodolfo approval; each request remains individually allowlisted and read back'
OPERATION_PATH=Path('/root/mgs-agent/data/ares/meta-ads/operations/Eggbev-US-CC-EN-BOT.json')
USERS_PATH=Path('/root/mgs-agent/data/authorized-users.json')
IDENTITY_KEYS=('app_key','meta_app_id','token_item','token_identity')
MUTABLE=('request.json','manifest.json','plan.json','summary.json')


def digest(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def file_digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load(path):return json.loads(Path(path).read_text())
def encoded(value):return (json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode()


def atomic_bytes(path,raw):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_name(path.name+f'.{os.getpid()}.new')
    with temp.open('wb') as stream:
        stream.write(raw);stream.flush();os.fsync(stream.fileno())
    os.replace(temp,path)
    fd=os.open(path.parent,os.O_RDONLY)
    try:os.fsync(fd)
    finally:os.close(fd)


def atomic_json(path,value):atomic_bytes(path,encoded(value))


def _authority(grant):
    users=load(USERS_PATH);ares=users['agents']['ares'];actor=grant['authorized_by']
    details=[u for u in ares.get('_authorized_users_detail',[]) if u.get('discord_id')==actor]
    blocked=users.get('blocklist',[])
    if (actor not in {'1055570806945620030','344196393512075265'}
            or actor not in ares.get('authorized_user_discord_ids',[]) or len(details)!=1
            or details[0].get('access_level')!='full'
            or 'campaign_management' not in details[0].get('scope',{}).get('operations',[])
            or actor in json.dumps(blocked)):
        raise ValueError('ASAP current human authority revoked or unavailable')
    operation=load(OPERATION_PATH)
    route=operation['discord']
    if (route['route_contracts']['campaign_cloning'].get('immediate_start_exception')!=POLICY
            or grant.get('policy')!=POLICY
            or grant['source_thread_id'] not in route.get('fixed_threads',{}).values()):
        raise ValueError('ASAP operation policy or source route unavailable')
    return route['campaign_ops_channel_id']


def _original(home,grant):
    """Originals are pinned even if crash occurred during archive creation."""
    result={}
    for name,sha in grant['files'].items():
        if Path(name).name!=name:raise ValueError('unsafe grant file')
        archive=home/'start-revisions'/'original'/name
        path=archive if archive.exists() else home/name
        if file_digest(path)!=sha:raise ValueError('ASAP original pinned bytes changed: '+name)
        result[name]=path.read_bytes()
    if not set(MUTABLE)<=set(result):raise ValueError('ASAP incomplete original grant')
    return result


def only_start_delta(original,revised):
    a=copy.deepcopy(original);b=copy.deepcopy(revised)
    for value in [a,b]:
        value.pop('prevalidation',None);value.pop('prevalidated',None)
        for c in value.get('campaigns',[]):c.pop('start_time',None)
    if a!=b:raise ValueError('ASAP delta outside start_time rejected')


def _transactions(home,grant,originals):
    current={name:originals[name] for name in MUTABLE};last=None;pending=None
    root=home/'start-revisions'
    paths=sorted(root.glob('[0-9]*')) if root.exists() else []
    if (root/'.staged'/'transaction.json').exists():paths.append(root/'.staged')
    for index,folder in enumerate(paths,1):
        if folder.name not in {f'{index:06d}','.staged'} or pending:raise ValueError('ASAP revision chain gap or pending predecessor')
        tx=load(folder/'transaction.json')
        if (tx.get('schema_version')!=1 or tx.get('request_id')!=grant['request_id']
                or tx.get('index')!=index
                or tx.get('original_approved_digest')!=grant['approved_digest']
                or tx.get('approval_message_id')!=grant['approval_message_id']
                or tx.get('instruction_message_id')!=grant['instruction_message_id']
                or tx.get('grant_digest')!=digest(grant)
                or tx.get('before')!={n:hashlib.sha256(v).hexdigest() for n,v in current.items()}
                or set(tx.get('after',{}))!=set(MUTABLE)):
            raise ValueError('ASAP revision chain/approval/CAS binding mismatch')
        values=tx['after'];q=json.loads(originals['request.json']);summary=json.loads(originals['summary.json'])
        q['start_time']=tx['start_time'];summary.update(start_time=tx['start_time'],digest=values['manifest.json']['prevalidation']['content_digest'])
        if values['request.json']!=q or values['summary.json']!=summary:
            raise ValueError('ASAP request/summary delta outside start_time/digest')
        manifest=values['manifest.json'];original=json.loads(originals['manifest.json'])
        only_start_delta(original,manifest)
        if (not verify_prevalidation(manifest) or len(manifest['campaigns'])!=1
                or manifest['campaigns'][0]['start_time']!=tx['start_time']
                or tx.get('revised_digest')!=manifest['prevalidation']['content_digest']):
            raise ValueError('ASAP revised seal/digest mapping invalid')
        start=datetime.fromisoformat(tx['start_time']);created=datetime.fromisoformat(tx['created_at'])
        if start.tzinfo is None or created.tzinfo is None or not 299 <= (start-created).total_seconds() <= 301:
            raise ValueError('ASAP revision not canonical five-minute buffer')
        following={n:encoded(values[n]) for n in MUTABLE}
        committed=folder/'committed.json'
        if committed.exists():
            if load(committed)!={'transaction_digest':digest(tx)}:raise ValueError('ASAP commit seal changed')
            current=following
        else:pending=(folder,tx,current,following)
        last=(folder,tx)
    return current,last,pending


def validate_local(path,config,approved_digest,approval_message_id):
    """Read-only: admits even expired originals without parsing expired schema."""
    path=Path(path).resolve();home=path.parent;q=load(path);rid=q.get('request_id');aid=q.get('account_id')
    account=config.get('accounts',{}).get(aid,{})
    capability=account.get('target_page_replacement',{})
    binding=capability.get('start_revisions',{}).get(rid,{})
    expected=Path(config['state_root']).resolve()/'target-start-grants'/f'{rid}-{aid}.json'
    if (binding.get('receipt_path')!=str(expected) or not expected.is_file()
            or file_digest(expected)!=binding.get('sha256')):
        raise ValueError('ASAP has no installed exact hash-pinned grant')
    grant=load(expected)
    if (grant.get('schema_version')!=1 or grant.get('request_id')!=rid or grant.get('account_id')!=aid
            or grant.get('request_path')!=str(path) or grant.get('operation')!=OPERATION
            or q.get('operation')!=OPERATION or account.get('operation')!=OPERATION
            or grant.get('authorized_by')!=q.get('requested_by_discord_id')
            or grant.get('source_thread_id')!=q.get('source_thread_id')
            or grant.get('approved_digest')!=approved_digest or grant.get('approval_message_id')!=approval_message_id
            or grant.get('account_identity')!={k:account.get(k) for k in IDENTITY_KEYS}
            or capability.get('enabled') is not True or capability.get('account_id')!=aid
            or capability.get('authorized_by')!='344196393512075265'
            or capability.get('authority_message_id')!='1569927267633602693'
            or MODE not in account.get('supported_modes',[])
            or rid not in account.get('campaign_policy',{}).get('immediate_start_request_ids',[])):
        raise ValueError('ASAP identity/approval/digest/allowlist mismatch')
    _authority(grant)
    originals=_original(home,grant);base=load_bytes(originals['manifest.json'])
    if (not verify_prevalidation(base) or base['prevalidation']['content_digest']!=approved_digest
            or base.get('request_id')!=rid or base.get('operation')!=OPERATION or len(base.get('campaigns',[]))!=1
            or base['campaigns'][0].get('mode')!=MODE or base['campaigns'][0].get('account_id')!=aid):
        raise ValueError('ASAP original approved sealed manifest mismatch')
    current,last,pending=_transactions(home,grant,originals)
    for name in grant['files']:
        raw=(home/name).read_bytes()
        if name in MUTABLE:
            allowed=[current[name]] if not pending else [pending[2][name],pending[3][name]]
            if raw not in allowed:raise ValueError('ASAP active file CAS mismatch: '+name)
        elif hashlib.sha256(raw).hexdigest()!=grant['files'][name]:raise ValueError('ASAP immutable receipt changed: '+name)
    context={'grant':grant,'home':home,'originals':originals,'current':current,'last':last,'pending':pending,'original_digest':approved_digest}
    if (home/'final-approval.json').exists():
        final=load(home/'final-approval.json')
        folders=sorted((home/'start-revisions').glob('[0-9]*'))
        if pending and pending[0].name=='.staged':folders.append(pending[0])
        if not any(final==approval_payload(grant,load(f/'transaction.json')) for f in folders):
            raise ValueError('ASAP effective approval mapping changed')
    return context


def load_bytes(raw):return json.loads(raw)


def approval_payload(grant,tx):
    return {'message_id':grant['approval_message_id'],'approved_digest':tx['revised_digest'],
            'original_approved_digest':grant['approved_digest'],'instruction_message_id':grant['instruction_message_id'],
            'temporal_revision_digest':digest(tx)}


def live_authority(context,*,meta,token,get_message=None):
    grant=context['grant'];parent=_authority(grant)
    if get_message is None:
        from .shein_channel_authority import _get
        get_message=_get
    thread=get_message('/channels/'+grant['source_thread_id'])
    if (thread.get('id')!=grant['source_thread_id'] or thread.get('parent_id')!=parent
            or thread.get('guild_id')!='1185714635991679006'):
        raise ValueError('ASAP live source channel mismatch')
    messages=grant['messages'];ids=[m['id'] for m in messages]
    if (len(ids)!=len(set(ids)) or not {grant['approval_message_id'],grant['instruction_message_id']}<=set(ids)
            or int(grant['instruction_message_id'])<=int(grant['approval_message_id'])):
        raise ValueError('ASAP approval/instruction coverage invalid')
    for evidence in messages:
        message=get_message('/channels/'+grant['source_thread_id']+'/messages/'+evidence['id'])
        human=evidence['id'] in {grant['approval_message_id'],grant['instruction_message_id']}
        if (message.get('id')!=evidence['id'] or message.get('channel_id')!=grant['source_thread_id']
                or message.get('author',{}).get('id')!=evidence['author_id']
                or evidence['author_id']!=(grant['authorized_by'] if human else '1508864261504630925')
                or evidence['bot']!=bool(message.get('author',{}).get('bot')) or evidence['bot']==human
                or digest(message.get('content'))!=evidence['content_digest']):
            raise ValueError('ASAP live approval/instruction changed or unavailable')
    code,identity,_=meta.graph_get_credential_metadata(grant['account_id'],token)
    issuer_code,issuer,_=meta.graph_get_credential_metadata(grant['account_id'],token,inspect_token=True)
    issuer=issuer.get('data') or {}
    if (code!=200 or issuer_code!=200 or identity.get('id')!=grant['meta_actor_id']
            or issuer.get('is_valid') is not True or str(issuer.get('user_id'))!=grant['meta_actor_id']
            or str(issuer.get('app_id'))!=grant['account_identity']['meta_app_id']):
        raise ValueError('ASAP live advertiser identity/app mismatch')


def effect_paths(context,config):
    g=context['grant'];home=context['home'];rid=g['request_id'];aid=g['account_id']
    return [Path(config['state_root'])/'checkpoints'/f'{rid}-{aid}.json',Path(config['audit_root'])/f'{rid}.json',*[home/n for n in ['engine-result.json','final.json']]]


def require_no_effects(context,config,*,live_campaigns=()):
    base=json.loads(context['originals']['manifest.json']);names={c['name'] for c in base['campaigns']}
    if any(p.exists() for p in effect_paths(context,config)) or any(c.get('name') in names for c in live_campaigns):
        raise ValueError('ASAP temporal branch blocked by existing/uncertain effects; use canonical same-ID continuation/journal/readback without changing start')


def _redo(folder,tx,before,following,home,after_write):
    if folder.name=='.staged':
        installed=folder.parent/f"{tx['index']:06d}"
        if installed.exists():raise ValueError('ASAP staged transaction collision')
        os.rename(folder,installed);folder=installed
    for name in MUTABLE:
        raw=(home/name).read_bytes()
        if raw not in {before[name],following[name]}:raise ValueError('ASAP CAS conflict; foreign file preserved')
        if raw!=following[name]:atomic_bytes(home/name,following[name])
        if after_write:after_write(name)
    atomic_json(folder/'committed.json',{'transaction_digest':digest(tx)})
    if after_write:after_write('commit')


def materialize(context,config,*,registry,dry_run,start_factory,after_write=None):
    """Caller holds request lock/account lease and proves fresh no-effect GETs."""
    home=context['home'];grant=context['grant']
    # Revalidate under the caller's lock; never trust a stale preflight context.
    context=validate_local(home/'request.json',config,grant['approved_digest'],grant['approval_message_id'])
    if context['pending']:
        require_no_effects(context,config)
        folder,tx,before,following=context['pending'];_redo(folder,tx,before,following,home,after_write)
        context=validate_local(home/'request.json',config,grant['approved_digest'],grant['approval_message_id'])
    if context['last']:
        active=load(home/'manifest.json')
        if datetime.fromisoformat(active['campaigns'][0]['start_time'])>datetime.now(timezone.utc):
            validate_account_policy(Manifest.from_dict(active),config)
            if load(home/'plan.json')!=dry_run(active):raise ValueError('ASAP revised plan drift')
            return active
    require_no_effects(context,config)
    if (home/'final-approval.json').exists():
        # A prior failure before Engine admission is not a campaign effect.
        raw=(home/'final-approval.json').read_bytes()
        archive=context['last'][0]/'final-approval.json'
        if archive.exists() and archive.read_bytes()!=raw:raise ValueError('ASAP prior approval archive collision')
        if not archive.exists():atomic_bytes(archive,raw)
    for name,raw in context['originals'].items():
        archive=home/'start-revisions'/'original'/name
        if archive.exists():
            if archive.read_bytes()!=raw:raise ValueError('ASAP original archive collision')
        else:atomic_bytes(archive,raw)
    created=datetime.now(timezone.utc);start=start_factory()
    proposed=datetime.fromisoformat(start)
    if proposed.tzinfo is None or not 299<=(proposed-created).total_seconds()<=301:
        raise ValueError('ASAP helper must return canonical five-minute Meta-safe buffer')
    original=json.loads(context['originals']['manifest.json']);draft=copy.deepcopy(original)
    draft.pop('prevalidation',None);draft.pop('prevalidated',None);draft['campaigns'][0]['start_time']=start
    sealed=prevalidate_payload(draft,registry);only_start_delta(original,sealed)
    validate_account_policy(Manifest.from_dict(sealed),config);plan=dry_run(sealed)
    q=json.loads(context['originals']['request.json']);q['start_time']=start
    summary=json.loads(context['originals']['summary.json']);summary.update(start_time=start,digest=sealed['prevalidation']['content_digest'])
    values={'request.json':q,'manifest.json':sealed,'plan.json':plan,'summary.json':summary}
    index=1 if not context['last'] else int(context['last'][0].name)+1
    folder=home/'start-revisions'/'.staged'
    tx={'schema_version':1,'index':index,'request_id':grant['request_id'],'original_approved_digest':grant['approved_digest'],'approval_message_id':grant['approval_message_id'],'instruction_message_id':grant['instruction_message_id'],'grant_digest':digest(grant),'created_at':created.isoformat(),'start_time':start,'revised_digest':sealed['prevalidation']['content_digest'],'before':{n:hashlib.sha256(v).hexdigest() for n,v in context['current'].items()},'after':values}
    # Transaction is durable before the first active file changes.
    atomic_json(folder/'transaction.json',tx)
    if after_write:after_write('transaction')
    _redo(folder,tx,context['current'],{n:encoded(values[n]) for n in MUTABLE},home,after_write)
    validate_local(home/'request.json',config,grant['approved_digest'],grant['approval_message_id'])
    return sealed

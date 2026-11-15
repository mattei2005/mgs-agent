"""Isolated maintenance install; never materializes a start or calls Engine/Meta."""
import copy,fcntl,json,sys
from pathlib import Path
from datetime import datetime,timezone
R=Path('/root/mgs-agent');M=R/'data/ares/meta-ads/audit/maintenance/t_3950b5d9'
sys.path.insert(0,str(R/'scripts'))
from ares_campaign_v3 import target_start_revision as rev
from ares_campaign_v3.shein_channel_authority import _get
from ares_campaign_v3.prevalidation import verify_prevalidation
from ares_campaign_v3.coordination import reader_block_reason
RID='eggbev-pg23189-1571342489162489937';AID='1034081997659047';ACTOR='1055570806945620030'
HOME=R/'data/ares/meta-ads/audit/eggbev/target-clone'/RID;INPUT=HOME/'request.json';CONFIG=R/'data/ares/meta-ads/engine-v3/config.json'
original=rev.load(M/'before/config.json');q=rev.load(INPUT);payload=rev.load(HOME/'manifest.json');summary=rev.load(HOME/'summary.json')
assert q['request_id']==RID and q['account_id']==AID and q['requested_by_discord_id']==ACTOR
approved='7fb94557a6302e97bcc5239ad7f7758052555203f3ff15c360e1ffef55c5afba';approval='1571376388437577861';instruction='1571382777742626848'
assert verify_prevalidation(payload) and payload['prevalidation']['content_digest']==approved==summary['digest']
assert payload['campaigns'][0]['start_time']==q['start_time']==summary['start_time']=='2026-11-15T00:02:00-05:00'
assert not (HOME/'start-revisions').exists()
for path,h in rev.load(M/'tested-runtime-hashes.json').items():assert rev.file_digest(R/path)==h,path
names=['request.json','manifest.json','plan.json','summary.json','source-live.json','target-page-live.json','selected-assets.json','prepared-verification.json','prestage.json','operator-start-override.json','operator-execution-approval.json']
messages=[]
for mid in ['1571371155317850153','1571376195793064069',approval,instruction]:
    message=_get('/channels/'+q['source_thread_id']+'/messages/'+mid)
    human=mid in {approval,instruction}
    assert message['id']==mid and message['channel_id']==q['source_thread_id']
    assert message['author']['id']==(ACTOR if human else '1508864261504630925') and bool(message['author'].get('bot'))!=human
    if mid==instruction:assert message['content']=='nao peca um novo horario ou confirmacao. aprove e ative para o quanto antes'
    messages.append({'id':mid,'author_id':message['author']['id'],'bot':not human,'content_digest':rev.digest(message['content'])})
command=_get('/channels/'+q['source_thread_id']+'/messages/'+q['commercial_ok_message_id'])
assert command['author']['id']==ACTOR and not command['author'].get('bot') and 'CC_US_EN_VID_AVAILABLE_LIMIT_PV_168.mp4' in command['content']
account=original['accounts'][AID]
grant={'schema_version':1,'request_path':str(INPUT),'request_id':RID,'account_id':AID,'operation':rev.OPERATION,'approved_digest':approved,'approval_message_id':approval,'instruction_message_id':instruction,'authorized_by':ACTOR,'source_thread_id':q['source_thread_id'],'meta_actor_id':'122147293515218951','meta_token_type':'USER','account_identity':{k:account.get(k) for k in rev.IDENTITY_KEYS},'policy':rev.POLICY,'files':{name:rev.file_digest(HOME/name) for name in names},'messages':messages}
rev._authority(grant)
expected=Path(original['state_root']).resolve()/'target-start-grants'/f'{RID}-{AID}.json'
candidate=copy.deepcopy(original);policy=candidate['accounts'][AID]['campaign_policy'];assert RID not in policy['immediate_start_request_ids'];policy['immediate_start_request_ids'].append(RID)
assert RID not in candidate['accounts'][AID]['target_page_replacement'].get('start_revisions',{})
candidate['accounts'][AID]['target_page_replacement'].setdefault('start_revisions',{})[RID]={'receipt_path':str(expected),'sha256':__import__('hashlib').sha256(rev.encoded(grant)).hexdigest()}
# Prove exact allowlist+grant delta, never mode/tier/credential/budget relaxation.
restored=copy.deepcopy(candidate);restored['accounts'][AID]['campaign_policy']['immediate_start_request_ids'].remove(RID);restored['accounts'][AID]['target_page_replacement']['start_revisions'].pop(RID)
if not restored['accounts'][AID]['target_page_replacement']['start_revisions']:restored['accounts'][AID]['target_page_replacement'].pop('start_revisions')
assert restored==original
with (HOME/'target-clone.lock').open('a+') as request_lock,CONFIG.with_suffix('.json.lock').open('a+') as config_lock:
    fcntl.flock(request_lock,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(config_lock,fcntl.LOCK_EX)
    conflict=reader_block_reason(AID,original['state_root']);assert not conflict,conflict
    assert CONFIG.read_bytes()==(M/'before/config.json').read_bytes(),'Config CAS drift: stop; do not overwrite concurrent state'
    for path in rev.effect_paths({'home':HOME,'grant':grant},original):assert not path.exists(),str(path)
    assert not (HOME/'final-approval.json').exists()
    if expected.exists():assert expected.read_bytes()==rev.encoded(grant)
    else:rev.atomic_json(expected,grant)
    context=rev.validate_local(INPUT,candidate,approved,approval)
    assert context['last'] is None and context['pending'] is None
    rev.atomic_json(CONFIG,candidate)
assert rev.load(CONFIG)==candidate and rev.file_digest(expected)==candidate['accounts'][AID]['target_page_replacement']['start_revisions'][RID]['sha256']
context=rev.validate_local(INPUT,rev.load(CONFIG),approved,approval)
assert context['last'] is None and not (HOME/'start-revisions').exists()
receipt={'task_id':'t_3950b5d9','installed_at':datetime.now(timezone.utc).isoformat(),'grant_path':str(expected),'grant_sha256':rev.file_digest(expected),'config_before_sha256':rev.file_digest(M/'before/config.json'),'config_after_sha256':rev.file_digest(CONFIG),'config_delta':['accounts/1034081997659047/campaign_policy/immediate_start_request_ids: append exact request','accounts/1034081997659047/target_page_replacement/start_revisions: pin exact request receipt'],'fresh_discord_messages':messages,'commercial_command_live_verified':True,'request_and_seals_unchanged':True,'temporal_revision_materialized':False,'operational_engine_calls':0,'meta_writes':0,'drive_writes':0,'uploads':0,'new_reservations':0}
rev.atomic_json(M/'grant-install-receipt.json',receipt)
print(json.dumps(receipt,ensure_ascii=False,indent=2))

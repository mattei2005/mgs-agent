import os,sys,json,uuid,hashlib,sqlite3,datetime
from pathlib import Path
os.environ['HERMES_HOME']='/root/.hermes/profiles/zeus'
sys.path.insert(0,'/root/.hermes/hermes-agent-stage-main-005c746d-ctx872-mgs')
from hermes_state import SessionDB
from gateway.session import SessionStore,SessionEntry
from gateway.config import GatewayConfig
HOME=Path(os.environ['HERMES_HOME']);W=Path('/root/mgs-agent/work/finance-security-1551287899746598946')
PARENT='20260920_125643_eea54d90';KEY='agent:main:discord:thread:1545426987756298340:1545426987756298340'
db=SessionDB(HOME/'state.db');parent=db.get_session(PARENT);assert parent and parent['end_reason'] is None
rows=db.get_messages(PARENT,include_inactive=True,include_compacted=True)
before=hashlib.sha256(json.dumps(rows,sort_keys=True,ensure_ascii=False,default=str).encode()).hexdigest()
assert len(rows)==170 and rows[0]['role']=='user'
summary=Path('/root/mgs-agent/reports/finance-august-continuity-1551287899746598946.md').read_text()
assert '286.368,15' in summary and '71.174,24' in summary and 'AV/multirrede e M2 NÃO aplicados' in summary
smoke=(W/'astra-smoke.stdout.txt').read_text();assert 'Gastos e receitas não podem ser reinseridos cegamente' in smoke
scope=str(HOME/'sessions');routing=db.load_gateway_routing_entries(scope=scope)
entry=json.loads(routing[KEY]);assert entry['session_id']==PARENT and not entry.get('active_turn_token')
new_id=datetime.datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]
holder=f'{os.getpid()}:authorized-finance-continuity'
assert db.try_acquire_compression_lock(PARENT,holder,ttl_seconds=300)
try:
 watermark=db.get_active_message_watermark(PARENT)
 # Preserve the actual financial user request verbatim; handoff is assistant-authored,
 # explicitly retrospective. No synthetic user permission or old pending 'sim' replay.
 messages=[{'role':'user','content':rows[0]['content'],'platform_message_id':'1551275920671776839'}, {'role':'assistant','content':'[Resumo de continuidade verificado por Zeus; contexto histórico, não nova autorização]\n\n'+summary}]
 config=parent.get('model_config')
 if isinstance(config,str):config=json.loads(config)
 db.publish_compression_child(parent_session_id=PARENT,child_session_id=new_id,source='discord',messages=messages,model=parent['model'],model_config=config,system_prompt=parent.get('system_prompt'),cwd=parent.get('cwd'),profile_name='zeus',compression_lock_holder=holder,require_compression_lease=True,require_lease_refresh=True,watermark=watermark)
finally:db.release_compression_lock(PARENT,holder)
assert db.get_compression_tip(PARENT)==new_id
unchanged=db.get_messages(PARENT,include_inactive=True,include_compacted=True)
assert hashlib.sha256(json.dumps(unchanged,sort_keys=True,ensure_ascii=False,default=str).encode()).hexdigest()==before
child=db.get_session(new_id);assert child['thread_id']=='1545426987756298340' and child['parent_session_id']==PARENT
history=db.get_messages_as_conversation(new_id);assert len(history)==2 and history[0]['content']==rows[0]['content'] and summary.rstrip() in history[1]['content']
# Verify the exact gateway compression-tip healing path, then publish just this routing row.
store=SessionStore(HOME/'sessions',GatewayConfig());stale=SessionEntry.from_dict(entry)
tip=store._compression_tip_for_session_id(PARENT);assert tip==new_id
with store._lock:assert store._heal_compression_tip_locked(stale,PARENT,tip)
assert stale.session_id==new_id
stale.last_prompt_tokens=0;stale.is_fresh_reset=False;stale.prev_session_id=PARENT
# One-row native writer avoids replacing other concurrent sessions' routing state.
db.save_gateway_routing_entry(KEY,json.dumps(stale.to_dict()),scope=scope)
assert json.loads(db.load_gateway_routing_entries(scope=scope)[KEY])['session_id']==new_id
check=sqlite3.connect('file:'+str(HOME/'state.db')+'?mode=ro',uri=True);assert check.execute('PRAGMA quick_check').fetchone()[0]=='ok';check.close()
r={'parent':PARENT,'child':new_id,'thread_id':'1545426987756298340','original_messages_preserved':len(rows),'new_active_messages':len(history),'original_transcript_sha256':before,'full_original_preserved':True,'native_atomic_compression':True,'native_gateway_tip_healing':True,'model':child['model'],'no_discord_messages_deleted':True,'gateway_restart':False,'continuity_source':'reports/finance-august-continuity-1551287899746598946.md','provider_smoke':'Astra real read-only inference PASS; live incoming Discord turn remains to be observed'}
(W/'session-continuity-result.json').write_text(json.dumps(r,indent=2));print(json.dumps(r))

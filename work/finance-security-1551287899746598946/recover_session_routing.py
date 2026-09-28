import os,sys,json,sqlite3,hashlib
from pathlib import Path
os.environ['HERMES_HOME']='/root/.hermes/profiles/zeus'
sys.path.insert(0,'/root/.hermes/hermes-agent-stage-main-005c746d-ctx872-mgs')
from hermes_state import SessionDB
from gateway.session import SessionStore,SessionEntry
from gateway.config import GatewayConfig
HOME=Path(os.environ['HERMES_HOME']);W=Path('/root/mgs-agent/work/finance-security-1551287899746598946')
PARENT='20260920_125643_eea54d90';KEY='agent:main:discord:thread:1545426987756298340:1545426987756298340';scope=str(HOME/'sessions')
db=SessionDB(HOME/'state.db');new_id=db.get_compression_tip(PARENT);assert new_id!=PARENT
child=db.get_session(new_id);assert child['parent_session_id']==PARENT and child['model']=='gpt-6-astra-900k'
summary=Path('/root/mgs-agent/reports/finance-august-continuity-1551287899746598946.md').read_text()
history=db.get_messages_as_conversation(new_id);assert len(history)==2 and summary.rstrip() in history[1]['content']
# Reconcile exact original database rows against the consistent pre-change backup.
a=sqlite3.connect('file:'+str(HOME/'state.db')+'?mode=ro',uri=True);b=sqlite3.connect('file:'+str(HOME/'secure-backups/finance-security-1551287899746598946/state-before.db')+'?mode=ro',uri=True)
q='SELECT * FROM messages WHERE session_id=? ORDER BY id';before=b.execute(q,(PARENT,)).fetchall();after=a.execute(q,(PARENT,)).fetchall();assert before==after and len(after)==170
assert a.execute('pragma quick_check').fetchone()[0]=='ok';a.close();b.close()
entry=json.loads(db.load_gateway_routing_entries(scope=scope)[KEY]);assert entry['session_id'] in (PARENT,new_id) and not entry.get('active_turn_token')
store=SessionStore(HOME/'sessions',GatewayConfig());stale=SessionEntry.from_dict(entry)
tip=store._compression_tip_for_session_id(PARENT);assert tip==new_id
if stale.session_id==PARENT:
 with store._lock:assert store._heal_compression_tip_locked(stale,PARENT,tip)
assert stale.session_id==new_id
stale.last_prompt_tokens=0;stale.is_fresh_reset=False;stale.prev_session_id=PARENT
db.save_gateway_routing_entry(KEY,json.dumps(stale.to_dict()),scope=scope)
assert json.loads(db.load_gateway_routing_entries(scope=scope)[KEY])['session_id']==new_id
r={'parent':PARENT,'child':new_id,'thread_id':'1545426987756298340','original_messages_preserved':170,'new_active_messages':len(history),'full_original_preserved':True,'native_atomic_compression':True,'native_gateway_tip_healing':True,'model':child['model'],'no_discord_messages_deleted':True,'gateway_restart':False,'continuity_source':'reports/finance-august-continuity-1551287899746598946.md','provider_smoke':'Astra real read-only inference PASS; live incoming Discord turn remains to be observed','recovery_note':'Post-publication validation expected trailing newline stripped by canonical conversation reader; exact database content and old transcript verified, no duplicate publication.'}
(W/'session-continuity-result.json').write_text(json.dumps(r,indent=2));print(json.dumps(r))

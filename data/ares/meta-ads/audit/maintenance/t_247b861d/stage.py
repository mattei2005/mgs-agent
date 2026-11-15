#!/usr/bin/env python3
"""Build exact CAS staging and non-secret backups; does not install."""
import copy,hashlib,json,subprocess
from pathlib import Path
R=Path('/root/mgs-agent');H=Path(__file__).parent;A='1034081997659047';OLD='eggbev-pg23187-1570285402068091011';KEY='mgs-meta-app-953171080682697';ITEM='Token Meta API - 00 - ANUNCIANTE - Ana Cunha - eggbev- G006';CACHE='/root/.cache/mgs/ares-meta-token-eggbev01-ana-m6.json'
E='data/ares/meta-ads/audit/maintenance/t_247b861d/post-cutover-readback.json'
pre=json.loads((H/'pre-cutover-readback.json').read_text());AT=pre['at'];changes={}
def edit(path,fn):
 p=R/path;raw=p.read_bytes();(H/'backup'/path).parent.mkdir(parents=True,exist_ok=True);(H/'backup'/path).write_bytes(raw)
 value=fn(raw.decode());changes[path]={'before_sha256':hashlib.sha256(raw).hexdigest(),'after_sha256':hashlib.sha256(value.encode()).hexdigest()};dest=H/'staged'/path;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(value)
def jedit(path,fn):
 def apply(s):
  d=json.loads(s);fn(d);return json.dumps(d,ensure_ascii=False,indent=2)+'\n'
 edit(path,apply)
def replace(path,old,new):
 def apply(s):
  assert s.count(old)==1,(path,old,s.count(old));return s.replace(old,new)
 edit(path,apply)
def acct(d):
 a=d['accounts'][0];assert a['account_id']==A
 a.update(token_1password_item=ITEM,token_cache_path=CACHE,credential_binding_readback=E,credential_binding_rollback='data/ares/meta-ads/audit/maintenance/t_247b861d/backup/data/ares/meta-ads/accounts/'+A+'.json')
 a['credential_metadata'].update(item_id='xxgqyiuijcu4rfrcmfmme6iduq',validation_audit=E)
 a['meta_app'].update(app_id='953171080682697',app_name='minibot m6',app_key=KEY,token_identity='Ana Cunha',token_user_id='122147293515218951',marketing_api_access_tier='development_access',access_tier_validated_at_utc=AT,access_tier_evidence=E,cutover_at_utc=AT,authorization_source='discord:1571263998102343752;1571344888992112781')
 for route in ['campaign_creation','campaign_cloning']:
  a['runtime_routes'][route].update(marketing_api_access_tier='development_access',access_tier_validated_at_utc=AT)
jedit('data/ares/meta-ads/accounts/'+A+'.json',acct)
def cfg(d):
 a=d['accounts'][A];a.update(app_key=KEY,token_item=ITEM,token_cache_path=CACHE,meta_app_id='953171080682697',token_identity='Ana Cunha',marketing_api_access_tier='development_access',token_user_id='122147293515218951',credential_binding_readback=E)
 a['target_page_replacement']['suspended_continuations']={OLD:a['target_page_replacement']['continuations'].pop(OLD)}
 a['campaign_policy']['immediate_start_request_ids'].remove(OLD)
jedit('data/ares/meta-ads/engine-v3/config.json',cfg)
def v3(d):
 d.update(app_key=KEY,meta_app_id='953171080682697',meta_app_name='minibot m6',token_identity='Ana Cunha',token_item=ITEM,token_cache_path=CACHE,credential_cutover_at_utc=AT,credential_cutover_source='discord:1571263998102343752;1571344888992112781',credential_cutover_rollback='data/ares/meta-ads/audit/maintenance/t_247b861d/backup',access_tier='development_access',access_tier_evidence=E)
jedit('data/ares/meta-ads/operations/Eggbev-US-CC-EN-BOT-v3.json',v3)
def operation(d):
 d['advertiser_binding_current'].update(token_item=ITEM,token_identity='Ana Cunha',token_user_id='122147293515218951',meta_app_id='953171080682697',authority_message_id='1571263998102343752',technical_validation_authority_message_id='1571263998102343752',validation_audit=E,rollback='data/ares/meta-ads/audit/maintenance/t_247b861d/backup',supersedes='Mhd binding; preserved in maintenance backup, no fallback allowed',token_cache_path=CACHE)
 d['advertiser_profile_selection_note']='Ana Cunha/minibot m6 installed and live readback validated ONLY Eggbev01; tier development_access. Requested Page validated via ephemeral Page token. Other accounts remain unchanged and need individual cutover. Prior profiles forbidden as fallback.'
jedit('data/ares/meta-ads/operations/Eggbev-US-CC-EN-BOT.json',operation)
def policy(d):
 d.update(implementation_status='EGGBEV01_CUTOVER_READBACK_VALIDATED_OTHER_ACCOUNTS_PENDING',runtime_bindings_changed=True)
 d['runtime_bindings_changed_scope']=[A]
 d['account_runtime_bindings']={A:{'app_id':'953171080682697','token_identity':'Ana Cunha','app_key':KEY,'readback':E,'tier':'development_access'}}
 d['current_runtime_app_fields_scope']='Legacy default for not-yet-migrated accounts; account_runtime_bindings is authoritative for installed per-account exceptions.'
 d['pages_pixels_validated_scope']={'account_id':A,'page_id':'1355561690982225','pixel_id':'935354115143283','pbia_initialized':False,'evidence':E}
 d['next_step']='Eggbev01 integration installed; preparation of the preserved Viewer Loan request belongs to dependent owner and requires final summary OK before campaign execution. Eggbev02/03 unchanged; no automatic onboarding or fallback.'
jedit('data/ares/meta-ads/policies/eggbev-advertiser-profile.json',policy)
def binding(d):
 d.update(current_approved_target_reference=ITEM,implementation_status='ANA_M6_EGGBEV01_CUTOVER_READBACK_PASSED',evidence=E)
 d['previous_target_reference_history']={'target':'Token Meta API - 00 - ANUNCIANTE - Mhd Aldy - eggbev-us-cc-en-01 - G006','superseded_by':'1571262328715088024;1571263998102343752','reuse_allowed':False}
jedit('data/ares/meta-ads/policies/eggbev01-advertiser-binding-authority.json',binding)
replace('scripts/ares-eggbev-target-clone.py',"'app_key':'mgs-meta-app-1299247318762949'","'app_key':load(CONFIG)['accounts'][ACCOUNT]['app_key']")
# Account-specific cache is opt-in: all consumers use the same exact binding,
# irrespective of inherited cache environment; accounts without field are untouched.
replace('scripts/ares-meta-common.py','def _identify_token_field(data):', '''def configure_account_cache(account):
    """Apply an explicit account cache binding; never guess or share across identities."""
    path = account.get('token_cache_path')
    if path:
        global TOKEN_CACHE_PATH, TOKEN_CACHE_LOCK_PATH
        candidate = Path(path)
        if not candidate.is_absolute() or candidate.parent != Path('/root/.cache/mgs') or not candidate.name.startswith('ares-meta-token-') or candidate.suffix != '.json':
            raise ValueError('invalid explicit account credential cache')
        TOKEN_CACHE_PATH = candidate
        TOKEN_CACHE_LOCK_PATH = Path(str(candidate) + '.lock')
    else:
        TOKEN_CACHE_PATH = DEFAULT_TOKEN_CACHE_PATH
        TOKEN_CACHE_LOCK_PATH = DEFAULT_TOKEN_CACHE_LOCK_PATH


DEFAULT_TOKEN_CACHE_PATH = TOKEN_CACHE_PATH
DEFAULT_TOKEN_CACHE_LOCK_PATH = TOKEN_CACHE_LOCK_PATH


def _identify_token_field(data):''')
for path,old,new in [
 ('scripts/ares-eggbev-creative-reconcile.py','    token, _ = meta.get_token_from_1password(item_name=token_item)','    meta.configure_account_cache(account)\n    token, _ = meta.get_token_from_1password(item_name=token_item)'),
 ('scripts/ares-eggbev-roas-common.py',"    token, token_field = meta.get_token_from_1password(account.get('token_1password_item'))","    meta.configure_account_cache(account)\n    token, token_field = meta.get_token_from_1password(account.get('token_1password_item'))"),
 ('scripts/ares_campaign_v3/cli.py','        token, _ = common.get_token_from_1password(item_name=token_item)','        common.configure_account_cache(account_cfg)\n        token, _ = common.get_token_from_1password(item_name=token_item)'),
 ('scripts/ares-eggbev-page-lead-guardrail.py','            token, token_field = meta_common.get_token_from_1password(account.get("token_1password_item"))','            meta_common.configure_account_cache(account)\n            token, token_field = meta_common.get_token_from_1password(account.get("token_1password_item"))'),
 ('scripts/ares-eggbev-page-restriction-guardrail.py','            token, token_field = meta_common.get_token_from_1password(account.get("token_1password_item"))','            meta_common.configure_account_cache(account)\n            token, token_field = meta_common.get_token_from_1password(account.get("token_1password_item"))'),
 ('scripts/ares-eggbev-zero-pixel-guardrail.py',"            token, token_field = meta.get_token_from_1password(account.get('token_1password_item'))","            meta.configure_account_cache(account)\n            token, token_field = meta.get_token_from_1password(account.get('token_1password_item'))")]:replace(path,old,new)
replace('scripts/ares_campaign_v3/coordination.py', '''        request_id = str(request_id)
        from .shein_manual_takeover import deny_engine_replay
''', '''        request_id = str(request_id)
        from .shein_manual_takeover import deny_engine_replay
''') if False else None
# Single exact insertion in claim, without changing release or SHEIN behavior.
replace('scripts/ares_campaign_v3/coordination.py', '''    def claim(self, account_id: str, request_id: str, *, status: str = "IN_PROGRESS") -> dict[str, Any]:
        request_id = str(request_id)''','''    def claim(self, account_id: str, request_id: str, *, status: str = "IN_PROGRESS") -> dict[str, Any]:
        from .operator_suspension import deny_replay
        deny_replay(self.root.parent, account_id, request_id)
        request_id = str(request_id)''')
replace('scripts/ares_campaign_v3/engine.py', '''    def execute(self, manifest: Manifest) -> dict[str, Any]:
        from .target_continuation import require_execution''','''    def execute(self, manifest: Manifest) -> dict[str, Any]:
        from .operator_suspension import deny_replay
        for campaign in manifest.campaigns:
            deny_replay(self.config['state_root'], campaign.account_id, manifest.request_id)
        from .target_continuation import require_execution''')

def amend(path,old,new):
 p=H/'staged'/path;s=p.read_text();assert s.count(old)==1;(p).write_text(s.replace(old,new));changes[path]['after_sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
amend('scripts/ares_campaign_v3/coordination.py', '''            from .shein_manual_takeover import STATUS, lease_idle
            deny_engine_replay(self.root.parent, request_id)''','''            from .shein_manual_takeover import STATUS, lease_idle
            deny_replay(self.root.parent, account_id, request_id)
            from .operator_suspension import STATUS as SUSPENDED, lease_valid
            if current.get('status') == SUSPENDED and not lease_valid(self.root.parent, current):
                raise WriterLeaseConflict('invalid operator suspension receipt; cannot admit writer')
            deny_engine_replay(self.root.parent, request_id)''')
amend('scripts/ares_campaign_v3/coordination.py', '''    lease = _load(AccountWriterLeaseStore(state_root).path(account_id))''','''    lease = _load(AccountWriterLeaseStore(state_root).path(account_id))
    from .operator_suspension import STATUS as SUSPENDED, lease_valid
    if lease.get('status') == SUSPENDED and not lease_valid(state_root, lease):
        return {'source':'operator_suspension_invalid','request_id':lease.get('request_id'),'status':SUSPENDED}''')
amend('scripts/ares_campaign_v3/coordination.py','''    def retire_manual(self, account_id: str, request_id: str, *, expected_sha256: str) -> dict[str, Any]:''','''    def suspend_operator(self, account_id: str, request_id: str, *, expected_sha256: str) -> dict[str, Any]:
        \"\"\"Retire only coordination under exact receipt and CAS; never campaign COMPLETE.\"\"\"
        import hashlib
        from .operator_suspension import validate, path, STATUS, lease_valid
        validate(self.root.parent, account_id, request_id)
        receipt_sha = hashlib.sha256(path(self.root.parent, account_id, request_id).read_bytes()).hexdigest()
        def mutate(current):
            if current.get('status') == STATUS and lease_valid(self.root.parent, current):
                return current
            if (current.get('account_id') != account_id or current.get('request_id') != request_id
                    or current.get('status') != 'RECOVERY_PENDING' or current.get('blocks_readers') is not True
                    or hashlib.sha256(self.path(account_id).read_bytes()).hexdigest() != expected_sha256):
                raise WriterLeaseConflict('operator suspension lease CAS/owner/state mismatch')
            return {**current, 'status':STATUS, 'blocks_readers':False, 'campaign_qa_complete':False,
                    'released_at_utc':_utc(), 'updated_at_utc':_utc(), 'operator_suspension_sha256':receipt_sha}
        return self._locked_update(account_id, mutate)

    def retire_manual(self, account_id: str, request_id: str, *, expected_sha256: str) -> dict[str, Any]:''')
newfile='scripts/ares_campaign_v3/operator_suspension.py';p=H/'staged'/newfile
assert not (R/newfile).exists();changes[newfile]={'before_sha256':None,'after_sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
(H/'changes.json').write_text(json.dumps(changes,indent=2)+'\n')
# Preserve exact other-account configuration projection for regression.
c=json.loads((R/'data/ares/meta-ads/engine-v3/config.json').read_text());c['accounts'].pop(A)
(H/'other-account-config-before.json').write_text(json.dumps(c,sort_keys=True,indent=2)+'\n')
# Positive inventory: code consumers, account contracts, schedules and cache metadata only.
consumers=[]
for p in (R/'scripts').glob('ares-eggbev*.py'):
 text=p.read_text()
 if 'load_runtime_modules' in text or 'get_token_from_1password' in text:consumers.append({'path':str(p.relative_to(R)),'central_runtime':'load_runtime_modules' in text,'reads_account_binding':"token_1password_item" in text})
schedules=[]
for p in [Path('/root/.hermes/profiles/ares/cron/jobs.json')]:
 if p.exists():
  data=json.loads(p.read_text());rows=data if isinstance(data,list) else data.get('jobs',[])
  if isinstance(rows,dict):rows=rows.values()
  for row in rows:
   if 'eggbev' in json.dumps(row).lower():schedules.append({k:row.get(k) for k in ['id','name','enabled','schedule','no_agent','deliver','command']})
cron=subprocess.run(['crontab','-l'],capture_output=True,text=True).stdout
(H/'consumer-inventory.json').write_text(json.dumps({'consumers':consumers,'engine_transport':'scripts/ares_campaign_v3/cli.py','bindings':[p for p in changes if p.endswith('.json')],'scheduled_jobs':schedules,'system_cron_eggbev':[line for line in cron.splitlines() if 'eggbev' in line.lower()],'cache_policy':'New dedicated Ana/m6 cache; item equality mandatory; old caches retained historical, no fallback; no cache secrets backed up','rollback_policy':'CAS restore code/config from non-secret backups only; prohibited old identities must remain disabled; any rollback keeps operator suspension fence and campaign write hold'},ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'staged_files':len(changes),'consumers':len(consumers),'scheduled_jobs':len(schedules)}))

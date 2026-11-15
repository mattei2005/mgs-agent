from pathlib import Path
import json,hashlib,copy
R=Path('/root/mgs-agent');H=Path(__file__).parent;S=H/'staged'
A='1481815942722118';SRC='1034081997659047';M='clone_cross_account_prestaged';RID='eggbev03-cross-account-1571623835822858352';AUTH='1571652369467445359'
E='data/ares/meta-ads/audit/maintenance/t_e524bad0/live-target-readback.json'
ITEM='Token Meta API - 00 - ANUNCIANTE - Ana Cunha - eggbev- G006';KEY='mgs-meta-app-953171080682697';CACHE='/root/.cache/mgs/ares-meta-token-eggbev01-ana-m6.json'
B={'token_item':ITEM,'token_identity':'Ana Cunha','token_user_id':'122147293515218951','meta_app_id':'953171080682697','app_key':KEY,'token_cache_path':CACHE,'marketing_api_access_tier':'development_access'}
pins=json.loads((H/'initial-pins.json').read_text())
def edit(path,fn):
 p=S/path
 if not p.exists():
  p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((R/path).read_bytes());pins[path]=hashlib.sha256((R/path).read_bytes()).hexdigest()
 d=json.loads(p.read_text());fn(d);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
cap={'enabled':True,'mode':M,'authority_message_id':AUTH,'source_account_id':SRC,'target_account_id':A,'policy_source':'data/ares/meta-ads/policies/eggbev01-to03-clone-authority.json','semantics':'source_derived_shell_local_seed_copy','runner':'scripts/ares-eggbev-target-clone.py','live_campaign_acceptance_verified':False,'serving_verified':False,'maintenance_canary_authorized':False}
def pol(d):
 d.update(status='active',implementation_verified=True,capability=cap,advertiser_binding=B,implementation_receipt='data/ares/meta-ads/audit/maintenance/t_e524bad0/acceptance.json',remote_page_access_verified=False)
 d['technical_identity_validation']={'status':'active','account_id':A,'authorized_by_discord_id':'344196393512075265','authority_message_id':AUTH,'allowed_reads':['me:id,name','debug_token:self_only'],'expected_app_id':'953171080682697','scope':'Own approved advertiser credential metadata only; no asset enumeration, grants, credential replacement or Page ACL write'}
 d['naming_scope']={'policy':'data/ares/meta-ads/policies/eggbev-us-en-global-creation-naming.json','mode':M,'scope':'Exact allowlisted cross-account request only; preserve other naming modes and accounts'}
edit('data/ares/meta-ads/policies/eggbev01-to03-clone-authority.json',pol)
def cfg(d):
 a=d['accounts'][A];a.update(B);a.update(supported_modes=[M],ad_serving_route='lineage_required_for_new_media',write_enabled=True,cross_account_clone=cap,onboarding_status='installed_guarded_requested_Page_readiness_required',binding_evidence=E)
 a['campaign_policy']={'name_regex':r'[0-9]+ - .+ - ENG - US - \(pg_[0-9]+\) - C[0-9]{2,}','budget_update_required':True,'budget_source':'campaign_create','configured_status':'ACTIVE','start_local_time':None,'allowed_ad_counts':[3],'required_media_variants':['vertical','square'],'creative_materialization_route':'inline_copy','immediate_start_request_ids':[RID],'immediate_start_requires_final_ok':True}
 d['points_per_mode'][M]=30
 d['mode_taxonomy'][M]='Source account READ_ONLY references; explicit source-derived campaign/adset shells in target03, PAUSED local target seeds and same-account same-Page final copies. Not native cross-account copy, from-zero defaults or social-proof preservation.'
edit('data/ares/meta-ads/engine-v3/config.json',cfg)
def acct(d):
 a=d['accounts'][0];a.update(token_1password_item=ITEM,token_field='oauth_token',token_cache_path=CACHE,credential_resolution_status='approved_Ana_m6_binding_installed_Page_request_gate_required',write_mode='guarded_exact_request_only')
 a['meta_app']={**B,'app_id':'953171080682697','app_name':'minibot m6'}
 a['runtime_routes']['campaign_cloning'].update(supported_modes=[M],write_enabled=True,runner='scripts/ares-eggbev-target-clone.py',capability_authority=AUTH)
 a['runtime_routes']['campaign_creation']['write_enabled']=False
 a['credential_metadata']={'item_id':'xxgqyiuijcu4rfrcmfmme6iduq','binding_evidence':E}
edit('data/ares/meta-ads/accounts/'+A+'.json',acct)
def operation(d):
 d.update(status='cross_account_capability_installed_remote_Page_readiness_required',supported_modes=[M],token_item=ITEM,advertiser_identity='Ana Cunha',meta_app_id='953171080682697',write_enabled=True,activation_enabled=True,media_upload_enabled=True)
 d['write_scope_note']='Exact request-specific capability only; fresh Page/advertiser/source/media gates and subsequent final summary OK required. Installation is not Page access, publication or serving proof.'
 d['cross_account_clone_implementation_authority'].update(status='active',capability_enabled=True)
 d['readiness']['historical_other_Page_evidence']=copy.deepcopy(d['readiness'])
 d['readiness'].update(page_access_verified=False,requested_page_token='pg_23187',requested_page_id_candidate='1272524399287905',reason='Exact requested Page live read must pass; source reader exclusion respected. Historical other-Page denials are not a global grant conclusion.',maintenance_evidence=E)
 d['next_step']='Same central prepare --input preserved request --confirm-prepare. No campaign writes; gate may defer source reader or report exact requested Page access. Delivery owner posts sealed full summary including15 preserved PAUSED seeds and awaits subsequent explicit OK.'
edit('data/ares/meta-ads/operations/Eggbev-US-CC-EN-03-BOT.json',operation)
def v3(d):
 d.update(B);d.update(status='installed_guarded_request_scoped',supported_modes=[M],ad_serving_route='lineage_required_for_new_media',write_enabled=True,activation_enabled=True,media_upload_enabled=True,immediate_start_request_ids=[RID],runner='scripts/ares-eggbev-target-clone.py',cross_account_clone=cap,blocked_reason='Not a blanket write release: exact source reader, requested Page/PBIA, media, sealed summary and subsequent explicit OK remain mandatory.',live_campaign_acceptance_verified=False)
edit('data/ares/meta-ads/operations/Eggbev-US-CC-EN-03-BOT-v3.json',v3)
def consumers(d):
 a=d['onboarding_candidates'].pop('Eggbev-US-CC-EN-03-BOT');a.update(status='installed_guarded_exact_cross_account_request',supported_modes=[M],write_enabled=True,activation_enabled=True,media_upload_enabled=True,capability_authority=AUTH,runner='scripts/ares-eggbev-target-clone.py',live_page_access_verified=False,recurring_automation_enabled=False)
 d['consumers']['Eggbev-US-CC-EN-03-BOT']=a
edit('data/ares/meta-ads/strategy-families/chatpion-bot-messenger-consumers.json',consumers)
def naming(d):
 d['cross_account_replacement_extension']={'status':'active','authority_message_id':AUTH,'source_account_id':SRC,'target_account_id':A,'mode':M,'allowed_request_ids':[RID],'scope':'Exact request only, same global/page sequence and ledger; supersedes no existing mode; no DUP suffix; source unchanged.'}
edit('data/ares/meta-ads/policies/eggbev-us-en-global-creation-naming.json',naming)
def advertiser(d):
 d['account_runtime_bindings'][A]={'app_id':'953171080682697','token_identity':'Ana Cunha','app_key':KEY,'readback':E,'tier':'development_access','Page_readiness_verified':False,'capability_authority':AUTH}
 if A not in d['runtime_bindings_changed_scope']:d['runtime_bindings_changed_scope'].append(A)
 d['implementation_status']='EGGBEV01_AND03_BINDINGS_INSTALLED_03_REQUESTED_PAGE_GATE_REQUIRED'
 d['next_step']='Eggbev03 exact cross-account capability installed; fresh requested Page/source/media readiness and final summary OK remain. Eggbev02 unchanged; no new credential or permissions.'
edit('data/ares/meta-ads/policies/eggbev-advertiser-profile.json',advertiser)
(H/'initial-pins.json').write_text(json.dumps(pins,indent=2)+'\n')
print('data staged')

"""Generate scoped contract candidates; no production writes or campaign calls."""
import sys,json,copy,hashlib
from pathlib import Path
R=Path('/root/mgs-agent')
S=Path('/root/.hermes/profiles/ares/cache/scratch/eggbev03-same-account-1571911721063546892')
H=R/'data/ares/meta-ads/audit/maintenance/eggbev03-same-account-1571911721063546892'
sys.path.insert(0,str(S/'scripts'))
from ares_campaign_v3.eggbev_same_account_replacement import spec,digest
rid='eggbev03-c212-replacement-1571894746719330377';aid='1481815942722118';auth='1571911721063546892'
q=json.loads((R/'data/ares/meta-ads/requests'/(rid+'.json')).read_text())
policy_rel='data/ares/meta-ads/policies/eggbev03-same-account-replacement.json'
p={'schema_version':1,'status':'active','implementation_verified':True,'mode':'clone_target_prestaged',
   'authorized_by_discord_id':'344196393512075265','authority_message_id':auth,
   'authority_content_sha256':hashlib.sha256(b'sim').hexdigest(),'source_thread_id':q['source_thread_id'],
   'account_ids':[aid],'request_only':True,'future_requests_authorized':False,
   'exclusions':['other accounts','source changes','credential changes','billing','automation changes','old request recovery'],
   'requests':{rid:{'spec_sha256':digest(spec(q)),'source_campaign_id':q['source_campaign_id'],
      'template_ad_ids':['120250364730460507','120250364730470507','120250364730460507'],
      'source_snapshot_cardinality':4,'output_ads_per_campaign':3,
      'mapping_note':'Preserve all four source objects in snapshot. Explicit output mapping reuses source AFS templates with directly observed empty primary text and literal CTA/features; each output replaces media/copy as requested. No source ad is deleted or mislabeled as a seed.',
      'target_page_id':'1272524399287905','target_page_token':'pg_23187',
      'start_intent':'IMMEDIATE_EXPLICIT_NEW_REQUEST','commercial_execution_message_id':'1571904284692316444',
      'final_summary_ok_required':True,'technical_paused_seeds_preserved':True}}}
cap={'enabled':True,'account_id':aid,'authorized_by':'344196393512075265','authority_message_id':auth,
     'policy_source':policy_rel,'runner':'scripts/ares-eggbev-target-clone.py','allowed_request_ids':[rid],
     'mode':'clone_target_prestaged','live_campaign_acceptance_verified':False,'serving_verified':False,
     'legacy_copied_adset_page_switch_enabled':False}
paths=['data/ares/meta-ads/engine-v3/config.json','data/ares/meta-ads/operations/Eggbev-US-CC-EN-03-BOT.json','data/ares/meta-ads/operations/Eggbev-US-CC-EN-03-BOT-v3.json','data/ares/meta-ads/accounts/1481815942722118.json','data/ares/meta-ads/policies/eggbev-us-en-global-creation-naming.json']
for rel in paths:
    old=json.loads((H/'baseline'/rel).read_text());d=copy.deepcopy(old)
    if rel.endswith('engine-v3/config.json'):
        a=d['accounts'][aid];a['supported_modes'].append('clone_target_prestaged');a['target_page_replacement']=cap
        a['campaign_policy']['immediate_start_request_ids'].append(rid)
        assert all(d['accounts'][k]==old['accounts'][k] for k in old['accounts'] if k!=aid)
        assert {k:v for k,v in d.items() if k!='accounts'}=={k:v for k,v in old.items() if k!='accounts'}
    elif rel.endswith('eggbev-us-en-global-creation-naming.json'):
        d['same_account_replacement_extension']={'status':'active','account_id':aid,'mode':'clone_target_prestaged','allowed_request_ids':[rid],'authority_message_id':auth,'scope':'this independent request only; preserve shared global naming and existing three-account history rules'}
    elif rel.endswith('accounts/1481815942722118.json'):
        a=d['accounts'][0];a['runtime_routes']['campaign_cloning']['supported_modes'].append('clone_target_prestaged')
        a['runtime_routes']['campaign_cloning']['same_account_replacement_authority']=auth
    else:
        d['supported_modes'].append('clone_target_prestaged');d['target_page_replacement']=cap
        if 'immediate_start_request_ids' in d:d['immediate_start_request_ids'].append(rid)
        d['same_account_request_only_authority']=auth
        d['same_account_replacement_policy']=policy_rel
    target=S/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
target=S/policy_rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(p,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'staged_contracts':len(paths)+1,'request_only':rid,'other_accounts_unchanged':True,'campaign_writes':0}))

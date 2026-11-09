import copy,json,sys
from pathlib import Path
from unittest.mock import patch
import pytest
ROOT=Path('/root/.hermes/profiles/ares/cache/scratch/shein-omission-manager-maintenance')
sys.path.insert(0,str(ROOT/'stage'));sys.path.insert(1,'/root/mgs-agent/scripts')
from ares_campaign_v3 import reviewed_copy_omissions as m
from ares_campaign_v3.shein_continuation import content_digest

def fixtures():
 return [json.loads((ROOT/n).read_text()) for n in ['receipt.json','state.before.json','checkpoint.before.json','messages.json','index.staged.json']]

def validate(receipt=None,state=None,checkpoint=None,messages=None,index=None,authority=True):
 r,s,c,msg,i=fixtures();r=receipt or r;s=state or s;c=checkpoint or c;msg=messages or msg;i=index or i
 def get(path):return copy.deepcopy(msg['history'] if '?' in path else msg['prompt'] if path.endswith(r['prompt_id']) else msg['approval'])
 with patch.object(m,'POLICY_INDEX',ROOT/'index.staged.json'),patch.object(Path,'read_text',autospec=True,side_effect=lambda p,*a,**k:json.dumps(i) if p==ROOT/'index.staged.json' else ORIGINAL_READ(p,*a,**k)),patch('ares_campaign_v3.shein_channel_authority.verify',return_value={'verified':authority}):
  return m.validate(r,s,c,get_message=get)
ORIGINAL_READ=Path.read_text

def test_exact_manager_receipt():assert validate()['verified']

@pytest.mark.parametrize('kind',['marker','grant_actor','grant_digest','actor','origin','account','clock','budget','source','slot','approval_text','intervening','authority'])
def test_reject_invalid_context(kind):
 r,s,c,msg,i=fixtures();g=i['requests'][r['binding']['request_id']]
 if kind=='marker':g.pop('review_authority')
 if kind=='grant_actor':g['approved_by']='99999'
 if kind=='grant_digest':g['receipt_digest']='bad'
 if kind=='actor':s['request']['authorized_by']='99999'
 if kind=='origin':s['request']['source_thread_id']='99999'
 if kind=='account':c['account_id']='99999'
 if kind=='clock':s['execution_started_at']='changed'
 if kind=='budget':s['manifest']['campaigns'][0]['campaign_updates']['daily_budget']=1
 if kind=='source':s['source']['ads'][0]['id']='99999'
 if kind=='slot':c['bundles'][0]['readback_results'][0]['body']['id']='99999';r['binding']['slots'][0]['ad_id']='99999';g['receipt_digest']=content_digest(r)
 if kind=='approval_text':msg['approval']['content']='Não'
 if kind=='intervening':msg['history'].append({'id':str(int(r['approval_id'])-1),'author':{'id':r['approved_by'],'bot':False},'content':'another decision'})
 with pytest.raises(ValueError):validate(r,s,c,msg,i,authority=kind!='authority')

def test_ceo_path_preserved_without_manager_marker():
 r,s,c,msg,i=fixtures();r['approved_by']='344196393512075265';msg['approval']['author']['id']=r['approved_by'];r['approval_digest']=m.message_digest(msg['approval']);g=i['requests'][r['binding']['request_id']];g['approved_by']=r['approved_by'];g.pop('review_authority');g['receipt_digest']=content_digest(r)
 assert validate(r,s,c,msg,i,authority=False)['verified']

def test_only_bound_missing_fields_accepted():
 r,s,c,msg,i=fixtures();proof=validate();slot=r['binding']['slots'][0];expected=next(a['creative_payload'] for d in s['manifest']['campaigns'] if d['idempotency_key']==slot['key'] for a in d['ads'] if a['source_ad_id']==slot['source_ad_id']);from ares_campaign_v3.creative_copy_policy import effective
 expected=effective(expected);actual=copy.deepcopy(expected);actual['id']=slot['creative_id'];f=actual['degrees_of_freedom_spec']['creative_features_spec']
 for k in r['accepted_omissions']:f.pop(k)
 marker=m.CURRENT.set(proof)
 try:
  desired=m.expected_degrees(actual,expected);assert set(expected['degrees_of_freedom_spec']['creative_features_spec'])-set(desired['creative_features_spec'])==set(r['accepted_omissions'])
  additional=copy.deepcopy(actual);additional['degrees_of_freedom_spec']['creative_features_spec'].pop('inline_comment')
  with pytest.raises(ValueError):m.expected_degrees(additional,expected)
  changed_id=copy.deepcopy(actual);changed_id['id']='other'
  with pytest.raises(ValueError):m.expected_degrees(changed_id,expected)
 finally:m.CURRENT.reset(marker)
 assert m.CURRENT.get() is None

def test_no_review_keeps_strict_expected():
 _,s,*_=fixtures();expected=s['manifest']['campaigns'][0]['ads'][0]['creative_payload'];assert m.expected_degrees({},expected)==expected['degrees_of_freedom_spec']

import copy,json,sys
from pathlib import Path
from dataclasses import replace
import pytest
ROOT=Path('/root/.hermes/profiles/ares/cache/scratch/shein-ad-schedule-maintenance')
sys.path.insert(0,str(ROOT/'stage'));sys.path.insert(1,'/root/mgs-agent/scripts')
from ares_campaign_v3 import reviewed_ad_schedule as m,progress
from ares_campaign_v3.schema import Manifest
from ares_campaign_v3.planning import Planner
from ares_campaign_v3.transport import BatchOperation,BatchResult
from ares_campaign_v3.creative_copy_policy import effective
BASE=Path('/root/mgs-agent/data/ares/meta-ads');RID='shein-1569343054090084383'

def data():
 s=json.loads((BASE/'state/shein-campaigns/single-clone'/RID/'state.json').read_text())
 c=json.loads((BASE/'engine-v3/state/checkpoints'/f'{RID}-7840111366055613.json').read_text())
 r=json.loads((ROOT/'receipt.json').read_text());messages=json.loads((ROOT/'dialogue-messages.json').read_text())
 def get(path):return copy.deepcopy(messages['history'] if '?' in path else messages[path.rsplit('/',1)[1]])
 return s,c,r,get

def proof():
 s,c,r,get=data();return m.validate(r,s,c,get_message=get,verify_authority=lambda req:{'verified':True})

def bundle(index=0):
 s,*_=data();b=Planner().build(Manifest.from_dict(s['manifest'])).lanes['7840111366055613'][index]
 return replace(b,campaigns=tuple(replace(c,ads=tuple(replace(a,creative_payload=effective(a.creative_payload)) for a in c.ads)) for c in b.campaigns))

def test_valid_binding():assert proof()['verified']

@pytest.mark.parametrize('field',['request','manifest','target_manifest','source','execution_started_at'])
def test_binding_mutation_rejected(field):
 s,c,r,get=data()
 if field=='execution_started_at':s[field]+='x'
 else:s[field]['unexpected']='delta'
 with pytest.raises(ValueError):m.validate(r,s,c,get_message=get,verify_authority=lambda req:{'verified':True})

@pytest.mark.parametrize('kind',['account','lost_campaign','lost_ad','source','actor','digest','authority'])
def test_invalid_review_rejected(kind):
 s,c,r,get=data()
 if kind=='account':c['account_id']='99999'
 if kind=='lost_campaign':c['bundles'][0]['campaign_ids']=[]
 if kind=='lost_ad':c['bundles'][0]['confirmed_objects']={}
 if kind=='source':r['source_ad_ids']=['99999']
 if kind=='actor':r['review']['approved_by']='99999'
 if kind=='digest':r['review']['approval_digest']='bad'
 with pytest.raises(ValueError):m.validate(r,s,c,get_message=get,verify_authority=lambda req:{'verified':kind!='authority'})

def test_default_no_change():
 b=bundle();ops=list(b.stages[3].operations);assert m.prepare(b,ops,'existing_post_copy_and_creative') is ops

def test_initial_missing_creative_dependency_and_other_ad_unchanged():
 b=bundle(1);ops=list(b.stages[3].operations);record={};p=m.CURRENT.set(proof());j=progress.CURRENT.set((record,lambda:None))
 try:
  new=m.prepare(b,ops,'existing_post_copy_and_creative');assert len(new)==len(ops)
  a=next(x for x in new if x.name=='existing_post_ad_copy_1_1');assert a.relative_url=='act_7840111366055613/ads' and a.kind=='ad_create'
  assert a.body['status']=='PAUSED' and a.body['source_ad_id']=='120256206547070150';assert 'ad_schedule_start_time' not in a.body
  assert a.depends_on=='existing_post_creative_1_1' and new.index(next(x for x in new if x.name==a.depends_on))<new.index(a)
  other=next(x for x in ops if x.name=='existing_post_ad_copy_1_2');assert other in new and other.kind=='existing_post_ad_copy'
  assert ops==list(b.stages[3].operations)
 finally:m.CURRENT.reset(p);progress.CURRENT.reset(j)

def test_recovery_reuses_verified_persisted_creatives():
 b=bundle();ops=[BatchOperation('existing_post_recovery_ad_copy_1_1','POST','120256206547070150/copies',{'adset_id':'120256216323910150','status_option':'PAUSED'},kind='existing_post_ad_copy')];p=m.CURRENT.set(proof());j=progress.CURRENT.set(({'existing_post_creative_ids':{'1.1':'1136589995943189'}},lambda:None))
 try:
  new=m.prepare(b,ops,'existing_post_recovery_materialize');assert len(new)==1 and new[0].body['creative']=={'creative_id':'1136589995943189'} and new[0].depends_on is None
 finally:m.CURRENT.reset(p);progress.CURRENT.reset(j)

@pytest.mark.parametrize('kind',['no_journal','missing_creative','active','payload','account'])
def test_prepare_rejects_unsafe_context(kind):
 b=bundle();p=m.CURRENT.set(proof());record={};j=progress.CURRENT.set(None if kind=='no_journal' else (record,lambda:None))
 ops=[BatchOperation('existing_post_recovery_ad_copy_1_1','POST','120256206547070150/copies',{'adset_id':'120256216323910150','status_option':'PAUSED'},kind='existing_post_ad_copy')]
 if kind=='active':b=replace(b,campaigns=(replace(b.campaigns[0],status='ACTIVE'),*b.campaigns[1:]))
 if kind=='payload':
  c=b.campaigns[0];a=c.ads[0];b=replace(b,campaigns=(replace(c,ads=(replace(a,creative_payload={'bad':'new'}),*c.ads[1:])),*b.campaigns[1:]))
 if kind=='account':b=replace(b,account_id='99999')
 try:
  with pytest.raises(ValueError):m.prepare(b,ops,'existing_post_recovery_materialize')
 finally:m.CURRENT.reset(p);progress.CURRENT.reset(j)

@pytest.mark.parametrize('field',['ad_schedule_start_time','ad_schedule_end_time'])
def test_individual_schedule_fails_final_readback(field):
 p=m.CURRENT.set(proof())
 try:
  with pytest.raises(ValueError):m.verify_results(bundle(),[BatchResult('readback_ads_1',200,{'data':[{'source_ad_id':'120256206547070150',field:'2026-11-09T00:00:00-0500'}]})])
 finally:m.CURRENT.reset(p)

def test_final_no_schedule_and_context_reset():
 p=m.CURRENT.set(proof())
 try:m.verify_results(bundle(),[BatchResult('readback_ads_1',200,{'data':[{'source_ad_id':'120256206547070150'}]})])
 finally:m.CURRENT.reset(p)
 assert m.CURRENT.get() is None

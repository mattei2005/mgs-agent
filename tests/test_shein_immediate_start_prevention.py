"""Offline regression: morning NOW must not inherit source midnight. No Meta I/O."""
import copy,json,sys
from pathlib import Path
from datetime import datetime
from types import SimpleNamespace as N
from unittest.mock import patch
import pytest
ROOT=Path(__file__).resolve().parent
if (ROOT/'stage/ares_campaign_v3').exists():sys.path.insert(0,str(ROOT/'stage'))
sys.path.insert(1,'/root/mgs-agent/scripts')
from ares_campaign_v3 import reviewed_ad_schedule as m,progress
from ares_campaign_v3.shein_single_clone import resolve_intent
from ares_campaign_v3.transport import BatchOperation,BatchResult,FakeBatchTransport
NOW=datetime.fromisoformat('2026-11-09T08:29:00-05:00')
POLICY={'enabled':True,'approved_by':'344196393512075265','scope':'new_pure_clone_immediate_requests',
        'target_individual_start':'INHERIT_NEW_ADSET_START','source_mutation':'FORBIDDEN',
        'source_message_id':'offline-policy-test-only'}

def state(start='2026-11-09T00:00:00-05:00',end=None):
 cp={'name':'offline-only-creative','object_story_spec':{'page_id':'77777','link_data':{'link':'https://example.invalid/offline'}}}
 ad={'id':'11111','creative':copy.deepcopy(cp)}
 if start is not None:ad['ad_schedule_start_time']=start
 if end is not None:ad['ad_schedule_end_time']=end
 spec={'mode':'pure_clone','status':'PAUSED','start_intent':'IMMEDIATE','idempotency_key':'offline-1-c1','ads':[{'source_ad_id':'11111','name':'offline-only-ad','creative_payload':cp}]}
 return {'request':{'request_id':'offline-1','account':'55555','mode':'pure_clone','start_now':True},'resolved_request':{'start_now':True},'manifest':{'operation':'SHEIN-US-DIRECT','campaigns':[spec]},'target_manifest':{'campaigns':[copy.deepcopy(spec)]},'source':{'ad_schedule_fields_verified':True,'ads':[ad]},'execution_started_at':NOW.isoformat()}

def bundle(s):
 c=s['manifest']['campaigns'][0];a=c['ads'][0]
 return N(account_id='55555',campaigns=[N(idempotency_key=c['idempotency_key'],status='PAUSED',ads=[N(source_ad_id='11111',name=a['name'],creative_payload=a['creative_payload'])])])

def ops():
 return [BatchOperation('existing_post_ad_copy_1_1','POST','11111/copies',{'adset_id':'66666','status_option':'PAUSED'},kind='existing_post_ad_copy'),BatchOperation('existing_post_creative_1_1','POST','act_55555/adcreatives',{'name':'offline-only-creative'},kind='creative_create')]

def transform(s):
 plan=m.immediate_plan(s,POLICY,now=NOW);assert plan
 marker=m.CURRENT.set({'verified':True,'receipt':plan,'state':s,'preventive':True});journal=progress.CURRENT.set(({},lambda:None))
 try:return plan,m.prepare(bundle(s),ops(),'existing_post_copy_and_creative')
 finally:m.CURRENT.reset(marker);progress.CURRENT.reset(journal)

def test_morning_now_is_today_current_time_not_midnight():
 r=resolve_intent({'start_now':True,'start_time':'2026-11-09T00:00:00-05:00'},{},now=NOW,profile={'timezone':'America/New_York'})
 assert datetime.fromisoformat(r['start_time']).astimezone(NOW.tzinfo).isoformat()=='2026-11-09T08:29:30-05:00'

def test_now_beats_stale_default_midnight_marker_without_timezone_dependency():
 r=resolve_intent({'start_now':True,'start_next_midnight':True},{},now=NOW,profile={})
 assert 'start_next_midnight' not in r and datetime.fromisoformat(r['start_time']).astimezone(NOW.tzinfo).hour==8

def test_explicit_future_clock_unchanged():
 r={'start_time':'2026-11-10T17:00:00-05:00'};assert resolve_intent(r,{},now=NOW,profile={'timezone':'America/New_York'})==r

def test_default_midnight_only_when_no_immediate_intent():
 with patch('ares_campaign_v3.shein_single_clone.request_clock',return_value=(None,'offline')):
  r=resolve_intent({'start_next_midnight':True},{},now=NOW,profile={'timezone':'America/New_York'})
 assert r['start_time']=='2026-11-10T00:00:00-05:00'

@pytest.mark.parametrize('start',['2026-11-09T00:00:00-05:00','2026-11-08T00:00:00-05:00','2026-11-09T17:00:00-05:00'])
def test_now_never_inherits_any_source_individual_start(start):
 s=state(start);before=copy.deepcopy(s);plan,new=transform(s);direct=next(x for x in new if x.kind=='ad_create')
 assert direct.relative_url=='act_55555/ads' and direct.body['source_ad_id']=='11111'
 assert 'ad_schedule_start_time' not in direct.body and direct.body['status']=='PAUSED'
 assert direct.body['adset_id']=='66666' and direct.depends_on=='existing_post_creative_1_1'
 assert all(x.relative_url!='11111/copies' for x in new) and s==before

def test_future_individual_end_preserved():
 end='2026-11-12T22:00:00-05:00';s=state(end=end);plan,new=transform(s);assert next(x for x in new if x.kind=='ad_create').body['ad_schedule_end_time']==end
 marker=m.CURRENT.set({'verified':True,'receipt':plan,'state':s})
 try:m.verify_results(bundle(s),[BatchResult('readback_ads_1',200,{'data':[{'id':'88888','source_ad_id':'11111','ad_schedule_end_time':end}]})])
 finally:m.CURRENT.reset(marker)

@pytest.mark.parametrize('end',['2026-11-08T22:00:00-05:00','2026-11-09T08:28:00-05:00'])
def test_expired_end_rejected_before_any_write(end):
 with pytest.raises(ValueError,match='before writes'):m.immediate_plan(state(end=end),POLICY,now=NOW)

def test_no_individual_start_keeps_native_copy():assert m.immediate_plan(state(None),POLICY,now=NOW) is None

@pytest.mark.parametrize('kind',['future','not_now','new_media','disabled','wrong_authority'])
def test_other_intents_not_silently_changed(kind):
 s=state();p=copy.deepcopy(POLICY)
 if kind=='future':s['resolved_request']={'start_time':'2026-11-10T00:00:00-05:00'}
 if kind=='not_now':s['resolved_request']={'start_next_midnight':True}
 if kind=='new_media':s['request']['mode']='from_zero_prestaged'
 if kind=='disabled':p['enabled']=False
 if kind=='wrong_authority':p['approved_by']='other'
 assert m.immediate_plan(s,p,now=NOW) is None

@pytest.mark.parametrize('kind',['missing_preflight','scheduled_manifest','active_manifest','naive_source'])
def test_unsafe_plan_rejected(kind):
 s=state()
 if kind=='missing_preflight':s['source'].pop('ad_schedule_fields_verified')
 if kind=='scheduled_manifest':s['manifest']['campaigns'][0]['start_intent']='SCHEDULED'
 if kind=='active_manifest':s['manifest']['campaigns'][0]['status']='ACTIVE'
 if kind=='naive_source':s['source']['ads'][0]['ad_schedule_start_time']='2026-11-09T00:00:00'
 with pytest.raises(ValueError):m.immediate_plan(s,POLICY,now=NOW)

def test_central_engine_batches_direct_ad_without_source_write(tmp_path):
 from ares_campaign_v3.engine import CampaignEngine
 s=state();plan=m.immediate_plan(s,POLICY,now=NOW);marker=m.CURRENT.set({'verified':True,'receipt':plan,'state':s});record={};journal=progress.CURRENT.set((record,lambda:None));transport=FakeBatchTransport('55555')
 try:
  engine=CampaignEngine({'state_root':str(tmp_path/'state'),'audit_root':str(tmp_path/'audit')},transport_factory=lambda aid:transport)
  results=engine._batch(bundle(s),transport,ops(),'existing_post_copy_and_creative')
  assert len(results)==2 and record['confirmed_objects']['existing_post_ad_copy_1_1']['id']
  assert all(x['path']!='11111/copies' for x in record['write_journal'][0]['operations'])
 finally:m.CURRENT.reset(marker);progress.CURRENT.reset(journal)

def test_source_schedule_fields_are_in_canonical_preflight_query():
 import inspect
 from ares_campaign_v3 import shein_single_clone
 text=inspect.getsource(shein_single_clone._prepare)
 assert 'ad_schedule_start_time,ad_schedule_end_time' in text and "'ad_schedule_fields_verified': True" in text

def test_normalization_does_not_accept_feature_omissions():
 from ares_campaign_v3.creative_copy_policy import verify_creative
 expected={'degrees_of_freedom_spec':{'creative_features_spec':{'image_background_gen':{'enroll_status':'OPT_OUT'},'image_touchups':{'enroll_status':'OPT_IN'}}}}
 with pytest.raises(ValueError):verify_creative({'id':'offline-only','degrees_of_freedom_spec':{'creative_features_spec':{'image_background_gen':{'enroll_status':'OPT_OUT'}}}},expected)

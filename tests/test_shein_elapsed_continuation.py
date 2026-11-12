"""Offline regressions: every fixture and write is confined to tmp_path."""
import copy
import json
from datetime import datetime, timezone
from types import SimpleNamespace
import pytest
from ares_campaign_v3 import shein_elapsed_continuation as m
from ares_campaign_v3.prevalidation import content_digest

NOW = '2026-11-12T07:00:00+00:00'
START = '2026-11-12T01:00:00-05:00'
OBSERVED = '2026-11-12T01:20:27-0500'
RID = 'test-explicit-1'
AID = '123'


def seal(value):
    value['prevalidated'] = True
    value['prevalidation'] = {'content_digest': content_digest(value)}
    return value


def fixture():
    policy = {'enabled': True, 'approved_by': '344196393512075265',
        'source_message_id': '1558142161659105342', 'source_thread_id': '1557274000680288307',
        'scope': 'explicit_start_same_account_day_only', 'when_elapsed': 'IMMEDIATE_AFTER_QA',
        'account_timezone': 'verified_ad_account_timezone', 'preserve_future_schedule': True,
        'preserve_explicit_paused': True, 'preserve_original_requested_time_in_audit': True,
        'implicit_next_day_rollover': False,
        'already_created_objects': 'readback-first continuation of same request and IDs, never a new copy or silent manifest rewrite'}
    request = {'request_id': RID, 'account': AID, 'status': 'ACTIVE', 'mode': 'pure_clone',
        'quantity': 2, 'source_channel_id': '1548150155184701440', 'source_thread_id': '1558134703565967394',
        'source_message_id': '1570314359530459327', 'authorized_by': '1055570806945620030',
        'start_time': START, 'budget_usd': '85'}
    specs = [{'account_id': AID, 'status': 'PAUSED', 'start_time': START,
              'idempotency_key': RID+'-c'+str(i), 'ads': [{'source_ad_id': '700'}],
              'campaign_updates': {'daily_budget': '8500', 'bid_strategy': 'COST_CAP'}} for i in range(2)]
    creation = seal({'request_id': RID, 'operation': 'SHEIN-US-DIRECT', 'campaigns': specs})
    target = copy.deepcopy(creation)
    for c in target['campaigns']: c['status'] = 'ACTIVE'
    seal(target)
    state = {'request': request, 'resolved_request': copy.deepcopy(request), 'phase': 'POSTPROCESS_PENDING',
        'account': {'id': 'act_123', 'timezone_name': 'America/New_York'},
        'manifest': creation, 'target_manifest': target,
        'execution_started_at': '2026-11-12T05:48:38.342000+00:00', 'prepared_at': '2026-11-12T05:49:00+00:00',
        'source': {'adset': {'bid_amount': 95}}, 'engine_result': {'campaign_ids': ['456', '457']}}
    bundle = {'status': 'COMPLETE', 'stage': 'readback_complete', 'campaign_ids': ['456','457'],
        'adset_ids': ['789','790'], 'ad_ids': ['900','901'], 'idempotency_keys': [c['idempotency_key'] for c in specs],
        'timings': {'adset_copy': {'started_at': '2026-11-12T06:20:26.213729+00:00', 'finished_at': '2026-11-12T06:20:31.219732+00:00'}},
        'readback_results': []}
    originals = []
    for i in range(2):
        cid, sid, ad = str(456+i), str(789+i), str(900+i)
        start = START if i == 0 else OBSERVED
        camp = {'id': cid, 'account_id': AID, 'start_time': start, 'status': 'PAUSED'}
        sets = [{'id': sid, 'start_time': start, 'status': 'PAUSED'}]
        ads = [{'id': ad, 'adset_id': sid, 'source_ad_id': '700', 'status': 'PAUSED'}]
        for name, body in [('campaign', camp), ('adsets', {'data': sets}), ('ads', {'data': ads})]:
            bundle['readback_results'].append({'name': 'readback_'+name+'_'+str(i+1), 'code': 200, 'body': body})
        originals.append({'campaign_id': cid, 'account_id': AID, 'start_time': start, 'status': 'PAUSED',
            'budget_minor': 8500, 'bid_strategy': 'COST_CAP',
            'adsets': [dict(sets[0],bid_amount=95)], 'ads': copy.deepcopy(ads)})
    checkpoint = {'status': 'COMPLETE', 'account_id': AID, 'campaign_ids': ['456','457'], 'bundles': [bundle]}
    original = {'request_id': RID, 'account_id': AID, 'phase': 'POSTPROCESS_PENDING', 'engine_status': 'COMPLETE',
        'readback_at': '2026-11-12T06:24:30+00:00', 'counts': {'campaigns': 2, 'adsets': 2, 'ads': 2}, 'campaigns': originals}
    profile = {'account_id': AID, 'timezone': 'America/New_York', 'channel_id': request['source_channel_id']}
    return state, checkpoint, original, policy, profile


def authority(s, p):
    def msg(mid, chan, actor, timestamp):
        return {'id': mid, 'channel_id': chan, 'content': 'explicit human command', 'timestamp': timestamp,
                'edited_timestamp': None, 'author': {'id': actor, 'bot': None}}
    r = s['request']
    return {'permission': {'verified': True},
        'request_message': msg(r['source_message_id'], r['source_thread_id'], r['authorized_by'], s['execution_started_at']),
        'policy_message': msg(p['source_message_id'], p['source_thread_id'], p['approved_by'], '2026-10-09T15:40:40.221000+00:00')}


def registered(tmp_path, monkeypatch):
    s,c,o,p,pr = fixture(); auth = authority(s,p)
    receipt = {'kind': m.KIND, 'issued_at': NOW, 'binding': m.binding(s,c,o,p,pr,now=NOW), 'authority': auth}
    operation = {'request_defaults': {'expired_explicit_start_policy': p}}
    paths = m.paths(tmp_path,RID,AID)
    for path,obj in zip(paths,[s,c,o,receipt]):
        path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(obj))
    for path,obj in [(tmp_path/m.POLICY_FILE,operation),
                     (tmp_path/'data/ares/meta-ads/operations/SHEIN-US-DIRECT-profiles.json',{'profiles':{AID:pr}}),
                     (tmp_path/m.GRANTS_FILE,{'kind':m.KIND,'grants':{RID:{'account_id':AID,'authority_message_id':'1558142161659105342','receipt_digest':m.digest(receipt)}}})]:
        path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(obj))
    monkeypatch.setattr(m,'live_authority',lambda *a,**kw: auth)
    m._AUTH_CACHE.clear()
    return s,c,o,p,pr,receipt,auth


def call(tmp_path, **kw):
    args = dict(request_id=RID,account_id=AID,campaign_id='457',idempotency_key=RID+'-c1',base=tmp_path,now=NOW)
    args.update(kw)
    return m.proof(START,OBSERVED,**args)


def test_bound_exact_and_native_no_mutations(tmp_path,monkeypatch):
    s,c,o,p,pr,r,a = registered(tmp_path,monkeypatch)
    before = copy.deepcopy((s,c,o,p,pr))
    assert call(tmp_path)['verified']
    assert m.proof(START,START,request_id=RID,account_id=AID,campaign_id='456',idempotency_key=RID+'-c0',base=tmp_path,now=NOW)['classification']=='EXACT_ORIGINAL'
    assert (s,c,o,p,pr)==before
    assert call(tmp_path)['qa_certified'] is False


@pytest.mark.parametrize('change',[{'request_id':'other'},{'account_id':'999'}, {'campaign_id':'999'},
    {'idempotency_key':'other'}, {'now':'2026-11-13T07:00:00+00:00'}, {'now':'2026-11-12T05:59:59+00:00'}])
def test_wrong_identity_or_day(tmp_path,monkeypatch,change):
    registered(tmp_path,monkeypatch); assert call(tmp_path,**change) is None


@pytest.mark.parametrize('part,key,value',[
    ('state','execution_started_at','2026-11-12T05:49:01+00:00'),
    ('state','prepared_at','2026-11-12T05:50:00+00:00'),
    ('state','phase','COMPLETE_FUTURE_ACTIVE'),('state','phase','COMPLETE_PAUSED'),
    ('state','summary',{'done':True}),('policy','enabled',False),
    ('policy','approved_by','other'),('policy','scope','any_day'),
    ('policy','source_message_id','9999999999999999999'),('profile','timezone','America/Los_Angeles'),
    ('checkpoint','status','IN_PROGRESS'),('original','account_id','999')])
def test_immutable_or_live_inputs_drift(tmp_path,monkeypatch,part,key,value):
    s,c,o,p,pr,r,a=registered(tmp_path,monkeypatch)
    obj={'state':s,'checkpoint':c,'original':o,'policy':p,'profile':pr}[part];obj[key]=value
    sp,cp,lp,rp=m.paths(tmp_path,RID,AID)
    path={'state':sp,'checkpoint':cp,'original':lp,'policy':tmp_path/m.POLICY_FILE,
          'profile':tmp_path/'data/ares/meta-ads/operations/SHEIN-US-DIRECT-profiles.json'}[part]
    out={'request_defaults':{'expired_explicit_start_policy':p}} if part=='policy' else {'profiles':{AID:pr}} if part=='profile' else obj
    path.write_text(json.dumps(out));assert call(tmp_path) is None


def test_no_receipt_no_grant_no_source_evidence(tmp_path,monkeypatch):
    registered(tmp_path,monkeypatch)
    rp=m.paths(tmp_path,RID,AID)[-1];r=json.loads(rp.read_text());r.pop('authority');rp.write_text(json.dumps(r))
    assert call(tmp_path) is None
    registered(tmp_path,monkeypatch)
    (tmp_path/m.GRANTS_FILE).write_text(json.dumps({'kind':m.KIND,'grants':{}}))
    assert call(tmp_path) is None


def test_live_authority_failure_no_fallback(tmp_path,monkeypatch):
    registered(tmp_path,monkeypatch)
    def fail(*a,**kw):raise ValueError('no authority')
    monkeypatch.setattr(m,'live_authority',fail)
    assert call(tmp_path) is None


@pytest.mark.parametrize('field',['manifest','target_manifest','request','resolved_request'])
def test_never_reseal_or_rewrite_request(tmp_path,monkeypatch,field):
    s,*_=registered(tmp_path,monkeypatch)
    if 'manifest' in field:s[field]['campaigns'][0]['start_intent']='IMMEDIATE';seal(s[field])
    else:s[field]['start_now']=True
    m.paths(tmp_path,RID,AID)[0].write_text(json.dumps(s));assert call(tmp_path) is None


@pytest.mark.parametrize('observed',['2026-11-12T01:20:25-0500','2026-11-12T01:20:32-0500','2026-11-13T01:20:27-0500'])
def test_even_consistent_changed_second_outside_copy_window_is_not_authorized(observed):
    s,c,o,p,pr=fixture()
    o['campaigns'][1]['start_time']=observed;o['campaigns'][1]['adsets'][0]['start_time']=observed
    for r in c['bundles'][0]['readback_results']:
        if r['name']=='readback_campaign_2':r['body']['start_time']=observed
        if r['name']=='readback_adsets_2':r['body']['data'][0]['start_time']=observed
    with pytest.raises(ValueError,match='window'):m.binding(s,c,o,p,pr,now=NOW)


def test_exact_observed_second_no_generic_tolerance(tmp_path,monkeypatch):
    registered(tmp_path,monkeypatch)
    assert m.proof(START,'2026-11-12T01:20:28-0500',request_id=RID,account_id=AID,campaign_id='457',idempotency_key=RID+'-c1',base=tmp_path,now=NOW) is None


def test_historical_manual_replay_fence(tmp_path,monkeypatch):
    registered(tmp_path,monkeypatch)
    from ares_campaign_v3 import shein_manual_takeover
    fence=shein_manual_takeover.path(tmp_path,RID)
    fence.parent.mkdir(parents=True,exist_ok=True);fence.write_text('{}')
    assert call(tmp_path) is None
    from ares_campaign_v3.activation import activate
    from ares_campaign_v3.engine import CampaignEngine
    engine=SimpleNamespace(config={'state_root':str(tmp_path/'data/ares/meta-ads/engine-v3/state')})
    manifest=SimpleNamespace(request_id=RID,operation='SHEIN-US-DIRECT')
    with pytest.raises(ValueError,match='manual takeover'):
        activate(engine,manifest,None,None)
    execute=getattr(CampaignEngine.execute,'__wrapped__',CampaignEngine.execute)
    with pytest.raises(ValueError,match='manual takeover'):
        execute(engine,manifest)


def test_original_clock_cannot_be_shifted_with_reissued_receipt():
    s,c,o,p,pr=fixture();a=authority(s,p)
    s['execution_started_at']='2026-11-12T05:48:39+00:00'
    r={'kind':m.KIND,'issued_at':NOW,'binding':m.binding(s,c,o,p,pr,now=NOW),'authority':a}
    with pytest.raises(ValueError,match='clock'):m.validate_receipt(r,s,c,o,p,pr,now=NOW,authority=a)


@pytest.mark.parametrize('change',['missing_window','ad_id','adset_id','campaign_id','first_second','missing_first_proof'])
def test_native_evidence_required(tmp_path,monkeypatch,change):
    s,c,o,p,pr,r,a=registered(tmp_path,monkeypatch)
    if change=='missing_window':c['bundles'][0]['timings']={}
    elif change=='ad_id':c['bundles'][0]['ad_ids'][0]='999'
    elif change=='adset_id':o['campaigns'][1]['adsets'][0]['id']='999'
    elif change=='campaign_id':o['campaigns'][1]['campaign_id']='999'
    elif change=='first_second':o['campaigns'][1]['start_time']='2026-11-12T01:20:28-0500'
    else:o={}
    _,cp,lp,_=m.paths(tmp_path,RID,AID)
    cp.write_text(json.dumps(c));lp.write_text(json.dumps(o))
    assert call(tmp_path) is None


def test_schema_scope_never_leaks_and_needs_whole_exact_target(tmp_path,monkeypatch):
    s,c,o,p,pr,r,a=registered(tmp_path,monkeypatch)
    monkeypatch.setattr(m,'BASE',tmp_path)
    real=m.proof
    monkeypatch.setattr(m,'proof',lambda *args,**kw:real(*args,**kw,now=NOW))
    from ares_campaign_v3.shein_elapsed_schema import admission,allows_campaign
    value=s['target_manifest'];spec=value['campaigns'][1]
    assert not allows_campaign(spec)
    with admission(value):assert allows_campaign(spec)
    assert not allows_campaign(spec)
    for k,v in [('operation','Other'),('request_id','other')]:
        bad=copy.deepcopy(value);bad[k]=v
        with admission(bad):assert not allows_campaign(spec)
    bad=copy.deepcopy(value);bad['campaigns'][1]['campaign_updates']['daily_budget']='9000';seal(bad)
    with admission(bad):assert not allows_campaign(bad['campaigns'][1])


def test_activation_elapsed_guard_uses_central_proof(tmp_path,monkeypatch):
    registered(tmp_path,monkeypatch)
    monkeypatch.setattr(m,'BASE',tmp_path)
    real=m.proof
    monkeypatch.setattr(m,'proof',lambda *a,**kw:real(*a,**kw,now=NOW))
    from ares_campaign_v3.activation import elapsed_policy_allows_activation
    spec=SimpleNamespace(start_time=START,account_id=AID,idempotency_key=RID+'-c1')
    assert elapsed_policy_allows_activation(spec,RID,{'campaign':{'id':'457','start_time':OBSERVED}})
    assert not elapsed_policy_allows_activation(spec,'other',{'campaign':{'id':'457','start_time':OBSERVED}})

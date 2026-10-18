"""One authorized source-removal diagnostic per target; original validation untouched."""
import asyncio, importlib.util, json, os, shutil, sqlite3, subprocess, sys, time
from pathlib import Path
sys.path.insert(0, '/root/mgs-agent/scripts')
from ares_campaign_v3 import landing_followup as core
from ares_campaign_v3.landing_batch import validate_mapping
from ares_campaign_v3.landing_lean import observe_prepared, validate_lean_observation, VISUAL_PROMPT
from ares_campaign_v3.landing_mobile import MOBILE_PROMPT

AUTH='1561385193653280868'
JOB='88a91c22a991a71d8ed2d860fa4d4e0173f6a3d2f20aa911b4a4b04fddcc4035'
ROOT=Path('/root/mgs-agent/data/ares/meta-ads/audit/landing-source-variant-'+AUTH)

def variant(url):
    base, sep, query=url.partition('?')
    if not sep or query.split('&').count('utm_source=facebook') != 1:
        raise ValueError('exact single source token required')
    return base+'?'+'&'.join(x for x in query.split('&') if x!='utm_source=facebook')

def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2))

def prepare():
    c=sqlite3.connect('file:/root/.hermes/profiles/ares/state.db?mode=ro',uri=True)
    c.row_factory=sqlite3.Row;c.execute('PRAGMA query_only=ON')
    rows=c.execute('SELECT m.content,m.timestamp,s.user_id,s.thread_id FROM messages m JOIN sessions s ON s.id=m.session_id WHERE m.platform_message_id=? AND m.role=?', (AUTH,'user')).fetchall()
    assert len(rows)==1
    r=rows[0]
    assert r['user_id']=='344196393512075265' and r['thread_id']==core.INCIDENT_THREAD
    assert '[Rodolfo Mattei] nesses 3, tente sem o utm_source=facebook' in r['content']
    q=core.Queue();j=q.job(JOB)
    assert j['state']=='WAITING_HUMAN' and len(j['links'])==3
    items=[]
    for l in j['links']:
        assert l['state']=='REVIEW_REQUIRED'
        core.validate_closure(json.loads(l['evidence']))
        e=json.loads(l['evidence'])
        source={'job':JOB,'index':l['idx'],'url':e['observed_url'],'mapping_source':e['mapping_source'],'destination_count':1}
        source=validate_mapping(q,source)
        items.append(dict(source, original_url=source['url'], url=variant(source['url']), maximum_visits=1))
    assert len({x['url'] for x in items})==3
    s={'authority_message_id':AUTH,'authority_user_id':r['user_id'],'authority_thread_id':r['thread_id'],'authority_timestamp':r['timestamp'],'purpose':'DIAGNOSTIC_ONLY_REMOVE_LITERAL_UTM_SOURCE_FACEBOOK','original_payload_digest':j['digest'],'original_job_state':j['state'],'original_links':j['links'],'items':items,'meta_writes':0,'original_status_changes':0}
    save(ROOT/'scope.json',s)
    return s

def run():
    s=json.loads((ROOT/'scope.json').read_text());sid=os.environ['HERMES_SESSION_ID']
    q=core.Queue();j=q.job(JOB)
    assert j['digest']==s['original_payload_digest'] and j['links']==s['original_links']
    assert s['authority_message_id']==AUTH and s['authority_thread_id']==core.INCIDENT_THREAD
    for x in s['items']:
        original=dict(x,url=x['original_url'])
        validate_mapping(q,original)
        assert x['url']==variant(x['original_url']) and x['maximum_visits']==1
    if q.db.execute("SELECT 1 FROM jobs WHERE state IN ('RUNNING','RECONCILING','REPAIRING','NEEDS_RECONCILIATION','WAITING_HUMAN_UNCLOSED')").fetchone():
        return {'state':'WAITING_EXISTING_OBSERVER','browser_actions':0}
    sys.path.insert(0,str(Path(shutil.which('hermes')).resolve().parents[2]))
    from tools.computer_use import tool as ct
    from tools.vision_tools import vision_analyze_tool
    spec=importlib.util.spec_from_file_location('variant_capture',core.BASE/'scripts/ares-direct-traffic-sample.py')
    sampler=importlib.util.module_from_spec(spec);spec.loader.exec_module(sampler)
    safe=True;leased=False
    def lease(action):
        args=[sys.executable,str(core.BASE/'scripts/mgs-pc1-computer-use-lock.py'),action,'--agent','ares','--session-id',sid]
        if action=='acquire':args+=['--ttl','900','--thread-id',core.INCIDENT_THREAD]
        elif action=='renew':args+=['--ttl','900']
        p=subprocess.run(args,capture_output=True,text=True,timeout=20)
        if p.returncode:raise ValueError('physical PC1 unavailable')
    def call(args):
        r=ct.handle_computer_use(args,session_id=sid)
        return json.loads(r) if isinstance(r,str) else r
    def capture():return sampler.capture_screen(ct,sid)
    def review(shot,prompt=VISUAL_PROMPT):
        from ares_campaign_v3.landing_rewarded import STATE_PROMPT
        if prompt==STATE_PROMPT:
            prompt+=' Critical distinction: the inline questionnaire One last question / Store pickup / Home delivery is NOT the CLAIM MY FREE PRODUCTS gate. If that exact CLAIM MY FREE PRODUCTS button is absent, site_gate_visible must be false and cta_label empty; do not classify a questionnaire or advertiser CTA such as Get Square as the site gate. Read actual visible article text independently. Do not infer or force any ad result.'
        return asyncio.run(vision_analyze_tool(shot['screenshot_path'],prompt))
    def mobile():return review(capture(),MOBILE_PROMPT)
    results=[]
    try:
        lease('acquire');leased=True
        for x in s['items']:
            idx=x['index'];directory=ROOT/str(idx);directory.mkdir(exist_ok=True)
            old=[]
            for row in q.db.execute("SELECT kind,detail FROM events WHERE job=? AND kind IN ('explicit_url_variant_started','explicit_url_variant_result') ORDER BY seq",(JOB,)):
                d=json.loads(row['detail'])
                if d.get('authority_message_id')==AUTH and d.get('idx')==idx:old.append((row['kind'],d))
            if old:
                if old[-1][0]=='explicit_url_variant_result':
                    results.append(old[-1][1]);continue
                raise ValueError('variant already started; exact evidence reconciliation required')
            assert q.job(JOB)['links']==s['original_links']
            lease('renew')
            with q.tx():q.event(JOB,'explicit_url_variant_started',dict(authority_message_id=AUTH,idx=idx,url=x['url'],original_url=x['original_url'],maximum_visits=1,diagnostic_only=True))
            safe=False
            result,e=observe_prepared(call,lambda:review(capture()),x['url'],x['mapping_source']+'; Rodolfo '+AUTH+' authorizes only removing literal utm_source=facebook for separate diagnostic.',on_owned=lambda v:save(directory/'normal-open.json',v),read_mobile=mobile,capture_visual=capture,review_visual=review)
            safe=e.get('tab_closed_verified') is True or (e.get('no_tab_opened') is True and e.get('browser_inputs_zero_verified') is True)
            save(directory/'raw-result.json',dict(result=result,evidence=e))
            if result in {'PASS','NO_AD'}:
                diagnostic_link={'effective_campaign_url':x['url'],'landing_url':x['url'],'mapping_source':x['mapping_source']}
                validate_lean_observation(e,diagnostic_link,negative=result=='NO_AD')
            e=core.preserve_evidence(e,'url-variant-'+AUTH,idx,1)
            output=directory/'result.json';save(output,dict(authority_message_id=AUTH,idx=idx,result=result,evidence=e,original_url=x['original_url'],diagnostic_url=x['url'],original_status_preserved=True))
            d=dict(authority_message_id=AUTH,idx=idx,result=result,evidence_file=str(output),diagnostic_only=True,original_status_preserved=True)
            with q.tx():q.event(JOB,'explicit_url_variant_result',d)
            results.append(d);save(ROOT/'results.json',results)
            print(json.dumps({'item':idx,'result':result,'safe_closed':safe}),flush=True)
            assert q.job(JOB)['links']==s['original_links']
            if result=='ERROR' or not safe:break
        save(ROOT/'verification.json',dict(results=results,expected_items=3,recorded_items=len(results),original_links_unchanged=q.job(JOB)['links']==s['original_links'],original_job_state=q.job(JOB)['state'],meta_writes=0,safe_closed=safe))
        return {'state':'DIAGNOSTIC_RECORDED' if len(results)==3 else 'DIAGNOSTIC_REPAIR_REQUIRED','results':results}
    finally:
        ct.release_computer_use_session(sid)
        if leased and safe:lease('release')

if __name__=='__main__':
    if '--test' in sys.argv:
        assert variant('https://a.test/?utm_source=facebook&x=a%2Fb&nocache')=='https://a.test/?x=a%2Fb&nocache'
        assert variant('https://a.test/?x=1&utm_source=facebook&x=2')=='https://a.test/?x=1&x=2'
        for bad in ['https://a.test/?utm_source=Facebook','https://a.test/?utm_source=facebook&utm_source=facebook','https://a.test/']:
            try:variant(bad)
            except ValueError:pass
            else:raise AssertionError('invalid removal accepted')
        print('SOURCE_VARIANT_GUARDS_OK')
    elif '--prepare' in sys.argv:print(json.dumps(prepare(),ensure_ascii=False))
    else:print(json.dumps(run(),ensure_ascii=False))

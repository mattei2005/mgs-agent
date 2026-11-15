"""Independent, request-pinned media reconciliation; never execute an Engine.

Only remote mutation: ACTIVE on the previously confirmed parent. Original
Engine errors/seals/GET responses are immutable. A paused pre-QA expectation is
an in-memory CampaignSpec, not a normalized API response. Receipts are generated
from fresh reads/downloads, not supplied as caller booleans. See CLI handoff.
"""
from __future__ import annotations
import copy,fcntl,hashlib,json,os,re,ssl,subprocess,tempfile,time
from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime,timezone
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlsplit
from . import target_continuation as continuation
from . import target_start_revision as revision
from .target_page_clone import verify

GRANT_PATH=Path('/root/mgs-agent/data/ares/meta-ads/audit/maintenance/t_53c187db/media-grant.json')
GRANT_SHA256='ac247f2228ffe33662438c3e5cec74c0d6a487410e47277c6494bc06b0d3d03b'
MAX_ATTESTATION_AGE=86400
MAX_FRESH_SECONDS=600
MAX_VIDEO_BYTES=100*1024*1024
SCHEMA='mgs.target.media.recovery.v1'

def require(ok,message):
    if not ok:raise ValueError('target media recovery: '+message)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def file_sha(p):return sha(Path(p).read_bytes())
def digest(v):return sha(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode())
def load(p):return json.loads(Path(p).read_text())
def utc():return datetime.now(timezone.utc).isoformat()
def atomic(p,v):revision.atomic_json(Path(p),v)
def missing(p,v):
    p=Path(p)
    if p.exists():require(load(p)==v,'immutable receipt collision');return
    # Caller owns request lock; atomic replace is crash safe, never overwrites a
    # different immutable receipt (checked again before installation).
    atomic(p,v)
def cas_link(p,key,value,backup):
    p=Path(p);raw=p.read_bytes();v=json.loads(raw)
    if key in v:require(v[key]==value,'existing recovery link differs');return
    b=Path(backup);b.parent.mkdir(parents=True,exist_ok=True)
    if not b.exists():revision.atomic_bytes(b,raw)
    require(p.read_bytes()==raw,'CAS link drift');v[key]=value;atomic(p,v)
def fresh(at,now=None,limit=MAX_FRESH_SECONDS):
    at=datetime.fromisoformat(at);now=now or datetime.now(timezone.utc)
    require(at.tzinfo is not None and 0 <= (now-at).total_seconds() <= limit,'stale/future clock')

@contextmanager
def request_lock(path):
    with (Path(path).parent/'target-clone.lock').open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);yield

def grant_load(path,approved_digest,approval_message_id):
    require(file_sha(GRANT_PATH)==GRANT_SHA256,'installed grant hash')
    g=load(GRANT_PATH);path=Path(path).resolve()
    require(g.get('schema')=='mgs.target.media.grant.v1' and g['request_path']==str(path)
            and approved_digest==g['original_approved_digest'] and approval_message_id==g['approval_message_id'],'original request/approval')
    fresh(g['attested_at'],limit=MAX_ATTESTATION_AGE)
    mutable={g['checkpoint_path'],g['audit_path'],str(path.parent/'engine-result.json')}
    for p,s in g['pins'].items():
        if p in mutable:
            v=load(p);v.pop('independent_media_recovery',None);v.pop('independent_media_finalization',None)
            # Linking is missing-only and preserves every original field.
            original=path.parent/'media-recovery'/'original'/Path(p).name
            require(file_sha(original if original.exists() else p)==s,'original Engine receipt changed')
            if original.exists():require(v==load(original),'Engine fields changed outside recovery link')
        else:require(file_sha(p)==s,'attested proof changed')
    return g

def local(path,runner,approved_digest,approval_message_id):
    g=grant_load(path,approved_digest,approval_message_id);cfg=runner.load(runner.CONFIG);q=runner.load(path);payload=runner.load(Path(path).parent/'manifest.json')
    require(cfg.get('enabled') is True and cfg.get('write_enabled') is True,'runtime write gates')
    temporal=revision.validate_local(path,cfg,approved_digest,approval_message_id)
    require(temporal['last'] and not temporal['pending'],'committed original ASAP mapping')
    ctx=continuation.validate_local(path,payload,cfg)
    # validate_record needs the exact elapsed admission; no schema bypass.
    marker=continuation.CURRENT.set(ctx)
    try:ids=continuation.validate_record(payload,ctx['record'])
    finally:continuation.CURRENT.reset(marker)
    require(ids==g['ids'] and ctx['record'].get('target_clone_ids')==ids and len(ids)==11,'all confirmed children/journal')
    require(ctx['record'].get('ad_ids')==[ids[f'copied_ad_id_1_{i}'] for i in range(1,4)],'final slot list')
    require(g['request_id']==q['request_id'] and len(payload['campaigns'])==1 and len(payload['campaigns'][0]['ads'])==3,'exact 3-slot request')
    return g,cfg,q,payload

def pair_expectations(payload,ids,selected,snapshot,pairs):
    """Validate the attested bijection against the sealed slots AND raw GETs."""
    c=payload['campaigns'][0];ads=snapshot['ads'];byid={a['id']:a for a in ads}
    require(len(ads)==6 and len(byid)==6 and len(pairs)==6 and len(selected)==3,'media/child cardinality')
    wanted_ids={ids[f'{key}_1_{i}'] for i in range(1,4) for key in ['copied_ad_id','seed_ad_id']}
    require(set(byid)==wanted_ids,'unexpected/missing final/seed ID')
    result=[];seen=set();expected_seen=set();observed_seen=set()
    for i,(a,asset) in enumerate(zip(c['ads'],selected),1):
        final=byid[ids[f'copied_ad_id_1_{i}']];seed=byid[ids[f'seed_ad_id_1_{i}']]
        require(final.get('adset_id')==ids['adset_id_1'] and seed.get('adset_id')==ids['adset_id_1'],'ad parent')
        if 'campaign_id' in final:require(final['campaign_id']==ids['campaign_id_1'],'ad campaign')
        afs=final['creative']['asset_feed_spec'];expected=a['creative_payload']['asset_feed_spec']
        require(len(afs.get('videos',[]))==2 and len(expected['videos'])==2,'variant cardinality')
        for v,w in zip(afs['videos'],expected['videos']):
            labels=[x.get('name') for x in v.get('adlabels',[])];wl=[x.get('name') for x in w.get('adlabels',[])]
            require(labels==wl and len(labels)==1 and labels[0] not in seen,'missing/extra/reordered labels');seen.update(labels)
            variant='vertical' if labels[0].endswith('_vertical') else 'square' if labels[0].endswith('_square') else None
            require(variant and w['video_id']==a['media'][variant+'_video_id'],'variant identity')
            matches=[p for p in pairs if p.get('slot')==i and p.get('labels')==labels]
            require(len(matches)==1,'ambiguous pair');p=matches[0]
            require(p.get('asset_id')==asset['asset_id']==a['media']['asset_id'] and p.get('expected_video_id')==w['video_id']
                    and p.get('observed_video_id')==v['video_id'] and p.get('final_ad_id')==final['id'] and p.get('final_creative_id')==final['creative']['id'],'attested ID/asset/creative mismatch')
            require(w['video_id'] not in expected_seen and v['video_id'] not in observed_seen,'non-bijective videos');expected_seen.add(w['video_id']);observed_seen.add(v['video_id'])
            result.append({**p,'variant':variant,'checksum':a['media']['checksum']})
    require(len(expected_seen)==len(observed_seen)==6,'incomplete bijection')
    return result

def semantic(payload,ids,selected,snapshot,pairs,parent_status):
    """Only expectations change; raw response hashes must remain unchanged."""
    from .schema import CampaignSpec
    from .eggbev_create import messenger_welcome_message
    before=digest(snapshot);ps=pair_expectations(payload,ids,selected,snapshot,pairs)
    require(snapshot['campaign'].get('id')==ids['campaign_id_1'] and snapshot['campaign'].get('status')==parent_status,'parent status/id')
    c=copy.deepcopy(payload['campaigns'][0]);c['status']=parent_status
    for i,a in enumerate(c['ads'],1):
        for v in a['creative_payload']['asset_feed_spec']['videos']:
            p=next(p for p in ps if p['slot']==i and p['labels']==[l['name'] for l in v['adlabels']]);v['video_id']=p['observed_video_id']
    # Elapsed admission is already active in production. Pre-QA PAUSED affects
    # only campaign expectation; finals remain the approved ACTIVE.
    campaigns=SimpleNamespace(**c)
    campaigns.ads=tuple(SimpleNamespace(**a) for a in c['ads'])
    record={'target_clone_ids':ids,'readback_results':[
        {'name':'readback_campaign_1','body':snapshot['campaign']},
        {'name':'readback_adsets_1','body':{'data':snapshot['adsets']}},
        {'name':'readback_ads_1','body':{'data':snapshot['ads']}}]}
    # verify couples parent/final status. Two independent expectations permit
    # PAUSED parent preflight without ever changing the responses: delegate
    # campaign check to an exact PAUSED expectation, and final hierarchy to an
    # ACTIVE expectation by verifying each approved branch separately below.
    if parent_status=='PAUSED':
        # Original verifier sees PAUSED expectation and real PAUSED parent, but
        # requires final ACTIVE. A read-only str subtype matches both approved
        # states would be a bypass, so do not invoke it for this phase. Instead
        # validate all hierarchy fields with strict checks below; post-ACTIVE
        # always invokes original verify unchanged.
        live=snapshot['campaign']
        require(all(str(live.get(k))==str(c.get('campaign_create',{}).get(k)) for k in ['daily_budget','bid_strategy'])
                and live.get('name')==c['name'] and live.get('account_id')==c['account_id'],'paused parent commercial fields')
    else:verify(SimpleNamespace(campaigns=(campaigns,)),record)
    # Strict additional checks cover gaps not checked by the original verifier,
    # including identical copy labels/rules, Page PBIA, features, JSON and event.
    from .prevalidation import _require_subset
    sets=snapshot['adsets'];require(len(sets)==1 and sets[0]['id']==ids['adset_id_1'],'adset cardinality')
    st=sets[0];require(st.get('status')=='ACTIVE' and st.get('name')==c['adset_name'],'adset status/name')
    require(datetime.fromisoformat(st['start_time'])==datetime.fromisoformat(c['start_time']),'start_time drift')
    for k,v in c['adset_create'].items():_require_subset(st.get(k),v,'adset.'+k)
    byid={a['id']:a for a in snapshot['ads']}
    for i,a in enumerate(c['ads'],1):
        final=byid[ids[f'copied_ad_id_1_{i}']];seed=byid[ids[f'seed_ad_id_1_{i}']]
        require(final.get('status')=='ACTIVE' and seed.get('status')=='PAUSED' and final.get('source_ad_id')==seed['id'] and final.get('name')==a['name'],'final/seed status/lineage')
        actual=final['creative'];expected=a['creative_payload']
        for k in ['object_story_spec','instagram_user_id','url_tags','degrees_of_freedom_spec','contextual_multi_ads']:
            if k in expected:_require_subset(actual.get(k),expected[k],k)
        afs=actual['asset_feed_spec'];ex=expected['asset_feed_spec']
        for k in ex:
            if k in {'additional_data','videos'}:continue
            _require_subset(afs.get(k),ex[k],'asset_feed_spec.'+k)
        for v,w in zip(afs['videos'],ex['videos']):_require_subset(v,w,'video')
        raw=afs.get('additional_data',{}).get('page_welcome_message');parsed=json.loads(raw) if isinstance(raw,str) else raw
        require(parsed==json.loads(messenger_welcome_message()),'JSON-AGT/envelope/flags mismatch')
    require(digest(snapshot)==before,'raw GET mutation forbidden')
    return ps

def rendered(g,ids,ps):
    v=load(g['rendered_proof_path']);require(v.get('verified') is True and len(v.get('rendered_media',[]))==3,'rendered coverage')
    require(v.get('ad_ids')==[ids[f'copied_ad_id_1_{i}'] for i in range(1,4)] and v.get('creative_ids')==[next(p['final_creative_id'] for p in ps if p['slot']==i) for i in range(1,4)],'rendered ID mismatch')
    for row in v['rendered_media']:
        require(row.get('videos') and all(x.get('readyState')==4 and x.get('error') is None and x.get('width',0)>0 and x.get('height',0)>0 for x in row['videos']),'rendered video incomplete')

def validate_video(meta,p,proof):
    require(meta.get('id') in {p['expected_video_id'],p['observed_video_id']},'video GET ID')
    expected=next(d for d in proof['downloads'] if d['video_id']==meta['id'])
    title=f"V3 {p['variant'].upper()} {p['asset_id']} {p['checksum'][:12]}"
    require(meta.get('title')==title==expected['title'] and meta.get('length')==expected['length'],'video title/length')
    status=meta.get('status',{});require(status.get('video_status')=='ready' and all(status.get(k,{}).get('status')=='complete' for k in ['uploading_phase','processing_phase','publishing_phase']),'video not ready/complete')
    return expected

def fetch_video(url):
    """Bounded, IP-pinned HTTPS FB CDN fetch, no redirect/proxy/credential."""
    from .native_thumbnail_equivalence import _PinnedHTTPS
    require(isinstance(url,str) and len(url)<=16384 and re.fullmatch(r'[\x21-\x7e]+',url),'video URL shape')
    p=urlsplit(url);require(p.scheme=='https' and re.fullmatch(r'scontent-[a-z0-9-]+\.xx\.fbcdn\.net',p.netloc) and p.path.endswith('.mp4') and not p.fragment,'video CDN endpoint')
    conn=_PinnedHTTPS(p.netloc,timeout=30,context=ssl.create_default_context())
    try:
        conn.request('GET',p.path+'?'+p.query,headers={'Accept':'video/mp4','Connection':'close'});r=conn.getresponse()
        require(r.status==200 and not r.getheader('Location') and r.getheader('Content-Encoding','identity')=='identity','video HTTP/redirect')
        length=r.getheader('Content-Length');require(length is not None and length.isdigit() and 0<int(length)<=MAX_VIDEO_BYTES,'video size')
        raw=r.read(MAX_VIDEO_BYTES+1);require(len(raw)==int(length) and raw[4:8]==b'ftyp','video bytes/signature');return raw
    except Exception:raise ValueError('target media recovery: safe video download failed') from None
    finally:conn.close()

def inspect_bytes(raw,expected):
    require(len(raw)==expected['bytes'] and sha(raw)==expected['sha256'],'media bytes mismatch')
    root=Path(os.environ.get('TMPDIR','/root/.hermes/profiles/zeus/cache/scratch'));root.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='target-media-',dir=root) as d:
        p=Path(d)/'video.mp4';p.write_bytes(raw)
        out=subprocess.run(['ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=width,height','-show_entries','format=duration','-of','json',str(p)],check=True,capture_output=True,timeout=30)
        probe=json.loads(out.stdout);s=probe['streams'][0]
        require([s['width'],s['height']]==[expected['width'],expected['height']] and probe['format']['duration']==expected['duration'],'dimensions/duration')
        require([f['timestamp'] for f in expected['frames']]==[3,8,12],'decoded frame coverage')
        for f in expected['frames']:
            frame=Path(d)/'frame.png'
            subprocess.run(['ffmpeg','-nostdin','-v','error','-y','-ss',str(f['timestamp']),'-i',str(p),'-frames:v','1',str(frame)],capture_output=True,check=True,timeout=30)
            require(file_sha(frame)==f['sha256'],'decoded frame mismatch')
    return {'video_id':expected['video_id'],'sha256':sha(raw),'bytes':len(raw),'frames':[f['sha256'] for f in expected['frames']],'dimensions':[expected['width'],expected['height']]}

class Runtime:
    def __init__(self,runner,path,cfg,q,payload):
        from .quota import LaneQuotaStore
        from .transport import GraphBatchTransport
        self.runner=runner;self.path=Path(path);self.cfg=cfg;self.q=q;self.payload=payload
        self.common,self.meta,self.sb,self.token=runner.runtime()
        self.quota=LaneQuotaStore(cfg['state_root'],soft_score=cfg['soft_score'],hard_score=cfg['hard_score'],window_seconds=cfg['score_window_seconds'],development_score_max=cfg['development_access_score_max'],standard_score_max=cfg['standard_access_score_max'])
        self.lane=(payload['campaigns'][0]['app_key'],q['account_id']);self.n=0;self.run=utc()
        self.transport=GraphBatchTransport(q['account_id'],payload['graph_version'],self.token)
    def reserve(self,points):
        self.n+=1;return self.quota.reserve(self.lane,points,request_id=self.q['request_id']+':media:'+self.run+':'+str(self.n))
    def authority(self):
        self.reserve(2);revision.live_authority(revision.validate_local(self.path,self.cfg, self.g['original_approved_digest'],self.g['approval_message_id']),meta=self.meta,token=self.token)
    def source_page(self):
        r=self.runner;self.reserve(5);current=r.source_read(self.q,self.common,self.meta,self.token);old=r.load(self.path.parent/'source-live.json')
        if r.source_comparison(current)!=r.source_comparison(old):
            from .native_thumbnail_equivalence import compare
            compare(old,current,context={'request_id':self.q['request_id'],'approved_digest':self.g['original_approved_digest'],'account_id':self.q['account_id'],'source_campaign_id':self.q['source_campaign_id_candidate']},normalize=r.source_comparison)
        page=r.resolve_page(self.meta,self.sb,self.token,self.q['account_id'],self.q['target_page_token'])
        require(all(page.get(k)==r.load(self.path.parent/'target-page-live.json').get(k) for k in ['id','name','instagram_user_id','page_token']),'Page/PBIA changed')
        self.page=page
        rows=[json.loads(x) for x in r.INVENTORY.read_text().splitlines() if x.strip()]
        for wanted in load(self.path.parent/'selected-assets.json'):
            hits=[x for x in rows if x.get('asset_id')==wanted['asset_id']]
            require(len(hits)==1 and hits[0].get('reservation_request_id')==self.q['request_id'] and hits[0].get('clean_checksum')==wanted['clean_checksum'],'reservation/checksum')
        alloc=r.naming.allocation(self.q['request_id']);require(alloc and alloc.get('account_id')==self.q['account_id'] and alloc.get('names')==[self.payload['campaigns'][0]['name']] and alloc.get('status') in {'RESERVED','IN_FLIGHT','COMMITTED'},'naming allocation')
    def read(self):
        from .engine import CampaignEngine
        self.reserve(3);ops=CampaignEngine._readback_ops([self.g['ids']['campaign_id_1']])
        extra=','.join(k for k in self.payload['campaigns'][0]['adset_create'] if k not in ops[1].relative_url.split('?fields=')[1].split('&')[0].split(','))
        if extra:ops[1]=replace(ops[1],relative_url=ops[1].relative_url.replace('&limit=',','+extra+'&limit='))
        rows=self.transport.execute(ops,'independent_media_readback')
        self.quota.observe_headers(self.lane,self.transport.last_outer_headers)
        require(len(rows)==3 and all(x.code==200 for x in rows),'fresh hierarchy GET failed')
        b={x.name:x.body for x in rows};sets=b['readback_adsets_1'];ads=b['readback_ads_1']
        require(not sets.get('paging',{}).get('next') and not ads.get('paging',{}).get('next'),'unread pagination')
        return {'campaign':b['readback_campaign_1'],'adsets':sets['data'],'ads':ads['data']}
    def video(self,vid):
        self.reserve(1);code,v,_=self.meta.graph_get(vid,self.token,{'fields':'id,title,length,status,source'})
        if code==200 and v.get('source'):return v
        # Only the already validated own Page, same advertiser; ephemeral token
        # never written to logs or returned. Page runtime scope enforces lineage.
        self.reserve(2);code,page,_=self.meta.graph_get(self.page['id'],self.token,{'fields':'id,access_token'})
        require(code==200 and page.get('id')==self.page['id'] and page.get('access_token'),'own Page read token unavailable')
        code,v,_=self.meta.graph_get(vid,page['access_token'],{'fields':'id,title,length,status,source'})
        require(code==200 and v.get('source'),'fresh video source unavailable');return v
    def activate(self):
        from .transport import BatchOperation
        self.reserve(3)
        op=BatchOperation('independent_media_parent_activate','POST',self.g['ids']['campaign_id_1'],{'status':'ACTIVE'},kind='campaign_finalize')
        rows=self.transport.execute([op],'independent_media_parent_activate');self.quota.observe_headers(self.lane,self.transport.last_outer_headers)
        require(len(rows)==1 and rows[0].code==200 and rows[0].body.get('success') is True,'parent status outcome uncertain; GET before retry')

def receipt_value(g,payload,path,ps,snapshot,downloads):
    return {'schema':SCHEMA,'request_id':g['request_id'],'request_sha256':file_sha(path),'manifest_digest':digest(payload),'original_approved_digest':g['original_approved_digest'],'approval_message_id':g['approval_message_id'],'grant_sha256':GRANT_SHA256,'ids':g['ids'],'pairs':ps,'fresh_at':utc(),'fresh_readback_digest':digest(snapshot),'downloads':downloads,'phase':'RECOVERY_VERIFIED_INDEPENDENT','original_engine_success':False}

def recover(path,runner,approved_digest,approval_message_id,*,runtime_factory=Runtime):
    from .coordination import AccountWriterLeaseStore
    with request_lock(path):
        g,cfg,q,payload=local(path,runner,approved_digest,approval_message_id)
        leases=AccountWriterLeaseStore(cfg['state_root']);leases.claim(q['account_id'],q['request_id'],status='RECOVERY_PENDING')
        runtime=runtime_factory(runner,path,cfg,q,payload);runtime.g=g;home=Path(path).parent/'media-recovery';home.mkdir(exist_ok=True)
        runtime.authority();runtime.source_page()
        with continuation.admission(path,payload,cfg,meta=runtime.meta,token=runtime.token):
            selected=load(Path(path).parent/'selected-assets.json');snapshot=runtime.read();state=snapshot['campaign'].get('status')
            intent=home/'activation-intent.json';binding={'grant_sha256':GRANT_SHA256,'request_id':g['request_id'],'ids':g['ids'],'manifest_digest':digest(payload)}
            require(state=='PAUSED' or (state=='ACTIVE' and intent.exists() and load(intent)==binding),'ACTIVE without own durable intent or unsupported state')
            ps=semantic(payload,g['ids'],selected,snapshot,g['pairs'],state);rendered(g,g['ids'],ps)
            proof=load(g['proof_path']);downloads=[];started=utc()
            for p in ps:
                for vid in [p['expected_video_id'],p['observed_video_id']]:
                    meta=runtime.video(vid);expected=validate_video(meta,p,proof);downloads.append(inspect_bytes(fetch_video(meta['source']),expected))
            fresh(started);runtime.authority();runtime.source_page()
            # Re-read after long downloads. No stale hierarchy can activate.
            snapshot=runtime.read();semantic(payload,g['ids'],selected,snapshot,g['pairs'],state)
            for p in [Path(path),Path(path).parent/'manifest.json']:require(file_sha(p)==g['pins'][str(p)],'prewrite CAS')
            if state=='PAUSED':
                missing(intent,binding);runtime.activate()
            post=runtime.read();semantic(payload,g['ids'],selected,post,g['pairs'],'ACTIVE')
            receipt=receipt_value(g,payload,path,ps,post,downloads);rp=home/('receipt-'+digest(receipt)+'.json');missing(rp,receipt)
            link={'path':str(rp),'sha256':file_sha(rp),'phase':receipt['phase']}
            # Each run may generate fresher evidence; preserve the first terminal
            # receipt and check it before repairing partial links.
            terminal=home/'verified.json'
            if terminal.exists():link=load(terminal);validate_receipt(link,g,payload,path,allow_stale=True)
            else:missing(terminal,link)
            for p in [g['checkpoint_path'],g['audit_path'],str(Path(path).parent/'engine-result.json')]:cas_link(p,'independent_media_recovery',link,home/'original'/Path(p).name)
            return {'phase':'POSTPROCESS_PENDING','request_id':g['request_id'],'recovery_receipt':link,'campaign_ids':[g['ids']['campaign_id_1']],'engine_replayed':False,'next_step':'finalize with same original digest/approval; real IDs and Usados receipts required'}

def validate_receipt(link,g,payload,path,allow_stale=False):
    p=Path(link['path']);root=Path(path).parent/'media-recovery'
    require(p.resolve().parent==root.resolve() and p.name.startswith('receipt-') and file_sha(p)==link['sha256'],'receipt path/hash')
    v=load(p);require(p.name=='receipt-'+digest(v)+'.json' and v.get('schema')==SCHEMA and v.get('phase')=='RECOVERY_VERIFIED_INDEPENDENT'
        and v.get('request_id')==g['request_id'] and v.get('grant_sha256')==GRANT_SHA256 and v.get('ids')==g['ids']
        and v.get('request_sha256')==file_sha(path) and v.get('manifest_digest')==digest(payload) and v.get('approval_message_id')==g['approval_message_id']
        and v.get('original_approved_digest')==g['original_approved_digest'] and len(v.get('pairs',[]))==6 and len(v.get('downloads',[]))==12,'receipt binding/coverage')
    if not allow_stale:fresh(v['fresh_at'])
    return v

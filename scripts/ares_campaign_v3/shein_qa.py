"""SHEIN read-only media proof, before status-only activation."""
from __future__ import annotations
import html
import re
from .creative_media import video_slots, matches
from .shein_media_handoff import ready_status
from .preview_renderer import render_previews


def validate_rendered(row, expect_video):
    videos=[v for v in row.get('videos',[]) if v.get('readyState',0)>=2 and (v.get('duration') or 0)>0 and v.get('width',0)>0 and v.get('height',0)>0 and not v.get('error')]
    if expect_video and not videos:raise ValueError('preview lacks the expected playable video; activation blocked')
    if not expect_video and not videos and not row.get('images'):raise ValueError('preview lacks real ad media; activation blocked')


def verify_media(common, token, live, desired, source, policy):
    if policy.get('enabled') is not True:raise ValueError('SHEIN media QA policy unavailable')
    actual={str(a.get('source_ad_id')):a for a in live['ads']['data']}
    sources={str(a['id']):a for a in source['ads']};pairs=[];metadata=dict(source.get('video_metadata') or {})
    expected_video=[]
    for slot in desired['ads']:
        ad=actual[str(slot['source_ad_id'])];cp=slot['creative_payload'];cr=ad['creative']
        if (cp.get('asset_feed_spec') or cp.get('object_story_spec')) and not matches(cr,cp):raise ValueError('full flexible media/copy/identity mismatch')
        expected=video_slots(cp) or video_slots(sources[str(slot['source_ad_id'])]['creative'])
        observed=video_slots(cr)
        if cp.get('asset_feed_spec') and set(observed)!=set(expected):raise ValueError('flexible variant labels/count mismatch')
        for label,vid in observed.items():
            # New-media routes can have IDs rematerialized by the Meta copy endpoint.
            sourcevid=expected.get(label)
            if not sourcevid:raise ValueError('unrecognized video slot')
            pairs.append((sourcevid,vid))
        expected_video.append(bool(expected))
    needed=sorted({v for pair in pairs for v in pair if v not in metadata})
    for offset in range(0,len(needed),50):
        chunk=needed[offset:offset+50]
        http,rows,_=common.graph_batch_get(token,[{'name':v,'path':v,'params':{'fields':'id,title,length,status'}} for v in chunk])
        if http!=200 or len(rows)!=len(chunk) or any(r['code']!=200 for r in rows):raise ValueError('video QA read incomplete')
        metadata.update({r['name']:r['body'] for r in rows})
    for expected,observed in pairs:
        e=metadata[expected];o=metadata[observed]
        if not ready_status(o) or not ready_status(e) or e.get('title')!=o.get('title') or e.get('length')!=o.get('length'):
            raise ValueError('video lineage/processing mismatch')
    ads=[actual[str(slot['source_ad_id'])] for slot in desired['ads']]
    urls=[]
    for offset in range(0,len(ads),50):
        group=ads[offset:offset+50]
        http,rows,_=common.graph_batch_get(token,[{'name':a['id'],'path':a['id']+'/previews','params':{'ad_format':'MOBILE_FEED_STANDARD'}} for a in group])
        if http!=200 or len(rows)!=len(group) or any(r['code']!=200 for r in rows):raise ValueError('preview QA read incomplete')
        byname={r['name']:r['body'] for r in rows}
        for ad in group:
            data=byname[ad['id']].get('data') or []
            if len(data)!=1:raise ValueError('preview QA ambiguous')
            match=re.search(r'<iframe[^>]+src=[\"\']([^\"\']+)',data[0].get('body',''))
            if not match:raise ValueError('preview iframe missing')
            urls.append(html.unescape(match[1]))
    rendered=render_previews(urls,chrome_path=policy['chrome_path'],timeout=int(policy.get('timeout_seconds',35)),expect_video=expected_video,python_path=policy.get('python_path'))
    for row,wanted in zip(rendered,expected_video):validate_rendered(row,wanted)
    if len(rendered)!=len(ads):raise ValueError('preview media QA incomplete')
    return {'verified':True,'ad_ids':[a['id'] for a in ads],'creative_ids':[a['creative']['id'] for a in ads], 'variant_pairs':pairs,'rendered_media':rendered,'signed_urls_persisted':False}

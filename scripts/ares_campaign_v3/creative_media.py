"""Pure creative normalization and media QA; no network or mutations."""
from __future__ import annotations
import copy
import json
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

TWO_PHASE_ROUTES = {'existing_post_two_phase', 'full_media_two_phase'}

def source_links(creative, story):
    data=story.get('video_data') or story.get('link_data') or {}
    direct=(data.get('call_to_action') or {}).get('value',{}).get('link') or data.get('link')
    links=[direct] if direct else []
    links.extend(x.get('website_url') for x in creative.get('asset_feed_spec',{}).get('link_urls',[]) if x.get('website_url'))
    if not links:raise ValueError('source creative has no resolved destination')
    return sorted(set(links))


def strip_output(value: Any) -> Any:
    if isinstance(value,dict):return {k:strip_output(v) for k,v in value.items() if k not in {'id','reasons_to_shop','shops_bundle'}}
    if isinstance(value,list):return [strip_output(v) for v in value]
    return value


def stable(value: Any) -> Any:
    if isinstance(value,dict):return {k:stable(v) for k,v in value.items() if k not in {'id','thumbnail_url','picture','image_url','reasons_to_shop','shops_bundle'}}
    if isinstance(value,list):return [stable(v) for v in value]
    return value


def full_creative(creative, story, tags, name, degrees):
    feed=strip_output(copy.deepcopy(creative.get('asset_feed_spec') or {}))
    if not feed.get('videos') and not feed.get('images'):raise ValueError('flexible reference has no media')
    if not feed.get('link_urls'):raise ValueError('flexible reference has no link package')
    oss={'page_id':story['page_id']}
    ig=creative.get('instagram_user_id') or story.get('instagram_user_id')
    if not ig:raise ValueError('flexible reference Instagram identity not verified')
    oss['instagram_user_id']=ig
    for link in feed['link_urls']:
        parsed=urlparse(link['website_url']);params=dict(parse_qsl(parsed.query,keep_blank_values=True));params.update(dict(parse_qsl(tags)))
        link['website_url']=urlunparse(parsed._replace(query=urlencode(params)))
    return {'name':name,'object_story_spec':oss,'asset_feed_spec':feed,'url_tags':tags,'degrees_of_freedom_spec':degrees}


def creative_body(payload):
    if payload.get('asset_feed_spec') or payload.get('object_story_spec'):
        return {k:copy.deepcopy(payload[k]) for k in ['name','object_story_spec','asset_feed_spec','url_tags','degrees_of_freedom_spec','media_sourcing_spec'] if k in payload}
    return {k:copy.deepcopy(payload[k]) for k in ['name','object_story_id','url_tags','degrees_of_freedom_spec'] if k in payload}


def matches(actual, expected):
    if str(actual.get('url_tags') or '') != str(expected.get('url_tags') or ''):return False
    if expected.get('object_story_spec') and not expected.get('asset_feed_spec'):
        def semantic_story(value):
            out=stable(value)
            if isinstance(out,dict):
                out={k:semantic_story(v) for k,v in out.items() if k not in {'video_id','image_hash'}}
            elif isinstance(out,list):out=[semantic_story(v) for v in out]
            return out
        wanted=copy.deepcopy(expected['object_story_spec']);observed=copy.deepcopy(actual.get('object_story_spec') or {})
        if wanted.get('instagram_user_id') and not observed.get('instagram_user_id'):
            observed['instagram_user_id']=actual.get('instagram_user_id')
        return semantic_story(observed)==semantic_story(wanted)
    if not expected.get('asset_feed_spec'):
        return (actual.get('object_story_id') or actual.get('effective_object_story_id'))==expected.get('object_story_id')
    actual_story=actual.get('object_story_spec') or {};wanted_story=expected.get('object_story_spec') or {}
    if actual_story.get('page_id')!=wanted_story.get('page_id'):return False
    if (actual.get('instagram_user_id') or actual_story.get('instagram_user_id'))!=wanted_story.get('instagram_user_id'):return False
    af=actual.get('asset_feed_spec') or {};ef=expected['asset_feed_spec']
    for key in set(ef)-{'videos','images'}:
        if stable(af.get(key))!=stable(ef.get(key)):return False
    for kind in ['videos','images']:
        ar=af.get(kind) or [];er=ef.get(kind) or []
        if len(ar)!=len(er):return False
        def shape(row):
            out=stable(row);out.pop('video_id',None);out.pop('url',None);return out
        if sorted((json.dumps(shape(x), sort_keys=True) for x in ar))!=sorted((json.dumps(shape(x), sort_keys=True) for x in er)):return False
    return True


def video_slots(creative):
    feed=creative.get('asset_feed_spec') or {}
    if feed.get('videos'):
        rows={}
        for index,v in enumerate(feed['videos']):
            names=tuple(sorted(x['name'] for x in v.get('adlabels',[]))) or ('slot-'+str(index),)
            if names in rows:raise ValueError('ambiguous media slot labels')
            rows[names]=str(v['video_id'])
        return rows
    v=(creative.get('object_story_spec') or {}).get('video_data') or {}
    return {('direct',):str(v['video_id'])} if v.get('video_id') else {}


def definition_creative(creative, story, tags, name):
    """Preserve Create ad and the source tracking location; never freeze its post."""
    oss=strip_output(copy.deepcopy(story))
    ig=creative.get('instagram_user_id') or oss.get('instagram_user_id')
    if ig: oss['instagram_user_id']=ig
    source_tags=str(creative.get('url_tags') or '')
    wanted=dict(parse_qsl(tags,keep_blank_values=True))
    def destinations(value):
        if isinstance(value,dict):
            for k,v in value.items():
                if k in {'link','website_url'} and isinstance(v,str) and urlparse(v).scheme in {'https','http'}:
                    parsed=urlparse(v);q=dict(parse_qsl(parsed.query,keep_blank_values=True))
                    if not source_tags:q.update(wanted)
                    else:q.update({key:val for key,val in wanted.items() if key in q})
                    value[k]=urlunparse(parsed._replace(query=urlencode(q)))
                else:destinations(v)
        elif isinstance(value,list):
            for row in value:destinations(row)
    destinations(oss)
    vd=oss.get('video_data') or {}
    if vd.get('image_hash'):vd.pop('image_url',None)
    feed=strip_output(copy.deepcopy(creative.get('asset_feed_spec') or {}));destinations(feed)
    degrees=copy.deepcopy(creative.get('degrees_of_freedom_spec') or {})
    degrees.get('creative_features_spec',{}).pop('standard_enhancements',None)
    result={'name':name,'object_story_spec':oss,'url_tags':tags if source_tags else ''}
    if feed:result['asset_feed_spec']=feed
    if degrees:result['degrees_of_freedom_spec']=degrees
    if creative.get('media_sourcing_spec'):result['media_sourcing_spec']=strip_output(copy.deepcopy(creative['media_sourcing_spec']))
    return result

"""Offline regression for post-preserving AFS recovery; zero Meta calls."""
import copy
import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from ares_campaign_v3.creative_media import creative_body, matches


def package():
    return {'name':'post-afs','object_story_id':'page_post','url_tags':'utm_campaign=c46',
            'asset_feed_spec':{'videos':[{'video_id':'v1'},{'video_id':'v2'}],
                'bodies':[{'text':'a'},{'text':'b'}], 'titles':[{'text':'x'},{'text':'y'}],
                'asset_customization_rules':[{'priority':1},{'priority':2,'is_default':True,'use_existing_post':True}]}}


def test_body_preserves_post_and_complete_feed():
    p=package();body=creative_body(p)
    assert body['object_story_id']==p['object_story_id']
    assert body['asset_feed_spec']==p['asset_feed_spec']
    assert p==package()


def test_existing_post_feed_requires_explicit_fallback_flag():
    p=package();p['asset_feed_spec']['asset_customization_rules'][-1].pop('use_existing_post')
    with pytest.raises(ValueError,match='use_existing_post'):
        creative_body(p)


def test_post_feed_readback_checks_post_and_all_variants():
    p=package();actual=copy.deepcopy(p)
    assert matches(actual,p)
    actual['object_story_id']='other_post';assert not matches(actual,p)
    actual=copy.deepcopy(p);actual['asset_feed_spec']['videos']=[];assert not matches(actual,p)
    actual=copy.deepcopy(p);actual['asset_feed_spec']['bodies'].pop();assert not matches(actual,p)


def test_readback_can_omit_transport_only_default_flags():
    p=package();actual=copy.deepcopy(p)
    for key in ['is_default','use_existing_post']:
        actual['asset_feed_spec']['asset_customization_rules'][-1].pop(key)
    assert matches(actual,p)


def test_old_post_only_payload_is_unchanged():
    p={'name':'old','object_story_id':'page_post','url_tags':'utm_campaign=c46'}
    assert creative_body(p)==p
    assert matches(p,p)

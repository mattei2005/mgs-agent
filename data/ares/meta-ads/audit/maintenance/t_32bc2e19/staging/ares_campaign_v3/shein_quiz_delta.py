"""Explicit same-site quiz-version delta for SHEIN pure clones; no I/O/writer."""
from __future__ import annotations
import copy
import re
from urllib.parse import urlparse, urlunparse
from .creative_media import source_links


def validate_intent(request):
    if 'target_quiz_version' not in request:
        return
    if (request.get('mode', 'pure_clone') != 'pure_clone'
            or request.get('target_quiz_version') not in ('v1', 'v2', 'v3')
            or request.get('source_account') or request.get('preserve_posts') is True):
        raise ValueError('quiz delta requires pure clone, v1/v2/v3 and new posts')


def target_base(request, profile):
    validate_intent(request)
    base = profile['destination_base']
    if 'target_quiz_version' not in request:
        return base
    parsed = urlparse(base)
    manager = str(profile['manager_code']).lower()
    if (parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password
            or parsed.port not in (None, 443) or parsed.query or parsed.fragment
            or not re.fullmatch(r'/quiz/us/sh[123]-' + re.escape(manager) + r'/', parsed.path)):
        raise ValueError('source quiz route not canonical for account manager')
    return urlunparse(parsed._replace(path='/quiz/us/sh' + request['target_quiz_version'][1] + '-' + manager + '/'))


def apply(payload, request, profile):
    if 'target_quiz_version' not in request:
        return payload
    target = target_base(request, profile)
    original = profile['destination_base']
    result = copy.deepcopy(payload)
    if result.get('object_story_id') or not result.get('object_story_spec'):
        raise ValueError('quiz delta requires complete editable creative definition')
    changes = 0
    def walk(value):
        nonlocal changes
        if isinstance(value, dict):
            for key, item in value.items():
                if key in ('link', 'website_url') and isinstance(item, str) and urlparse(item).scheme in ('http', 'https'):
                    parsed = urlparse(item)
                    if urlunparse(parsed._replace(query='', fragment='')) != original:
                        raise ValueError('quiz delta encountered non-source destination')
                    wanted = urlparse(target)
                    value[key] = urlunparse(parsed._replace(path=wanted.path))
                    changes += 1
                else:
                    walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)
    walk(result.get('object_story_spec', {}))
    walk(result.get('asset_feed_spec', {}))
    if not changes or any(link.split('?', 1)[0] != target for link in source_links(result, result['object_story_spec'])):
        raise ValueError('quiz delta destination coverage incomplete')
    return result

"""SHEIN approved naming, derived from verified quiz-route and real bid strategy."""
from __future__ import annotations
import re
from datetime import datetime
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

BIDS={'LOWEST_COST_WITHOUT_CAP':'MAXVOL','COST_CAP':'COCAP','LOWEST_COST_WITH_BID_CAP':'BIDCAP'}
NEW_NAME=re.compile(r'^([0-9]+) - ([0-9]{2}/[0-9]{2}) - (v[123]) - (.+?) - (MAXVOL|COCAP|BIDCAP) - \(([^()]+)\) - add_to_wishlist$')


def product_label(source_name):
    modern=NEW_NAME.fullmatch(source_name)
    if modern:return modern[4]
    value=source_name.split('(',1)[0]
    value=re.sub(r'^[0-9]+\s*-\s*','',value)
    value=re.sub(r'\s*\[[^\]]*\]\s*',' ',value)
    value=re.sub(r'\b(?:MAXVOL|COCAP|BIDCAP|COSTCAP|BID|COST\s+CAP)(?:\s+(?:USD\s*)?[0-9]+(?:[.,][0-9]+)?)?\b','',value,flags=re.I)
    value=re.sub(r'\[?[0-9]{2}/[0-9]{2}\]?','',value)
    value=re.sub(r'\s*-?\s*US-(?:EN|ES)\b','',value)
    value=re.sub(r'\s*-\s*-\s*',' - ',value).strip(' -')
    value=re.sub(r'\s+',' ',value)
    if not value:raise ValueError('campaign product label unavailable')
    return value


def quiz_version(destination,policy):
    parsed=urlparse(destination)
    if parsed.scheme!='https' or not parsed.hostname:raise ValueError('quiz destination invalid')
    match=re.fullmatch(policy['route_regex'],parsed.path)
    if not match:raise ValueError('quiz route not in verified corporate model contract')
    version=policy['layout_version_map'].get(match[1])
    if version not in {'v1','v2','v3'}:raise ValueError('quiz model version unresolved')
    return version


def campaign_name(number,start_time,timezone,destination,product,bid_strategy,tracking,policy):
    alias=BIDS.get(bid_strategy)
    if not alias:raise ValueError('SHEIN bid strategy not one of approved MAXVOL/COCAP/BIDCAP')
    version=quiz_version(destination,policy)
    date=datetime.fromisoformat(start_time).astimezone(ZoneInfo(timezone)).strftime('%d/%m')
    if not product.strip() or '(' in product or ')' in product:raise ValueError('ambiguous product label')
    return f'{int(number)} - {date} - {version} - {product.strip()} - {alias} - ({tracking}) - add_to_wishlist'

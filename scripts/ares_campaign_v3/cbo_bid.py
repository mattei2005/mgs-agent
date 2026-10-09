"""CBO bid deltas are campaign-atomic; manifests retain the requested adset cap."""
from __future__ import annotations
import re


def shell_payloads(spec, adset_id):
    campaign = {'name': spec.name, 'status': spec.status, 'start_time': spec.start_time, **spec.campaign_updates}
    adset = {'name': spec.adset_name or spec.name, 'status': spec.status, **spec.adset_updates}
    if getattr(spec, 'bid_override', False):
        strategy = campaign.get('bid_strategy')
        cap = str(adset.get('bid_amount') or '0')
        if not str(adset_id).isdigit() or adset.get('bid_constraints'):
            raise ValueError('CBO bid delta requires confirmed numeric adset and empty constraints')
        if strategy in {'COST_CAP', 'LOWEST_COST_WITH_BID_CAP'}:
            if not re.fullmatch(r'[1-9][0-9]*', cap):
                raise ValueError('CBO bid cap must be exact positive minor units')
            campaign['adset_bid_amounts'] = {str(adset_id): int(cap)}
        elif strategy != 'LOWEST_COST_WITHOUT_CAP' or cap != '0':
            raise ValueError('unsupported CBO bid delta')
        adset.pop('bid_amount', None)
        adset.pop('bid_constraints', None)
    return campaign, adset


def cap_matches(spec, observed):
    if not getattr(spec, 'bid_override', False):
        return True
    return (str(observed.get('bid_amount') or '0') == str(spec.adset_updates['bid_amount'])
            and (observed.get('bid_constraints') or {}) == spec.adset_updates['bid_constraints'])

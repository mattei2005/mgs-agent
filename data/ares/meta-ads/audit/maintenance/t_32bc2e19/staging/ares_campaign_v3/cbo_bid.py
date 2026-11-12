"""CBO bid deltas are campaign-atomic; manifests retain the requested adset cap."""
from __future__ import annotations
import re


def shell_payloads(spec, adset_id, *, source_strategy=None):
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
            if strategy == source_strategy:
                return campaign, adset
            campaign['adset_bid_amounts'] = {str(adset_id): int(cap)}
        elif strategy != 'LOWEST_COST_WITHOUT_CAP' or cap != '0':
            raise ValueError('unsupported CBO bid delta')
        adset.pop('bid_amount', None)
        adset.pop('bid_constraints', None)
    return campaign, adset


def reconcile_shells(engine, bundle, transport, record, campaign_ids, adset_ids):
    """Resume a failed shell update by live IDs, before any missing ad copy."""
    if record.get('stage') != 'adsets_created':
        return
    from .transport import BatchOperation
    reads = []
    for i, (cid, sid) in enumerate(zip(campaign_ids, adset_ids), 1):
        reads.extend([
            BatchOperation(f'shell_campaign_{i}', 'GET', cid+'?fields=id,account_id,name,status,daily_budget,bid_strategy', kind='readback'),
            BatchOperation(f'shell_adset_{i}', 'GET', sid+'?fields=id,campaign_id,name,status,bid_amount,bid_constraints,start_time', kind='readback')])
    rows = engine._batch(bundle, transport, reads, 'recovery_shell_readback')
    live = {r.name:r.body for r in rows}; writes=[]
    for i, (spec,cid,sid) in enumerate(zip(bundle.campaigns,campaign_ids,adset_ids),1):
        c=live[f'shell_campaign_{i}'];a=live[f'shell_adset_{i}']
        if c.get('id')!=cid or c.get('account_id')!=spec.account_id or a.get('id')!=sid or a.get('campaign_id')!=cid:
            raise ValueError('shell recovery account/parent identity mismatch')
        cp,ap=shell_payloads(spec,sid,source_strategy=c.get('bid_strategy'))
        cp.pop('start_time',None)
        def changed(expected, observed):
            return {k:v for k,v in expected.items() if ((observed.get(k) or {}) != v if k=='bid_constraints' else str(observed.get(k)) != str(v))}
        cp=changed(cp,c);ap=changed(ap,a)
        if cp:writes.append(BatchOperation(f'recovery_shell_campaign_{i}','POST',cid,body=cp,kind='campaign_update'))
        if ap:writes.append(BatchOperation(f'recovery_shell_adset_{i}','POST',sid,body=ap,kind='adset_update'))
    if writes:engine._batch(bundle,transport,writes,'recovery_shell_normalize')
    record['recovery']['shell_ids_preserved']=True
    record['recovery']['shell_mutations']=len(writes)
    record['stage']='shells_normalized'


def cap_matches(spec, observed):
    if not getattr(spec, 'bid_override', False):
        return True
    return (str(observed.get('bid_amount') or '0') == str(spec.adset_updates['bid_amount'])
            and (observed.get('bid_constraints') or {}) == spec.adset_updates['bid_constraints'])

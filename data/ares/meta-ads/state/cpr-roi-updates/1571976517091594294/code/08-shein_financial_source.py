"""Offline SHEIN finance: already-adjusted SB investment, no timezone shifting.

No API, auth, posting, scheduler or Meta mutations. Historical snapshots retain
legacy semantics before the contract's effective financial collection time.
"""
import copy
import hashlib
import json
from datetime import datetime
from decimal import Decimal, InvalidOperation


class FinancialSourceError(ValueError):
    pass


def number(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        n = Decimal(str(value))
        return n if n.is_finite() else None
    except (InvalidOperation, ValueError):
        return None


def roi(revenue, spend):
    r, s = number(revenue), number(spend)
    return (r - s) * 100 / s if r is not None and s is not None and s > 0 else None


def active_rule(model, cfg):
    rule = cfg.get('financial_source_standard') or {}
    if rule.get('status') != 'active':
        return None
    aid = str(model.get('account', {}).get('id', '')).removeprefix('act_')
    binding = cfg.get('account_report_overrides', {}).get(aid)
    if not binding or binding.get('status') != 'active':
        return None
    if model['account'].get('name') != binding.get('account_name'):
        raise FinancialSourceError('Financial account identity mismatch')
    stamps = model.get('source_timestamps', {})
    collected = [datetime.fromisoformat(stamps[k]) for k in ('insights', 'sb') if stamps.get(k)]
    if not collected:
        return None  # The renderer separately requires timestamp evidence.
    if any(t.tzinfo is None for t in collected):
        raise FinancialSourceError('Financial timestamps require offsets')
    return rule if max(collected) >= datetime.fromisoformat(rule['effective_from_financial_snapshot']) else None


def scoped_evidence(rows, account_id, history_dates):
    fields = ('CUSTOMER_ID', 'CAMPAIGN_ID', 'ADGROUP_ID', 'PK_JBF_PERFORMANCE_PER_ADGROUP',
              'DATE', 'PUBLISHER', 'DOMAIN', 'COUNTRY', 'VERTICAL', 'SOURCE',
              'INVESTIMENT', 'NET_REVENUE', 'REVENUE_ESTIMATED')
    result, seen = [], set()
    for row in rows:
        if str(row.get('CUSTOMER_ID', '')).removeprefix('act_') != account_id:
            raise FinancialSourceError('SB financial row outside exact account')
        dt = str(row.get('DATE', ''))[:10]
        if dt not in history_dates:
            raise FinancialSourceError('SB financial row outside history period')
        if not row.get('CAMPAIGN_ID'):
            raise FinancialSourceError('SB financial campaign missing')
        pk = row.get('PK_JBF_PERFORMANCE_PER_ADGROUP')
        key = (account_id, dt, str(row['CAMPAIGN_ID']), str(pk) if pk is not None else
               tuple(str(row.get(k, '')) for k in ('ADGROUP_ID', 'COUNTRY', 'VERTICAL', 'SOURCE')))
        if key in seen:
            raise FinancialSourceError('Duplicate SB financial source row')
        seen.add(key)
        item = {k: row[k] for k in fields if k in row}
        item['DATE'] = dt
        result.append(item)
    return result


def sum_metric(rows, field):
    values = [number(row.get(field)) for row in rows]
    if not values or any(v is None for v in values):
        return None
    if field == 'INVESTIMENT' and any(v < 0 for v in values):
        raise FinancialSourceError('Negative SB investment requires review')
    return sum(values, Decimal(0))


def additional_campaign_ids(sb_rows, account_id, day):
    """Keep SB financial-day delivery even when Meta's NY day has no delivery."""
    selected = set()
    for row in sb_rows:
        if str(row.get('CUSTOMER_ID', '')).removeprefix('act_') != account_id or str(row.get('DATE', ''))[:10] != day:
            continue
        metrics = ('INVESTIMENT', 'NET_REVENUE', 'REVENUE_ESTIMATED', 'IMPRESSIONS', 'CLICKS')
        if any(number(row.get(k)) is not None and number(row[k]) > 0 for k in metrics):
            selected.add(str(row['CAMPAIGN_ID']))
    return selected


def evidence_hash(rows):
    return hashlib.sha256(json.dumps(rows, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


def apply_financial_source(model, sb_rows, cfg):
    rule = active_rule(model, cfg)
    if not rule:
        return model
    aid = str(model['account']['id']).removeprefix('act_')
    evidence = scoped_evidence(sb_rows, aid, model['history_dates'])
    stamp = model['source_timestamps'].get('sb')
    if not stamp:
        raise FinancialSourceError('Missing SB financial collection timestamp')
    groups = {}
    for item in evidence:
        groups.setdefault((str(item['CAMPAIGN_ID']), item['DATE']), []).append(item)
    for row in model['rows']:
        row.setdefault('meta_spend', row['spend'])
        selected = groups.get((str(row['id']), model['date']), [])
        row['spend'] = sum_metric(selected, 'INVESTIMENT')
        row['net_revenue'] = sum_metric(selected, 'NET_REVENUE')
        row['estimated_revenue'] = sum_metric(selected, 'REVENUE_ESTIMATED')
        row['roi'] = roi(row['net_revenue'], row['spend'])
        row['estimated_roi'] = roi(row['estimated_revenue'], row['spend'])
        row['spend_source'] = 'SB_INVESTIMENT_ADJUSTED'
        for cell in row['history']:
            cell.setdefault('meta_spend', cell['spend'])
            values = groups.get((str(row['id']), cell['date']), [])
            cell['spend'] = sum_metric(values, 'INVESTIMENT')
            cell['net_revenue'] = sum_metric(values, 'NET_REVENUE')
            cell['roi'] = roi(cell['net_revenue'], cell['spend'])
            cell['spend_source'] = 'SB_INVESTIMENT_ADJUSTED'
        if row['spend'] is None:
            model.setdefault('configuration_limitations', []).append(
                'Investimento SB indisponível em '+row['number']+'; gasto/Saldo/ROI financeiros n/d, sem fallback Meta.')
    model['financial_source'] = {'policy_id': rule['policy_id'], 'source_kind': 'SB_INVESTIMENT_ADJUSTED',
        'account_id': aid, 'currency': model['account']['currency'], 'data_date': model['date'],
        'observed_at': stamp, 'investment_field': 'INVESTIMENT', 'revenue_field': 'NET_REVENUE',
        'estimated_revenue_field': 'REVENUE_ESTIMATED', 'additional_timezone_shift': False,
        'rows': evidence, 'sha256': evidence_hash(evidence)}
    model['source_timestamps']['financial'] = stamp
    return model


def validate_financial_source(model, cfg):
    rule = active_rule(model, cfg)
    if not rule:
        return False
    source = model.get('financial_source') or {}
    aid = str(model['account']['id']).removeprefix('act_')
    expected = {'policy_id': rule['policy_id'], 'source_kind': 'SB_INVESTIMENT_ADJUSTED',
        'account_id': aid, 'currency': model['account']['currency'], 'data_date': model['date'],
        'observed_at': model['source_timestamps'].get('sb'), 'investment_field': 'INVESTIMENT',
        'revenue_field': 'NET_REVENUE', 'estimated_revenue_field': 'REVENUE_ESTIMATED',
        'additional_timezone_shift': False}
    if any(source.get(k) != v for k, v in expected.items()) or not isinstance(source.get('rows'), list):
        raise FinancialSourceError('Missing or invalid adjusted SB financial provenance')
    evidence = scoped_evidence(source['rows'], aid, model['history_dates'])
    if evidence_hash(evidence) != source.get('sha256') or model['source_timestamps'].get('financial') != expected['observed_at']:
        raise FinancialSourceError('SB financial evidence hash/timestamp mismatch')
    expected_model = apply_financial_source(copy.deepcopy(model), evidence, cfg)
    for actual, calculated in zip(model['rows'], expected_model['rows']):
        for key in ('spend', 'net_revenue', 'estimated_revenue', 'roi', 'estimated_roi'):
            if number(actual.get(key)) != number(calculated.get(key)):
                raise FinancialSourceError('Mixed financial source metric: '+key)
        if actual.get('spend_source') != 'SB_INVESTIMENT_ADJUSTED' or number(actual.get('meta_spend')) is None:
            raise FinancialSourceError('Missing separate raw Meta spend evidence')
        if number(actual['meta_spend']) < 0:
            raise FinancialSourceError('Invalid raw Meta spend evidence')
        for a, c in zip(actual['history'], calculated['history']):
            if any(number(a.get(k)) != number(c.get(k)) for k in ('spend', 'net_revenue', 'roi')) or a.get('spend_source') != 'SB_INVESTIMENT_ADJUSTED':
                raise FinancialSourceError('Mixed financial history source')
    return True

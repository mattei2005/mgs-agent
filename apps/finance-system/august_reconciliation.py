"""Explicit August-only AdOps corrections; immutable source remains untouched."""
from copy import deepcopy
AUTHORITY = '1551324490271695064'
POLICY_ID = 'august-adops-cpv16-1551324490271695064'

YOLO_AUTHORITY = '1551644766125428847'
YOLO_POLICY_ID = 'august-yolokfx-mgs-' + YOLO_AUTHORITY

def yolo_metadata(data, additions, period):
    policies = [a for a in additions if a.get('kind') == 'reconciliation_policy' and a.get('id') == YOLO_POLICY_ID]
    if not policies:
        return data
    if len(policies) != 1 or period != '2026-08' or policies[0].get('authorization') != YOLO_AUTHORITY:
        raise ValueError('Invalid August Yolokfx authority or period')
    base = {c['cell']: c for c in data['cells'] if c['book'] == 'principal' and c['sheet'] == 'BASE_DASH'}
    targets = [key[1:] for key,c in base.items() if key.startswith('F') and c.get('input') == 'Yolokfx' and base.get('C'+key[1:],{}).get('input') == 'SITE']
    if len(targets) != 1:
        raise ValueError('Yolokfx SITE metadata not unique')
    replacements = {'G'+targets[0]:'SEM_COMISSAO', 'H'+targets[0]:'MGS'}
    result = dict(data)
    result['cells'] = [{**c,'input':replacements[c['cell']]} if c['book']=='principal' and c['sheet']=='BASE_DASH' and c['cell'] in replacements else c for c in data['cells']]
    return result

def prepare(data, additions, period):
    data = yolo_metadata(data, additions, period)
    policies = [a for a in additions if a.get('kind') == 'reconciliation_policy' and a.get('id') == POLICY_ID]
    if not policies:
        return data
    if period != '2026-08' or len(policies) != 1 or policies[0].get('authorization') != AUTHORITY:
        raise ValueError('Invalid August reconciliation authority or period')
    result = dict(data)
    result['cells'] = list(data['cells'])
    replacements = {}
    for day in range(1,32):
        input_row, source_row = 45+day, 304+day
        ident = f'principal|Agosto 2026|AJQ{source_row}'
        prior = f'=-ABS(SUM(AJV{input_row},AJW{input_row}))'
        replacement = f'=-ABS(SUM(AJV{input_row},AJW{input_row},AJX{input_row}))'
        replacements[ident] = (prior,replacement)
    found = set()
    for i,cell in enumerate(result['cells']):
        if cell['id'] not in replacements:
            continue
        old,new = replacements[cell['id']]
        if cell.get('formula') != old:
            raise ValueError('CPV16 source formula changed: '+cell['id'])
        result['cells'][i] = {**cell, 'formula':new}
        found.add(cell['id'])
    if found != set(replacements):
        raise ValueError('Incomplete CPV16 daily lineage')
    return result

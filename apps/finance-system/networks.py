"""Monthly network bindings; immutable source never changes.
Compatibility rates materialize only in this calculation's copied graph.
"""
import json,pathlib,re,copy
from calc import address,ci,num
RULES=json.loads((pathlib.Path(__file__).parent/'network-rules.json').read_text())
NETWORKS=RULES['networks'];MONTH='Agosto 2026'
def canonical(value):return RULES['legacy_aliases'].get(value,value)
def prepare(data,overrides,additions):
 changes={a['id']:a for a in additions if a.get('kind')=='site' and a.get('network')}
 for a in changes.values():
  if a['network'] not in NETWORKS:raise ValueError('Rede inválida')
 if not changes:return data
 # Resolve source site name and segment from the existing audited metadata binding.
 base={c['cell']:c.get('input',c.get('expected','')) for c in data['cells'] if c['book']=='principal' and c['sheet']=='BASE_DASH'}
 records={c['cell']:c for c in data['cells'] if c['book']=='principal' and c['sheet']=='BASE_DASH'};bybinding={}
 for r in range(2,155):
  if base.get('C'+str(r))=='SITE':
   formula=records.get('N'+str(r),{}).get('formula','');m=re.fullmatch(r"='Agosto 2026'!([A-Z]+\d+)",formula)
   if m:bybinding[m[1]]=(base.get('F'+str(r)),r)
 byname={a.get('name'):a for a in changes.values()};ranges=[];metadata={}
 for b in data['blocks']:
  name,row=bybinding[b['metrics']['RECEITA_NET_TOTAL']+str(b['totalrow'])];a=byname.get(name)
  if not a:continue
  rule=NETWORKS[a['network']];ranges.append((ci(b['start']),ci(b['end']),b['header'],max(address(c['cell'])[0] for c in data['cells'] if c['book']=='principal' and c['sheet']==MONTH),rule));metadata['E'+str(row)]=a['network']
 value=num(overrides.get(RULES['rede2_key'],RULES['rede2_initial']))
 if not 0<=value<=1:raise ValueError('Invalid network rate')
 cells=[]
 for c in data['cells']:
  if c['book']=='principal' and c['sheet']=='BASE_DASH' and c['cell'] in metadata:c={**c,'input':metadata[c['cell']],'kind':'input'}
  if c['book']=='principal' and c['sheet']==MONTH:
   if c['cell']=='XFD1':raise ValueError('Internal network bridge collides with source')
   if c.get('formula'):
    row,col=address(c['cell'])
    for lo,hi,first,last,rule in ranges:
     if lo<=col<=hi and first<=row<=last:
      fixed=lambda s:'$'+re.sub(r'\d','',s)+'$'+re.sub(r'\D','',s)
      f=re.sub(r'\$(?:J\$1|K\$1|L\$1|EN\$82)(?!\d)',lambda m:fixed(rule['invalid_source']),c['formula'])
      f=re.sub(r'\$(?:D\$1|EW\$82)(?!\d)',lambda m:fixed(rule['share_source']),f)
      c={**c,'formula':f};break
  cells.append(c)
 cells.append({'id':'principal|'+MONTH+'|XFD1','book':'principal','sheet':MONTH,'cell':'XFD1','kind':'input','input':value,'expected':value,'internal_network_bridge':True})
 return {**data,'cells':cells}

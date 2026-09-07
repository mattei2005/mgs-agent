"""Explicit, month-scoped WavesBee CAD repair. Never change imported evidence.
Authorization 1546607083468623912 covers August/September 2026 only.
"""
import re
POLICY='wavesbee-cad-1546607083468623912'
SITE='site-wavesbee-principal'
MONTHS=('2026-08','2026-09')
def enabled(additions,period):
 rows=[a for a in additions if a.get('kind')=='site' and a.get('currency_policy')==POLICY]
 if not rows:return False
 if len(rows)!=1 or rows[0].get('id')!=SITE or rows[0].get('name')!='WavesBee' or rows[0].get('input_currency')!='CAD' or period not in MONTHS:raise ValueError('Currency repair outside authorized monthly site scope')
 return True
def prepare(data,additions,period):
 if not enabled(additions,period):return data
 blocks=[];found=0
 for b in data['blocks']:
  if b['name'].split('\n')[0]=='WavesBee':
   assert b['start']=='GP' and b['header']==2 and b['metrics'].get('GROSS_GBP_US')=='GP','WavesBee source mapping changed'
   b={**b,'name':'WavesBee\nCAD\nUS','metrics':{('GROSS_CAD_US' if k=='GROSS_GBP_US' else k):v for k,v in b['metrics'].items()}};found+=1
  blocks.append(b)
 assert found==1
 cells=[];converted=0
 for c in data['cells']:
  if c['book']=='principal' and c['sheet']=='Agosto 2026':
   if c['cell'] in ('GP2','GP3'):
    c={**c,'input':'GROSS_CAD_US' if c['cell']=='GP2' else 'WavesBee\nCAD\nUS'}
   elif re.fullmatch(r'GQ(?:[5-9]|[12][0-9]|3[0-5])',c['cell']):
    row=c['cell'][2:];old=f'=IF(GP{row}="","",GP{row}*$I$1)'
    assert c.get('formula')==old,'Unexpected WavesBee conversion formula'
    c={**c,'formula':f'=IF(GP{row}="","",GP{row}/$H$1)'};converted+=1
  cells.append(c)
 assert converted==31
 return {**data,'cells':cells,'blocks':blocks}

"""Calendar-scoped template preparation; August evidence is never rewritten.
New periods inherit rules and identities, not imported monetary movements/reviews.
"""
import calendar,re,copy
from datetime import date,datetime
from zoneinfo import ZoneInfo
from calc import numeric
PERIODS=tuple(f'{y}-{m:02d}' for y in (2026,2027) for m in range(1,13) if '2026-08'<=f'{y}-{m:02d}'<='2027-12')
def info(period):
 if period not in PERIODS:raise ValueError('Período não cadastrado; permitido agosto/2026 a dezembro/2027')
 y,m=map(int,period.split('-'));return date(y,m,1),calendar.monthrange(y,m)[1]
def today():return datetime.now(ZoneInfo('America/New_York')).date().isoformat()
def valid_keys(model,period):
 _,days=info(period)
 return {key for ident,f in model['facts'].items() if int(ident.rsplit('|',1)[1])<=days for metric in ('gross','spend') for key in f[metric]}
def prepare(data,model,period,overrides,as_of=None):
 start,days=info(period)
 if period=='2026-08':return data
 allowed=valid_keys(model,period)
 if any(key in model['inputs'] and key not in allowed for key in overrides):raise ValueError('Entrada corresponde a dia inexistente neste mês')
 result={**data,'_period':period,'as_of':as_of or today(),'cells':[]}
 for c in data['cells']:
  replacement=None
  if c['id'] in model['inputs']:
   if c.get('formula'):raise ValueError('Template monetary leaf unexpectedly became formula')
   replacement={'kind':'input','input':''}
  elif c['book']=='principal' and c['sheet']=='Agosto 2026':
   if c['cell']=='A3':replacement={'input':start.month}
   elif c['cell']=='B4':replacement={'input':start.year}
   else:
    col=re.sub(r'\d','',c['cell']);row=int(re.sub(r'\D','',c['cell']))
    if 100<=row<=144 or 148<=row<=160:
     if col in ('O','P','R') and not c.get('formula'):replacement={'kind':'input','input':''}
     elif col=='Q':replacement={'kind':'input','input':'A conferir'}
  if replacement:c={**c,**replacement}
  result['cells'].append(c)
 return result

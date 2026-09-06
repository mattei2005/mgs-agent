from engine import *
from collections import Counter,defaultdict
A=GRIDS['principal','Agosto 2026'];V=lambda x:val(A.get(x,{}));N=lambda x:num(V(x)) if isinstance(V(x),(int,float)) else 0
blocks=json.loads((ROOT/'live-blocks.json').read_text());checks=[];warnings=[]
def ck(kind,cell,a,e,detail=None):checks.append({'kind':kind,'cell':cell,'actual':a,'expected':e,'pass':same(a,e),'detail':detail})
for b in blocks:
 hr=42 if b['header']==2 else 142;sr=46 if b['header']==2 else 146
 slots=[];countries={}
 for i in range(ci(b['start']),ci(b['end'])+1):
  label=str(V(col(i)+str(hr+1))).strip()
  if label in ['BM - $','$']:
   slot=col(i);slots.append(slot);lab=str(V(slot+str(hr))).upper()
   m=re.search(r'(?:^|[^A-Z])(US|GB|BR|DE|ES|TR|MX|CA|AR|ZA)(?:$|[^A-Z])',lab)
   if m:countries[slot]=m[1]
 for d in range(31):
  dest=b['metrics']['GASTOS_TOTAL']+str(b['sr']+d);row=sr+d
  ck('spend_all_slots',dest,N(dest),-sum(abs(N(co+str(row))) for co in slots),[co+str(row) for co in slots])
  # Country labels on actual account slots are read independently of formulas.
  metric_countries={h.split('_')[-1]:co for h,co in b['metrics'].items() if h.startswith('GASTOS_') and h!='GASTOS_TOTAL'}
  if len(metric_countries)>1:
   for country,co in metric_countries.items():
    src=[s+str(row) for s in slots if countries.get(s)==country]
    unmapped=[s+str(row) for s in slots if s not in countries and abs(N(s+str(row)))>1e-9]
    if not unmapped:ck('spend_country_labels',co+str(b['sr']+d),N(co+str(b['sr']+d)),-sum(abs(N(s)) for s in src),src)
 # Structural omissions of unused unlabeled slots are retained as future-risk candidates.
 totalformula=formula(A.get(b['metrics']['GASTOS_TOTAL']+str(b['sr']),{}))
 for co in slots:
  if co not in countries and not any(N(co+str(r)) for r in range(sr,sr+31)):continue
# Date runs in every main date band; one anchored calendar sequence per block.
for sr in [5,46,105,145,185,225,265,305]:
 for d in range(31):
  cell='B'+str(sr+d)
  if sr in [185,225,265,305] and V('B'+str(sr))=='':continue
  ck('calendar',cell,V(cell),(date(2026,8,1)+timedelta(days=d)-EPOCH).days)
# Monetary columns: identify both-manual and mismatched conversion pairs without assuming which paid currency is canonical.
for r in range(100,161):
 left,right='O'+str(r),'P'+str(r)
 if not any(isinstance(V(x),(int,float)) for x in [left,right]):continue
 lf=formula(A.get(left,{}));rf=formula(A.get(right,{}))
 if not lf and not rf and (N(left) or N(right)):
  warnings.append({'kind':'dual_manual_currency_needs_receipt','cells':[left,right],'label':V('M'+str(r)),'usd':N(left),'brl':N(right),'brl_at_provisional_fx':N(left)*N('F1'),'difference':N(right)-N(left)*N('F1')})
# Company expense daily distributions add up exactly once, not once per country or manager.
expenses=[(b['metrics']['DESPESA_TOTAL'],b['sr']) for b in blocks]
ck('company_expense_distribution','O145',sum(N(co+str(sr+d)) for co,sr in expenses for d in range(31)),N('O145'))
# Country rollup table lists no BR; quantify informational incompleteness independently.
countrykeys={h.split('_')[-1] for b in blocks for h in b['metrics'] if h.startswith('GROSS_USD_') or h=='GROSS_BR'}
rollupkeys={m[1] for c in range(ci('AMC'),ci('APC')+1) for m in re.finditer(r'"GROSS_USD_([A-Z]{2})"',formula(A.get(col(c)+'5',{})))}
missing=countrykeys-rollupkeys
for co in missing:
 refs=[cc+str(b['totalrow']) for b in blocks for h,cc in b['metrics'].items() if h in ['GROSS_USD_'+co,'GROSS_'+co]]
 warnings.append({'kind':'country_rollup_missing_country','country':co,'gross_usd':sum(N(x) for x in refs),'sources':refs})
save('spend-calendar-checks.json',checks);save('business-review-candidates.json',warnings)
print('counts',dict(Counter(x['kind'] for x in checks)),'failed',dict(Counter(x['kind'] for x in checks if not x['pass'])))
print('failure sample',[x for x in checks if not x['pass']][:15]);print('warnings',warnings)

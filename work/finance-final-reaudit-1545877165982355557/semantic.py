from engine import *
from collections import Counter,defaultdict
A=GRIDS['principal','Agosto 2026'];C=GRIDS['principal','CAIXA SINTETICO']
def v(addr):return val(A.get(addr,{}))
def n(addr):return num(v(addr)) if isinstance(v(addr),(int,float)) else 0
def f(addr):return formula(A.get(addr,{}))
checks=[]
def check(kind,cell,actual,expected,detail=None):
 checks.append({'kind':kind,'cell':cell,'actual':actual,'expected':expected,'pass':same(actual,expected),'detail':detail})
blocks=[]
for hrow,sr,er,tr in [(2,5,35,36),(102,105,135,136)]:
 i=4
 while i<=ci('AMA'):
  if not v(col(i)+str(hrow)):i+=1;continue
  start=i
  while i<=ci('AMA') and v(col(i)+str(hrow)):i+=1
  end=i-1
  metrics={str(v(col(c)+str(hrow))):col(c) for c in range(start,end+1)}
  if 'RECEITA_NET_TOTAL' not in metrics:continue
  b={'start':col(start),'end':col(end),'header':hrow,'sr':sr,'er':er,'totalrow':tr,'metrics':metrics,'name':v(col(start)+'3')}
  blocks.append(b)
  for r in range(sr,tr+1):
   for key,prefix in [('RECEITA_NET_TOTAL','NET_'),('IMPOSTO_TOTAL','IMPOSTO_'),('INVALIDO_TOTAL','INVALIDO_'),('GASTOS_TOTAL','GASTOS_')]:
    components=[co+str(r) for h,co in metrics.items() if h.startswith(prefix) and not h.endswith('_TOTAL')]
    check('component_total',metrics[key]+str(r),n(metrics[key]+str(r)),sum(n(x) for x in components),components)
   gross=[co+str(r) for h,co in metrics.items() if h.startswith('GROSS_USD_') or h=='GROSS_BR']
   net=metrics['RECEITA_NET_TOTAL']+str(r);tax=metrics['IMPOSTO_TOTAL']+str(r);expense=metrics['DESPESA_TOTAL']+str(r);spend=metrics['GASTOS_TOTAL']+str(r)
   profit=metrics['LUCRO_LIQUIDO_TOTAL']+str(r)
   check('profit_identity',profit,n(profit),sum(n(x) for x in [net,tax,expense,spend]))
   g=sum(n(x) for x in gross);s=abs(n(spend));ng=n(net);cost=s+abs(n(tax))+abs(n(expense))
   check('roi_gross_total',metrics['ROI_GROSS_TOTAL']+str(r),v(metrics['ROI_GROSS_TOTAL']+str(r)),g/s-1 if s else '',gross)
   check('roi_net_total',metrics['ROI_NET_TOTAL']+str(r),v(metrics['ROI_NET_TOTAL']+str(r)),ng/cost-1 if s and cost else '',[net,tax,expense,spend])
   for h,co in metrics.items():
    if not h.startswith('GROSS_USD_') and h!='GROSS_BR':continue
    country=h.split('_')[-1];grosscell=co+str(r)
    def by(prefix):return metrics.get(prefix+country)
    nc=by('NET_USD_') or by('NET_');tc=by('IMPOSTO_');sc=by('GASTOS_');ic=by('INVALIDO_');pc=by('LUCRO_LIQUIDO_');rg=by('ROI_GROSS_');rn=by('ROI_NET_')
    if not all([nc,tc,sc,ic,pc,rg,rn]):continue
    # Rates are existing contract parameters, not newly inferred business policy.
    share=0.05 if start in [ci('DH'),ci('EG')] else n('D1')
    rate=n('J1')
    invalid_formula=f(ic+str(sr));m=re.search(r'\$([A-Z]+)\$(\d+)',invalid_formula)
    if m:rate=n(m[1]+m[2])
    exp_invalid=-n(grosscell)*rate
    check('invalid_rate',ic+str(r),n(ic+str(r)),exp_invalid)
    check('net_rate',nc+str(r),n(nc+str(r)),(n(grosscell)+n(ic+str(r)))*(1-share))
    check('tax_rate',tc+str(r),n(tc+str(r)),-n(nc+str(r))*n('C1'))
    check('country_profit',pc+str(r),n(pc+str(r)),sum(n(x+str(r)) for x in [nc,tc,sc]))
    spendnum=abs(n(sc+str(r)));den=spendnum+abs(n(tc+str(r)))
    check('country_roi_gross',rg+str(r),v(rg+str(r)),n(grosscell)/spendnum-1 if spendnum else '')
    check('country_roi_net',rn+str(r),v(rn+str(r)),n(nc+str(r))/den-1 if spendnum and den else '')
  for h,co in metrics.items():
   if h.startswith('ROI_'):continue
   check('daily_sum_total',co+str(tr),n(co+str(tr)),sum(n(co+str(r)) for r in range(sr,er+1)))
# All numeric/type anomalies and all owned cell inventory.
inventory=[];data_anomalies=[]
for (book,title),cc in GRIDS.items():
 if title not in ['Agosto 2026','CAIXA SINTETICO','BASE_DASH','DASH EXECUTIVO']:continue
 for cell,x in cc.items():
  vv=val(x);ff=formula(x);ue=x.get('userEnteredValue',{})
  inventory.append({'book':book,'sheet':title,'cell':cell,'value':vv,'formula':ff,'entered_type':next(iter(ue),'spill'),'format':x.get('effectiveFormat',{}).get('numberFormat',{}).get('type')})
  if isinstance(vv,str) and re.fullmatch(r'[-+]?\d+[.,]?\d*',vv.strip()):data_anomalies.append({'book':book,'sheet':title,'cell':cell,'value':vv,'kind':'numeric_string'})
  if isinstance(vv,(int,float)) and not math.isfinite(vv):data_anomalies.append({'book':book,'sheet':title,'cell':cell,'kind':'nonfinite'})
with (ROOT/'all-cell-inventory.jsonl').open('w') as out:
 for row in inventory:out.write(json.dumps(row,ensure_ascii=False)+'\n')
# Formula continuity: relative R/C normalization in every daily semantic band.
def norm_formula(formula_,r,c):
 def rep(m):
  ac,cc,ar,rr=m.groups();nr=int(rr)
  return ('C'+str(ci(cc)) if ac else 'DC'+str(ci(cc)-c))+('R'+str(nr) if ar else 'DR'+str(nr-r))
 parts=re.split(r'("(?:[^"]|"")*")',formula_)
 return ''.join(p if i%2 else re.sub(r'(\$?)([A-Z]{1,3})(\$?)(\d+)',rep,p) for i,p in enumerate(parts)).strip()
continuity=[]
for sr,er,c1,c2 in [(5,35,4,ci('APM')),(46,76,4,ci('AMA')),(105,135,ci('RR'),ci('AGI')),(146,176,ci('RR'),ci('AGI'))]+[(r,r+30,ci('ZQ'),ci('ZX')) for r in [145,185,225,265,305]]+[(r,r+30,ci('AJM'),ci('AJT')) for r in [105,145,185,225,265,305]]:
 for c in range(c1,c2+1):
  fs=[(col(c)+str(r),norm_formula(f(col(c)+str(r)),r,c)) for r in range(sr,er+1) if f(col(c)+str(r))]
  if len(fs)<20:continue
  counter=Counter(z for _,z in fs)
  if len(counter)>1 or len(fs)!=er-sr+1:
   continuity.append({'col':col(c),'rows':[sr,er],'count':len(fs),'patterns':[{'normalized':pat,'cells':[a for a,z in fs if z==pat]} for pat,_ in counter.most_common()],'missing':[col(c)+str(r) for r in range(sr,er+1) if not f(col(c)+str(r))]})
save('semantic-checks.json',checks);save('live-blocks.json',blocks);save('data-anomalies.json',data_anomalies);save('continuity-candidates.json',continuity)
summary={'check_counts':dict(Counter(x['kind'] for x in checks)),'failed_counts':dict(Counter(x['kind'] for x in checks if not x['pass'])),'failures':[x for x in checks if not x['pass']],'data_anomalies':data_anomalies,'continuity_candidates':len(continuity),'inventory_counts':dict(Counter(x['book']+':'+x['sheet'] for x in inventory))}
save('semantic-summary.json',summary)
print('checks',summary['check_counts']);print('failures',summary['failed_counts']);print('FAIL SAMPLE',summary['failures'][:25]);print('data',data_anomalies[:20]);print('continuity',[(x['col'],x['rows'],len(x['patterns']),x['missing'][:3]) for x in continuity]);print('inventory',summary['inventory_counts'])

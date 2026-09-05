from engine import *
from collections import Counter, defaultdict
A=GRIDS['principal','Agosto 2026'];C=GRIDS['principal','CAIXA SINTETICO']
V=lambda cc,x:val(cc.get(x,{}));N=lambda cc,x:num(V(cc,x)) if isinstance(V(cc,x),(float,int)) else 0
blocks=json.loads((ROOT/'live-blocks.json').read_text())
records=[]
def ck(kind,cell,actual,expected,detail=None):records.append({'kind':kind,'cell':cell,'actual':actual,'expected':expected,'pass':same(actual,expected),'detail':detail})
# Independent daily/total arithmetic for all 12 gestor mini-blocks.
for start in ['ZQ','AJM']:
 base=ci(start)
 for sr in [105,145,185,225,265,305]:
  for r in range(sr,sr+32):
   gross,inv,net,tax,spend,profit,rg,rn=[col(c)+str(r) for c in range(base,base+8)]
   g=N(A,gross);sp=abs(N(A,spend));den=sp+abs(N(A,tax))
   for kind,cell,expect in [('mini_invalid',inv,-g*N(A,'J1')),('mini_net',net,(g+N(A,inv))*(1-N(A,'D1'))),('mini_tax',tax,-N(A,net)*N(A,'C1')),('mini_profit',profit,N(A,net)+N(A,tax)+N(A,spend))]:ck(kind,cell,N(A,cell),expect)
   ck('mini_roi_gross',rg,V(A,rg),g/sp-1 if sp else '')
   ck('mini_roi_net',rn,V(A,rn),N(A,net)/den-1 if sp and den else '')
  for c in range(base,base+6):ck('mini_sum',col(c)+str(sr+31),N(A,col(c)+str(sr+31)),sum(N(A,col(c)+str(r)) for r in range(sr,sr+31)))
# Independently recompute the all-sites raw gross from currency-normalized components.
for r in range(5,37):
 src=[co+str(r+(100 if b['header']==102 else 0)) for b in blocks for h,co in b['metrics'].items() if h.startswith('GROSS_USD_') or h=='GROSS_BR']
 gross=sum(N(A,x) for x in src);sp=abs(N(A,'APB'+str(r)))
 ck('global_gross_roi','APD'+str(r),V(A,'APD'+str(r)),gross/sp-1 if sp else '',{'gross':gross,'spend':sp})
 # Existing sheet definition for net ROI is return on all costs, not profit/media.
 den=sum(abs(N(A,co+str(r))) for co in ['APB','AOX','AOY','AOZ'])
 ck('global_net_roi_without_double_invalid','APE'+str(r),V(A,'APE'+str(r)),N(A,'AOW'+str(r))/den-1 if den else '',{'net':N(A,'AOW'+str(r)),'cost':den,'invalid_already_inside_net':N(A,'APA'+str(r))})
# Detailed manager mapping: every C/D summary precedent belongs to the named site's imported block and expected metric.
manager={}
for name in list(IDS)[1:]:
 cc=GRIDS[name,'Agosto 2026'];spills=[];covered=set();mapping=[]
 for cell,x in cc.items():
  ff=formula(x)
  if 'IMPORTRANGE' not in ff:continue
  rr=evaluate(Parser(ff).parse(),name,'Agosto 2026',cell)
  r0,c0=int(re.search(r'\d+',cell)[0]),ci(re.match(r'[A-Z]+',cell)[0])
  spills.append((cell,rr,r0,c0))
  for r in range(r0,r0+rr.r2-rr.r1+1):
   for c in range(c0,c0+rr.c2-rr.c1+1):covered.add(col(c)+str(r))
 for row in range(2,12):
  label=V(cc,'B'+str(row))
  if not label:continue
  for co,metric in [('C','INVALIDO'),('D','LUCRO_LIQUIDO')]:
   dest=co+str(row);ff=formula(cc.get(dest,{}));refs=re.findall(r'\b([A-Z]+)(\d+)\b',ff)
   if len(refs)!=1:mapping.append({'dest':dest,'status':'unresolved','formula':ff});continue
   targetcol,targetrow=ci(refs[0][0]),int(refs[0][1]);found=[]
   for anchor,rr,r0,c0 in spills:
    if r0<=targetrow<=r0+rr.r2-rr.r1 and c0<=targetcol<=c0+rr.c2-rr.c1:
     src=col(rr.c1+targetcol-c0)+str(rr.r1+targetrow-r0);header=V(A,col(rr.c1+targetcol-c0)+str(rr.r1));origin=V(A,col(rr.c1)+str(rr.r1))
     found.append({'source':src,'header':header,'origin':origin,'anchor':anchor})
   if len(found)!=1:mapping.append({'dest':dest,'status':'unresolved','found':found});continue
   detail=found[0];h=re.sub(r'\s+','_',str(detail['header']).upper())
   valid=('INVALIDO' in h or 'INVALI' in h) if metric=='INVALIDO' else ('LUCRO' in h and 'LIQUIDO' in h)
   mapping.append({'dest':dest,'status':'pass' if valid else 'metric_mismatch','label':label,**detail})
 # Projection control: actual dates selected, not number of nonempty header cells.
 forecasts=[]
 for col_ in ['C','D','E','F']:
  cell=col_+'14';ff=formula(cc[cell]);m=re.search(r'\$C\$(\d+):\$C\$(\d+)',ff);r1,r2=map(int,m.groups());dates=[V(cc,'A'+str(r)) for r in range(r1,r2+1)]
  dated=[(EPOCH+timedelta(days=d)).isoformat() for d in dates if isinstance(d,(float,int)) and 46000<d<47000]
  present=[r for r in range(r1,r2+1) if V(cc,'C'+str(r))!=''];den=max(present)-r1+1 if present else 0
  forecasts.append({'cell':cell,'formula':ff,'anchor_dates':{'first':dated[0] if dated else None,'last':dated[-1] if dated else None,'count':len(dated),'non_dates':[d for d in dates if d!='' and not isinstance(d,(int,float))]},'denominator':den,'sum_row12':V(cc,col_+'12'),'forecast_row14':V(cc,cell)})
 # Every non-formula, non-spill cell is catalogued to catch detached manual amounts.
 detached=[{'cell':cell,'value':V(cc,cell)} for cell,x in cc.items() if not formula(x) and cell not in covered and int(re.search(r'\d+',cell)[0])>=19]
 manager[name]={'gid':load(name)['sheets'][0]['properties']['sheetId'],'summary_mapping':mapping,'forecasts':forecasts,'detached':detached,'month_label':V(cc,'A1')}
# Compare every summary revenue line against actual country components, including special lower blocks.
summary=[]
for b in blocks:
 sr=b['totalrow'];cohort=[co+str(sr) for h,co in b['metrics'].items() if h.startswith('GROSS_USD_') or h=='GROSS_BR']
 # Find closing summary from final I136 explicit constituents within this block.
 candidates=re.findall(r'\b([A-Z]+)(97|198)\b',formula(A['I136']))
 closure=[co+rr for co,rr in candidates if ci(b['start'])<=ci(co)<=ci(b['end']) and int(rr)==(97 if sr==36 else 198)]
 if len(closure)!=1:continue
 close=closure[0];co=re.match('[A-Z]+',close)[0];revrow=83 if sr==36 else 184
 ck('closure_revenue_components',co+str(revrow),N(A,co+str(revrow)),sum(N(A,x) for x in cohort),cohort)
 invalidrow=revrow+1;netrow=revrow+2;taxrow=revrow+3
 ck('closure_invalid',co+str(invalidrow),N(A,co+str(invalidrow)),N(A,b['metrics']['INVALIDO_TOTAL']+str(sr)))
 ck('closure_postshare',co+str(netrow),sum(N(A,co+str(r)) for r in range(revrow,netrow+1)),N(A,b['metrics']['RECEITA_NET_TOTAL']+str(sr)))
 ck('closure_tax',co+str(taxrow),N(A,co+str(taxrow)),N(A,b['metrics']['IMPOSTO_TOTAL']+str(sr)))
# Exact reconciliation bridge of the two competing 50% results.
bridge={
 'cash_J81':N(C,'J81'),'month_J137':N(A,'J137'),'fx':N(A,'F1'),
 'cash_profit':N(C,'J77'),'daily_profit':N(A,'APC36'),'closure_profit':N(A,'I136'),
 'cash_minus_daily_usd':N(C,'J77')-N(A,'APC36'),
 'daily_minus_closure_usd':N(A,'APC36')-N(A,'I136'),
 'missing_share_yolok_gross':N(C,'J37')*N(C,'B3')*(1-N(C,'B2')),
 'omitted_invalid_yolok':-N(A,'AGQ84')*.9*.95,
 'omitted_invalid_infinity_lower':-N(A,'AFN185')*.9*.95,
 'eggbev_missing_gross':N(A,'LD36'),
 'cliquet_missing_gross':N(A,'NF36'),
 'eggbev_missing_gross_net':N(A,'LD36')*(1-N(A,'J1'))*.9*.95,
 'cliquet_missing_gross_net':N(A,'NF36')*(1-N(A,'J1'))*.9*.95,
 'eggbev_missing_invalid_cash':N(A,'LD36')*N(A,'J1')*.9*.95,
 'cliquet_missing_invalid_cash':N(A,'NF36')*N(A,'J1')*.9*.95,
}
bridge['explained_delta_usd']=sum(bridge[k] for k in ['missing_share_yolok_gross','omitted_invalid_yolok','omitted_invalid_infinity_lower','eggbev_missing_gross_net','cliquet_missing_gross_net','eggbev_missing_invalid_cash','cliquet_missing_invalid_cash'])
bridge['actual_delta_usd']=N(C,'J77')-N(A,'I136');bridge['residual_usd']=bridge['actual_delta_usd']-bridge['explained_delta_usd']
save('extended-semantic-checks.json',records);save('manager-semantic-audit.json',manager);save('J81-J137-bridge.json',bridge)
print('extended counts',dict(Counter(x['kind'] for x in records)));print('failed',dict(Counter(x['kind'] for x in records if not x['pass'])))
print('closure failures',[x for x in records if not x['pass'] and x['kind'].startswith('closure')]);print('bridge',bridge)
for name,data in manager.items():print(name,'mapping',dict(Counter(x['status'] for x in data['summary_mapping'])),'detached',data['detached'],'forecast',data['forecasts'][1])

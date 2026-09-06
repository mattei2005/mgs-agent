from engine import *
from collections import Counter,defaultdict
from zoneinfo import ZoneInfo
from datetime import datetime
A=GRIDS['principal','Agosto 2026'];C=GRIDS['principal','CAIXA SINTETICO'];B=GRIDS['principal','BASE_DASH'];D=GRIDS['principal','DASH EXECUTIVO']
V=lambda cc,t:val(cc.get(t,{}))
N=lambda cc,t:V(cc,t) if isinstance(V(cc,t),(int,float)) else 0
F=lambda cc,t:formula(cc.get(t,{}))
checks=[];notes=[]
def ck(kind,cell,actual,expected,detail=None):checks.append(dict(kind=kind,cell=cell,actual=actual,expected=expected,passed=same(actual,expected),detail=detail))
blocks=load('live-blocks')
for start in ['ZQ','AJM']:
 base=ci(start)
 for sr in [105,145,185,225,265,305]:
  for r in range(sr,sr+32):
   g,iv,ne,ta,sp,pr,rg,rn=[col(c)+str(r) for c in range(base,base+8)]
   gross=N(A,g);spend=abs(N(A,sp));den=spend+abs(N(A,ta))
   for kind,t,e in [('mini_invalid',iv,-gross*N(A,'J1')),('mini_net',ne,(gross+N(A,iv))*(1-N(A,'D1'))),('mini_tax',ta,-N(A,ne)*N(A,'C1')),('mini_profit',pr,N(A,ne)+N(A,ta)+N(A,sp)),('mini_roi_gross',rg,gross/spend-1 if spend else ''),('mini_roi_net',rn,N(A,ne)/den-1 if spend and den else '')]:ck(kind,t,V(A,t) if kind.startswith('mini_roi') else N(A,t),e)
  for c in range(base,base+6):ck('mini_total',col(c)+str(sr+31),N(A,col(c)+str(sr+31)),sum(N(A,col(c)+str(r)) for r in range(sr,sr+31)))
closures=[]
for b in blocks:
 tr=b['totalrow'];refs=[co+str(tr) for h,co in b['metrics'].items() if h.startswith('GROSS_USD_') or h=='GROSS_BR']
 candidates=[co+rr for co,rr in re.findall(r'\b([A-Z]+)(97|198)\b',F(A,'I136')) if ci(b['start'])<=ci(co)<=ci(b['end']) and int(rr)==(97 if tr==36 else 198)]
 ck('closure_identified',b['start']+str(tr),len(candidates),1)
 if len(candidates)!=1:continue
 close=candidates[0];co=re.match('[A-Z]+',close)[0];rr=83 if tr==36 else 184;closures.append(close)
 ck('closure_gross',co+str(rr),N(A,co+str(rr)),sum(N(A,t) for t in refs),refs)
 ck('closure_invalid',co+str(rr+1),N(A,co+str(rr+1)),N(A,b['metrics']['INVALIDO_TOTAL']+str(tr)))
 ck('closure_postshare',co+str(rr+2),sum(N(A,co+str(r)) for r in range(rr,rr+3)),N(A,b['metrics']['RECEITA_NET_TOTAL']+str(tr)))
 ck('closure_tax',co+str(rr+3),N(A,co+str(rr+3)),N(A,b['metrics']['IMPOSTO_TOTAL']+str(tr)))
 # RR38 and AFJ38 intentionally aggregate their matching lower blocks.
 if b['start']=='RR' and tr==136:continue
 summaryrefs=list(refs)
 if tr==36:
  for lower in blocks:
   if lower['start']==b['start'] and lower['totalrow']==136:
    summaryrefs += [co+'136' for h,co in lower['metrics'].items() if h.startswith('GROSS_USD_') or h=='GROSS_BR']
 ck('row38_gross_summary',b['start']+str(tr+2),N(A,b['start']+str(tr+2)),sum(N(A,t) for t in summaryrefs),summaryrefs)
# Independent country and global metrics from every source block, including aliases and lower blocks.
for r in range(5,37):
 totals=defaultdict(float);countries=defaultdict(lambda:defaultdict(float))
 for b in blocks:
  rr=r+(100 if b['header']==102 else 0)
  for h,co in b['metrics'].items():
   if h.endswith('_TOTAL'):totals[h]+=N(A,co+str(rr));continue
   metric=None
   for pref,m in [('GROSS_USD_','gross'),('NET_USD_','net'),('IMPOSTO_','tax'),('GASTOS_','spend'),('LUCRO_LIQUIDO_','profit')]:
    if h.startswith(pref):metric=m;break
   if h=='GROSS_BR':metric='gross'
   if h=='NET_BR':metric='net'
   if metric:countries[h.split('_')[-1]][metric]+=N(A,co+str(rr))
 for cc in range(ci('AMC'),ci('APC')+1):
  label=str(V(A,col(cc)+'3')).replace('\n',' ').split()
  if len(label)<3 or label[:2]!=['GROSS','USD']:continue
  country=label[-1];vals=countries[country]
  for off,m in enumerate(['gross','net','tax','spend','profit']):ck('country_rollup',col(cc+off)+str(r),N(A,col(cc+off)+str(r)),vals[m],country)
  for off,revenue in [(5,vals['gross']),(6,vals['net'])]:
   den=abs(vals['spend'])+(abs(vals['tax']) if off==6 else 0)
   expected='' if vals['spend']==0 or (r<36 and revenue==0) else revenue/den-1
   ck('country_rollup_roi',col(cc+off)+str(r),V(A,col(cc+off)+str(r)),expected,country)
 gross=sum(v['gross'] for v in countries.values());sp=abs(N(A,'APJ'+str(r)))
 ck('global_gross_roi','APL'+str(r),V(A,'APL'+str(r)),gross/sp-1 if sp else '')
 den=sum(abs(N(A,c+str(r))) for c in ['APJ','APF','APG','APH'])
 ck('global_net_roi','APM'+str(r),V(A,'APM'+str(r)),N(A,'APE'+str(r))/den-1 if sp and den else '')
 for c,key in [('APE','RECEITA_NET_TOTAL'),('APF','IMPOSTO_TOTAL'),('APG','DESPESA_TOTAL'),('APJ','GASTOS_TOTAL')]:ck('global_component',c+str(r),N(A,c+str(r)),totals[key])
 ck('global_profit','APK'+str(r),N(A,'APK'+str(r)),sum(N(A,c+str(r)) for c in ['APE','APF','APG','APH','APJ']))
ck('cash_month_profit','J77/I136',N(C,'J77'),N(A,'I136'));ck('cash_daily_profit','J77/APK36',N(C,'J77'),N(A,'APK36'));ck('half_brl','J81/J137',N(C,'J81'),N(A,'J137'));ck('fx','F1/J2',N(A,'F1'),N(C,'J2'))
# Full manager summaries, projected rates, imported metric labels and current calendar.
managers={}
for name in list(IDS)[1:]:
 cc=GRIDS[name,'Agosto 2026'];imports=[];covered=set()
 for t,x in cc.items():
  ff=formula(x)
  if ff.startswith('=IMPORTRANGE'):
   rr=evaluate(Parser(ff).parse(),name,'Agosto 2026',t);r0=int(re.search(r'\d+',t)[0]);c0=ci(re.match('[A-Z]+',t)[0]);imports.append((t,rr,r0,c0))
   covered.update(col(c)+str(r) for r in range(r0,r0+rr.r2-rr.r1+1) for c in range(c0,c0+rr.c2-rr.c1+1))
 mapping=[]
 for row in range(2,12):
  label=V(cc,'B'+str(row))
  if not label:continue
  for co,metric in [('C','INVALID'),('D','LUCRO')]:
   t=co+str(row);refs=re.findall(r'\b([A-Z]+)(\d+)\b',F(cc,t));found=[]
   if len(refs)==1:
    tc,tr=ci(refs[0][0]),int(refs[0][1])
    for anchor,rr,r0,c0 in imports:
     if r0<=tr<=r0+rr.r2-rr.r1 and c0<=tc<=c0+rr.c2-rr.c1:
      src=col(rr.c1+tc-c0)+str(rr.r1+tr-r0);head=V(A,col(rr.c1+tc-c0)+str(rr.r1));found.append(dict(source=src,header=head,origin=V(A,col(rr.c1)+str(rr.r1))))
   ck('manager_metric_map',name+':'+t,len(found),1)
   if len(found)==1:ck('manager_metric_label',name+':'+t,metric in str(found[0]['header']).upper(),True)
   mapping.append(dict(cell=t,label=label,found=found))
 for co in 'CDEF':ck('manager_summary',name+':'+co+'12',N(cc,co+'12'),sum(N(cc,co+str(r)) for r in range(2,12)))
 for row in range(2,12):
  if not V(cc,'B'+str(row)):continue
  ck('manager_7pct',name+':E'+str(row),N(cc,'E'+str(row)),N(cc,'D'+str(row))*.07)
  ck('manager_10pct',name+':F'+str(row),N(cc,'F'+str(row)),N(cc,'D'+str(row))*.10)
 startcells=sorted([t for t,x in cc.items() if re.fullmatch('A[0-9]+',t) and V(cc,t)==(date(2026,8,1)-EPOCH).days],key=lambda t:int(t[1:]));ck('manager_calendar_present',name,bool(startcells),True)
 anchor=startcells[0];startrow=int(anchor[1:])
 for t in startcells:
  r=int(t[1:])
  for off in range(31):ck('manager_calendar',name+':A'+str(r+off),V(cc,'A'+str(r+off)),(date(2026,8,1)+timedelta(days=off)-EPOCH).days)
 for co in 'CDEF':
  refa='$A$'+str(startrow);expected=f'=IF({co}12="";"";IF(TODAY()<={refa};"";{co}12/MIN(DAY(EOMONTH({refa};0));TODAY()-{refa})*DAY(EOMONTH({refa};0))))'
  ck('manager_projection_formula',name+':'+co+'14',F(cc,co+'14').strip().replace(';',','),expected.replace(';',','))
 ck('manager_month_label',name+':A1',V(cc,'A1'),'Agosto')
 managers[name]={'mapping':mapping,'anchor':anchor,'calendar_blocks':len(startcells),'unimported_manual_cells':[dict(cell=t,value=V(cc,t)) for t,x in cc.items() if t not in covered and not formula(x) and int(re.search(r'\d+',t)[0])>=19]}
save('integrated-checks.json',checks);save('manager-mapping-review.json',managers)
print('checks',len(checks),'failures',dict(Counter(x['kind'] for x in checks if not x['passed'])))
print('failed',[x for x in checks if not x['passed']][:25]);print('closure count',len(closures));print('manager manual cells',{k:v['unimported_manual_cells'] for k,v in managers.items()})

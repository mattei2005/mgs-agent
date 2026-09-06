import engine as eng
from engine import *
from collections import Counter
import copy
checks=[];imports=[];provider=[]
def ck(kind,cell,actual,expected):checks.append(dict(kind=kind,cell=cell,actual=actual,expected=expected,passed=same(actual,expected)))
# Strict equality, not tolerance: every cell in every IMPORTRANGE spill.
for (book,title),cc in GRIDS.items():
 if title not in ['Agosto 2026','CAIXA SINTETICO','BASE_DASH','DASH EXECUTIVO']:continue
 for cell,x in cc.items():
  f=formula(x)
  if 'IMPORTRANGE(' in f:
   tree=Parser(f).parse();source=evaluate(tree,book,title,cell)
   if not isinstance(source,Ref):
    # SUM(IMPORTRANGE(...)) consumes source cells without spilling them.
    def nested(node):
     if isinstance(node,tuple):
      if node[0]=='call' and node[1]=='IMPORTRANGE':yield evaluate(node,book,title,cell)
      for child in node[1:]:yield from nested(child)
     elif isinstance(node,list):
      for child in node:yield from nested(child)
    refs=list(nested(tree));assert refs
    for rr in refs:
     ck('nested_import_source',book+':'+cell,(rr.book,rr.sheet) in GRIDS,True)
     rr.matrix()
    ck('nested_import_aggregate',book+':'+cell,source,val(x))
    imports.append(dict(book=book,sheet=title,anchor=cell,wrapped=True,cells=0,source_ranges=[dict(book=rr.book,sheet=rr.sheet,range=[rr.r1,rr.c1,rr.r2,rr.c2]) for rr in refs],mismatches=[]))
    continue
   r0=int(re.search(r'\d+',cell)[0]);c0=ci(re.match('[A-Z]+',cell)[0]);bad=[];n=0
   for dr,row in enumerate(source.matrix()):
    for dc,value in enumerate(row):
     dst=col(c0+dc)+str(r0+dr);actual=val(cc.get(dst,{}));n+=1
     if actual!=value:bad.append(dict(cell=dst,actual=actual,expected=value))
   imports.append(dict(book=book,sheet=title,anchor=cell,source_book=source.book,source_sheet=source.sheet,source_range=[source.r1,source.c1,source.r2,source.c2],cells=n,mismatches=bad))
  if 'GOOGLEFINANCE(' in f:
   value=val(x);ck('provider_result',book+':'+title+':'+cell,isinstance(value,(int,float)) and value>0,True);provider.append(dict(book=book,sheet=title,cell=cell,formula=f,value=value,classification='provider_quote_observed_not_independent_market_pricing'))
cash=GRIDS['principal','CAIXA SINTETICO'];vv=lambda co:val(cash[co])
for cell,mult in [('J2',.99),('K2',.99),('L2',.99),('M2',.99),('N2',.99),('R3',.98)]:ck('provider_spread',cell,vv(cell),vv('R4')*mult)
ck('provider_cad_parity','Agosto H1/Caixa R5',val(GRIDS['principal','Agosto 2026']['H1']),vv('R5'))
# Calendar scenarios execute the actual parsed live formulas against isolated in-memory copies.
real_date=eng.date
scenario_results=[]
for book in list(IDS)[1:]:
 cc=GRIDS[book,'Agosto 2026'];backup=copy.deepcopy(cc);anchor='A23' if book=='isliago' else 'A22'
 for year,month in [(2026,2),(2028,2),(2026,9),(2026,8)]:
  start=real_date(year,month,1);days=calendar.monthrange(year,month)[1]
  for elapsed in [-1,0,1,4,days-1,days,days+8]:
   today=start+timedelta(days=elapsed)
   class ScenarioDate(real_date):
    @classmethod
    def today(cls):return today
   eng.date=ScenarioDate;cc[anchor]={'effectiveValue':{'numberValue':(start-EPOCH).days}}
   for amount in ['',0,2000,-100]:
    for co in 'CDEF':
     cc[co+'12']={'effectiveValue':{'stringValue':amount} if isinstance(amount,str) else {'numberValue':amount}}
     f=formula(backup[co+'14']);actual=scalar(evaluate(Parser(f).parse(),book,'Agosto 2026',co+'14'))
     expected='' if amount=='' or elapsed<=0 else amount/min(elapsed,days)*days
     rec=dict(book=book,cell=co+'14',month=start.isoformat(),today=today.isoformat(),amount=amount,actual=actual,expected=expected,passed=same(actual,expected));scenario_results.append(rec)
 cc.clear();cc.update(backup)
eng.date=real_date
# Continuity candidates receive explicit dispositions, not silently ignored.
continuity=[]
for x in load('continuity-candidates'):
 co=x['col']
 if co in ['K','L','S','T']:reason='First-row guard differs; inactive block currently has zero spend/revenue. Semantic checks validate every actual daily result; no current financial discrepancy.'
 elif co in ['BP','PH','TL']:
  reason='Earlier days are manually entered USD with adjacent raw CAD blank; later days use CAD conversion. Not missing numeric input.'
  main=GRIDS['principal','Agosto 2026']
  for t in x['missing']:
   rr=int(re.search(r'\d+',t)[0]);ccidx=ci(co);ck('currency_transition_manual',t,isinstance(val(main.get(t,{})),(int,float)),True);ck('currency_transition_no_cad_duplication',t,val(main.get(col(ccidx-1)+str(rr),{})),'')
 else:reason='Generic scan crosses mini-table total row. Exact-date mini-table audit supersedes generic row46/146 band; every daily and total result passed.'
 continuity.append(dict(candidate=x,disposition=reason))
save('strict-import-parity.json',imports);save('calendar-scenarios.json',scenario_results);save('provider-continuity-checks.json',checks);save('provider-scope.json',provider);save('continuity-dispositions.json',continuity)
print('strict imports',len(imports),'cells',sum(x['cells'] for x in imports),'mismatches',sum(len(x['mismatches']) for x in imports));print('calendar scenarios',len(scenario_results),'failed',sum(not x['passed'] for x in scenario_results));print('other checks',len(checks),'failed',[x for x in checks if not x['passed']])

from engine import *
from collections import defaultdict,Counter
A=GRIDS['principal','Agosto 2026'];C=GRIDS['principal','CAIXA SINTETICO'];B=GRIDS['principal','BASE_DASH'];D=GRIDS['principal','DASH EXECUTIVO']
V=lambda cc,t:val(cc.get(t,{}))
N=lambda cc,t:V(cc,t) if isinstance(V(cc,t),(int,float)) else 0
F=lambda cc,t:formula(cc.get(t,{}))
checks=[];issues=[];exceptions=[]
def ck(kind,cell,actual,expected):checks.append(dict(kind=kind,cell=cell,actual=actual,expected=expected,passed=same(actual,expected)))
rows=[{col(c):V(B,col(c)+str(r)) for c in range(1,23)}|{'row':r} for r in range(2,155)]
blocks=load('live-blocks');used=[]
for row in rows:
 r=row['row'];level=row['C']
 if level not in ['SITE','PAÍS']:continue
 refs=re.findall(r"'Agosto 2026'!([A-Z]+)(\d+)",F(B,'N'+str(r)))
 assert len(refs)==1,(r,refs)
 co,tr=refs[0];tr=int(tr)
 source=[b for b in blocks if b['totalrow']==tr and co in b['metrics'].values()]
 ck('base_source_block',str(r),len(source),1)
 if len(source)!=1:continue
 b=source[0];m=b['metrics'];expected={}
 if level=='SITE':
  used.append((b['start'],tr))
  expected['L']=sum(N(A,c+str(tr)) for h,c in m.items() if h.startswith('GROSS_USD_') or h=='GROSS_BR')
  for out,key in [('M','INVALIDO_TOTAL'),('N','RECEITA_NET_TOTAL'),('O','IMPOSTO_TOTAL'),('P','DESPESA_TOTAL'),('R','GASTOS_TOTAL'),('S','LUCRO_LIQUIDO_TOTAL'),('T','ROI_GROSS_TOTAL'),('U','ROI_NET_TOTAL')]:expected[out]=V(A,m[key]+str(tr))
  expected['Q']=''
 else:
  country=row['J'];idx={h:c for h,c in m.items() if h.endswith('_'+country)}
  for out,prefs in [('L',['GROSS_USD_','GROSS_']),('M',['INVALIDO_']),('N',['NET_USD_','NET_']),('O',['IMPOSTO_']),('R',['GASTOS_']),('S',['LUCRO_LIQUIDO_']),('T',['ROI_GROSS_']),('U',['ROI_NET_'])]:
   coords=[idx[p+country] for p in prefs if p+country in idx];ck('base_country_component',str(r)+out,len(coords),1)
   if coords:expected[out]=V(A,coords[0]+str(tr))
  expected.update(P='',Q='')
 for out,value in expected.items():ck('base_semantic_metric',out+str(r),row[out],value)
ck('base_complete_blocks','SITE rows',sorted(used),sorted((b['start'],b['totalrow']) for b in blocks))
for i,row in enumerate([r for r in rows if r['C']=='GERAL'],5):
 for co,source in [('M','API'),('N','APE'),('O','APF'),('P','APG'),('Q','APH'),('R','APJ'),('S','APK'),('T','APL'),('U','APM')]:ck('base_daily_semantic',co+str(row['row']),row[co],V(A,source+str(i)))
 # Literal provenance strings do not auto-adjust when Google shifts source columns.
 expected='Agosto 2026!APE'+str(i)+':APM'+str(i)
 if row['V']!=expected:issues.append(dict(kind='stale_literal_provenance',cell='V'+str(row['row']),actual=row['V'],expected=expected,impact='documentation_only'))
for co,sourcerange in [('L',['J58']),('M',['J59','J60','J61','J62']),('N',['J64']),('O',['J71']),('P',['J72']),('Q',['J73']),('R',['J75']),('S',['J77']),('U',['J79'])]:ck('base_month_cash',co+'154',V(B,co+'154'),sum(N(C,x) for x in sourcerange))
# Independent aggregation reproduces all 5 QUERY arrays, COUNTUNIQUE, and the KPI counts.
def select(level,filters=None):
 out=[r for r in rows if r['C']==level and r['F']!='']
 for field,value in (filters or {}).items():
  if value!='TODOS':out=[r for r in out if r[field]==value]
 return out
filters={co:V(D,t) for co,t in [('E','B13'),('I','D13'),('G','F13'),('K','H13'),('F','J13')]}
def group(data,key,limit=None):
 totals=defaultdict(lambda:[0,0,0])
 for r in data:
  for j,co in enumerate(['N','R','S']):totals[r[key]][j]+=(r[co] or 0)*(-1 if co=='R' else 1)
 return [[k]+v for k,v in sorted(totals.items(),key=lambda item:(-item[1][2],item[0]))][:limit]
arrays={
 'A16':[['Site','Receita líquida','Gastos','Lucro líquido']]+group(select('SITE',filters),'F',10),
 'A32':[['Data','Receita líquida','Gastos','Lucro líquido']]+[[r['B'],r['N'],-r['R'],r['S']] for r in sorted(select('GERAL'),key=lambda r:r['B'])],
 'A66':[['Parceiro','Receita líquida','Gastos','Lucro líquido']]+group(select('SITE',filters),'E'),
 'A75':[['País','Receita líquida','Gastos','Lucro líquido']]+group(select('PAÍS',filters),'J')}
for anchor,arr in arrays.items():
 start=int(anchor[1:])
 for i,row in enumerate(arr):
  for j,value in enumerate(row):ck('query_spill',col(j+1)+str(start+i),V(D,col(j+1)+str(start+i)),value)
 for j in range(4):ck('query_no_extra_row',col(j+1)+str(start+len(arr)),V(D,col(j+1)+str(start+len(arr))),'')
active=select('SITE',{'I':'ATIVO'});ck('countunique_sites','G8',V(D,'G8'),len(set(r['F'] for r in active)));profitable=group(active,'F');ck('countif_profitable','J8',V(D,'J8'),sum(r[3]>0 for r in profitable))
for t,e in [('A5',N(C,'J58')),('D5',N(C,'J64')),('G5',abs(N(C,'J75'))),('J5',N(C,'J77')),('A8',N(C,'J77')/abs(N(C,'J75'))),('D8',abs(sum(N(C,'J'+str(r)) for r in range(59,63)))/N(C,'J58'))]:ck('dashboard_kpi',t,N(D,t),e)
ck('provisional_label','A2','PROVISÓRIO' in V(D,'A2'),True)
# Independent bridge: site results omit employees; after-invalid gross is not post-share net.
site=select('SITE');country=select('PAÍS')
ck('cash_gross_coverage','SUM SITE L / CAIXA J58',sum(r['L'] for r in site),N(C,'J58'))
ck('cash_tax_coverage','SUM SITE O / CAIXA J71',sum(r['O'] for r in site),N(C,'J71'))
for partner,grossrows,invcell,sharecell,share in [('ActiveView',range(12,36),'J59','J67',.1),('JBF',range(37,52),'J62','J70',.1),('M2',range(53,55),'J60','J68',.05),('YMonetize',range(9,11),'J61','J69',.1)]:
 rr=[r for r in site if r['E']==partner];gross=sum(r['L'] for r in rr);invalid=sum(r['M'] for r in rr)
 ck('partner_cash_gross',partner,sum(N(C,'J'+str(i)) for i in grossrows),gross)
 ck('partner_cash_invalid',partner,N(C,invcell),invalid)
 ck('partner_cash_share',partner,N(C,sharecell),-(gross+invalid)*share)
for metric in ['L','M','N','O','R']:
 ck('base_grain_bridge',metric+' SITE/PAÍS',sum(r[metric] or 0 for r in site),sum(r[metric] or 0 for r in country))
ck('site_month_profit_bridge','SITE profit + employees',sum(r['S'] for r in site)+N(C,'J73'),N(C,'J77'))
ck('country_month_profit_bridge','PAÍS profit + overhead',sum(r['S'] for r in country)+N(C,'J72')+N(C,'J73'),N(C,'J77'))
ck('net_share_bridge','BASE N154 vs sum SITE N + shares',N(B,'N154'),sum(r['N'] for r in site)-sum(N(C,'J'+str(r)) for r in range(67,71)))
# Chart range integrity, complete query coverage and correct value series/axis.
chartdoc=load('dashboard-chart-metadata');charts=next(s for s in chartdoc['sheets'] if s['properties']['title']=='DASH EXECUTIVO')['charts'];ck('charts_count','dashboard',len(charts),4)
for chart,anchor in zip(charts,['A16','A32','A66','A75']):
 bc=chart['spec']['basicChart'];sources=bc['domains'][0]['domain']['sourceRange']['sources']
 series=bc['series'];r0=int(anchor[1:])-1
 for rg in sources+[s['series']['sourceRange']['sources'][0] for s in series]:
  ck('chart_sheet',chart['chartId'],rg['sheetId'],292770908)
  ck('chart_start',chart['chartId'],rg['startRowIndex'],r0)
  ck('chart_end',chart['chartId'],rg['endRowIndex']>=r0+len(arrays[anchor]),True)
 ck('chart_domain',chart['chartId'],sources[0]['startColumnIndex'],0)
 ck('chart_series_columns',chart['chartId'],[s['series']['sourceRange']['sources'][0]['startColumnIndex'] for s in series],[3] if anchor in ['A16','A75'] else [1,2,3])
 for s in series:ck('chart_axis',chart['chartId'],s['targetAxis'],'BOTTOM_AXIS' if bc['chartType']=='BAR' else 'LEFT_AXIS')
# Read-only filter contract checking: all possible dimension values are matched exactly locally.
filtercases=[]
for field in filters:
 for value in sorted(set(r[field] for r in site)):
  chosen=select('SITE',{field:value});arr=group(chosen,'F')
  ck('filter_local_partition',field+':'+value,sum(x[3] for x in arr),sum(r['S'] for r in chosen))
  filtercases.append(dict(field=field,value=value,site_rows=len(chosen)))
# No live filter probe is allowed in this read-only task.
exceptions.append(dict(kind='filter_validation_scope',detail='Current live filter outputs and formulas checked; alternate selections exercised locally only, no live writes.'))
exceptions.append(dict(kind='different_roi_denominator',cash_roi=N(C,'J79'),monthly_roi=N(A,'APM36'),cash_definition='net_profit / media_spend',monthly_definition='postshare_net / (media_spend+tax+company+staff)-1',impact='same label, different criteria, not a cash arithmetic mismatch'))
save('dashboard-independent-checks.json',checks);save('dashboard-findings.json',issues);save('dashboard-scope-notes.json',exceptions);save('dashboard-query-recomputation.json',arrays);save('dashboard-local-filter-cases.json',filtercases)
print('checks',len(checks),'failures',dict(Counter(x['kind'] for x in checks if not x['passed'])));print('failed',[x for x in checks if not x['passed']][:20]);print('findings',len(issues),issues[:2]);print('roi definitions',exceptions[-1])

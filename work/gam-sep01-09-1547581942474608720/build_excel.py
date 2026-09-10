import json,re,hashlib
from pathlib import Path
from decimal import Decimal as D
from collections import defaultdict,Counter
from datetime import datetime
from openpyxl import load_workbook,Workbook
from openpyxl.styles import Font,PatternFill,Alignment,Border,Side
from openpyxl.comments import Comment
P=Path(__file__).parent
SOURCE=Path('/root/.hermes/profiles/zeus/cache/documents/doc_10d5b4efd431_report_1_de_set_ate_9_de_set.xlsx')
OUT=P/'Receita-01-09set-2026-Zeus.xlsx'
# Daily product only: suffixes are preserved. Financial rules from approved 1547441127697678418.
owners={'autocreditadx':'g002-d','cephyric':'g002-d','cliquet':'g002-d','cliquetfinanzas':'g002-d','eggbev':'g006-d','eggbevfinanzas':'g006-d','financeadx':'g006-d','gamingadx':'g002-d','helixenit':'g005-d','infinitynexx':'g004-d','lyzmo':'g006-d','lyzmofinanzas':'g006-d','marevelx':'g001-d','newsoun':'g005-d','newsounde':'g005-d','newsounfinanzas':'g005-d','openzed':'g003-d','openzedfinanzas':'g003-d','portalrelevante':'g001-d','topfeed':'g004-d','topfeedfinanzas':'g004-d','vizioid':'g002-s','wavesbee':'g003-d','xyvlov':'g003-d','yolokfx':'g002-s','zuoutfinanzas':'g002-d','zytiva':'g003-d','zytivafinanzas':'g003-d','creditoparaveiculo':'g002-s','fincgriffin':'g002-d','gamezonead':'g002-s'}
langs={'us':'en','gb':'en','ca':'en','za':'en','mx':'es','es':'es','de':'de','fr':'fr','br':'br','ar':'es'}
sb=[r for q in json.loads((P/'sb-daily.json').read_text()) for r in q['data']]
assert json.loads((P/'sb-verification.json').read_text())['combined_exact_match']
bridge=defaultdict(set);sb_issues=[]
for r in sb:
 code=re.fullmatch(r'(b\d+fb\d+c\d+)g\d+',r['UTM_ADGROUP'] or '')
 manager=re.search(r'-(g00[1-6])$',r['ACCOUNT_NAME'] or '',re.I)
 nc=re.findall(r'\((b\d+fb\d+c\d+)\)',r['CAMPAIGN_NAME'] or '')
 if not code or not manager or (nc and code.group(1) not in nc):
  sb_issues.append({k:r.get(k) for k in ('DATE','CUSTOMER_ID','CAMPAIGN_ID','UTM_ADGROUP','CAMPAIGN_NAME','ACCOUNT_NAME','REVENUE')});continue
 bridge[(r['DATE'],code.group(1))].add((r['CUSTOMER_ID'],r['ACCOUNT_NAME'],manager.group(1).lower()+'-s'))
assert all(len(v)==1 for v in bridge.values())
agg=defaultdict(lambda:D(0));raw_daily=defaultdict(lambda:D(0));counts=Counter();lineage=[];yolo=defaultdict(lambda:D(0));pending=[];zero_rows=0
w=load_workbook(SOURCE,read_only=True,data_only=True)
assert w.sheetnames==['usd','cad']
for s in w:
 currency=s.title.upper();assert s.max_column==10
 for rownum,r in enumerate(s.iter_rows(min_row=2,values_only=True),2):
  if all(v is None for v in r):continue
  assert isinstance(r[0],datetime) and isinstance(r[9],(int,float)),(s.title,rownum)
  day=r[0].date().isoformat();assert '2026-09-01'<=day<='2026-09-09'
  placement,medium,campaign=r[1:4];match=re.fullmatch(r'pl_digital-trust_([a-z]+)_([a-z]{2})',placement);assert match,placement
  brand,country=match.groups();assert country in langs
  amount=D(str(r[9]));assert amount.is_finite();zero_rows+=amount==0
  counts[currency]+=1;raw_daily[(currency,day)]+=amount
  site=brand+'.com';vertical=f'{country}-cc-{langs[country]}';rules=[];proof=[]
  if brand.endswith('finanzas'):
   base=brand.removesuffix('finanzas');site='finanzas.'+base+('.fun' if base=='topfeed' else '.com');vertical=f'{country}-cc-es'
  if brand=='topfeed':site='finance.topfeed.fun'
  if brand=='topfeedfinanzas':vertical='us-cc-es';rules.append('Topfeedfinanzas somente US aprovado')
  if brand=='newsounde':site='de.newsoun.com';vertical='de-cc-de'
  if brand=='autocreditadx':vertical='us-car-en';rules.append('Autocreditadx CAR aprovado')
  if brand=='gamingadx':vertical='us-game-en'
  if brand=='gamezonead':vertical='br-game-br'
  if brand=='creditoparaveiculo':vertical='br-car-br'
  if brand=='fincgriffin':vertical='us-car-en'
  if brand in ('vizioid','yolokfx'):vertical='us-shein-en'
  manager=medium
  if not re.fullmatch(r'g00[1-6]-[ds]',medium or ''):
   manager=owners.get(brand,'A confirmar');rules.append('Fallback site; medium original='+str(medium))
  if brand in ('gamezonead','newsounde'):
   manager=owners[brand];rules.append('Override aprovado '+brand)
  if brand=='yolokfx' and not re.fullmatch(r'g00[1-6]-[ds]',medium or ''):
   proof=sorted(bridge.get((day,campaign),set()))
   if proof:manager=proof[0][2];method='Campanha + conta SB (mesmo dia)'
   else:manager='g002-s';method='Residual G002 autorizado, sem identidade segura'
   rules.append(method);yolo[(day,method)]+=amount
  if brand=='mavroa':vertical='A confirmar'
  if brand=='yolokfx' and re.fullmatch(r'g00[1-6]-[ds]',medium or ''):
   rules.append('Medium GAM explícito');yolo[(day,'Medium GAM explícito')]+=amount
  if brand not in owners:
   pending.append({'currency':currency,'date':day,'row':rownum,'placement':placement,'site':site,'vertical':vertical,'manager':manager,'amount':str(amount),'reason':'Sem default financeiro confirmado; valor preservado, não atribuído por suposição.'})
  key=(currency,day,site,vertical,manager);agg[key]+=amount
  lineage.append({'sheet':s.title,'row':rownum,'key':key,'placement':placement,'medium':medium,'campaign':campaign,'amount':str(amount),'rules':rules,'account_evidence':proof})
assert len(lineage)==sum(counts.values())==27091
assert len({(r['sheet'],r['row']) for r in lineage})==len(lineage)
for key,value in raw_daily.items():assert sum((v for k,v in agg.items() if k[:2]==key),D(0))==value
assert set(raw_daily)=={(c,f'2026-09-{d:02}') for c in ['USD','CAD'] for d in range(1,10)}
# Preserve full Excel numeric precision; two decimals for display, no per-row rounding.
book=Workbook();book.remove(book.active)
navy='17365D';blue='DCE6F1';amber='FFF2CC';green='E2F0D9'
for currency in ['USD','CAD']:
 s=book.create_sheet('Receita '+currency);s.append(['Data','Site','Vertical','Gestor','Receita'])
 for k,value in sorted(agg.items()):
  if k[0]!=currency:continue
  s.append([*k[1:],float(value)])
  if k[4]=='A confirmar':
   for cell in s[s.max_row]:cell.fill=PatternFill('solid',fgColor=amber)
   s.cell(s.max_row,4).comment=Comment('Não há regra financeira confirmada nas fontes consultadas. Receita integral preservada; não presumir gestor.','Zeus')
  if k[2]=='yolokfx.com':
   rows=[r for r in lineage if tuple(r['key'])==k]
   fallback=sum((D(r['amount']) for r in rows if 'Residual G002 autorizado, sem identidade segura' in r['rules']),D(0))
   explicit=sum((D(r['amount']) for r in rows if 'Medium GAM explícito' in r['rules']),D(0));identified=value-fallback-explicit
   s.cell(s.max_row,5).comment=Comment(f'Receita GAM original. Medium explícito GAM: CAD {explicit}. Campanha/conta SB: CAD {identified}. Residual pela decisão de Rodolfo ao g002-s: CAD {fallback}. Ver Validacao.','Zeus')
 total=sum((v for k,v in agg.items() if k[0]==currency),D(0));s.append(['TOTAL',None,None,None,float(total)])
 s.freeze_panes='A2';s.auto_filter.ref=f'A1:E{s.max_row-1}'
 for col,width in {'A':14,'B':31,'C':18,'D':17,'E':20}.items():s.column_dimensions[col].width=width
 for row in s.iter_rows(min_row=2):row[4].number_format='#,##0.00'
 for cell in s[s.max_row]:cell.fill=PatternFill('solid',fgColor=blue);cell.font=Font(bold=True,color=navy)
v=book.create_sheet('Validacao');v.append(['Controle / data','Moeda / site','Original / identificado','Consolidado / residual','Diferença / observação'])
v.append(['Período','01 a 09/09/2026',None,None,'Datas validadas nas linhas do anexo.'])
v.append(['Fonte',SOURCE.name,None,None,'Moedas informadas pelas abas usd/cad; sem Properties no anexo.'])
v.append(['Critério','Receita bruta GAM',None,None,'Sem conversão cambial, share, gastos ou imposto.'])
v.append(['Precisão','Valores não arredondados',None,None,'2 casas apenas na exibição; totais usam precisão original do Excel.'])
v.append(['Linhas originais','USD',counts['USD'],None,None]);v.append(['Linhas originais','CAD',counts['CAD'],None,None])
for currency in ['USD','CAD']:
 for day in [f'2026-09-{d:02}' for d in range(1,10)]:
  original=raw_daily[(currency,day)];output=sum((val for k,val in agg.items() if k[:2]==(currency,day)),D(0));v.append([day,currency,float(original),float(output),float(output-original)])
 total=sum((val for k,val in raw_daily.items() if k[0]==currency),D(0));v.append(['TOTAL '+currency,currency,float(total),float(total),0])
v.append([]);v.append(['YOLOKFX','CAD: origem identificada x residual',None,None,'Residual G002 aprovado por Rodolfo; não é prova de origem.'])
for day in [f'2026-09-{d:02}' for d in range(1,10)]:
 explicit=yolo[(day,'Medium GAM explícito')];identified=yolo[(day,'Campanha + conta SB (mesmo dia)')]+explicit;fallback=yolo[(day,'Residual G002 autorizado, sem identidade segura')]
 v.append([day,'yolokfx.com',float(identified),float(fallback),f'Identificado inclui medium GAM explícito CAD {explicit} e ponte SB.'])
v.append(['Atenção SB','09/09: campanha 11 x 12',None,None,'Código do adgroup diverge do nome da campanha em uma linha; evidência conflitante excluída da ponte.'])
v.append([]);v.append(['CLASSIFICAÇÕES','Regras aprovadas',None,None,'Mensagem Rodolfo 1547441127697678418'])
for rule in ['Eggbev: GB separado de US.','Openzedfinanzas: ES separado de US; Topfeedfinanzas somente US.','Gamezonead: tudo g002-s / br-game-br.','Autocreditadx: us-car-en.','Defaults sem medium: Infinitynexx G004, Openzed G003, Creditoparaveiculo g002-s.','Sufixos -s/-d preservados neste produto diário.','Demais placements: país original preservado; finanzas usa idioma es.']:
 v.append([rule])
v.append([]);v.append(['PENDÊNCIAS','Receita preservada',None,None,'Não lançar em gestor sem confirmação financeira.'])
for r in pending:v.append([r['date'],r['site'],float(D(r['amount'])),r['manager'],r['reason']])
v.append(['Escalatepower','us-cc-en',None,None,'Há histórico operacional de catálogo g003-d, não confirmação de default financeiro.'])
v.append(['Mavroa','Placement _us',None,None,'Vertical/gestor sem regra financeira confirmada.'])
v.freeze_panes='A2'
for col,width in {'A':44,'B':47,'C':26,'D':27,'E':92}.items():v.column_dimensions[col].width=width
for row in v.iter_rows(min_row=2):
 for cell in row:
  if isinstance(cell.value,(float,int)):cell.number_format='#,##0.000000'
  cell.alignment=Alignment(vertical='top',wrap_text=True)
 v.row_dimensions[row[0].row].height=32
for s in book:
 for cell in s[1]:cell.font=Font(color='FFFFFF',bold=True);cell.fill=PatternFill('solid',fgColor=navy)
 s.row_dimensions[1].height=24;s.sheet_view.showGridLines=False
book.save(OUT)
# Read-back numeric/group/date/shape validation independent of serialized writer.
rw=load_workbook(OUT,read_only=True,data_only=True);check={};read_totals={}
for currency in ['USD','CAD']:
 s=rw['Receita '+currency]
 for row in s.iter_rows(min_row=2,values_only=True):
  if row[0]=='TOTAL':read_totals[currency]=D(str(row[4]));continue
  key=(currency,*row[:4]);assert key not in check;check[key]=D(str(row[4]))
assert set(check)==set(agg)
max_error=max(abs(check[k]-agg[k]) for k in agg);assert max_error<D('0.000000001')
for currency,day in raw_daily:
 got=sum((val for k,val in check.items() if k[:2]==(currency,day)),D(0));assert abs(got-raw_daily[(currency,day)])<D('0.00000001')
for currency in ['USD','CAD']:
 total=sum((val for k,val in raw_daily.items() if k[0]==currency),D(0));assert abs(read_totals[currency]-total)<D('0.00000001')
summary={'status':'RECONCILED_WITH_CLASSIFICATION_CAVEATS','input':str(SOURCE),'output':str(OUT),'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'output_sha256':hashlib.sha256(OUT.read_bytes()).hexdigest(),'input_rows':dict(counts),'total_input_rows':len(lineage),'output_groups':len(agg),'groups_by_currency':dict(Counter(k[0] for k in agg)),'raw_totals':{c:str(sum((val for k,val in raw_daily.items() if k[0]==c),D(0))) for c in ['USD','CAD']},'max_excel_roundtrip_group_error':str(max_error),'exact_decimal_daily_reconciliation':True,'all_18_currency_days_verified':True,'readback_groups_and_totals_verified':True,'pending':pending,'pending_total_cad':str(sum((D(r['amount']) for r in pending),D(0))),'sb_issues':sb_issues,'yolo_identified':str(sum((val for k,val in yolo.items() if k[1].startswith('Campanha')),D(0))),'yolo_fallback':str(sum((val for k,val in yolo.items() if k[1].startswith('Residual')),D(0))),'financial_sheet_writes':False}
summary['yolo_explicit_medium']=str(sum((val for k,val in yolo.items() if k[1]=='Medium GAM explícito'),D(0)))
summary['yolo_total_original']=str(sum(yolo.values(),D(0)))
summary['yolo_identified_total']=str(D(summary['yolo_explicit_medium'])+D(summary['yolo_identified']))
assert D(summary['yolo_total_original'])==sum((val for k,val in agg.items() if k[2]=='yolokfx.com'),D(0))
(P/'lineage.json').write_text(json.dumps(lineage,ensure_ascii=False,indent=2))
(P/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
(P/'aggregate.json').write_text(json.dumps([{'key':k,'revenue':str(val)} for k,val in sorted(agg.items())],ensure_ascii=False,indent=2))
print(json.dumps(summary,ensure_ascii=False,indent=2))

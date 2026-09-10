import json,re
from pathlib import Path
from collections import defaultdict,Counter
from decimal import Decimal,ROUND_HALF_EVEN
P=Path(__file__).parent
raw=json.loads((P/'raw.json').read_text()); claude=json.loads((P/'claude.json').read_text())
# Reverse-engineered from source and result. Reproduces Claude, NOT an approval of business rules.
owners={'autocreditadx':'g002-d','cephyric':'g002-d','cliquetfinanzas':'g002-d','eggbev':'g006-d','eggbevfinanzas':'g006-d','financeadx':'g006-d','gamingadx':'g002-d','helixenit':'g005-d','infinitynexx':'g004-d','lyzmo':'g006-d','lyzmofinanzas':'g006-d','marevelx':'g001-d','newsoun':'g005-d','newsounde':'g005-d','newsounfinanzas':'g005-d','openzed':'g003-d','openzedfinanzas':'g003-d','portalrelevante':'g001-d','topfeed':'g004-d','topfeedfinanzas':'g004-d','vizioid':'g002-s','wavesbee':'g003-d','xyvlov':'g003-d','yolokfx':'g002-s','zuoutfinanzas':'g002-d','zytiva':'g003-d','zytivafinanzas':'g003-d','creditoparaveiculo':'g002-s','fincgriffin':'g002-d','gamezonead':'g002-s'}
langs={'us':'en','gb':'en','ca':'en','za':'en','mx':'es','es':'es','de':'de','fr':'fr','br':'br'}
def mapping(r):
 brand,country=r['placement'].removeprefix('pl_digital-trust_').rsplit('_',1); flags=[]
 site=brand+'.com'; vertical=f'{country}-cc-{langs[country]}'
 if brand.endswith('finanzas'):
  base=brand.removesuffix('finanzas'); site='finanzas.'+base+('.fun' if base=='topfeed' else '.com'); vertical='us-cc-es'
  if country!='us':flags.append('finanzas_country_to_us')
 if brand=='topfeed':site='finance.topfeed.fun'
 if brand=='newsounde':site='de.newsoun.com';vertical='de-cc-de'
 if brand=='eggbev':
  vertical='us-cc-en'
  if country!='us':flags.append('eggbev_country_to_us')
 if brand in ('gamingadx','autocreditadx'):vertical='us-game-en'
 if brand=='gamezonead':
  vertical='br-game-br'
  if country!='br':flags.append('gamezone_country_to_br')
 if brand=='creditoparaveiculo':vertical='br-car-br'
 if brand=='fincgriffin':vertical='us-car-en'
 if brand in ('vizioid','yolokfx'):vertical='us-shein-en'
 manager=r['medium']
 if not re.fullmatch(r'g00[1-6]-[ds]',manager or ''):
  flags.append('medium_fallback:'+str(manager));manager=owners[brand]
 if brand in ('gamezonead','newsounde') and manager!=owners[brand]:
  flags.append('explicit_manager_override:'+manager);manager=owners[brand]
 return (r['currency'],r['date'],site,vertical,manager),flags
agg=defaultdict(lambda:Decimal(0)); detail=defaultdict(list); rules=defaultdict(lambda:{'rows':0,'amount':Decimal(0)})
for r in raw:
 k,flags=mapping(r);v=Decimal(r['revenue']);agg[k]+=v;detail[k].append({'file':r['file'],'row':r['row'],'placement':r['placement'],'medium':r['medium'],'revenue':str(v),'rules':flags})
 for flag in flags:
  q=rules[(r['currency'],flag)];q['rows']+=1;q['amount']+=v
output={};comparison=[]
for r in claude:
 if r['date']=='TOTAL':continue
 k=tuple(r[x] for x in ['currency','date','site','vertical','manager']);assert k not in output;output[k]=Decimal(r['revenue'])
for k in sorted(set(agg)|set(output)):
 diff=output.get(k,Decimal(0))-agg.get(k,Decimal(0));comparison.append({'key':k,'raw_sum':str(agg.get(k,0)),'claude':str(output.get(k,0)),'difference':str(diff),'rounded_match':agg.get(k,Decimal(0)).quantize(Decimal('0.000001'))==output.get(k),'source_rows':len(detail[k])})
summaries=[]
for currency in ('CAD','USD'):
 for day in ('2026-09-07','2026-09-08','TOTAL'):
  a=sum((Decimal(r['revenue']) for r in raw if r['currency']==currency and (day=='TOTAL' or r['date']==day)),Decimal(0)); b=sum((v for k,v in output.items() if k[0]==currency and (day=='TOTAL' or k[1]==day)),Decimal(0));summaries.append({'currency':currency,'date':day,'raw':str(a),'claude_rows':str(b),'difference':str(b-a),'cent_match':a.quantize(Decimal('.01'))==b.quantize(Decimal('.01'))})
summary={'files':5,'original_files':4,'raw_rows':len(raw),'claude_rows':len(output),'reconstructed_groups':len(agg),'all_102_rounded_match':all(x['rounded_match'] for x in comparison),'max_abs_difference':str(max(abs(Decimal(x['difference'])) for x in comparison)),'summaries':summaries,'claude_total_labels':[r for r in claude if r['date']=='TOTAL'],'rules':[{'currency':k[0],'rule':k[1],**v} for k,v in sorted(rules.items())],'yolo':[r for r in comparison if r['key'][2]=='yolokfx.com']}
for name,obj in [('reconciliation.json',summary),('comparison-102.json',comparison),('lineage-102.json',[{'key':k,'sources':v} for k,v in sorted(detail.items())])]: (P/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2,default=str))
assert len(raw)==5943 and len(output)==102 and len(agg)==102
assert all(x['rounded_match'] for x in comparison), [x for x in comparison if not x['rounded_match']]
print(json.dumps(summary,ensure_ascii=False,default=str,indent=2))

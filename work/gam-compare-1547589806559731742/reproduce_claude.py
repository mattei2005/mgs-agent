import json,re
from pathlib import Path
from decimal import Decimal as D
from collections import defaultdict,Counter
from openpyxl import load_workbook
P=Path(__file__).parent;OLD=Path('/root/mgs-agent/work/gam-sep01-09-1547581942474608720')
a=json.loads((OLD/'lineage.json').read_text());s=json.loads((P/'summary.json').read_text());claude={};pred=defaultdict(lambda:D(0));changes=defaultdict(lambda:{'rows':0,'revenue':D(0)})
for sh in load_workbook(s['manifest']['claude']['path'],read_only=True,data_only=True):
 for r in sh.iter_rows(min_row=2,values_only=True):
  if r[0]=='TOTAL':continue
  claude[(sh.title.removeprefix('Receita '),*r[:4])]=D(str(r[4]))
for r in a:
 k=list(r['key']);site=k[2];rule=None
 if site in ('escalatepower.com','mavroa.com'):k[4]='g002-d'
 if site=='eggbev.com' and k[3]=='gb-cc-en':k[3]='us-cc-en';rule='Eggbev GB fundido US'
 if site=='finanzas.openzed.com' and k[3]=='es-cc-es':k[3]='us-cc-es';rule='Openzedfinanzas ES fundido US'
 if site=='finanzas.zytiva.com' and k[3]=='es-cc-es':k[3]='us-cc-es';rule='Zytivafinanzas ES fundido US'
 if site=='cliquet.com' and k[3]=='gb-cc-en':k[3]='us-cc-en';rule='Cliquet GB fundido US'
 if site=='autocreditadx.com':k[3]='us-game-en';rule='Autocreditadx CAR para GAME'
 if site in ('cliquet.com','finance.topfeed.fun','openzed.com') and k[3]=='br-cc-br':k[3]='br-car-br';rule='Placement BR para CAR '+site
 if site=='escalatepower.com':k[3]='us';rule='Escalatepower vertical incompleta'
 if site=='mavroa.com':k[3]='us-cc-en';rule='Mavroa vertical CC'
 if site=='yolokfx.com' and not re.fullmatch(r'g00[1-6]-[ds]',r['medium'] or ''):
  if k[4]!='g002-s':rule='Yolo demais gestores para G002'
  k[4]='g002-s'
 amount=D(r['amount']);pred[tuple(k)]+=amount
 if rule:changes[rule]['rows']+=1;changes[rule]['revenue']+=amount
comparison=[]
for k in sorted(set(pred)|set(claude)):
 val=pred.get(k,D(0));actual=claude.get(k,D(0));match=k in pred and k in claude and val.quantize(D('.000001'))==actual
 comparison.append({'key':k,'reconstructed_from_original':str(val),'claude':str(actual),'six_decimal_match':match})
failed=[r for r in comparison if not r['six_decimal_match']]
# Explicit traffic strategy check: identify every original valid suffix pair and whether both files preserve it outside named overrides.
strategies=defaultdict(lambda:D(0))
for r in a:
 if re.fullmatch(r'g00[1-6]-[sd]',r['medium'] or ''):strategies[(r['key'][0],r['medium'][-1])]+=D(r['amount'])
result={'reconstructed_groups':len(pred),'claude_groups':len(claude),'matched_groups':len(comparison)-len(failed),'all_groups_reproduced_at_six_decimals':not failed,'failed':failed,'explanations':{k:{'source_rows':v['rows'],'original_revenue':str(v['revenue'])} for k,v in changes.items()},'original_strategy_totals':[{'currency':k[0],'strategy':k[1],'revenue':str(v)} for k,v in sorted(strategies.items())]}
(P/'claude-reproduction.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));(P/'claude-reproduction-groups.json').write_text(json.dumps(comparison,ensure_ascii=False,indent=2))
print(json.dumps(result,ensure_ascii=False,indent=2));assert not failed

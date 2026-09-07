"""Read-only complete August source capture and spend/site reconciliation."""
import sys,json,pathlib,re,collections,datetime
from decimal import Decimal as D
from urllib.parse import urlencode
ROOT=pathlib.Path(__file__).resolve().parents[1];STATE=ROOT/'private/networks-1546579646227943506'
sys.path.insert(0,'/root/mgs-agent/work/finance-final-reaudit-1545877165982355557');import audit
source=json.loads((ROOT/'private/source.json').read_text());model=json.loads((ROOT/'private/ui-model.json').read_text());before=json.loads((STATE/'production-before.json').read_text());reg=next(r for r in before if r['id']=='master-ad-accounts');aug=next(r for r in before if r['id']=='workspace-2026-08');live={};formula_changes=[];captures=[]
for name,meta in source['sources'].items():
 drive=audit.get('https://www.googleapis.com/drive/v3/files/'+meta['id']+'?'+urlencode({'supportsAllDrives':'true','fields':'id,trashed,modifiedTime'}));assert not drive['trashed']
 qs=[('ranges',"'Agosto 2026'")]+([('ranges',"'BASE_DASH'")] if name=='principal' else [])+[('includeGridData','true'),('fields','spreadsheetId,sheets(properties,data(startRow,startColumn,rowData(values(userEnteredValue,effectiveValue,formattedValue))))')]
 data=audit.get('https://sheets.googleapis.com/v4/spreadsheets/'+meta['id']+'?'+urlencode(qs));(STATE/('live-'+name+'.json')).write_text(json.dumps(data,ensure_ascii=False));captured=datetime.datetime.now(datetime.timezone.utc).isoformat();captures.append({'book':name,'captured_at':captured,'id':meta['id']})
 for sheet in data['sheets']:
  for cell,x in audit.cells(sheet).items():live[name+'|'+sheet['properties']['title']+'|'+cell]=x
 for c in source['cells']:
  if c['book']==name and c['sheet']=='Agosto 2026' and c.get('formula','')!=audit.formula(live.get(c['id'],{})):formula_changes.append(c['id'])
lookup={c['id']:c for c in source['cells']};bykey={key:a for a in reg['additions'] for key in a['source_links']};slots=[];mismatches=[];totals=collections.defaultdict(lambda:D(0));unique_keys=set()
num=lambda v:D(str(v)) if isinstance(v,(int,float)) or isinstance(v,str) and re.fullmatch(r'-?\d+(\.\d+)?',v) else D(0)
for slot in reg['result']['slots']:
 amounts=[];missing=[]
 for key in slot['keys']:
  current=audit.val(live.get(key,{}));dash=aug['overrides'].get(key,lookup.get(key,{}).get('input',''));amount=num(current)
  if amount!=num(dash):mismatches.append({'key':key,'sheet':str(amount),'dash':str(num(dash)),'name':slot['sheet_name']})
  if amount:amounts.append({'key':key,'amount':str(amount)});missing.extend([] if key in bykey or slot['state']=='non_meta' else [key])
  if key not in unique_keys:totals[slot['currency']]+=abs(amount);unique_keys.add(key)
 slots.append({**slot,'has_spend':bool(amounts),'spend':str(sum((abs(D(a['amount'])) for a in amounts),D(0))),'missing_identity_with_spend':bool(missing),'movements':amounts})
# Rebuild site header coverage from the full monthly grid, not just former source bounds.
principal=next(s for s in json.loads((STATE/'live-principal.json').read_text())['sheets'] if s['properties']['title']=='Agosto 2026');grid=audit.cells(principal);headers={}
for cell,x in grid.items():
 row,co=re.fullmatch(r'([A-Z]+)(\d+)',cell).group(2),re.fullmatch(r'([A-Z]+)(\d+)',cell).group(1)
 value=audit.val(x)
 if row in ('2','102') and isinstance(value,str) and value.startswith('DESPESA_TOTAL'):headers[(co,int(row))]=value
expected={(b['metrics']['DESPESA_TOTAL'],b['header']) for b in source['blocks']};new_blocks=sorted(set(headers)-expected);missing_blocks=sorted(expected-set(headers))
network=json.loads((ROOT/'network-rules.json').read_text());sites=[]
for s in aug['result']['segments']:
 n=network['explicit_sites'].get(s['site'],network['legacy_aliases'].get(s['partner'],s['partner']));sites.append({'site':s['site'],'network':n,'source_partner':s['partner'],'source':s['source'],'explicit':s['site'] in network['explicit_sites']})
sites=list({s['site']:s for s in sites}.values());assert len(sites)==len({s['site'] for s in aug['result']['segments']})
unknown=[s for s in sites if s['network'] not in network['networks']];spent=[s for s in slots if s['has_spend']];gaps=[s for s in spent if s['missing_identity_with_spend']]
result={'captures':captures,'google_writes':0,'slots':slots,'sites':sites,'source_formula_changes':formula_changes,'mismatches':mismatches,'new_blocks':new_blocks,'missing_blocks':missing_blocks,'unknown_networks':unknown,'summary':{'pass_values':not mismatches and not formula_changes,'pass_site_coverage':not new_blocks and not missing_blocks and not unknown,'slots':len(slots),'slots_with_spend':len(spent),'accounts_with_spend':len({bykey[m['key']]['id'] for s in spent for m in s['movements'] if m['key'] in bykey}),'identity_gaps_with_spend':len(gaps),'value_mismatches':len(mismatches),'sites':len(sites),'blocks':len(expected),'source_formula_changes':len(formula_changes),'spend_by_currency':{k:str(v) for k,v in totals.items()}}}
(STATE/'source-reconciliation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result['summary'],ensure_ascii=False));print(json.dumps({'gaps':[{'name':s['sheet_name'],'sites':s['sites'],'spend':s['spend'],'currency':s['currency']} for s in gaps],'new_blocks':new_blocks,'missing_blocks':missing_blocks,'first_mismatches':mismatches[:8],'network_counts':dict(collections.Counter(s['network'] for s in sites))},ensure_ascii=False))

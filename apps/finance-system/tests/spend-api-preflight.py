"""Read-only July canary. No financial imports, scheduler or Meta mutations."""
import pathlib,sys,importlib.util,json,decimal,datetime
from urllib.parse import urlencode
R=pathlib.Path(__file__).resolve().parents[1];S=R/'private/navigation-1546682010066489394'
spec=importlib.util.spec_from_file_location('lookup',R/'meta-lookup-worker.py');lookup=importlib.util.module_from_spec(spec);spec.loader.exec_module(lookup)
accounts,pages=lookup.inventory();(S/'meta-inventory.json').write_text(json.dumps(list(accounts.values()),indent=2))
token,_=lookup.meta.get_token_from_1password('APP NOVO 02/09 Token Meta API - Contas de Anuncio Meta - Roosevelt Mattei')
canaries=[]
for name,expected in [('Cliquet-BR-CAR-BR-01','719.50'),('TopfeedFinanzas-US-CC-ES-01','12319.31')]:
 match=[x for x in accounts.values() if x['name']==name];assert len(match)==1,'Canary name not unique'
 a=match[0];params={'fields':'account_id,account_name,account_currency,date_start,date_stop,spend','level':'account','time_range':json.dumps({'since':'2026-07-01','until':'2026-07-31'}),'time_increment':1,'limit':100};out=[];seen=set()
 while True:
  status,d,_=lookup.meta.graph_get('act_'+a['account_id']+'/insights',token,params)
  if status!=200:raise RuntimeError('Insights HTTP '+str(status)+' code '+str(d.get('error',{}).get('code')))
  out.extend(d.get('data',[]))
  if not d.get('paging',{}).get('next'):break
  cursor=d.get('paging',{}).get('cursors',{}).get('after');assert cursor and cursor not in seen;seen.add(cursor);params['after']=cursor
 assert len({(x['account_id'],x['date_start']) for x in out})==len(out)
 total=sum((decimal.Decimal(x['spend']) for x in out),decimal.Decimal(0))
 canaries.append({'account':a,'rows':out,'sum':str(total),'screenshot_total':expected,'screenshot_match':total==decimal.Decimal(expected)})
(S/'meta-july-canaries.json').write_text(json.dumps(canaries,indent=2))
sys.path.insert(0,'/root/mgs-agent/work/finance-final-reaudit-1545877165982355557');import audit
sheet=audit.get('https://sheets.googleapis.com/v4/spreadsheets/'+audit.IDS['principal']+'?'+urlencode({'ranges':"'Julho 2026'",'includeGridData':'true','fields':'spreadsheetId,sheets(properties,data(startRow,startColumn,rowData(values(userEnteredValue,effectiveValue,formattedValue,note))))'}))
p=S/'july-sheet.json';p.write_text(json.dumps(sheet));p.chmod(0o600)
cells=audit.cells(sheet['sheets'][0]);hits={k:v for k,v in cells.items() if any(t in str(v).lower() for t in ['mattei 1','gamingadx-us','topfeedfinanzas','cliquet-br-car'])};(S/'july-sheet-labels.json').write_text(json.dumps(hits,indent=2))
out={'pass':True,'read_only':True,'bm_accounts':len(accounts),'bm_pages':pages,'canaries':[{'name':x['account']['name'],'currency':x['account']['currency'],'timezone':x['account']['timezone'],'days_with_rows':len(x['rows']),'sum':x['sum'],'screenshot_match':x['screenshot_match']} for x in canaries],'sheet_label_cells':list(hits),'meta_writes':0,'sheet_writes':0,'dashboard_writes':0,'full_portfolio_parity':False}
(S/'spend-preflight.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,ensure_ascii=False))

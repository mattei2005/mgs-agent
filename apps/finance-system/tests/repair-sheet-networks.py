"""Authorized August/September invalid-network repair. SA only; explicit cell plan.
Do not rerun apply after successful readback. No month duplication or revenue/spend edits.
"""
import pathlib,sys,json,re,hashlib,time,collections
from urllib.parse import urlencode
ROOT=pathlib.Path(__file__).resolve().parents[1];STATE=ROOT/'private/networks-1546579646227943506';sys.path.insert(0,'/root/mgs-agent/work/finance-final-reaudit-1545877165982355557');import audit
sys.path.insert(0,str(ROOT))
from calc import address,ci
ID=audit.IDS['principal'];TITLES=['Agosto 2026','Setembro 2026'];AUTH='1546595495726547094';phase=sys.argv[1];source=json.loads((ROOT/'private/source.json').read_text());rules=json.loads((ROOT/'network-rules.json').read_text())
def capture():
 q=[('ranges',"'"+t+"'") for t in TITLES]+[('includeGridData','true'),('fields','spreadsheetId,sheets(properties,merges,data(startRow,startColumn,rowData(values(userEnteredValue,effectiveValue,formattedValue,note,userEnteredFormat.numberFormat))))')]
 return audit.get('https://sheets.googleapis.com/v4/spreadsheets/'+ID+'?'+urlencode(q))
def save(name,data):(STATE/name).write_text(json.dumps(data,ensure_ascii=False,indent=2))
def post(suffix,payload):
 if audit.TOKEN is None:audit.get('https://www.googleapis.com/drive/v3/files/'+ID+'?fields=id')
 status,data=audit.auth.api_json('POST','https://sheets.googleapis.com/v4/spreadsheets/'+ID+suffix,audit.TOKEN,payload,quota_project='mgs-core-prod')
 if status!=200:raise RuntimeError('Sheets write HTTP '+str(status)+' '+str(data.get('error',{}).get('status')))
 return data
if phase=='plan':
 drive=audit.get('https://www.googleapis.com/drive/v3/files/'+ID+'?'+urlencode({'supportsAllDrives':'true','fields':'id,trashed,capabilities(canEdit)'}));assert drive['capabilities']['canEdit'] and not drive['trashed']
 snap=capture()
 if (STATE/'sheets-repair-before.json').exists():
  prior=json.loads((STATE/'sheets-repair-before.json').read_text());values=lambda d:{(s['properties']['title'],a):x.get('userEnteredValue',{}) for s in d['sheets'] for a,x in audit.cells(s).items() if x.get('userEnteredValue')}
  assert values(prior)==values(snap),'Source changed since backup';snap=prior
 else:save('sheets-repair-before.json',snap)
 changes=[];metadata=[];coverage=[]
 # Source block descriptors are accepted only after exact live header/name validation.
 base=json.loads((STATE/'production-readback.json').read_text());sites=next(p for p in base['periods'] if p['id']=='workspace-2026-08')['sites'];byid={s['id']:s for s in sites}
 for sheet in snap['sheets']:
  title=sheet['properties']['title'];grid=audit.cells(sheet);assert title in TITLES;assert not grid.get('M1',{}).get('userEnteredValue');assert not any(re.search(r'(?<![A-Z])\$?M\$?1(?!\d)',audit.formula(x)) for x in grid.values())
  ranges=[]
  for b in source['blocks']:
   if b['header']!=2:continue
   live_name=str(audit.val(grid.get(b['start']+'3',{}))).split('\n')[0].strip();expected=b['name'].split('\n')[0].strip();assert live_name==expected,(title,expected,live_name)
   for metric,co in b['metrics'].items():
    actual=audit.val(grid.get(co+'2',{}));currency_only=(title,co,metric,actual)==('Setembro 2026','GP','GROSS_GBP_US','GROSS_CAD_US')
    assert actual==metric or currency_only,(title,co,metric,actual)
    if currency_only:assert audit.formula(grid['GQ5'])=='=IF(GP5="","",GP5/$H$1)','Unresolved WavesBee currency lineage'
   slug=re.sub(r'[^a-z0-9]+','-',expected.lower()).strip('-');site=byid['site-'+slug+'-principal'];network=site['network'];ref={'SB Rede1':'L1','SB Rede2':'M1','ActiveView':'J1','Ymonetize':'K1','M2':'EN82'}[network];ranges.append((ci(b['start']),ci(b['end']),site['name'],network,ref));coverage.append({'title':title,'site':site['name'],'network':network,'invalid_source':ref})
  for cell,x in grid.items():
   old=audit.formula(x)
   if not old:continue
   row,co=address(cell)
   if row<2:continue
   for lo,hi,name,network,ref in ranges:
    if lo<=co<=hi:
     fixed='$'+re.sub(r'\d','',ref)+'$'+re.sub(r'\D','',ref);new=re.sub(r'\$(?:J\$1|K\$1|L\$1|EN\$82)(?!\d)',lambda m:fixed,old)
     if new!=old:changes.append({'title':title,'cell':cell,'old':old,'new':new,'site':name,'network':network})
     break
  changes.append({'title':title,'cell':'M1','old':None,'new':float(rules['rede2_initial']),'site':'monthly_parameter','network':'SB Rede2'})
  for co,label in [('J1','Inválidos ActiveView'),('K1','Inválidos Ymonetize'),('L1','Inválidos SB Rede1'),('M1','Inválidos SB Rede2')]:
   row,col=address(co);metadata.append({'updateCells':{'range':{'sheetId':sheet['properties']['sheetId'],'startRowIndex':row-1,'endRowIndex':row,'startColumnIndex':col-1,'endColumnIndex':col},'rows':[{'values':[{'note':label+' · '+title+' · parâmetro exclusivo deste mês. Rodolfo '+AUTH,**({'userEnteredFormat':{'numberFormat':{'type':'PERCENT','pattern':'0.00000%'}}} if co=='M1' else {})}]}],'fields':'note,userEnteredFormat.numberFormat' if co=='M1' else 'note'}})
  assert sum(c['title']==title and c['cell']!='M1' for c in changes)>0
 assert len(coverage)==82 and len({(x['title'],x['cell']) for x in changes})==len(changes)
 save('sheets-repair-plan.json',{'authorization':AUTH,'spreadsheet_id':ID,'changes':changes,'metadata':metadata,'coverage':coverage,'before_sha256':hashlib.sha256((STATE/'sheets-repair-before.json').read_bytes()).hexdigest()});print(json.dumps({'planned_changes':dict(collections.Counter(c['title'] for c in changes)),'site_coverage':dict(collections.Counter(c['title'] for c in coverage)),'rede2_parameter':'M1','source_rate1':'L1','metadata_requests':len(metadata)}))
elif phase=='apply':
 plan=json.loads((STATE/'sheets-repair-plan.json').read_text());before=json.loads((STATE/'sheets-repair-before.json').read_text());now=capture();bymonth={s['properties']['title']:audit.cells(s) for s in before['sheets']}
 for sheet in now['sheets']:
  title=sheet['properties']['title'];grid=audit.cells(sheet)
  for c in plan['changes']:
   if c['title']==title:assert grid.get(c['cell'],{}).get('userEnteredValue')==bymonth[title].get(c['cell'],{}).get('userEnteredValue'),('Concurrent edit',title,c['cell'])
 def write(rows):return post('/values:batchUpdate',{'valueInputOption':'USER_ENTERED','includeValuesInResponse':True,'responseValueRenderOption':'FORMULA','data':[{'range':"'"+c['title']+"'!"+c['cell'],'values':[[c['new']]]} for c in rows]})
 canary=[c for c in plan['changes'] if c['cell']=='M1']+[next(c for c in plan['changes'] if c['title']==t and c['cell']!='M1') for t in TITLES];res=write(canary)
 assert res['totalUpdatedCells']==len(canary)
 for c,r in zip(canary,res['responses']):assert r['updatedData']['values'][0][0]==c['new']
 # Independent GET confirms canary, not only update response.
 q=[('ranges',"'"+c['title']+"'!"+c['cell']) for c in canary]+[('valueRenderOption','FORMULA')];rb=audit.get('https://sheets.googleapis.com/v4/spreadsheets/'+ID+'/values:batchGet?'+urlencode(q));assert [r['values'][0][0] for r in rb['valueRanges']]==[c['new'] for c in canary];save('sheets-canary.json',{'pass':True,'cells':canary})
 rest=[c for c in plan['changes'] if c not in canary];written=len(canary)
 for offset in range(0,len(rest),500):
  rows=rest[offset:offset+500];r=write(rows);assert r['totalUpdatedCells']==len(rows);written+=len(rows);save('sheets-write-progress.json',{'written':written,'expected':len(plan['changes'])});time.sleep(1)
 post(':batchUpdate',{'requests':plan['metadata']});assert written==len(plan['changes']);print(json.dumps({'written_cells':written,'canary_readback':True,'metadata_requests':len(plan['metadata'])}))
elif phase=='verify':
 plan=json.loads((STATE/'sheets-repair-plan.json').read_text());before=json.loads((STATE/'sheets-repair-before.json').read_text());after=capture();save('sheets-repair-after.json',after);bymonth={s['properties']['title']:audit.cells(s) for s in before['sheets']};allowed={(c['title'],c['cell']):c for c in plan['changes']};bad=[];unexpected=[];errors=[];seen=0;summary=[]
 for sheet in after['sheets']:
  title=sheet['properties']['title'];grid=audit.cells(sheet);old=bymonth[title]
  for cell in set(grid)|set(old):
   uv=grid.get(cell,{}).get('userEnteredValue',{});prior=old.get(cell,{}).get('userEnteredValue',{})
   if uv!=prior and (title,cell) not in allowed:unexpected.append((title,cell))
   if (title,cell) in allowed:
    seen+=1;c=allowed[title,cell];actual=uv.get('formulaValue',uv.get('numberValue')); 
    if actual!=c['new']:bad.append((title,cell))
   if 'errorValue' in grid.get(cell,{}).get('effectiveValue',{}):errors.append((title,cell,grid[cell]['effectiveValue']['errorValue']))
  summary.append({'title':title,'modified':sum(c['title']==title for c in plan['changes']),'sites':sum(c['title']==title for c in plan['coverage']),'rede2_formatted':grid['M1'].get('formattedValue'),'formula_errors':sum(e[0]==title for e in errors)})
 out={'pass':not bad and not unexpected and not errors and seen==len(plan['changes']),'tabs':summary,'expected_cells':len(plan['changes']),'readback_cells':seen,'bad':bad,'unexpected':unexpected,'errors':errors,'revenue_spend_inputs_changed':0 if not unexpected else None,'authorization':AUTH};save('sheets-repair-readback.json',out);print(json.dumps(out,ensure_ascii=False));assert out['pass']
else:raise ValueError('Unknown phase')

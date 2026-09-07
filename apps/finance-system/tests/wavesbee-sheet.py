"""Bounded WavesBee CAD Sheet correction and independent readback; no financial input writes."""
import importlib.util,pathlib,json,sys,re,hashlib
from urllib.parse import urlencode
spec=importlib.util.spec_from_file_location('inspection',pathlib.Path(__file__).with_name('wavesbee-inspect.py'));i=importlib.util.module_from_spec(spec);spec.loader.exec_module(i)
audit=i.audit;STATE=i.STATE;ID=i.ID;TITLES=['Agosto 2026','Setembro 2026'];phase=sys.argv[1]
def maps(snap):return {s['properties']['title']:audit.cells(s) for s in snap['sheets']}
def entered(g):return {a:x['userEnteredValue'] for a,x in g.items() if x.get('userEnteredValue')}
def capture():return i.capture(ID,["'"+t+"'" for t in TITLES])
def post(payload):
 status,data=audit.auth.api_json('POST','https://sheets.googleapis.com/v4/spreadsheets/'+ID+'/values:batchUpdate',audit.TOKEN,payload,quota_project='mgs-core-prod');assert status==200,('Write HTTP',status);return data
def write(rows):
 r=post({'valueInputOption':'USER_ENTERED','includeValuesInResponse':False,'data':[{'range':"'"+x['title']+"'!"+x['cell'],'values':[[x['new']]]} for x in rows]});assert r['totalUpdatedCells']==len(rows)
def verify_rows(rows):
 q=[('ranges',"'"+x['title']+"'!"+x['cell']) for x in rows]+[('valueRenderOption','FORMULA')]
 rb=audit.get('https://sheets.googleapis.com/v4/spreadsheets/'+ID+'/values:batchGet?'+urlencode(q));assert [v.get('values',[['']])[0][0] for v in rb['valueRanges']]==[x['new'] for x in rows]
if phase=='plan':
 before=json.loads((STATE/'sheets-before.json').read_text());grids=maps(before);changes=[]
 for title,g in grids.items():
  assert audit.val(g['GP3']).split('\n')[0]=='WavesBee'
  desired={'GP2':'GROSS_CAD_US','GP3':'WavesBee\nCAD\nUS',**{'GQ'+str(r):f'=IF(GP{r}="","",GP{r}/$H$1)' for r in range(5,36)}}
  for a,new in desired.items():
   old=audit.formula(g[a]) or audit.val(g[a]);assert old in [new,new.replace('CAD','GBP')] or old==new.replace('/$H$1','*$I$1'),(title,a,old)
   if old!=new:changes.append({'title':title,'cell':a,'old':old,'new':new})
 assert all(x['title']=='Agosto 2026' for x in changes) and len(changes)==33
 i.save('sheet-plan.json',{'authorization':'1546607083468623912','changes':changes,'before_sha256':hashlib.sha256((STATE/'sheets-before.json').read_bytes()).hexdigest()});print(json.dumps({'planned':len(changes),'august':33,'september_already_correct':True}))
elif phase=='apply':
 before=maps(json.loads((STATE/'sheets-before.json').read_text()));now=maps(capture());plan=json.loads((STATE/'sheet-plan.json').read_text());rows=plan['changes']
 for t in TITLES:assert entered(before[t])==entered(now[t]),'Concurrent source change; replan required'
 canary=[next(x for x in rows if x['cell']=='GQ5')];write(canary);verify_rows(canary);write([x for x in rows if x not in canary]);verify_rows(rows);i.save('sheet-written.json',{'cells':len(rows),'canary_readback':True});print('33 authorized cells written/readback; September preserved')
elif phase=='verify':
 before=maps(json.loads((STATE/'sheets-before.json').read_text()));snap=capture();i.save('sheets-after.json',snap);after=maps(snap);rows=json.loads((STATE/'sheet-plan.json').read_text())['changes'];allowed={(r['title'],r['cell']) for r in rows};diff=[];errors=[]
 for t,g in after.items():
  for a in set(g)|set(before[t]):
   if g.get(a,{}).get('userEnteredValue',{})!=before[t].get(a,{}).get('userEnteredValue',{}):diff.append((t,a))
   err=g.get(a,{}).get('effectiveValue',{}).get('errorValue')
   if err:errors.append((t,a,err))
  assert audit.val(g['GP2'])=='GROSS_CAD_US' and audit.val(g['GP3'])=='WavesBee\nCAD\nUS'
  for r in range(5,36):assert audit.formula(g['GQ'+str(r)])==f'=IF(GP{r}="","",GP{r}/$H$1)'
 assert set(diff)==allowed and not errors
 out={'pass':True,'changed_cells':len(diff),'out_of_scope':0,'formula_errors':0,'months':['2026-08','2026-09'],'currency':'CAD','revenue_spend_written':0,'september_written':0};i.save('sheet-readback.json',out);print(json.dumps(out))
else:raise ValueError('Unknown phase')

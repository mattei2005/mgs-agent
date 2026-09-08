"""Two closed-month ROI display guards, zero-denominator only; values and inputs immutable."""
import sys,pathlib,json,urllib.parse,datetime,re,hashlib
sys.path.insert(0,'/root/mgs-agent/scripts');from mgs_google_workspace_auth import load_env,load_service_account,service_account_access_token,api_json
load_env();sa=load_service_account();assert sa['client_email']=='mgsagent@mgs-core-prod.iam.gserviceaccount.com';token=service_account_access_token();sid='16umGPmLukDGQtCEBh2inYLnE9xcqWbHa3gJCM9HG9ak';R=pathlib.Path('/root/mgs-agent/apps/finance-system');D=R/'private/manager-access-1546858367635685396';API='https://sheets.googleapis.com/v4/spreadsheets/'+sid

def call(method,url,body=None):
 status,d=api_json(method,url,token,body);assert status==200,(status,str(d)[:500]);return d

def save(n,d):
 p=D/n;p.write_text(json.dumps(d,ensure_ascii=False,indent=2));p.chmod(0o600);return hashlib.sha256(p.read_bytes()).hexdigest()

def col(n):
 out=''
 while n:n,k=divmod(n-1,26);out=chr(65+k)+out
 return out

def capture():
 names=['Janeiro 2026','Fevereiro 2026'];q=urllib.parse.urlencode([('ranges',"'"+n+"'") for n in names]+[('includeGridData','true'),('fields','spreadsheetId,sheets(properties,data(startRow,startColumn,rowData(values(userEnteredValue,effectiveValue,formattedValue,effectiveFormat.numberFormat))))')]);data=call('GET',API+'?'+q);out={}
 for sh in data['sheets']:
  cells={}
  for g in sh.get('data',[]):
   for ri,row in enumerate(g.get('rowData',[]),g.get('startRow',0)+1):
    for ci,c in enumerate(row.get('values',[]),g.get('startColumn',0)+1):
     if c.get('userEnteredValue') or c.get('effectiveValue') or c.get('formattedValue'):cells[col(ci)+str(ri)]=c
  out[sh['properties']['title']]=cells
 return out
phase=sys.argv[1]
if phase=='prepare':
 assert not (D/'roi-before.json').exists()
 meta=call('GET','https://www.googleapis.com/drive/v3/files/'+sid+'?supportsAllDrives=true&fields=id,capabilities');assert meta['capabilities']['canEdit'];before=capture();targets=[]
 for name,cells in before.items():
  for a,c in cells.items():
   err=c.get('effectiveValue',{}).get('errorValue')
   if not err:continue
   assert err['type']=='DIVIDE_BY_ZERO';m=re.fullmatch(r'(FN|FO|FP|FQ|FR)(10[2-9]|1[12][0-9]|13[0-2])',a);assert m
   assert cells[m[1]+'100']['formattedValue'].strip().startswith('ROI');formula=c['userEnteredValue']['formulaValue'];f=re.fullmatch(r'=SUM\(([A-Z]+\d+)\)/([A-Z]+\d+)-1',formula);assert f and cells[f[2]]['effectiveValue'].get('numberValue',0)==0
   targets.append({'sheet':name,'a1':a,'before':formula,'after':'=IF('+f[2]+'=0,"",'+formula[1:]+')'})
 counts={n:sum(t['sheet']==n for t in targets) for n in before};assert counts=={'Janeiro 2026':132,'Fevereiro 2026':148},counts
 h=save('roi-before.json',before);save('roi-plan.json',{'authority':'Rodolfo direct mid-turn1546858367635685396: zero division repairs only, no value change','before_sha256':h,'counts':counts,'targets':targets});print(json.dumps({'pass':True,'counts':counts,'before_sha256':h}))
elif phase in ['canary','apply']:
 plan=json.loads((D/'roi-plan.json').read_text());before=json.loads((D/'roi-before.json').read_text());now=capture();targets=plan['targets'];selected=targets[:1] if phase=='canary' else targets;allowed={(x['sheet'],x['a1']):x for x in targets}
 # Never replay a committed write or touch an unexpected source change.
 for n,cells in before.items():
  for a,c in cells.items():
   old=c.get('userEnteredValue',{});new=now[n].get(a,{}).get('userEnteredValue',{});t=allowed.get((n,a));assert new==old or t and new.get('formulaValue')==t['after'],(n,a,'concurrent input change')
 data=[]
 for t in selected:
  current=now[t['sheet']][t['a1']]['userEnteredValue']['formulaValue']
  if current==t['after']:continue
  assert current==t['before'];data.append({'range':"'"+t['sheet']+"'!"+t['a1'],'values':[[t['after']]]})
 if data:
  response=call('POST',API+'/values:batchUpdate',{'valueInputOption':'USER_ENTERED','data':data});assert response['totalUpdatedCells']==len(data);save('roi-'+phase+'-write.json',{'updatedCells':len(data),'ranges':[x['range'] for x in data]})
 after=capture();changes=[];numeric=0
 for n,cells in before.items():
  for a in set(cells)|set(after[n]):
   old=cells.get(a,{});new=after[n].get(a,{});t=allowed.get((n,a));applied=t and new.get('userEnteredValue',{}).get('formulaValue')==t['after']
   if applied:
    assert not new.get('effectiveValue',{}).get('errorValue') and new.get('formattedValue','')=='';changes.append({'sheet':n,'a1':a})
   else:assert old.get('userEnteredValue')==new.get('userEnteredValue') and old.get('effectiveValue')==new.get('effectiveValue') and old.get('formattedValue')==new.get('formattedValue'),(n,a,'unapproved difference')
   if 'numberValue' in old.get('effectiveValue',{}):assert old['effectiveValue']==new.get('effectiveValue');numeric+=1
 assert len(changes)==(1 if phase=='canary' else len(targets));save('roi-'+phase+'-after.json',after);out={'pass':True,'changed_cells':len(changes),'numeric_cells_unchanged':numeric,'changes':changes,'source_input_values_unchanged':True};save('roi-'+phase+'-readback.json',out);print(json.dumps({k:v for k,v in out.items() if k!='changes'}))
else:raise ValueError('Unsupported phase')

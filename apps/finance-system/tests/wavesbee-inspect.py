"""Read-only exact scopes for Rodolfo 1546607083468623912."""
import sys,pathlib,json,re,hashlib
from urllib.parse import urlencode
ROOT=pathlib.Path(__file__).resolve().parents[1];STATE=ROOT/'private/wavesbee-1546607083468623912';STATE.mkdir(mode=0o700,exist_ok=True)
sys.path.insert(0,'/root/mgs-agent/work/finance-final-reaudit-1545877165982355557');import audit
ID=audit.IDS['principal']
def save(name,data):
 p=STATE/name
 if p.exists():raise RuntimeError('Immutable capture already exists: '+name)
 p.write_text(json.dumps(data,ensure_ascii=False));p.chmod(0o600)
 return hashlib.sha256(p.read_bytes()).hexdigest()
def capture(id,ranges):return audit.get('https://sheets.googleapis.com/v4/spreadsheets/'+id+'?'+urlencode([('ranges',r) for r in ranges]+[('includeGridData','true'),('fields','spreadsheetId,sheets(properties,merges,data(startRow,startColumn,rowData(values(userEnteredValue,effectiveValue,formattedValue,note,userEnteredFormat.numberFormat))))')]))
if __name__=='__main__':
 drive=audit.get('https://www.googleapis.com/drive/v3/files/'+ID+'?'+urlencode({'supportsAllDrives':'true','fields':'id,trashed,capabilities(canEdit)'}));assert drive['capabilities']['canEdit'] and not drive['trashed'];save('drive.json',drive)
 snap=capture(ID,["'Agosto 2026'","'Setembro 2026'"]);print('backup sha256',save('sheets-before.json',snap))
 summary={}
 for sheet in snap['sheets']:
  title=sheet['properties']['title'];g=audit.cells(sheet)
  sel=['GP2','GP3','GP5','GP35','GP36','GQ5','GQ34','GQ35','GQ36','H1','I1','G29']
  print(title,'wavesbee',json.dumps({a:g.get(a,{}) for a in sel},ensure_ascii=False))
  if title=='Setembro 2026':
   view={a:x for a,x in g.items() if re.fullmatch(r'[EFGHIJ](2[5-9]|3[0-2])',a) or re.fullmatch(r'[LMNOPQRS]1(4[0-9]|5[0-9]|6[0-2])',a)}
   print('SEPT_CONTEXT',json.dumps(view,ensure_ascii=False))
   summary['september_imports']={a:audit.formula(x) for a,x in g.items() if 'IMPORTRANGE' in audit.formula(x).upper()}
 print('IMPORTS',json.dumps(summary,ensure_ascii=False));save('inspection.json',summary)
 for name,id in audit.IDS.items():
  if name=='principal':continue
  meta=audit.get('https://sheets.googleapis.com/v4/spreadsheets/'+id+'?fields=spreadsheetId,sheets.properties');save(name+'-metadata.json',meta)
  titles=[s['properties']['title'] for s in meta['sheets']];wanted=[t for t in ['Agosto 2026','Setembro 2026'] if t in titles]
  data=capture(id,["'"+t+"'!A1:K55" for t in wanted]);save(name+'-top.json',data)
  print('MANAGER',name,'months',wanted)
  for s in data['sheets']:
   g=audit.cells(s);print(s['properties']['title'],json.dumps({a:x for a,x in g.items() if a in ['H1','D12','D14','E12','F12','E14','F14','A21','A23','A55']},ensure_ascii=False))

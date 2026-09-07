"""Read-only exact ranges named by Rodolfo 1546642267291394199; no Sheet write."""
import pathlib,sys,json,hashlib
from urllib.parse import urlencode
R=pathlib.Path(__file__).resolve().parents[1];S=R/'private/payments-1546642267291394199';S.mkdir(mode=0o700,exist_ok=True)
sys.path.insert(0,'/root/mgs-agent/work/finance-final-reaudit-1545877165982355557');import audit
id=audit.IDS['principal'];ranges=["'Agosto 2026'!F95:K140","'Setembro 2026'!F95:K140","'Agosto 2026'!APE1:APM40","'Agosto 2026'!N98:S162"]
drive=audit.get('https://www.googleapis.com/drive/v3/files/'+id+'?'+urlencode({'supportsAllDrives':'true','fields':'id,trashed,capabilities(canEdit)'}));assert not drive['trashed']
snap=audit.get('https://sheets.googleapis.com/v4/spreadsheets/'+id+'?'+urlencode([('ranges',r) for r in ranges]+[('includeGridData','true'),('fields','spreadsheetId,sheets(properties,data(startRow,startColumn,rowData(values(userEnteredValue,effectiveValue,formattedValue,note))))')]))
p=S/'sheet-preflight.json';assert not p.exists();p.write_text(json.dumps(snap,ensure_ascii=False));p.chmod(0o600);print('snapshot_sha256',hashlib.sha256(p.read_bytes()).hexdigest())
for sheet in snap['sheets']:
 g=audit.cells(sheet);print(sheet['properties']['title']);print(json.dumps({a:x for a,x in g.items() if ((a[0] in 'FGHIJK' and len(a.rstrip('0123456789'))==1) or a in [c+str(r) for c in ['APE','APF','APG','APH','API','APJ','APK','APL','APM'] for r in [2,5,36]])},ensure_ascii=False))

"""Manual authorized reimport of original monthly tabs; no Caixa query or Sheet write."""
import sys,pathlib,json,datetime,re,hashlib,copy,urllib.parse
from decimal import Decimal as Dec
ROOT=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,'/root/mgs-agent/scripts')
from mgs_google_workspace_auth import load_env,load_service_account,service_account_access_token,api_json
DEFAULT_AUTH='1546991137171181578'
ALLOWED_AUTHORITIES={DEFAULT_AUTH,'1547732274936553532'}
def col(n):
 s=''
 while n:n,k=divmod(n-1,26);s=chr(65+k)+s
 return s
def safe(s):
 if re.search(r'(?i)(?:senha|password|access.?token|secret|api.?key)\s*[:=]|\bEA[A-Za-z0-9]{30,}\b|(?=\S{8,}\b)(?=\S*[A-Za-z])(?=\S*\d)\S*[@!#$%^&*]\S*',s):return '[Conteúdo protegido — fora do histórico financeiro]'
 return s
def projected(c,row,column):
 e=c.get('effectiveValue',{});kind=next(iter(e),'blank');v=e.get(kind);f=c.get('formattedValue','')
 if kind=='stringValue':v=safe(v);f=safe(f)
 if kind=='errorValue':v={'type':v['type']};f='#'+v['type']
 return {'a1':col(column)+str(row),'row':row,'col':column,'kind':kind,'value':v,'formatted':f,'number_format':c.get('effectiveFormat',{}).get('numberFormat',{})}
def rebuild(old,cells,at,authority=DEFAULT_AUTH):
 doc={**old,'cells':cells,'rows':max(c['row'] for c in cells),'columns':max(c['col'] for c in cells),'captured_at':at,'source':'original-monthly-tab','source_authority':authority};lookup={c['a1']:c for c in cells};doc['source_sha256']=hashlib.sha256(json.dumps(cells,sort_keys=True).encode()).hexdigest();doc['unavailable']=[c['a1'] for c in cells if c['kind']=='errorValue']
 if doc['unavailable'] and not(doc['book']=='nicolas' and doc['period'] in ['2026-01','2026-02'] and set(doc['unavailable'])=={'P1','AF38'}):raise ValueError('New source cell errors '+doc['book']+'/'+doc['period'])
 if doc['book']=='principal':
  def landmark(label):
   a=[c for c in cells if 95<=c['row']<=145 and c['col']<=10 and c['formatted'].strip().lower()==label.lower()];assert len(a)==1;return a[0]
  def metric(c):assert c['kind']=='numberValue';return {'reference':c['a1'],'raw':str(c['value']),'formatted':c['formatted'],'currency':'BRL'}
  geizian=landmark('Geizian');column=geizian['col'];refs={k:col(column)+str(landmark(label)['row']) for k,label in [('previous','Saldo Mes Anterior'),('due','Recebimento'),('balance','Total em R$')]};closure={k:metric(lookup[v]) for k,v in refs.items()};entries=[]
  for c in cells:
   if c['col']!=column or not geizian['row']<c['row']<lookup[refs['balance']]['row'] or c['kind']!='numberValue' or c['a1'] in refs.values():continue
   label=' · '.join(x['formatted'].strip() for x in cells if x['row']==c['row'] and column<x['col']<=column+3 and x['kind']=='stringValue' and x['formatted'].strip());kind='payment' if re.search(r'(?i)pgto|pago|pagamento',label) else 'adjustment';date=re.search(r'(?<!\d)(\d{1,2})/(\d{1,2})(?!\d)',label) if kind=='payment' else None;effective=datetime.date(2026,int(date[2]),int(date[1])).isoformat() if date else None
   entries.append({**metric(c),'description':label or 'Sem descrição na origem','kind':kind,'date':effective,'date_status':'source_label' if effective else 'not_recorded'})
  bridge=Dec(closure['previous']['raw'])+Dec(closure['due']['raw'])+sum((Dec(e['raw']) for e in entries),Dec(0))-Dec(closure['balance']['raw']);assert abs(bridge)<Dec('.0000001');doc['closure']={'counterparty':'geizian',**closure,'entries':entries,'bridge_residual':str(bridge)};doc['payroll']={}
  for manager in ['joe','nicolas','isliago','kelly','george','jislaine']:
   labels=[c for c in cells if 135<=c['row']<=160 and 10<=c['col']<=12 and c['kind']=='stringValue' and re.match('(?i)^'+manager+r'\s*-',c['formatted'].strip())];assert labels
   doc['payroll'][manager]=[{'label':c['formatted'].replace('George','Ícaro'),'reference':c['a1'],'values':[x for x in cells if x['row']==c['row'] and c['col']<x['col']<=c['col']+4 and x['kind']=='numberValue' and '$' in x['formatted']]} for c in labels]
  doc['caixa']=[];doc.pop('previous_month_link',None)
 return doc
def capture(out,books=None,periods=None,authority=DEFAULT_AUTH):
 assert authority in ALLOWED_AUTHORITIES
 load_env();sa=load_service_account();assert sa['client_email']=='mgsagent@mgs-core-prod.iam.gserviceaccount.com' and sa['project_id']=='mgs-core-prod';token=service_account_access_token();base=ROOT/'private/history-import-1546884731436671056/payloads';originals=[json.loads(p.read_text()) for p in base.glob('*.json')];assert len(originals)==40
 if periods:
  periods=set(periods);assert periods and periods<={f'2026-{m:02}' for m in range(1,8)};originals=[d for d in originals if d['period'] in periods]
 out.mkdir(parents=True,exist_ok=True,mode=0o700);written=[];summaries=[]
 for book in sorted({d['book'] for d in originals}):
  if books and book not in books:continue
  docs=sorted([d for d in originals if d['book']==book],key=lambda d:d['period']);sid=docs[0]['source_id'];assert all(d['source_id']==sid for d in docs)
  status,drive=api_json('GET','https://www.googleapis.com/drive/v3/files/'+sid+'?supportsAllDrives=true&fields=id,trashed,mimeType',token,quota_project='mgs-core-prod');assert status==200 and drive['id']==sid and not drive['trashed']
  params=[('ranges',"'"+d['sheet'].replace("'","''")+"'") for d in docs]+[('includeGridData','true'),('fields','spreadsheetId,sheets(properties,data(startRow,startColumn,rowData(values(effectiveValue,formattedValue,effectiveFormat.numberFormat))))')]
  status,data=api_json('GET','https://sheets.googleapis.com/v4/spreadsheets/'+sid+'?'+urllib.parse.urlencode(params),token,quota_project='mgs-core-prod');assert status==200 and data['spreadsheetId']==sid and len(data['sheets'])==len(docs);at=datetime.datetime.now(datetime.timezone.utc).isoformat();result=[]
  for old in docs:
   sh=next(s for s in data['sheets'] if s['properties']['sheetId']==old['sheet_id']);assert sh['properties']['title']==old['sheet'];cells=[]
   for grid in sh.get('data',[]):
    for ri,row in enumerate(grid.get('rowData',[]),grid.get('startRow',0)+1):
     for ci,c in enumerate(row.get('values',[]),grid.get('startColumn',0)+1):
      if c.get('effectiveValue') or c.get('formattedValue'):cells.append(projected(c,ri,ci))
   doc=rebuild(old,cells,at,authority);p=out/(book+'-'+doc['period']+'.json');p.write_text(json.dumps(doc,ensure_ascii=False));p.chmod(0o600);written.append(p);result.append({'book':book,'period':doc['period'],'cells':len(cells),'numeric':sum(c['kind']=='numberValue' for c in cells),'captured_at':at})
  summaries.extend(result);print(json.dumps({'source_readback':result,'sheet_writes':0,'caixa_queries':0}),flush=True)
 return {'documents':[json.loads(p.read_text()) for p in sorted(written)],'summary':summaries,'sheet_writes':0,'caixa_queries':0}
if __name__=='__main__':capture(pathlib.Path(sys.argv[1]),sys.argv[2:] or None)

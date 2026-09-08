"""Build immutable history from actual Google effective values; never evaluate formulas."""
import pathlib,json,re,sys,hashlib,datetime,decimal,urllib.parse,calendar
R=pathlib.Path(__file__).resolve().parents[1];D=R/'private/history-import-1546884731436671056';OUT=D/'payloads';OUT.mkdir(mode=0o700,exist_ok=True)
sys.path.insert(0,'/root/mgs-agent/scripts');from mgs_google_workspace_auth import load_env,service_account_access_token,api_json
months=[f'2026-{i:02d}' for i in range(1,8)];meta=json.loads((D/'metadata.json').read_text());Dec=decimal.Decimal

def save(p,x):
 p.write_text(json.dumps(x,ensure_ascii=False,separators=(',',':')));p.chmod(0o600);return hashlib.sha256(p.read_bytes()).hexdigest()
def col(n):
 s=''
 while n:n,k=divmod(n-1,26);s=chr(65+k)+s
 return s
# Financial source notes may contain credentials. Only these non-financial strings are suppressed.
protected=[]
def safe(s,ref):
 if re.search(r'(?i)(?:senha|password|access.?token|secret|api.?key)\s*[:=]|\bEA[A-Za-z0-9]{30,}\b|(?=\S{8,}\b)(?=\S*[A-Za-z])(?=\S*\d)\S*[@!#$%^&*]\S*',s):
  protected.append(ref);return '[Conteúdo protegido — fora do histórico financeiro]'
 return s

def projection(c,ref):
 e=c.get('effectiveValue',{});kind=next(iter(e),'blank');v=e.get(kind);f=c.get('formattedValue','');fmt=c.get('effectiveFormat',{}).get('numberFormat',{})
 if kind=='stringValue':v=safe(v,ref);f=v if v.startswith('[Conteúdo protegido') else safe(f,ref)
 if kind=='errorValue':v={'type':v['type']} # no formula/source secrets via error messages
 return {'a1':c['a1'],'row':c['row'],'col':c['col'],'kind':kind,'value':v,'formatted':f,'number_format':fmt}

def num(c):
 assert c['kind']=='numberValue',c['a1'];return Dec(str(c['value']))
def metric(c):return {'reference':c['a1'],'raw':str(num(c)),'formatted':c['formatted'],'currency':'BRL'}

p=D/'caixa-grid.json'
if not p.exists():
 load_env();t=service_account_access_token();sid=next(x['id'] for x in meta if x['key']=='principal')
 q=urllib.parse.urlencode({'ranges':"'CAIXA SINTETICO'!A:I",'includeGridData':'true','fields':'spreadsheetId,sheets(properties,data(startRow,startColumn,rowData(values(userEnteredValue,effectiveValue,formattedValue,effectiveFormat.numberFormat))))'})
 status,data=api_json('GET',f'https://sheets.googleapis.com/v4/spreadsheets/{sid}?'+q,t);assert status==200;save(p,data)
caixa=[]
for sheet in json.loads(p.read_text())['sheets']:
 for grid in sheet['data']:
  for ri,row in enumerate(grid.get('rowData',[]),grid.get('startRow',0)+1):
   for ci,c in enumerate(row.get('values',[]),grid.get('startColumn',0)+1):
    if c.get('effectiveValue') or c.get('formattedValue') or c.get('userEnteredValue'):caixa.append({'a1':col(ci)+str(ri),'row':ri,'col':ci,**c})
manifest=[];principals={};numeric=0;total=0
for book in meta:
 for m in book['selected']:
  period=m['month'];key=book['key'];path=D/f'{key}-{period}-cells.json'
  if not path.exists():assert key=='george' and period in months[:2];continue
  original=json.loads(path.read_text());cells=[projection(c,f'{key}/{period}/{c["a1"]}') for c in original];lookup={c['a1']:c for c in cells};errors=[c['a1'] for c in cells if c['kind']=='errorValue']
  assert not errors or key=='nicolas' and period in months[:2] and set(errors)=={'P1','AF38'},(key,period,errors)
  doc={'period':period,'book':key,'label':'Ícaro' if key=='george' else 'Empresa' if key=='principal' else key.capitalize(),'mode':'closed-history','read_only':True,'source':'dash-frozen-snapshot','source_id':book['id'],'sheet':m['matches'][0]['title'],'sheet_id':m['matches'][0]['sheetId'],'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'captured_at':json.loads((D/f'{key}-{period}.json').read_text())['captured_at'],'cells':cells,'rows':max(c['row'] for c in cells),'columns':max(c['col'] for c in cells),'unavailable':errors}
  if key=='principal':
   def landmark(label):
    a=[c for c in cells if 95<=c['row']<=145 and c['col']<=10 and c['formatted'].strip().lower()==label.lower()];assert len(a)==1,label;return a[0]
   geizian=landmark('Geizian');column=geizian['col'];refs={k:col(column)+str(landmark(label)['row']) for k,label in [('previous','Saldo Mes Anterior'),('due','Recebimento'),('balance','Total em R$')]}
   closure={k:metric(lookup[v]) for k,v in refs.items()};entries=[]
   for c in cells:
    if c['col']!=column or not geizian['row']<c['row']<lookup[refs['balance']]['row'] or c['kind']!='numberValue' or c['a1'] in refs.values():continue
    labels=[x['formatted'].strip() for x in cells if x['row']==c['row'] and column<x['col']<=column+3 and x['kind']=='stringValue' and x['formatted'].strip()];label=' · '.join(labels);kind='payment' if re.search(r'(?i)pgto|pago|pagamento',label) else 'adjustment';date=re.search(r'(?<!\d)(\d{1,2})/(\d{1,2})(?!\d)',label) if kind=='payment' else None
    effective=None
    if date:effective=datetime.date(2026,int(date[2]),int(date[1])).isoformat()
    entries.append({**metric(c),'description':label or 'Sem descrição na origem','kind':kind,'date':effective,'date_status':'source_label' if effective else 'not_recorded'})
   bridge=Dec(closure['previous']['raw'])+Dec(closure['due']['raw'])+sum((Dec(e['raw']) for e in entries),Dec(0))-Dec(closure['balance']['raw']);assert abs(bridge)<Dec('0.0000001'),(period,str(bridge))
   doc['closure']={'counterparty':'geizian',**closure,'entries':entries,'bridge_residual':str(bridge)}
   doc['payroll']={}
   for manager in ['joe','nicolas','isliago','kelly','george','jislaine']:
    labels=[c for c in cells if 135<=c['row']<=160 and 10<=c['col']<=12 and c['kind']=='stringValue' and re.match('(?i)^'+manager+r'\s*-',c['formatted'].strip())]
    assert labels,(period,manager)
    doc['payroll'][manager]=[{'label':c['formatted'].replace('George','Ícaro'),'reference':c['a1'],'values':[x for x in cells if x['row']==c['row'] and c['col']<x['col']<=c['col']+4 and x['kind']=='numberValue' and re.search(r'\$',x['formatted'])]} for c in labels]
   monthcol=int(period[-2:])+2
   doc['caixa']=[projection(c,f'caixa/{period}/{c["a1"]}') for c in caixa if c['col'] in [1,2,monthcol]]
   principals[period]=doc
  digest=save(OUT/f'{key}-{period}.json',doc);numbers=sum(c['kind']=='numberValue' for c in cells);numeric+=numbers;total+=len(cells)
  manifest.append({'period':period,'book':key,'file':f'{key}-{period}.json','sha256':digest,'cells':len(cells),'numeric':numbers,'errors':errors})
assert len(manifest)==40 and len(principals)==7
links=[]
for previous,current in zip(months,months[1:]):
 a=principals[previous]['closure']['balance'];b=principals[current]['closure']['previous'];delta=Dec(b['raw'])-Dec(a['raw']);links.append({'from':previous,'to':current,'matches':abs(delta)<Dec('0.0000001'),'previous_close':a,'next_open':b,'difference_raw':str(delta),'disposition':'Preservar valores fechados distintos; não criar ajuste nem recalcular'})
assert principals['2026-07']['payroll']['jislaine'][0]['values'][-1]['value']==-1500
assert round(Dec(principals['2026-07']['closure']['balance']['raw']),2)==Dec('0.71')
assert not any(c['a1']=='S19' and c['value'] not in [None,''] for c in principals['2026-04']['cells'])
for link in links:
 doc=principals[link['to']];doc['previous_month_link']=link
 item=next(x for x in manifest if x['book']=='principal' and x['period']==link['to']);item['sha256']=save(OUT/item['file'],doc)
result={'pass':True,'authority':'1546884731436671056','tabs':40,'months':7,'cells':total,'numeric':numeric,'manifest':manifest,'links':links,'protected_text_cells':sorted(set(protected)),'caixa_source_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'july_closure':principals['2026-07']['closure']['balance'],'source_sheets_written':False}
save(D/'built.json',result);print(json.dumps({k:v for k,v in result.items() if k not in ['manifest','links','protected_text_cells']}|{'protected_text_cells':len(set(protected))}))

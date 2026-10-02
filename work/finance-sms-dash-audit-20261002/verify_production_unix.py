import http.client,json,socket,sys,urllib.parse
SOCKET='/run/mgs-finance-dash.sock';HOST='dash.mgsdigitalcorp.com';ORIGIN='https://dash.mgsdigitalcorp.com'
creds=json.load(sys.stdin);cookie='';csrf=''
class U(http.client.HTTPConnection):
 def connect(self):self.sock=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);self.sock.connect(SOCKET)
def call(path,body=None):
 global cookie,csrf
 c=U('localhost',timeout=180);data=None if body is None else json.dumps(body).encode();h={'Host':HOST,'Origin':ORIGIN,'Accept':'application/json'}
 if cookie:h['Cookie']=cookie
 if csrf:h['X-CSRF-Token']=csrf
 if data is not None:h['Content-Type']='application/json'
 c.request('GET' if body is None else 'POST',path,body=data,headers=h);r=c.getresponse();raw=r.read()
 if r.status>=400:raise RuntimeError((r.status,path,raw[:500]))
 for k,v in r.getheaders():
  if k.lower()=='set-cookie' and v.startswith('__Host-mgs_finance='):cookie=v.split(';',1)[0]
 return json.loads(raw)
call('/api/auth/login',creds);me=call('/api/auth/me');csrf=me['csrf']
out={'actor':me['username'],'history':{},'workspaces':{},'managers':{},'ledger':{}}
for period in ['2026-05','2026-06','2026-07']:
 d=call('/api/history?period='+period+'&book=principal');out['history'][period]={'source_sha256':d.get('source_sha256'),'closure':d.get('closure'),'payroll':d.get('payroll')}
for period in ['2026-08','2026-09']:
 d=call('/api/workspace?period='+period);sms=[e for e in d['domain']['expenses'] if e['id']=='company|121'];facts=[f for f in d['domain']['facts'] if str(f.get('id','')).startswith('sms-direct-'+period+'-')];out['workspaces'][period]={'id':d['id'],'revision':d['revision'],'cash':d['domain']['cash'],'sms_expense':sms,'direct_costs':facts,'errors':d.get('summary',{}).get('counts',{}).get('error',0)}
 for manager in ['joe','nicolas','isliago','kelly','icaro']:
  m=call('/api/manager-workspace?period='+period+'&manager='+manager);out['managers'][period+'|'+manager]={'revision':m['revision'],'remuneration':m['remuneration'],'summary_control':m.get('summary_control'),'errors':m.get('errors')}
for period in ['2026-08','2026-09']:
 for party in ['geizian','personnel|148','personnel|149','personnel|151']:
  q=urllib.parse.urlencode({'period':period,'counterparty':party});d=call('/api/finance/ledger?'+q);out['ledger'][period+'|'+party]={'opening':d['opening'],'previous':d['previous'],'due':d['due'],'movement':d['movement'],'balance':d['balance'],'entries':[{'id':e['id'],'period':e['period'],'date':str(e['effective_date'])[:10],'kind':e['kind'],'amount_cents':e['amount_cents'],'direction':e['direction'],'voided_at':e['voided_at'],'description':e['description']} for e in d['entries']]}
# exact assertions
assert out['history']['2026-05']['closure']['balance']['formatted'].strip()=='R$  319.37'
assert out['history']['2026-06']['closure']['balance']['formatted'].strip()=='R$  752.68'
assert out['history']['2026-07']['closure']['balance']['formatted'].strip()=='R$  4,140.44'
for period,total in [('2026-08','20450.56'),('2026-09','105669.60')]:
 w=out['workspaces'][period];assert len(w['sms_expense'])==1 and w['sms_expense'][0]['archived'];assert len(w['direct_costs'])==6;assert round(sum(float(x['cost_amount']) for x in w['direct_costs']),2)==float(total);assert w['errors']==0
ids={'personnel|148':'1988c8e3-ef8b-558b-ab5b-625df4ccb834','personnel|149':'cfc637d7-b143-5ec0-9ba0-c987fc1847ad','personnel|151':'c4dba803-7d7d-5aae-a9ef-3faca0f8abce'}
for party,ident in ids.items():
 rows=[e for e in out['ledger']['2026-09|'+party]['entries'] if e['id']==ident];assert len(rows)==1 and rows[0]['kind']=='adjustment' and rows[0]['direction']==1 and not rows[0]['voided_at']
out['pass']=True;print(json.dumps(out,ensure_ascii=False))

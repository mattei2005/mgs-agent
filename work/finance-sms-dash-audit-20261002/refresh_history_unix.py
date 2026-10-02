import http.client, json, socket, sys, time
SOCKET='/run/mgs-finance-dash.sock';HOST='dash.mgsdigitalcorp.com';ORIGIN='https://dash.mgsdigitalcorp.com'
creds=json.load(sys.stdin);cookie='';csrf=''
class UnixHTTPConnection(http.client.HTTPConnection):
    def connect(self):
        self.sock=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);self.sock.connect(SOCKET)
def call(method,path,body=None):
    global cookie
    conn=UnixHTTPConnection('localhost',timeout=120)
    data=None if body is None else json.dumps(body).encode()
    headers={'Host':HOST,'Origin':ORIGIN,'Accept':'application/json'}
    if cookie:headers['Cookie']=cookie
    if csrf:headers['X-CSRF-Token']=csrf
    if data is not None:headers['Content-Type']='application/json'
    conn.request(method,path,body=data,headers=headers);res=conn.getresponse();raw=res.read();sets=res.getheaders()
    if res.status>=400:raise RuntimeError(f'HTTP {res.status} {path}: {raw[:500]!r}')
    for key,value in sets:
        if key.lower()=='set-cookie' and value.startswith('__Host-mgs_finance='):
            cookie=value.split(';',1)[0]
    return res.status,json.loads(raw)
status,login=call('POST','/api/auth/login',creds)
if status!=200:raise RuntimeError((status,login))
_,me=call('GET','/api/auth/me');csrf=me['csrf'];out=[]
for period in ['2026-05','2026-06','2026-07']:
    status,row=call('POST','/api/history-refreshes',{'period':period})
    if status!=202:raise RuntimeError((period,status,row))
    deadline=time.time()+240
    while row['status']=='pending' and time.time()<deadline:
        time.sleep(4);_,row=call('GET','/api/history-refreshes/'+row['request_id'])
    if row['status']!='ready' or row.get('documents')!=6:raise RuntimeError((period,row))
    out.append(row)
print(json.dumps({'pass':True,'actor':me['username'],'periods':out},ensure_ascii=False))

import http.cookiejar, json, pathlib, sys, time, urllib.error, urllib.request
sys.path.insert(0,'/root/mgs-agent/scripts')
from mgs_google_workspace_auth import load_env
load_env()
sys.path.insert(0,'/root/mgs-agent/apps/finance-system/deploy')
from runcloud_ops import secret, otp
BASE='https://dash.mgsdigitalcorp.com'
ITEM='MGS Finance - rodolfo - dash.mgsdigitalcorp.com'
jar=http.cookiejar.CookieJar();http=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar));csrf=None

def call(path,body=None):
    data=None if body is None else json.dumps(body).encode()
    headers={'Accept':'application/json','Origin':BASE}
    if data is not None:headers['Content-Type']='application/json'
    if csrf:headers['X-CSRF-Token']=csrf
    req=urllib.request.Request(BASE+path,data=data,method='GET' if body is None else 'POST',headers=headers)
    try:
        with http.open(req,timeout=120) as f:return f.status,json.load(f)
    except urllib.error.HTTPError as e:
        payload=e.read().decode(errors='replace')
        raise RuntimeError(f'HTTP {e.code} {path}: {payload[:500]}') from None

status,login=call('/api/auth/login',{'username':'rodolfo','password':secret(ITEM,'password'),'otp':otp(ITEM)})
if status!=200:raise RuntimeError(f'login status {status}: {login}')
status,me=call('/api/auth/me');csrf=me['csrf']
out=[]
for period in ['2026-05','2026-06','2026-07']:
    status,row=call('/api/history-refreshes',{'period':period})
    if status!=202:raise RuntimeError((period,status,row))
    rid=row['request_id'];deadline=time.time()+240
    while row['status']=='pending' and time.time()<deadline:
        time.sleep(4)
        _,row=call('/api/history-refreshes/'+rid)
    if row['status']!='ready':raise RuntimeError((period,row))
    if row.get('documents')!=6:raise RuntimeError((period,'documents',row))
    out.append(row)
root=pathlib.Path('/root/mgs-agent/apps/finance-system/private/sms-direct-1555422806940983327')
(root/'history-refresh-production.json').write_text(json.dumps({'pass':True,'actor':me['username'],'periods':out},ensure_ascii=False,indent=2));(root/'history-refresh-production.json').chmod(0o600)
print(json.dumps({'pass':True,'periods':[{'period':x['period'],'status':x['status'],'changed':x.get('changed'),'documents':x['documents'],'request_id':x['request_id']} for x in out]},ensure_ascii=False))

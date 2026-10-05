import json,pathlib,urllib.request,urllib.parse,urllib.error
W=pathlib.Path('/root/mgs-agent/work/sb-shein-adaccounts-1556517376651169892');W.mkdir(exist_ok=True)
token=json.load(open('/root/.cache/mgs/finance-bm-inventory-meta-token.json'))['token']
API='https://graph.facebook.com/v26.0/'
def get(path,params=None):
 url=API+path+'?'+urllib.parse.urlencode(params or {})
 req=urllib.request.Request(url,headers={'Authorization':'Bearer '+token,'User-Agent':'MGS-BM-Inventory/1.0'})
 try:
  with urllib.request.urlopen(req,timeout=45) as r:return json.load(r)
 except urllib.error.HTTPError as e:
  try:j=json.load(e).get('error',{});raise RuntimeError('Meta HTTP '+str(e.code)+' code='+str(j.get('code'))+' subcode='+str(j.get('error_subcode'))+' message='+str(j.get('message'))[:300]) from None
  except ValueError:raise RuntimeError('Meta HTTP '+str(e.code)) from None
def pages(path,fields):
 rows=[];params={'fields':fields,'limit':100}
 while True:
  x=get(path,params);rows.extend(x['data'])
  next_url=x.get('paging',{}).get('next')
  if not next_url:break
  q=urllib.parse.parse_qs(urllib.parse.urlsplit(next_url).query);params={k:v[-1] for k,v in q.items() if k!='access_token'}
 return rows
if __name__=='__main__':
 me=get('me',{'fields':'id,name'});businesses=pages('me/businesses','id,name');print('actor',json.dumps(me),'businesses',json.dumps(businesses))
 all_rows=pages('me/adaccounts','account_id,name,account_status,currency,timezone_name,business')
 match=[x for x in all_rows if any(s in x.get('name','').lower() for s in ['growpower','escalatepower','vizioid'])]
 out={'actor':me,'businesses':businesses,'accessible_accounts_count':len(all_rows),'targets':match}
 (W/'meta-before.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps({'accessible_accounts_count':len(all_rows),'targets':match},ensure_ascii=False))

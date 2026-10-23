"""Bounded keep-alive JSON transport for the isolated Drive connector.
Transport only: authentication remains supplied by the existing canonical owner
or SA component. No redirects, credentials in URLs, or mutating auto-retries.
"""
import json,urllib.parse,urllib.error,time
import urllib3
class DriveJSONPool:
 def __init__(self):self.pool=urllib3.PoolManager(num_pools=1,maxsize=4,block=True,cert_reqs='CERT_REQUIRED',timeout=urllib3.Timeout(connect=15,read=90),retries=False)
 def __call__(self,method,url,token,payload=None):
  parsed=urllib.parse.urlsplit(url)
  if parsed.scheme!='https' or parsed.netloc!='www.googleapis.com' or not parsed.path.startswith('/drive/v3/') or parsed.username or parsed.password:raise ValueError('PRIVATE_DRIVE_HTTP_SCOPE')
  data=json.dumps(payload,ensure_ascii=False,separators=(',',':')).encode() if payload is not None else None
  for attempt in range(3 if method=='GET' else 1):
   try:response=self.pool.request(method,url,body=data,headers={'Authorization':'Bearer '+token,'Content-Type':'application/json','User-Agent':'MGS-Private-Drive/1'},redirect=False,retries=False,preload_content=True)
   except urllib3.exceptions.HTTPError:raise urllib.error.URLError('PRIVATE_DRIVE_TRANSPORT') from None
   try:body=json.loads(response.data)
   except ValueError:body={'error':{'message':'PRIVATE_DRIVE_NON_JSON'}}
   status=response.status
   if method=='GET' and status in [429,500,502,503,504] and attempt<2:time.sleep(1+attempt);continue
   return status,body
  raise urllib.error.URLError('PRIVATE_DRIVE_READ_ATTEMPTS_EXHAUSTED')
 def close(self):self.pool.clear()

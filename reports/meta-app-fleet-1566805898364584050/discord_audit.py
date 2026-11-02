import importlib.util,json,os,time,urllib.request,urllib.error
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor
ROOT=Path('/root/.hermes/profiles/zeus/cache/scratch/meta-fleet-20261102')
spec=importlib.util.spec_from_file_location('poster','/root/mgs-agent/scripts/discord-bot-post.py'); poster=importlib.util.module_from_spec(spec);spec.loader.exec_module(poster);poster.load_env(poster.DEFAULT_ENV)
token=os.environ.get('MGS_DISCORD_BOT_TOKEN_OVERRIDE') or os.environ['DISCORD_BOT_TOKEN']
def get(path):
 for i in range(4):
  try:
   req=urllib.request.Request('https://discord.com/api/v10/'+path,headers={'Authorization':'Bot '+token,'User-Agent':'MGS-Zeus/1.0'})
   with urllib.request.urlopen(req,timeout=30) as r:return json.load(r)
  except urllib.error.HTTPError as e:
   if e.code!=429:raise RuntimeError('Discord HTTP '+str(e.code)) from None
   data=json.loads(e.read());time.sleep(float(data.get('retry_after',2))+0.2)
 raise RuntimeError('Discord rate limited after bounded retries')
def text(m):
 parts=[m.get('content','')]
 for e in m.get('embeds',[]):
  parts += [e.get('title',''),e.get('description','')]
  parts += [f.get('name','')+' '+f.get('value','') for f in e.get('fields',[])]
  parts += [e.get('footer',{}).get('text','')]
 return '\n'.join(parts)
def fetch(app):
 channel=app['channel_id']; start=datetime(2026,11,1,tzinfo=ZoneInfo('America/New_York'))
 after=str((int(start.timestamp()*1000)-1420070400000)<<22)
 messages=[]; before=None; pages=0
 while True:
  path=f'channels/{channel}/messages?limit=100&after={after}' + (f'&before={before}' if before else '')
  # Discord before and after may conflict; use before-only after first page.
  if before:path=f'channels/{channel}/messages?limit=100&before={before}'
  batch=get(path);pages+=1
  valid=[m for m in batch if int(m['id'])>int(after)];messages+=valid
  if len(batch)<100 or len(valid)<len(batch):break
  before=min(m['id'] for m in batch)
  if pages>=50:raise RuntimeError('pagination bound '+app['app'])
 messages=sorted({m['id']:m for m in messages}.values(),key=lambda m:int(m['id']))
 meta=get('channels/'+channel)
 out={'app':app['app'],'channel_id':channel,'channel_name':meta['name'],'messages':messages,'pages':pages,'from_et':start.isoformat(),'latest_id':max([m['id'] for m in messages],key=int) if messages else None}
 (ROOT/(app['app']+'-history.json')).write_text(json.dumps(out,ensure_ascii=False,indent=2))
 titles=[]
 for m in messages:
  title=' / '.join(e.get('title','') for e in m.get('embeds',[]))
  if title or ('```' not in m.get('content','')):titles.append({'id':m['id'],'time':m.get('timestamp'),'title':title,'text':text(m)[:1800]})
 return {'app':app['app'],'channel':meta['name'],'messages':len(messages),'pages':pages,'cards':titles}
if __name__=='__main__':
 apps=json.loads(Path('/root/mgs-agent/data/meta-app-registry.json').read_text())['apps']
 with ThreadPoolExecutor(max_workers=3) as pool: results=list(pool.map(fetch,apps))
 (ROOT/'history-summary.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
 print(json.dumps(results,ensure_ascii=False,indent=2))

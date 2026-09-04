#!/usr/bin/env python3
import json, os, urllib.request
from pathlib import Path

def load_env(path):
    for raw in Path(path).read_text(errors='ignore').splitlines():
        line=raw.strip()
        if not line or line.startswith('#') or '=' not in line: continue
        key,value=line.split('=',1)
        os.environ.setdefault(key.strip(),value.strip().strip('"').strip("'"))

load_env('/root/.hermes/profiles/zeus/.env')
token=os.environ.get('DISCORD_BOT_TOKEN')
if not token: raise RuntimeError('bot token missing')
channel='1498132022634483894'; message='1545556291521355817'
req=urllib.request.Request(f'https://discord.com/api/v10/channels/{channel}/messages/{message}',headers={'Authorization':'Bot '+token,'User-Agent':'MGS-Zeus/1.0'})
with urllib.request.urlopen(req,timeout=20) as response:
    data=json.loads(response.read())
result={
 'status':'pass' if str(data.get('id'))==message and str(data.get('channel_id'))==channel and data.get('content')=='' and len(data.get('embeds') or [])==1 and not (data.get('mentions') or []) else 'fail',
 'http':response.status,
 'message_id':str(data.get('id')),
 'channel_id':str(data.get('channel_id')),
 'content_empty':data.get('content')=='',
 'embed_count':len(data.get('embeds') or []),
 'mentions':len(data.get('mentions') or []),
 'embed_title':((data.get('embeds') or [{}])[0] or {}).get('title'),
 'thread_created':False,
}
print(json.dumps(result,ensure_ascii=False,separators=(',',':')))
if result['status']!='pass': raise SystemExit(2)

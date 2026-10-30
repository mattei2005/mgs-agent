"""Update the exact existing infrastructure receipt, never publish a copy."""
import json,sys,importlib.util,os
from pathlib import Path
from urllib.request import Request,urlopen
B=Path('/root/mgs-agent');sys.path.insert(0,str(B/'scripts'))
from ares_campaign_v3.shein_channel_authority import _get
path='/channels/1498132022634483894/messages/1565761035963465729'
old=_get(path);assert old['author']['id']=='1496296175014252634' and old['content']==''
embed={k:v for k,v in old['embeds'][0].items() if k in {'title','description','color','fields','footer','timestamp'}}
field=next(x for x in embed['fields'] if x['name']=='Evidência')
assert '529 testes' in field['value']
field['value']=field['value'].replace('529 testes','531 testes')+' Recovery da mesma request/lease também testado sem deadlock; writer estrangeiro/lock continuam bloqueados.'
assert len(field['value'])<=1024
spec=importlib.util.spec_from_file_location('poster',B/'scripts/discord-bot-post.py');poster=importlib.util.module_from_spec(spec);spec.loader.exec_module(poster)
poster.load_env(poster.DEFAULT_ENV)
token=os.environ.get('MGS_DISCORD_BOT_TOKEN_OVERRIDE') or os.environ.get('DISCORD_BOT_TOKEN');assert token
payload={'content':'','embeds':[embed],'allowed_mentions':{'parse':[]}}
request=Request('https://discord.com/api/v10'+path,data=json.dumps(payload,ensure_ascii=False).encode(),method='PATCH',headers={'Authorization':'Bot '+token,'Content-Type':'application/json','User-Agent':'MGS-Zeus/1.0'})
try:
 with urlopen(request,timeout=25) as response:
  status=response.status;result=json.load(response)
except Exception as exc:
 print(json.dumps({'status':'PATCH_UNCONFIRMED','error_type':type(exc).__name__,'http':getattr(exc,'code',None),'message_id':old['id']}));sys.exit(1)
new=_get(path)
assert status==200 and new['id']==old['id'] and new['content']=='' and not new['mentions']
assert next(x['value'] for x in new['embeds'][0]['fields'] if x['name']=='Evidência')==field['value']
print(json.dumps({'status':'EXISTING_EMBED_UPDATED_READBACK_VERIFIED','message_id':new['id'],'new_message_created':False,'tests':531}))

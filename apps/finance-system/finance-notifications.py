"""Zeus-only Discord notification, proposal metadata only, exact message readback.
No financial mutation, token transfer to hosting, or Meta write.
"""
import json,pathlib,re,urllib.request
import shlex
def dotenv_values(file):
 result={}
 for line in pathlib.Path(file).read_text().splitlines():
  line=line.strip().removeprefix('export ')
  if not line or line.startswith('#') or '=' not in line:continue
  key,value=line.split('=',1);parts=shlex.split(value,comments=True)
  if parts:result[key.strip()]=parts[0]
 return result
CHANNEL='1545426987756298340';OWNER='344196393512075265';BOT='1496296175014252634'
NODE='/home/mgsfinance/runtime/node-v22.23.2-linux-x64/bin/node'
def deliver(proposal,canary=False):
 assert re.fullmatch(r'[0-9a-f-]{36}',proposal['id'])
 token=dotenv_values('/root/.hermes/profiles/zeus/.env').get('DISCORD_BOT_TOKEN')
 if not token:raise RuntimeError('Zeus Discord credential unavailable')
 def request(path,body=None):
  req=urllib.request.Request('https://discord.com/api/v10'+path,data=json.dumps(body).encode() if body is not None else None,headers={'Authorization':'Bot '+token,'Content-Type':'application/json','User-Agent':'MGS-Finance-Notification/1.0'},method='POST' if body is not None else 'GET')
  with urllib.request.urlopen(req,timeout=30) as r:return json.load(r)
 assert request('/users/@me')['id']==BOT
 content=('<@'+OWNER+'> **Teste de notificação do financeiro:** entrega validada; nenhuma alteração financeira ou proposta real foi criada.' if canary else '<@'+OWNER+'> **Financeiro: nova proposta de alteração.** Revise e autorize/rejeite em <https://dash.mgsdigitalcorp.com/operations?view=approvals>. Nenhuma alteração é aplicada sem sua aprovação. Referência: `'+proposal['id']+'`.')
 payload={'content':content,'allowed_mentions':{'parse':[],'users':[OWNER],'roles':[],'replied_user':False},'nonce':proposal['id'].replace('-','')[:24],'enforce_nonce':True}
 result=request('/channels/'+CHANNEL+'/messages',payload);message=request('/channels/'+CHANNEL+'/messages/'+result['id']);assert message['content']==content and message['author']['id']==BOT and message['channel_id']==CHANNEL
 return {'id':proposal['id'],'message_id':message['id'],'channel_id':CHANNEL,'readback':True,'canary':canary}
def tick(ssh,target):
 rows=json.loads(ssh('sudo -n -u mgsfinance '+NODE+' '+target+'/deploy/finance-notices.mjs pending',timeout=45));done=[]
 for row in rows:
  notice=deliver(row);ack=json.loads(ssh('sudo -n -u mgsfinance '+NODE+' '+target+'/deploy/finance-notices.mjs ack',json.dumps(notice).encode(),timeout=45));assert ack['readback'];done.append(notice['message_id'])
 return {'ok':True,'delivered':len(done),'message_ids':done}

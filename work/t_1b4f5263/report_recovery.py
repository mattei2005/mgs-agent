"""Verify REPORT-INFRA and deliver one compact recovery update to its origin."""
import hashlib,importlib.util,json,os,subprocess,sys,urllib.request
from pathlib import Path
ROOT=Path('/root/mgs-agent');sys.path.insert(0,str(ROOT/'scripts'))
import ares_archive_bridge as b
H=b.DATA/'consumer-recovery-t_1b4f5263'
spec=importlib.util.spec_from_file_location('poster',ROOT/'scripts/discord-bot-post.py');assert spec and spec.loader
poster=importlib.util.module_from_spec(spec);spec.loader.exec_module(poster)
poster.load_env(Path('/root/.hermes/profiles/ares/.env'));token=os.environ['DISCORD_BOT_TOKEN']
def get(path):
 req=urllib.request.Request('https://discord.com/api/v10/'+path,headers={'Authorization':'Bot '+token,'User-Agent':'MGS-Ares/1.0'})
 with urllib.request.urlopen(req,timeout=30) as f:return json.load(f)
mid='1569461768999280802';infra=get('channels/1498132022634483894/messages/'+mid)
assert infra['id']==mid and infra['channel_id']=='1498132022634483894'
assert infra['content']=='' and infra.get('embeds') and not infra.get('mentions') and not infra.get('mention_roles') and not infra.get('mention_everyone')
b.atomic_json(H/'installed-report-infra-readback.json',{'message_id':mid,'channel_id':infra['channel_id'],'content_empty':True,'embeds':infra['embeds'],'no_mentions':True,'checked_at':b.now_iso()})
channel=get('channels/1558134300325716050');assert channel['parent_id']=='1548150155184701440'
text='Corrigi a leitura dos dois vídeos jeans: os 34 vídeos do pedido agora passam na leitura canônica, com os mesmos IDs e hashes. Não movi as cópias do Ícaro nem alterei as fontes do Nicolas, as reservas ou os registros históricos.\n\nAprendizado salvo e relido na skill Creative Ops, na referência de identidade Drive × Meta: conciliação limitada à autorização e aos vínculos exatos. A leitura está liberada para a continuação central das 17 campanhas do mesmo pedido, com os parâmetros originais; esta manutenção não executou campanhas.'
payload={'content':text,'allowed_mentions':{'parse':[]},'nonce':hashlib.sha256(b't_1b4f5263-maintenance-accepted').hexdigest()[:24],'enforce_nonce':True}
intent=H/'installed-origin-update-intent.json';prior=b.read_json(intent,{})
assert not prior or prior['payload']==payload,'origin_intent_changed'
recent=get('channels/1558134300325716050/messages?limit=50')
# Compare to the actual Ares API identity, never infer author from content alone.
me=get('users/@me');existing=[m for m in recent if m.get('content')==text and m.get('author',{}).get('id')==me['id']]
if existing:sent=existing[0]
else:
 if prior.get('status')=='posting':raise RuntimeError('ambiguous_prior_send_reconcile_no_replay')
 b.atomic_json(intent,{'status':'posting','payload':payload,'at':b.now_iso()})
 env=dict(os.environ,MGS_DISCORD_BOT_ENV='/root/.hermes/profiles/ares/.env')
 result=subprocess.run(['python3',str(ROOT/'scripts/discord-bot-post.py'),'--channel-id','1558134300325716050'],input=json.dumps(payload),text=True,capture_output=True,env=env)
 assert result.returncode==0,result.stderr
 import re
 match=re.search(r'message_id=(\d+)',result.stdout);assert match
 sent=get('channels/1558134300325716050/messages/'+match.group(1))
assert sent['channel_id']=='1558134300325716050' and sent['content']==text and sent['author']['id']==me['id'] and not sent.get('mentions')
receipt={'message_id':sent['id'],'channel_id':sent['channel_id'],'parent_id':channel['parent_id'],'author_id':sent['author']['id'],'content':sent['content'],'skill_readback_sha256':hashlib.sha256(Path('/root/.hermes/profiles/ares/skills/growth/creative-operations-mgs/references/drive-meta-asset-identity-and-manager-reservation.md').read_bytes()).hexdigest(),'checked_at':b.now_iso()}
b.atomic_json(H/'installed-origin-update-readback.json',receipt)
b.atomic_json(intent,{'status':'verified','payload':payload,'message_id':sent['id']})
print(json.dumps({'report_infra_message_id':mid,'report_content_empty':True,'report_no_mentions':True,'origin_message_id':sent['id'],'origin_readback':True}))

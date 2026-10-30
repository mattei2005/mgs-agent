"""GET exact REPORT-INFRA target with the same canonical report transport."""
import importlib.util,json,os,re
from pathlib import Path
from urllib.request import Request,urlopen
B=Path('/root/mgs-agent');W=B/'work/t_8426333c'
text=(W/'report-infra-send.txt').read_text();matches=re.findall(r'message_id=(\d+)',text);assert len(matches)==1
mid=matches[0];channel='1498132022634483894'
spec=importlib.util.spec_from_file_location('report_transport',B/'scripts/discord-bot-post.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
module.load_env(Path(os.environ.get('MGS_DISCORD_BOT_ENV',str(module.DEFAULT_ENV))))
token=os.environ.get('MGS_DISCORD_BOT_TOKEN_OVERRIDE') or os.environ.get('DISCORD_BOT_TOKEN');assert token
req=Request(f'https://discord.com/api/v10/channels/{channel}/messages/{mid}',headers={'Authorization':'Bot '+token,'User-Agent':'MGS-Report-Readback/1.0'})
with urlopen(req,timeout=20) as response:data=json.load(response)
assert data['id']==mid and data['channel_id']==channel and data.get('content','')==''
assert not data.get('mentions') and not data.get('mention_roles') and not data.get('mention_everyone')
assert not data.get('thread')
embeds=data.get('embeds',[]);assert len(embeds)==1 and embeds[0]['title']=='REPORT-INFRA — modificada'
fields={f['name']:f['value'] for f in embeds[0]['fields']}
assert 't_8426333c' in fields['Motivo'] and '583 testes+484 subtests' in fields['Evidência']
result={'message_id':mid,'channel_id':channel,'url':f'https://discord.com/channels/1185714635991679006/{channel}/{mid}','get_verified':True,'content_empty':True,'no_mentions':True,'no_thread':True,'embed_title':embeds[0]['title'],'exact_task_and_evidence_verified':True}
(W/'report-infra-readback.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

#!/usr/bin/env python3
"""Read back exact report and fresh existing hierarchy. No mutation."""
import os,sys,json,importlib.util,urllib.request
from pathlib import Path
from datetime import datetime,timezone
R=Path('/root/mgs-agent');M=Path(__file__).resolve().parent
sys.path.insert(0,str(R/'scripts'))
s=importlib.util.spec_from_file_location('zeus_discord_post_loader',R/'scripts/discord-bot-post.py')
assert s is not None and s.loader is not None
mod=importlib.util.module_from_spec(s);s.loader.exec_module(mod);mod.load_env(mod.DEFAULT_ENV)
req=urllib.request.Request('https://discord.com/api/v10/channels/1498132022634483894/messages/1571423196509380669',headers={'Authorization':'Bot '+os.environ['DISCORD_BOT_TOKEN'],'User-Agent':'MGS-Zeus/1.0'})
with urllib.request.urlopen(req,timeout=30)as resp:msg=json.load(resp)
assert msg['id']=='1571423196509380669' and msg['channel_id']=='1498132022634483894' and msg['content']=='' and len(msg['embeds'])==1 and not msg['mentions'] and not msg.get('mention_roles') and not msg.get('thread')
assert any('2446386'in x.get('value','') for x in msg['embeds'][0]['fields'])
receipt={'message_id':msg['id'],'channel_id':msg['channel_id'],'readback_verified':True,'content_empty':True,'embeds':1,'mentions':[],'thread':False,'at':datetime.now(timezone.utc).isoformat()}
(M/'report-infra-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print('REPORT',json.dumps(receipt))
s=importlib.util.spec_from_file_location('fresh_final_get_runner',R/'scripts/ares-eggbev-target-clone.py')
assert s is not None and s.loader is not None
r=importlib.util.module_from_spec(s);s.loader.exec_module(r);common,meta,_,token=r.runtime()
code,parent,_=meta.graph_get('120251246081230629',token,{'fields':'id,status,configured_status,effective_status,daily_budget,start_time'})
assert code==200 and parent['status']=='PAUSED'and parent['daily_budget']=='3500'
code,adset,_=meta.graph_get('120251246081300629',token,{'fields':'id,status,effective_status,start_time'})
assert code==200 and adset['status']=='ACTIVE' and adset['start_time']=='2026-11-15T00:26:40-0500'
ads=common.fetch_all_meta(meta,token,'120251246081230629/ads',{'fields':'id,status,configured_status,effective_status,issues_info,source_ad_id,creative{id}','limit':100})
expected={'120251246303620629':'PAUSED','120251246303850629':'ACTIVE','120251246303720629':'ACTIVE','120251246302480629':'PAUSED','120251246302450629':'PAUSED','120251246302470629':'PAUSED'}
assert len(ads)==6 and {a['id']:a['status']for a in ads}==expected
bad=next(a for a in ads if a['id']=='120251246303620629');assert bad['effective_status']=='WITH_ISSUES' and bad['issues_info'][0]['error_code']==2446386
assert all(not a.get('issues_info')for a in ads if a['id']in {'120251246303850629','120251246303720629'})
out={'at':datetime.now(timezone.utc).isoformat(),'campaign':parent,'adset':adset,'ads':ads,'meta_writes':0,'drive_writes':0}
(M/'final-live-get.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print('FRESH_GET',json.dumps({'campaign':parent,'adset':adset,'ad_count':len(ads),'ad01_status':bad['status'],'ad01_effective_status':bad['effective_status'],'issue':2446386}))

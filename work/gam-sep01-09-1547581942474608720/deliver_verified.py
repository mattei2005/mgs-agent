import json,os,fcntl,hashlib,importlib.util,uuid
from pathlib import Path
from datetime import datetime,timezone
from urllib.request import Request,urlopen
P=Path(__file__).parent
summary=json.loads((P/'summary.json').read_text());output=Path(summary['output'])
spec=importlib.util.spec_from_file_location('poster','/root/mgs-agent/scripts/discord-bot-post.py');poster=importlib.util.module_from_spec(spec);spec.loader.exec_module(poster)
poster.load_env(poster.DEFAULT_ENV);token=os.environ.get('MGS_DISCORD_BOT_TOKEN_OVERRIDE') or os.environ.get('DISCORD_BOT_TOKEN');assert token
headers={'Authorization':'Bot '+token,'User-Agent':'MGS-Zeus/1.0'}
def get(url):
 with urlopen(Request(url,headers=headers),timeout=30) as r:return json.loads(r.read())
report_id='1547584492623896587';report=get(f'https://discord.com/api/v10/channels/1498132022634483894/messages/{report_id}')
assert report['content']=='' and len(report['embeds'])==1 and not report['mentions']
fields={f['name']:f['value'] for f in report['embeds'][0]['fields']};assert all(k in fields for k in ['Ação','Tipo','Path','Motivo','Evidência'])
assert '513 grupos' in fields['Evidência']
state=P/'delivery.json';channel='1545426987756298340'
if state.exists():mid=json.loads(state.read_text())['message_id']
else:
 boundary='MGSUpload'+uuid.uuid4().hex
 payload={'content':'','allowed_mentions':{'parse':[]},'nonce':'1547581942474608720','enforce_nonce':True,'attachments':[{'id':0,'filename':output.name,'description':'Receita GAM 01–09 setembro 2026: consolidado Zeus, moedas separadas, validação e ressalvas.'}]}
 body=(f'--{boundary}\r\nContent-Disposition: form-data; name="payload_json"\r\nContent-Type: application/json\r\n\r\n'.encode()+json.dumps(payload,ensure_ascii=False).encode()+f'\r\n--{boundary}\r\nContent-Disposition: form-data; name="files[0]"; filename="{output.name}"\r\nContent-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet\r\n\r\n'.encode()+output.read_bytes()+f'\r\n--{boundary}--\r\n'.encode())
 req=Request(f'https://discord.com/api/v10/channels/{channel}/messages',data=body,method='POST',headers={**headers,'Content-Type':'multipart/form-data; boundary='+boundary})
 with urlopen(req,timeout=45) as response:data=json.loads(response.read())
 mid=data['id'];state.write_text(json.dumps({'message_id':mid,'channel_id':channel,'filename':output.name,'verified':False},indent=2))
msg=get(f'https://discord.com/api/v10/channels/{channel}/messages/{mid}');assert msg['channel_id']==channel and msg['content']=='' and not msg['mentions'];assert len(msg['attachments'])==1
attachment=msg['attachments'][0];assert attachment['filename']==output.name and attachment['size']==output.stat().st_size
with urlopen(Request(attachment['url'],headers={'User-Agent':'Mozilla/5.0'}),timeout=45) as r:download=r.read()
assert hashlib.sha256(download).hexdigest()==summary['output_sha256']
result={'message_id':mid,'channel_id':channel,'filename':output.name,'size':len(download),'sha256':summary['output_sha256'],'verified':True,'report_infra_message_id':report_id,'report_infra_readback':True}
state.write_text(json.dumps(result,ensure_ascii=False,indent=2))
root=Path('/root/mgs-agent');ident='zeus-gam-sep01-09-1547581942474608720';p=root/'data/infra-inventory.json'
skills=Path('/root/.hermes/profiles/zeus/skills/ops');paths=[skills/'revenue-spend-reporting-pipeline/SKILL.md',skills/'revenue-spend-reporting-pipeline/references/gam-daily-excel-consolidation.md',skills/'mgs-finance-dashboard/SKILL.md',P/'deliver_verified.py',state]
assert 'single procedural owner' in paths[2].read_text();assert 'three-bucket' in paths[0].read_text()
with (root/'data/.infra-inventory.lock').open('a') as f:
 fcntl.flock(f,fcntl.LOCK_EX);data=json.loads(p.read_text());entry=next(r for r in data['runtime_artifacts'] if r.get('id')==ident)
 for q in paths:
  entry['paths']=[x for x in entry['paths'] if x['path']!=str(q)];entry['paths'].append({'path':str(q),'sha256':hashlib.sha256(q.read_bytes()).hexdigest(),'size_bytes':q.stat().st_size})
 entry['report_infra_pending']=False;entry['report_infra_message_id']=report_id;entry['report_infra_readback']=True;entry['delivery']=result
 tmp=p.with_name(p.name+'.delivery.tmp')
 with tmp.open('w') as o:json.dump(data,o,ensure_ascii=False,indent=2);o.write('\n');o.flush();os.fsync(o.fileno())
 tmp.chmod(p.stat().st_mode&0o777);os.replace(tmp,p)
 assert next(r for r in json.loads(p.read_text())['runtime_artifacts'] if r.get('id')==ident)['delivery']==result
with (root/'logs/events-audit.jsonl').open('a') as f:
 fcntl.flock(f,fcntl.LOCK_EX);f.write(json.dumps({'timestamp':datetime.now(timezone.utc).isoformat(),'agent':'zeus','event':'gam_excel_delivery_and_infra_readback','authorization_message_id':'1547581942474608720','artifact_id':ident,'result':result,'procedural_owner':'revenue-spend-reporting-pipeline/references/gam-daily-excel-consolidation.md','dashboard_link_readback':True},ensure_ascii=False)+'\n');f.flush();os.fsync(f.fileno())
print(json.dumps(result,ensure_ascii=False))

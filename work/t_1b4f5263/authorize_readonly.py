"""Capture exact read-only reconciliation authority; no media or Meta writes."""
import sys,json,hashlib,urllib.request,importlib.util
from pathlib import Path
ROOT=Path('/root/mgs-agent');sys.path.insert(0,str(ROOT/'scripts'))
import ares_archive_storage as s
H=ROOT/'data/ares/creative-ops/30tb-archive/consumer-recovery-t_1b4f5263'
spec=importlib.util.spec_from_file_location('poster',ROOT/'scripts/discord-bot-post.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
m.load_env(Path('/root/.hermes/profiles/ares/.env'))
import os
token=os.environ['DISCORD_BOT_TOKEN']
def get(path):
 r=urllib.request.Request('https://discord.com/api/v10/'+path,headers={'Authorization':'Bot '+token,'User-Agent':'MGS-Ares/1.0'})
 with urllib.request.urlopen(r,timeout=30) as f:return json.load(f)
channel=get('channels/1558134300325716050');assert channel['parent_id']=='1548150155184701440'
messages=[]
for mid in ['1569458720050516030','1569459090634047609']:
 msg=get('channels/1558134300325716050/messages/'+mid)
 assert msg['id']==mid and msg['channel_id']=='1558134300325716050' and msg['author']['id']=='344196393512075265'
 messages.append({k:msg[k] for k in ['id','channel_id','content','timestamp','edited_timestamp'] }|{'author_id':msg['author']['id']})
assert messages[0]['content']=='Ignora isso. E faz o que o Nicolas pediu. Pois os arquivos tão na pasta dele Nicolas exclusivos correto ?'
assert messages[1]['content']=='Ok então executa.'
authority={'schema':'mgs.archive.readonly.authority.readback.v1','checked_at':s.b.now_iso(),'parent_id':channel['parent_id'],'messages':messages}
s.b.atomic_json(H/'approved-authority-readback.json',authority)
proposal=s.b.read_json(H/'readonly-reconciliation-proposal.json');baseline=s.b.read_json(H/'baseline.json')
d=s.drive();records=[]
for pair in proposal['pairs']:
 e=s.mapping(pair['logical_source_id']);a=s.meta(d,e['archiveId']);stock=s.meta(d,e['sourceId'])
 assert a['parents']==[pair['accepted_provider_parent_id']] and stock['parents']==[pair['retained_source_parent_id']]
 assert d.relative_parent(a['parents'][0],s.b.ARCHIVE_ROOT)==pair['accepted_provider_relative_path']
 assert s.locations.stock_parent(d,stock['parents'][0])==pair['retained_source_relative_path']
 assert s.require_historical_ack(d,e)
 expected={k:e[k] for k in ['size','md5','sha256']}
 assert d.hashes(e['archiveId'])==expected and d.hashes(e['sourceId'])==expected
 ack=d.one(s.b.config_load()['requests_folder_id'],'backfill-ack:'+e['jobId']);assert ack['id']==pair['ack_id']
 assert hashlib.sha256(d.raw(ack['id'])).hexdigest()==pair['ack_sha256']
 records.append({'pair':pair,'frozen_entry':e,'provider':a,'source':stock,'full_bytes_and_native_ack_verified':True,'hashes':expected})
proof={'schema':'mgs.archive.readonly.native.proof.v1','checked_at':s.b.now_iso(),'identity':s.b.CANONICAL_SA,'records':records}
s.b.atomic_json(H/'approved-native-proof.json',proof)
binding={'schema':'mgs.archive.readonly.pair.reconciliation.v1','phase':'active','authority_message_id':messages[0]['id'],'confirmation_message_id':messages[1]['id'],'request_id':proposal['request_id'],'request_path':'data/ares/meta-ads/audit/shein/campaigns/intake/shein-1569454008337301577/request.json','request_sha256':baseline['file_sha256']['data/ares/meta-ads/audit/shein/campaigns/intake/shein-1569454008337301577/request.json'],'authority_sha256':hashlib.sha256(s.b.canonical(authority)).hexdigest(),'native_proof_sha256':hashlib.sha256(s.b.canonical(proof)).hexdigest(),'read_only':True,'pairs':proposal['pairs']}
s.b.atomic_json(H/'approved-readonly-binding.json',binding)
print(json.dumps({'authority_message_id':messages[0]['id'],'confirmation_message_id':messages[1]['id'],'pairs_verified':len(records),'binding_sha256':hashlib.sha256(s.b.canonical(binding)).hexdigest()}))

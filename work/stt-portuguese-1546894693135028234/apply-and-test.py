"""Bounded Zeus STT language correction; no restart/provider/credential change."""
from pathlib import Path
import os,json,copy,hashlib
os.environ['HERMES_HOME']='/root/.hermes/profiles/zeus';os.environ['HERMES_PROFILE']='zeus'
import yaml
from hermes_cli.config import atomic_config_write
D=Path('/root/mgs-agent/work/stt-portuguese-1546894693135028234');D.mkdir(parents=True,exist_ok=True,mode=0o700)
paths=[Path('/root/.hermes/profiles/zeus/config.yaml'),Path('/root/mgs-agent/profiles/zeus-config.yaml')];out=[]
for i,p in enumerate(paths):
 raw=p.read_bytes();before=yaml.safe_load(raw);assert isinstance(before,dict);new=copy.deepcopy(before);assert new['stt']['provider']=='local';new['stt']['local']['language']='pt'
 backup=D/f'config-{i}-before.yaml'
 if not backup.exists():backup.write_bytes(raw);backup.chmod(0o600)
 atomic_config_write(p,new);check=yaml.safe_load(p.read_text());assert check==new;check['stt']['local']['language']=before['stt']['local']['language'];assert check==before
 out.append({'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'before_language':before['stt']['local']['language'],'after_language':'pt'})
from tools.transcription_tools import _resolve_stt_language,_transcribe_local,_load_stt_config
assert _resolve_stt_language('local',_load_stt_config())=='pt'
audio='/root/.hermes/profiles/zeus/cache/audio/audio_b80e7d562e4e.ogg'
r=_transcribe_local(audio,'base');assert r['success'];text=r['transcript'];(D/'retranscription.txt').write_text(text);(D/'retranscription.txt').chmod(0o600)
proof={'pass':True,'files':out,'resolved_language':'pt','provider':'local','model':'base','restart':False,'transcription_success':True,'transcript_characters':len(text)};(D/'readback.json').write_text(json.dumps(proof,indent=2));print(json.dumps(proof));print('RETRANSCRICAO: '+text)

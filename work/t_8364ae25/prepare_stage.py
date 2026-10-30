import json,hashlib,shutil
from pathlib import Path
B=Path('/root/mgs-agent');W=B/'work/t_8364ae25';W.mkdir(exist_ok=True)
live=B/'scripts/ares_campaign_v3';stage=W/'stage/ares_campaign_v3';shutil.copytree(live,stage)
for name in ['image_prestage.py','shein_media_handoff.py','shein_grouped_media.py']:
 p=W/'backup'/name;p.parent.mkdir(exist_ok=True);shutil.copy2(live/name,p)
R='shein-1565747351543480374'
paths=[B/'data/ares/meta-ads/state/shein-campaigns/single-clone'/R/'state.json',B/'data/ares/meta-ads/engine-v3/state/checkpoints'/(R+'-937846586033361.json'),B/'data/ares/meta-ads/engine-v3/media-registry.json',B/'data/ares/creative-ops/inventory/assets.jsonl']
paths+=list((B/'data/ares/meta-ads/audit/shein/campaigns/intake'/R).glob('*.json'))
paths+=list((B/'data/ares/meta-ads/state/shein-campaigns/single-clone').glob('shein-1565261967260647536*/state.json'))
paths+=list((B/'data/ares/meta-ads/audit/shein/campaigns/continuations').glob(R+'*.json'))
(W/'baseline-state-hashes.json').write_text(json.dumps({str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},indent=2)+'\n')
print('stage and code backup ready; operational paths',len(paths))

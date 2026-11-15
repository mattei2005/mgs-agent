import hashlib,json,shutil
from pathlib import Path
R=Path('/root/mgs-agent');M=R/'data/ares/meta-ads/audit/maintenance/t_53c187db';H=R/'data/ares/meta-ads/audit/eggbev/target-clone/eggbev-pg23189-1571342489162489937'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
(M/'before').mkdir(exist_ok=True)
runner=R/'scripts/ares-eggbev-target-clone.py';shutil.copy2(runner,M/'before/ares-eggbev-target-clone.py')
pins=json.loads((R/'data/ares/meta-ads/audit/maintenance/t_84f0dd13/installed-runtime-hashes.json').read_text())
protected={str(p):sha(p) for p in H.rglob('*') if p.is_file() and p.suffix!='.lock'}
for p in [R/'data/ares/meta-ads/engine-v3/config.json',R/'data/ares/creative-ops/inventory/assets.jsonl',R/'data/ares/meta-ads/engine-v3/media-registry.json'] :protected[str(p)]=sha(p)
(M/'protected-before.json').write_text(json.dumps(protected,indent=2)+'\n')
(M/'runtime-before.json').write_text(json.dumps(pins,indent=2)+'\n')
handoff=H/'owner-attempt5-handoff.json';assert sha(handoff)=='f28b1802f0f087889f05473504c3650726a5a2699354ae9fa5bee3709cf4d6b0'
h=json.loads(handoff.read_text());assert all(sha(Path(p))==s for p,s in h['hash_pins'].items())
proof=json.loads((H/'owner-attempt5-media-equivalence-proof.json').read_text())
files={**h['hash_pins'],str(handoff):sha(handoff)}
for d in proof['downloads']:
 for p in [Path(d['path']),*[Path(f['path']) for f in d['frames']]]:files[str(p)]=sha(p)
cfg=json.loads((R/'data/ares/meta-ads/engine-v3/config.json').read_text());cp=Path(cfg['state_root'])/'checkpoints'/f"{h['request_id']}-1034081997659047.json";audit=Path(cfg['audit_root'])/f"{h['request_id']}.json"
for p in [cp,audit,H/'engine-result.json']:files[str(p)]=sha(p);shutil.copy2(p,M/'before'/p.name)
grant={'schema':'mgs.target.media.grant.v1','request_id':h['request_id'],'request_path':str(H/'request.json'),'original_approved_digest':'7fb94557a6302e97bcc5239ad7f7758052555203f3ff15c360e1ffef55c5afba','approval_message_id':'1571376388437577861','attested_at':h['at'],'pins':files,'ids':json.loads(cp.read_text())['bundles'][0]['target_clone_ids'],'pairs':proof['pairs'],'checkpoint_path':str(cp),'audit_path':str(audit),'rendered_proof_path':str(H/'owner-attempt5-rendered-proof.json'),'proof_path':str(H/'owner-attempt5-media-equivalence-proof.json'),'maintenance_task':'t_53c187db','execution_owner':'t_bdfc754f'}
(M/'media-grant.json').write_text(json.dumps(grant,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'grant_sha256':sha(M/'media-grant.json'),'proof_pins':len(files),'protected_files':len(protected),'runtime_files':len(pins)}))

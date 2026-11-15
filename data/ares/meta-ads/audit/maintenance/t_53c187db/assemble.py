from pathlib import Path
R=Path('/root/mgs-agent');M=R/'data/ares/meta-ads/audit/maintenance/t_53c187db'
s=(M/'before/ares-eggbev-target-clone.py').read_text()
s=s.replace("choices=['prepare','execute','finalize','check-continuation']","choices=['prepare','execute','finalize','check-continuation','recover-media']")
s=s.replace("    # One foreground/request owner across preparation and engine invocation.","    if a.command=='recover-media' or (a.command=='finalize' and (a.input.parent/'media-recovery'/'verified.json').exists()):\n        from ares_campaign_v3 import target_media_recovery as recovery\n        runner=sys.modules[__name__]\n        value=(recovery.recover if a.command=='recover-media' else recovery.finalize)(a.input,runner,a.approved_digest,a.approval_message_id)\n        print(json.dumps(value,ensure_ascii=False,indent=2));return\n    # One foreground/request owner across preparation and engine invocation.")
# Imported finalize callers must also go through receipt gates, never legacy IDs.
s=s.replace("def finalize(path):\n    q=load(path)","def finalize(path,approved_digest=None,approval_message_id=None):\n    if (Path(path).parent/'media-recovery'/'verified.json').exists():\n        from ares_campaign_v3 import target_media_recovery as recovery\n        return recovery.finalize(path,sys.modules[__name__],approved_digest,approval_message_id)\n    q=load(path)")
(M/'ares-eggbev-target-clone.py').write_text(s)
p=M/'target_media_recovery.py'
s=p.read_text();part=(M/'finalize-part.py').read_text()
if '\ndef assignments_for(' not in s:p.write_text(s+part)
print('staged runner and recovery module')

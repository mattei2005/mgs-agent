"""Backup and isolated staging only; no runtime or campaign writes."""
import hashlib,json,shutil,os
from pathlib import Path
B=Path('/root/mgs-agent');W=B/'work/t_8426333c'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert not (W/'baseline.json').exists()
(W/'backup').mkdir(exist_ok=True)
shutil.copytree(B/'scripts/ares_campaign_v3',W/'stage/ares_campaign_v3',ignore=shutil.ignore_patterns('__pycache__'))
shutil.copy2(B/'scripts/ares_campaign_v3/preview_renderer.py',W/'backup/preview_renderer.py')
prior=json.loads((B/'work/t_8364ae25/baseline-state-hashes.json').read_text())
protected={p:digest(Path(p)) for p in prior}
for p in [B/'data/ares/meta-ads/engine-v3/config.json',B/'runtime/ares-media-qa/bin/python',Path('/root/.cache/ms-playwright/chromium-1228/chrome-linux64/chrome')]:protected[str(p)]=digest(p)
base={'package':{p.name:digest(p) for p in (B/'scripts/ares_campaign_v3').glob('*.py')},'protected':protected,'profile_home':os.environ.get('HERMES_HOME'),'tmpdir':os.environ.get('TMPDIR')}
(W/'baseline.json').write_text(json.dumps(base,indent=2)+'\n')
print(json.dumps({'backup_created':True,'stage_created':True,'package_files':len(base['package']),'protected_files':len(protected)}))

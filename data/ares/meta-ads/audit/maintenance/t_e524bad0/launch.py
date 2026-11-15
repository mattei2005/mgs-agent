"""Launch offline tests with immutable production, isolated state, zero network."""
import os,sys,json,subprocess,shutil
from pathlib import Path
H=Path(__file__).parent;R=Path('/root/mgs-agent');stage=H/'staged'
label=sys.argv[1];flavor=sys.argv[2];names=sys.argv[3:]
box=Path('/root/.hermes/profiles/ares/cache/scratch')/('cross-box-'+label);box.mkdir(exist_ok=True)
args=['bwrap','--ro-bind','/','/','--bind',str(H),str(H),'--bind','/root/.hermes/profiles/ares/cache/scratch','/root/.hermes/profiles/ares/cache/scratch','--bind',str(box),'/root/.hermes/profiles/zeus/cache/scratch','--bind',str(box),'/tmp','--unshare-net','--setenv','PYTHONDONTWRITEBYTECODE','1','--setenv','TMPDIR',str(box)]
for relative in ['data/ares/meta-ads/engine-v3/state','data/ares/meta-ads/state/eggbev-creation']:
 target=R/relative;shadow=box/relative
 if target.exists():
  shutil.copytree(target,shadow,dirs_exist_ok=True)
  args+=['--bind',str(shadow),str(target)]
if flavor=='staged':
 for part in ['scripts','tests']:args+=['--ro-bind',str(stage/part),str(R/part)]
 for p in (stage/'data').rglob('*.json'):
  target=R/p.relative_to(stage)
  if target.exists():args+=['--ro-bind',str(p),str(target)]
else:
 # The new test exists only in staged before installation; mount test file, not runtime.
 args+=['--ro-bind',str(stage/'tests'),str(R/'tests')]
args+=['--',sys.executable,str(H/'run_suites.py'),label,*names]
p=subprocess.run(args,check=False);sys.exit(p.returncode)

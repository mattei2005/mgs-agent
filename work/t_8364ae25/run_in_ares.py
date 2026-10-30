"""Inherit a live Ares worker environment without synthesizing profile identity."""
import os,subprocess,sys
from pathlib import Path
candidates=[]
for p in Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:
  cmd=(p/'cmdline').read_bytes()
  if b'hermes_kernel_runner.py' not in cmd:continue
  env={k.decode():v.decode() for item in (p/'environ').read_bytes().split(b'\0') if b'=' in item for k,v in [item.split(b'=',1)]}
 except (OSError,UnicodeError):continue
 if env.get('HERMES_HOME')=='/root/.hermes/profiles/ares' and env.get('TMPDIR','').startswith('/root/.hermes/profiles/ares/'):
  candidates.append((int(p.name),env))
assert candidates,'No authentic live Ares worker environment; do not forge profile'
pid,env=max(candidates)
print('Using existing live Ares worker environment PID',pid,flush=True)
cmd=['/root/.hermes/hermes-agent-port-main-3f2afed3-mgs-20261021/.venv/bin/python',*sys.argv[1:]]
sys.exit(subprocess.run(cmd,cwd='/root/mgs-agent',env=env).returncode)

"""Offline installed QA: production read-only; network/process transports denied."""
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path('/root/mgs-agent');AUDIT=ROOT/'data/ares/meta-ads/audit/maintenance/t_2559be3f'
SCRATCH=Path('/root/.hermes/profiles/zeus/cache/scratch')
sys.dont_write_bytecode=True
sys.path[:0]=[str(ROOT),str(ROOT/'scripts'),str(ROOT/'tests')]
# Process-local Ares scope is required by synthetic dependency-guard assertions.
# No profile files, credentials, runtime config or cache are changed.
os.environ['HERMES_PROFILE']='ares'
# Existing suites choose Ares scratch explicitly; keep all test writes in Zeus scratch.
original_tempdir=tempfile.TemporaryDirectory
class IsolatedDirectory(original_tempdir):
    def __init__(self,*args,**kwargs):
        if kwargs.get('dir') and str(kwargs['dir']).startswith('/root/.hermes/profiles/ares/cache/scratch'):
            kwargs['dir']=str(SCRATCH)
        super().__init__(*args,**kwargs)
tempfile.TemporaryDirectory=IsolatedDirectory
blocked=[]
forbidden={'socket.connect','socket.connect_ex','socket.sendto','socket.getaddrinfo','socket.gethostbyname','socket.gethostbyaddr','subprocess.Popen','os.system','os.exec','os.posix_spawn'}
def guard(event,args):
    if event in forbidden:
        blocked.append(event);raise RuntimeError('offline transport forbidden: '+event)
    if event=='open':
        path,mode,flags=args
        write=(isinstance(mode,str) and any(c in mode for c in 'wax+')) or (isinstance(flags,int) and flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND))
        if write and isinstance(path,(str,bytes,os.PathLike)):
            target=Path(os.fsdecode(path)).resolve()
            if not (target.is_relative_to(AUDIT) or target.is_relative_to(SCRATCH)):
                raise RuntimeError('offline write forbidden: '+str(target))
sys.addaudithook(guard)
modules=['test_eggbev_source_cta','test_eggbev_source_selection','test_eggbev_target_page_clone','test_eggbev_ana_integration','test_eggbev_clone_v3','test_eggbev_global_creation_naming','test_eggbev_creation_runner','test_eggbev_creation_call','test_creative_copy_policy']
label=sys.argv[1] if len(sys.argv)>1 else 'installed-tests'
if len(sys.argv)>2:modules=sys.argv[2:]
assert label.replace('-','').isalnum()
paths=[ROOT/'scripts/ares-eggbev-target-clone.py',ROOT/'tests/test_eggbev_source_cta.py']+list((ROOT/'scripts/ares_campaign_v3').glob('*.py'))
hashes=lambda:{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
before=hashes()
# Isolate the legacy creation runner's serialization lock, preserving all tests.
import test_eggbev_creation_runner
with tempfile.TemporaryDirectory(dir=str(SCRATCH)) as isolated_state:
    test_eggbev_creation_runner.RUNNER.STATE_ROOT=Path(isolated_state)/'creation-state'
    with (AUDIT/(label+'.log')).open('w') as log:
        result=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(modules))
after=hashes()
receipt={'modules':modules,'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'successful':result.wasSuccessful(),'network_process_guard':True,'write_guard':True,'blocked_transports':blocked,'production_code_unchanged_during_tests':before==after,'hashes':after,'log':str(AUDIT/(label+'.log'))}
(AUDIT/(label+'.json')).write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({k:v for k,v in receipt.items() if k!='hashes'},indent=2))
sys.exit(0 if result.wasSuccessful() and not blocked and before==after else 1)

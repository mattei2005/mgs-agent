#!/usr/bin/env python3
"""Native per-file runner with isolated, canonical MGS scratch."""
import importlib.util,os,pathlib,sys,tempfile
repo=pathlib.Path(sys.argv.pop(1)).resolve(strict=True)
script=repo/'scripts/run_tests_parallel.py'
if not script.is_file():raise SystemExit('Native runner missing')
base=pathlib.Path('/root/.hermes/profiles/zeus/cache/scratch');base.mkdir(parents=True,exist_ok=True)
work=pathlib.Path(tempfile.mkdtemp(prefix='native-tests-',dir=base))
for name in ['home','tmp','runtime']:(work/name).mkdir(mode=0o700)
# Match the native shell's credential/routing isolation before collection imports.
keep={k:v for k,v in os.environ.items() if k in {'PATH','LANG','LC_ALL','TZ','PYTHONHASHSEED','HERMES_TEST_WORKERS','HERMES_TEST_FILE_TIMEOUT','HERMES_TEST_FILE_RETRIES','HERMES_TEST_FAIL_ON_SKIP'}}
os.environ.clear();os.environ.update(keep);os.environ.update(HOME=str(work/'home'),TMPDIR=str(work/'tmp'),TMP=str(work/'tmp'),TEMP=str(work/'tmp'),HERMES_RUNTIME_DIR=str(work/'runtime'),HERMES_PYTHON=sys.executable,LANG='C.UTF-8',TZ='UTC',PYTHONHASHSEED='0')
spec=importlib.util.spec_from_file_location('mgs_native_runner',script)
assert spec is not None and spec.loader is not None
module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
setattr(module,'_runner_scratch_root',lambda:str(work/'tmp'))
sys.exit(getattr(module,'main')())

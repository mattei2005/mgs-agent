#!/usr/bin/env python3
"""Pure, non-lifecycle preflight for the owner-confirmed Hostinger operation."""
import importlib.util,pathlib,os,json,sys,stat
spec=importlib.util.spec_from_file_location('mgs_reboot_common',pathlib.Path(__file__).with_name('vps-maint-1574252891898908684-common.py'));c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
def check_preflight(installed=True,require_git=False):
 p=c.load(c.B/'prestate.json');checks={}
 checks['owner_confirmation']=p['authorization_message_id']==c.AUTH
 checks['same_boot']=pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip()==p['boot_id']
 checks['same_kernel']=os.uname().release==p['current_kernel']
 checks['launcher_unchanged']=str(pathlib.Path('/root/.local/bin/hermes').resolve())==p['hermes_launcher']
 checks['runtime_head_unchanged']=c.run(['git','-C',p['hermes_runtime'],'rev-parse','HEAD']).stdout.strip()==p['hermes_local_head']
 checks['exact_expected_packages']=all(c.run(['dpkg-query','-W','-f=${Version}',k]).stdout.strip()==v for k,v in p['expected_packages'].items())
 checks['configuration_and_boot_artifacts_frozen']=all(c.sha(path)==digest for path,digest in p['protected_file_hashes'].items())
 for name,old in p['units'].items():
  d=c.unit(name);checks[name+'_active']=d['ActiveState']=='active' and int(d['MainPID'])>0
  if name.endswith('-gateway'):checks[name+'_pid_unchanged']=d['MainPID']==old['MainPID']
 checks['dpkg_clean']=not c.run(['dpkg','--audit']).stdout.strip();checks['holds_zero']=not c.run(['apt-mark','showhold']).stdout.strip();checks['failed_units_zero']=not c.run(['systemctl','--failed','--no-legend','--no-pager']).stdout.strip()
 for name,args in [('upgrade',['apt-get','-s','upgrade']),('full_upgrade',['apt-get','-s','dist-upgrade'])]:
  text=c.run(args).stdout;checks[name+'_zero_candidates']=not any(l.startswith(('Inst ','Remv ')) for l in text.splitlines())
 s=pathlib.Path('/tmp').stat();checks['tmp_mode_owner']=s.st_uid==s.st_gid==0 and stat.S_IMODE(s.st_mode)==0o1777
 checks['rollback_hashes']=all(c.run(['sha256sum','-c',m]).returncode==0 for m in p['rollback_manifests'])
 if installed:
  for u in [c.VALIDATOR,c.CLOSURE]:
   d=c.unit(u);checks[u+'_enabled_inactive']=d['LoadState']=='loaded' and d['UnitFileState']=='enabled' and d['ActiveState']=='inactive' and d['MainPID']=='0'
  checks['dispatch_hashes']=c.run(['sha256sum','-c',c.B/'dispatch.sha256']).returncode==0
 if require_git:
  paths=p['owned_public_paths'];checks['scoped_git_clean']=not c.run(['git','-C',c.ROOT,'status','--porcelain','--']+paths).stdout.strip()
  checks['git_heads_equal']=c.run(['git','-C',c.ROOT,'rev-parse','HEAD']).stdout.strip()==c.run(['git','-C',c.ROOT,'rev-parse','origin/main']).stdout.strip()
 result={'at':c.now(),'overall':all(checks.values()),'checks':checks};c.atomic(c.B/'pure-preflight-result.json',result)
 if not result['overall']:raise RuntimeError('preflight failed: '+','.join(k for k,v in checks.items() if not v))
 return result
if __name__=='__main__':
 result=check_preflight(installed='--preparing' not in sys.argv,require_git='--require-git' in sys.argv);print(json.dumps({'overall':result['overall'],'checks_passed':sum(result['checks'].values())}))

"""Resume isolated preparation after HBA's expected fail-closed denial.
Connect as the existing DB admin only in the isolated database, and execute all
queries under the existing mgsfinance role. No HBA/grant/auth configuration edits.
"""
import runpy,pathlib,json,hashlib,shlex
x=runpy.run_path(str(pathlib.Path(__file__).with_name('ui-periods.py')));globals().update({k:v for k,v in x.items() if not k.startswith('__')})
f='deploy/register-periods.mjs';content=(ROOT/f).read_bytes();code='import pathlib,sys;p=pathlib.Path('+repr(STAGE+'/'+f)+');p.write_bytes(sys.stdin.buffer.read())';ssh('sudo -n -u mgsfinance python3 -c '+shlex.quote(code),content)
iso='/var/tmp/mgs-finance-periods-'+AUTH
code='import shutil,pathlib,os,pwd;src='+repr(STAGE)+';dst='+repr(iso)+';shutil.copytree(src,dst,symlinks=False) if not pathlib.Path(dst).exists() else shutil.copy2(src+"/deploy/register-periods.mjs",dst+"/deploy/register-periods.mjs");shutil.copy2('+repr(NODE)+',dst+"/node");u=pwd.getpwnam("mgs_pg");[(os.chown(p,u.pw_uid,u.pw_gid)) for p in [pathlib.Path(dst),*pathlib.Path(dst).rglob("*")]];os.chmod(dst,0o700)'
ssh('sudo -n python3 -c '+shlex.quote(code),timeout=180)
current=ssh(pg+'-d '+DB+' -c '+shlex.quote("SELECT count(*) FROM scenarios WHERE id LIKE 'workspace-%'; SELECT count(*) FROM scenarios WHERE id='TEST-periods-1546184035921829938';")).strip().splitlines();assert current==['17','0'];print('Isolated readback: 17 months already registered; no test row to duplicate',flush=True)
result=runseed(iso,DB,True);assert result['pass'] and result['isolated_crud'] and len(result['periods'])==17 and result['accounts']==78
backup={name:hashlib.sha256((STATE/name).read_bytes()).hexdigest() for name in ['code-before.tar.gz','finance-before.dump']}
for name,h in backup.items():assert ssh('sha256sum '+BACKUP+'/'+name).split()[0]==h
baseline=ssh(pg+'-d mgs_finance -c '+shlex.quote(check)).strip();assert ssh(pg+'-d '+DB+' -c '+shlex.quote(check)).strip()==baseline
(STATE/'pg-periods-evidence.json').write_text(json.dumps(result,indent=2));(STATE/'prepared.json').write_text(json.dumps({'pass':True,'files':local,'expected':expected,'backup_hashes':backup,'baseline':baseline,'stage':STAGE,'isolated_database':DB},indent=2));print(json.dumps({'prepared':True,'isolated_pg_months':17,'accounts':78,'app_role_verified':True,'hba_changes':0,'production_test_writes':0}),flush=True)

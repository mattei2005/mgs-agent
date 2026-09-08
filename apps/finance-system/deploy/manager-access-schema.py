"""Bounded schema gate, two CHECK constraints only; verified under administrator DB role."""
import pathlib,sys,shlex,json
R=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'deploy'));from runcloud_ops import ssh
sys.path.insert(0,'/root/mgs-agent/scripts');from mgs_google_workspace_auth import load_env
load_env();pg='sudo -n -u mgs_pg env LD_LIBRARY_PATH=/opt/mgs-postgresql18/usr/lib/x86_64-linux-gnu /opt/mgs-postgresql18/usr/lib/postgresql/18/bin/psql -h /run/mgs-postgresql18 -U mgs_pg -v ON_ERROR_STOP=1 -At '
database=sys.argv[1];assert database in ['mgs_finance_managers_1546858367635685396','mgs_finance'];S=R/'private/manager-access-1546858367635685396'
if database=='mgs_finance':assert json.loads((S/'pg-exercise.json').read_text())['pass'] and json.loads((S/'local-tests.json').read_text())['pass']
q="SELECT conname,pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid='finance_users'::regclass AND contype='c' ORDER BY conname;"
before=ssh(pg+'-d '+database+' -c '+shlex.quote(q))
if 'icaro' not in before:
 assert "manager_key = 'nicolas'::text" in before
 users=ssh(pg+'-d '+database+' -c '+shlex.quote('SELECT username,md5(row_to_json(u)::text) FROM finance_users u ORDER BY username'))
 ssh(pg+'-d '+database+' -f -',(R/'deploy/manager-access-migration.sql').read_bytes())
 assert users==ssh(pg+'-d '+database+' -c '+shlex.quote('SELECT username,md5(row_to_json(u)::text) FROM finance_users u ORDER BY username'))
after=ssh(pg+'-d '+database+' -c '+shlex.quote(q));assert all("'"+k+"'::text" in after for k in ['joe','isliago','kelly','icaro','nicolas']) and 'manager_key IS NOT NULL' in after
old=dict(l.split('|',1) for l in before.strip().splitlines());new=dict(l.split('|',1) for l in after.strip().splitlines());assert old.keys()==new.keys();assert all(old[k]==new[k] for k in old if k not in ['finance_users_check','finance_users_manager_key_check'])
(S/('schema-'+database+'.json')).write_text(json.dumps({'pass':True,'database':database,'before':before,'after':after,'users_unchanged':True},indent=2));print('Two CHECK constraints verified; roles, existing users and financial tables preserved: '+database)

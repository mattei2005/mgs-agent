import sys,json,shlex,subprocess,sqlite3,os
from pathlib import Path
sys.path.insert(0,'/root/mgs-agent/scripts')
from mgs_google_workspace_auth import load_env
load_env()
sys.path.insert(0,'/root/mgs-agent/apps/finance-system/deploy')
from runcloud_ops import ssh,op
PG='env LD_LIBRARY_PATH=/opt/mgs-postgresql18/usr/lib/x86_64-linux-gnu /opt/mgs-postgresql18/usr/lib/postgresql/18/bin/'
def sql(q):
 return ssh('sudo -u mgs_pg '+PG+'psql -X -v ON_ERROR_STOP=1 -h /run/mgs-postgresql18 -d mgs_finance -At -c '+shlex.quote(q))
if __name__=='__main__':
 print(sql("SELECT json_build_object('users',(SELECT json_agg(x) FROM (SELECT username,display_name,role,manager_key,enabled,revision FROM finance_users ORDER BY username)x),'mfa',(SELECT json_agg(x) FROM (SELECT username,status FROM auth_mfa ORDER BY username)x),'sessions',(SELECT count(*) FROM auth_sessions WHERE NOT revoked),'trusted',(SELECT count(*) FROM auth_trusted_devices WHERE NOT revoked),'finance',(SELECT json_agg(x) FROM (SELECT id,revision FROM scenarios WHERE id IN ('workspace-2026-08','master-ad-accounts'))x))"))
 print('VAULT_ITEMS',json.dumps([{'id':x['id'],'title':x['title']} for x in op(['item','list','--format','json']) if 'MGS Finance' in x.get('title','')],ensure_ascii=False))
 print('REMOTE_SERVICES',ssh('systemctl is-active mgs-finance-dash mgs-postgresql18 mgs-finance-dash.socket'))
 secure=Path('/root/.hermes/profiles/zeus/secure-backups/finance-security-1551287899746598946');secure.mkdir(parents=True,exist_ok=True,mode=0o700);secure.chmod(0o700)
 out=secure/'state-before.db'
 if not out.exists():
  src=sqlite3.connect('file:/root/.hermes/profiles/zeus/state.db?mode=ro',uri=True);dest=sqlite3.connect(out);src.backup(dest);dest.close();src.close();out.chmod(0o600)
 db=sqlite3.connect('file:'+str(out)+'?mode=ro',uri=True)
 print('SESSION_BACKUP',db.execute('PRAGMA quick_check').fetchone()[0]);print('SESSION_COLUMNS',[r[1] for r in db.execute('pragma table_info(sessions)')]);print('MESSAGE_COUNT',db.execute('select count(*) from messages where session_id=?',('20260920_125643_eea54d90',)).fetchone()[0]);db.close()
 index=secure/'sessions-before.json'
 if not index.exists():index.write_bytes(Path('/root/.hermes/profiles/zeus/sessions/sessions.json').read_bytes());index.chmod(0o600)

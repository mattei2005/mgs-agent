"""Monthly-tab-only historical presentation: one atomic JS replacement, no data/OS/service changes."""
import sys,pathlib,json,shlex,hashlib,fcntl
R=pathlib.Path(__file__).resolve().parents[1];D=R/'private/manual-quotes-1546975305216827412';sys.path.insert(0,str(R/'deploy'));from runcloud_ops import ssh
sys.path.insert(0,'/root/mgs-agent/scripts');from mgs_google_workspace_auth import load_env
load_env();T='/home/mgsfinance/releases/pg-auth-1545934831664242748';F='public/history-dashboard.js';B='/home/zeus/mgs-finance-backups/1546975305216827412/monthly-source';assert json.loads((D/'monthly-stage.json').read_text())['pass'];assert not (D/'monthly-published.json').exists()
PG='sudo -n -u mgs_pg env LD_LIBRARY_PATH=/opt/mgs-postgresql18/usr/lib/x86_64-linux-gnu /opt/mgs-postgresql18/usr/lib/postgresql/18/bin/psql -h /run/mgs-postgresql18 -U mgs_pg -v ON_ERROR_STOP=1 -At -d mgs_finance -c '
CHECK="SELECT id,revision,md5(result::text),md5(overrides::text),md5(additions::text) FROM scenarios ORDER BY id; SELECT period,book,md5(payload::text) FROM finance_history ORDER BY period,book; SELECT md5(coalesce(jsonb_agg(x ORDER BY id)::text,'')) FROM finance_ledger x; SELECT md5(coalesce(jsonb_agg(x ORDER BY username)::text,'')) FROM finance_users x;"
local=(R/F).read_bytes();expected=hashlib.sha256(local).hexdigest()
with (R/'private/quote-sync.lock').open('a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX);before=ssh(PG+shlex.quote(CHECK));old=ssh('sudo -n python3 -c '+shlex.quote('import pathlib;print(pathlib.Path('+repr(T+'/'+F)+').read_text(),end="")')).encode();(D/'history-dashboard.js.before').write_bytes(old);old_hash=hashlib.sha256(old).hexdigest()
 code='import pathlib,hashlib,os,shutil,sys;p=pathlib.Path('+repr(T+'/'+F)+');b=pathlib.Path('+repr(B)+');assert not b.exists();b.mkdir(mode=0o700);assert hashlib.sha256(p.read_bytes()).hexdigest()=='+repr(old_hash)+';shutil.copy2(p,b/p.name);v=sys.stdin.buffer.read();assert hashlib.sha256(v).hexdigest()=='+repr(expected)+';q=p.with_suffix(".monthly-source-pending");q.write_bytes(v);q.chmod(0o600);os.replace(q,p);assert hashlib.sha256(p.read_bytes()).hexdigest()=='+repr(expected)+';print("verified")'
 # Backup in zeus-owned directory, code replacement as root preserves original application uid/gid.
 code=code.replace('q.chmod(0o600);os.replace(q,p);','st=p.stat();os.chown(q,st.st_uid,st.st_gid);q.chmod(0o600);os.replace(q,p);')
 assert ssh('sudo -n python3 -c '+shlex.quote(code),local).strip()=='verified';after=ssh(PG+shlex.quote(CHECK));assert before==after
 remote=ssh('sudo -n sha256sum '+T+'/'+F).split()[0];assert remote==expected;assert ssh('sudo -n sha256sum '+B+'/history-dashboard.js').split()[0]==old_hash
out={'pass':True,'files':{F:expected},'backup':B+'/history-dashboard.js','backup_sha256':old_hash,'data_unchanged':True,'services_restarted':False,'historical_source':'frozen own-month tabs, not Caixa','live_source_differences_preserved':['2026-03','2026-05']};(D/'monthly-published.json').write_text(json.dumps(out));print(json.dumps(out))

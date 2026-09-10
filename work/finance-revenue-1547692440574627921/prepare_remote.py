import sys,json,hashlib,shlex,pathlib
sys.path.insert(0,'/root/mgs-agent/scripts');from mgs_google_workspace_auth import load_env
load_env();sys.path.insert(0,'/root/mgs-agent/apps/finance-system/deploy');from runcloud_ops import ssh
AUTH='1547692440574627921';ROOT=pathlib.Path('/root/mgs-agent/work/finance-revenue-'+AUTH);STAGE='/home/mgsfinance/imports/'+AUTH;BACKUP='/home/zeus/mgs-finance-backups/'+AUTH;DB='mgs_finance_gam_'+AUTH
BIN='/opt/mgs-postgresql18/usr/lib/postgresql/18/bin';ENV='env LD_LIBRARY_PATH=/opt/mgs-postgresql18/usr/lib/x86_64-linux-gnu ';PG='sudo -n -u mgs_pg '+ENV+BIN+'/';SOCK='/run/mgs-postgresql18'
plan=ROOT/'import-plan.json';runner=ROOT/'apply_revenue.mjs';assert plan.exists() and runner.exists()
# Resume only the exact partial staging directories from this request; never reuse another path.
ssh('if ! sudo -n -u mgsfinance test -e '+shlex.quote(STAGE)+'; then sudo -n -u mgsfinance mkdir -p '+shlex.quote(STAGE)+' && sudo -n -u mgsfinance chmod 700 '+shlex.quote(STAGE)+'; fi; if ! test -e '+shlex.quote(BACKUP)+'; then sudo -n mkdir -p '+shlex.quote(BACKUP)+' && sudo -n chown zeus:zeus '+shlex.quote(BACKUP)+' && chmod 700 '+shlex.quote(BACKUP)+'; fi; sudo -n -u mgsfinance test -d '+shlex.quote(STAGE)+' && test -d '+shlex.quote(BACKUP)+" && test \"$(sudo -n stat -c %U:%G:%a "+shlex.quote(STAGE)+')\" = mgsfinance:mgsfinance:700 && test "$(stat -c %U:%G:%a '+shlex.quote(BACKUP)+')" = zeus:zeus:700')
for src,name in [(plan,'import-plan.json'),(runner,'apply_revenue.mjs')]:
 dst=STAGE+'/'+name;data=src.read_bytes();expected=hashlib.sha256(data).hexdigest();remote=ssh('if sudo -n -u mgsfinance test -f '+shlex.quote(dst)+'; then sudo -n -u mgsfinance sha256sum '+shlex.quote(dst)+'; fi').strip()
 if remote:assert remote.split()[0]==expected
 else:ssh('sudo -n -u mgsfinance tee '+shlex.quote(dst)+' >/dev/null',data);ssh('sudo -n -u mgsfinance chmod 600 '+shlex.quote(dst));assert ssh('sudo -n -u mgsfinance sha256sum '+shlex.quote(dst)).split()[0]==expected
# Current row and a full consistent database backup before any write.
q="SELECT json_build_object('revision',revision,'state',state,'additions',jsonb_array_length(additions),'gross_1_9',(SELECT coalesce(sum(nullif(x->>'gross','')::numeric),0) FROM jsonb_array_elements(result->'domain'->'facts') x WHERE x->>'date' BETWEEN '2026-09-01' AND '2026-09-09')) FROM scenarios WHERE id='workspace-2026-09';"
before=json.loads(ssh(PG+'psql -h '+SOCK+' -U mgs_pg -d mgs_finance -At -c '+shlex.quote(q)).strip());assert before['state']=='draft' and float(before['gross_1_9'])==0
scenario=BACKUP+'/workspace-2026-09-before.json';dump=BACKUP+'/mgs_finance-before.dump'
if not ssh('test -f '+shlex.quote(scenario)+' && test -f '+shlex.quote(dump)+' && echo yes').strip():
 ssh(PG+'psql -h '+SOCK+' -U mgs_pg -d mgs_finance -At -c '+shlex.quote("SELECT row_to_json(s)::text FROM scenarios s WHERE id='workspace-2026-09'")+' > '+shlex.quote(scenario)+' && chmod 600 '+shlex.quote(scenario))
 ssh(PG+'pg_dump -h '+SOCK+' -U mgs_pg -Fc mgs_finance > '+shlex.quote(dump)+' && chmod 600 '+shlex.quote(dump),timeout=300)
backup_revision=int(ssh('python3 -c '+shlex.quote("import json;print(json.load(open("+repr(scenario)+"))['revision'])")).strip())
ssh(ENV+BIN+'/pg_restore --list '+shlex.quote(dump)+' >/dev/null')
# Restore the exact pre-write database into a fresh isolated rehearsal target.
exists=ssh(PG+'psql -h '+SOCK+' -U mgs_pg -d postgres -At -c '+shlex.quote("SELECT 1 FROM pg_database WHERE datname='"+DB+"'")).strip();assert not exists
ssh(PG+'createdb -h '+SOCK+' -U mgs_pg '+DB)
ssh(PG+'pg_restore -h '+SOCK+' -U mgs_pg -d '+DB+' < '+shlex.quote(dump),timeout=300)
counts=ssh(PG+'psql -h '+SOCK+' -U mgs_pg -d '+DB+' -At -F "|" -c '+shlex.quote("SELECT (SELECT count(*) FROM scenarios),(SELECT count(*) FROM source_cells),(SELECT revision FROM scenarios WHERE id='workspace-2026-09')")).strip().split('|');assert counts[1]=='85868' and int(counts[2])==backup_revision
files={}
for p in [scenario,dump,STAGE+'/import-plan.json',STAGE+'/apply_revenue.mjs']:
 prefix='sudo -n -u mgsfinance ' if p.startswith(STAGE) else ''
 files[p]=dict(sha256=ssh(prefix+'sha256sum '+shlex.quote(p)).split()[0],size=int(ssh(prefix+'stat -c %s '+shlex.quote(p)).strip()))
out={'pass':True,'authorization':AUTH,'stage':STAGE,'backup':BACKUP,'isolated_database':DB,'before':before,'counts':{'scenarios':int(counts[0]),'source_cells':int(counts[1]),'revision':int(counts[2])},'files':files,'production_financial_writes':0,'services':ssh('systemctl is-active mgs-postgresql18 mgs-finance-dash mgs-finance-dash.socket').split()};assert out['services']==['active']*3
(ROOT/'remote-prepared.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'pass':True,'before':before,'backup_dump_sha256':files[dump]['sha256'],'isolated_database':DB,'source_cells':counts[1],'services':out['services']}))

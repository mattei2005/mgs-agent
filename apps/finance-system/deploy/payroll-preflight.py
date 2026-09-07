"""Read-only deployment preflight; no gateway operation."""
import sys,pathlib,json,hashlib,shlex
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'deploy'));from runcloud_ops import ssh
sys.path.insert(0,'/root/mgs-agent/scripts');from mgs_google_workspace_auth import load_env
load_env()
STATE=ROOT/'private/payroll-1546380179654451281';STATE.mkdir(mode=0o700,exist_ok=True)
TARGET='/home/mgsfinance/releases/pg-auth-1545934831664242748'
FILES=['expenses.py','worker.py','workspace.mjs','public/app.js']
manifest=json.loads((ROOT/'private/ui-redesign-1546005809845243944/deploy-evidence.json').read_text())
code='import pathlib,hashlib,json;p=pathlib.Path('+repr(TARGET)+');print(json.dumps({f:hashlib.sha256((p/f).read_bytes()).hexdigest() for f in '+repr(FILES)+'}))'
actual=json.loads(ssh('sudo -n -u mgsfinance python3 -c '+shlex.quote(code)))
assert all(actual[f]==manifest['files'][f] for f in FILES),'Concurrent code change requires reconciliation'
(STATE/'expected.json').write_text(json.dumps(actual,indent=2))
for f in FILES:
 data=ssh('sudo -n -u mgsfinance python3 -c '+shlex.quote('import pathlib;print(pathlib.Path('+repr(TARGET+'/'+f)+').read_text(),end="")'))
 dest=STATE/'before'/f;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(data);assert hashlib.sha256(dest.read_bytes()).hexdigest()==actual[f]
pg='sudo -n -u mgs_pg env LD_LIBRARY_PATH=/opt/mgs-postgresql18/usr/lib/x86_64-linux-gnu /opt/mgs-postgresql18/usr/lib/postgresql/18/bin/psql -h /run/mgs-postgresql18 -U mgs_pg -v ON_ERROR_STOP=1 -At -d mgs_finance '
query="SELECT json_build_object('id',id,'revision',revision,'state',state,'personnel',result->'domain'->'cash'->'personnel','custom_reviews',(SELECT count(*) FROM jsonb_array_elements(additions) a WHERE a->>'kind'='expense' AND a->>'checked_on' IS NOT NULL)) FROM scenarios WHERE id LIKE 'workspace-%' ORDER BY id"
rows=[json.loads(x) for x in ssh(pg+'-c '+shlex.quote(query)).splitlines()];assert len(rows)==17 and all(r['state']=='draft' for r in rows)
(STATE/'preflight.json').write_text(json.dumps({'pass':True,'hashes':actual,'periods':rows},indent=2));print(json.dumps({'pass':True,'code_matches_published':True,'periods':len(rows),'custom_review_dates':sum(r['custom_reviews'] for r in rows)}))

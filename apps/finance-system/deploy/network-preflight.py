"""Read-only production snapshot and source comparison for authorized finance changes."""
import pathlib,sys,json,shlex,hashlib,datetime
ROOT=pathlib.Path(__file__).resolve().parents[1];STATE=ROOT/'private/networks-1546579646227943506';STATE.mkdir(mode=0o700,exist_ok=True)
sys.path.insert(0,'/root/mgs-agent/scripts');from mgs_google_workspace_auth import load_env
load_env();sys.path.insert(0,str(ROOT/'deploy'));from runcloud_ops import ssh
TARGET='/home/mgsfinance/releases/pg-auth-1545934831664242748'
files=[p.name for p in ROOT.glob('*.py')]+[p.name for p in ROOT.glob('*.mjs')]+['public/app.js','public/refinements.css']
code='import pathlib,json,hashlib;p=pathlib.Path('+repr(TARGET)+');print(json.dumps({f:hashlib.sha256((p/f).read_bytes()).hexdigest() for f in '+repr(files)+' if (p/f).exists()}))'
remote=json.loads(ssh('sudo -n python3 -c '+shlex.quote(code)));(STATE/'expected.json').write_text(json.dumps(remote,indent=2))
diffs=[f for f,h in remote.items() if hashlib.sha256((ROOT/f).read_bytes()).hexdigest()!=h]
q="SELECT json_build_object('id',id,'revision',revision,'overrides',overrides,'additions',additions,'result',CASE WHEN id='master-ad-accounts' THEN result ELSE jsonb_build_object('segments',result->'domain'->'segments','expenses',result->'domain'->'expenses','managers',result->'domain'->'managers','cash',result->'domain'->'cash') END) FROM scenarios WHERE id LIKE 'workspace-%' OR id='master-ad-accounts' ORDER BY id"
pg='sudo -n -u mgs_pg env LD_LIBRARY_PATH=/opt/mgs-postgresql18/usr/lib/x86_64-linux-gnu /opt/mgs-postgresql18/usr/lib/postgresql/18/bin/psql -h /run/mgs-postgresql18 -U mgs_pg -v ON_ERROR_STOP=1 -At -d mgs_finance -c '
rows=[json.loads(l) for l in ssh(pg+shlex.quote(q)).splitlines()];(STATE/'production-before.json').write_text(json.dumps(rows,ensure_ascii=False))
print(json.dumps({'production_workspaces':sum(r['id'].startswith('workspace-') for r in rows),'accounts':len(next(r for r in rows if r['id']=='master-ad-accounts')['additions']),'source_code_differences':diffs,'expected_files':len(remote)}))

"""Supplement retained gate logs and inspect candidate evidence linkage, without executing application code."""
from typing import Any
import pathlib,json,gzip,os,collections,stat
OUT=pathlib.Path(__file__).parent
if globals().get('__name__')=='__main__'and(OUT/'review-final.sha256').exists():raise SystemExit('SEALED_REFERENCE_AUDIT: read receipts instead of rerunning collectors')
OLD=pathlib.Path('/root/.hermes/secure-backups/storage-local-tests-1571996311308214363');PRIVATE=OLD/'batched';REPO=pathlib.Path('/root/mgs-agent');APP=REPO/'apps/finance-system'
source=(OUT/'batched-references.py').read_text();ns: dict[str, Any] = {'__file__':str(OUT/'batched-references.py')};exec(compile(source[:source.index('# Validate directory boundary')],'reference-engine-only','exec'),ns)
rows=json.load(open(OUT/'reference-matrix-collected.json'));targets=[r['path']for r in rows];lookup={r['path']:r for r in rows};proposed=[r['path']for r in rows if not r['protected']and not r['sources']];assert len(proposed)==3
logs=[];errors=[];hits=[]
for d,ds,fs in os.walk(REPO,followlinks=False,onerror=lambda e:errors.append(dict(path=e.filename,errno=e.errno))):
 if 'PG_VERSION'in fs and'base'in ds and'global'in ds:ds[:]=[];continue
 ds[:]=[x for x in ds if x not in {'.git','node_modules','.venv','venv','__pycache__','site-packages','cache','browser-profiles'}and not pathlib.Path(d,x).is_symlink()and not any(z in str(pathlib.Path(d,x))for z in ['/data/storage-','/work/storage-','/reports/storage-'])]
 for n in fs:
  p=pathlib.Path(d)/n
  if p.suffix not in {'.log','.out','.err','.stderr','.stdout'}or not p.is_file():continue
  logs.append(str(p))
  try:
   r=ns['scan'](str(p))
   for t in set(r['exact']+r['composite']):hits.append(dict(source=str(p),target=t,category='retained_text_log',source_stable=r['source_metadata_stable']))
  except OSError as e:errors.append(dict(path=str(p),errno=e.errno))
with gzip.open(OLD/'supplement-log-hits.json.gz','wt',compresslevel=1)as f:json.dump(hits,f)
added_to_proposed=[r for r in hits if r['target']in proposed]
summary=dict(log_files_scanned=len(logs),references=len(hits),references_to_three_proposed=added_to_proposed,errors=errors,raw_lines_or_payloads_written=False)
(OUT/'supplement-log-review.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary))
print('PROPOSED_REMAINING',[p for p in proposed if not any(r['target']==p for r in added_to_proposed)])
print('LOG_LINK_SUMMARY')
for target in targets:
 group=[h for h in hits if h['target']==target]
 if group:print(json.dumps(dict(target=target,sources=[r['source']for r in group])))

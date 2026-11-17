"""Snapshot the bounded reference corpus, including historical working material without printing content."""
import pathlib,json,gzip,importlib.util,os
R=pathlib.Path('/root/mgs-agent');O=pathlib.Path(__file__).parent;M=json.loads((O/'metadata-summary.json').read_text());P=pathlib.Path(M['own_analysis_excluded'][1]);assert not(P/'consumer-source-index.json.gz').exists();spec=importlib.util.spec_from_file_location('native_source_reader',R/'data/storage-rollback-dumps-1572270579850153987/gate.py');assert spec and spec.loader;g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g);native=g.full_code_inventory();paths=set(native);additional=0
extensions={'.py','.sh','.mjs','.cjs','.js','.ts','.tsx','.md','.json','.jsonl','.html','.yaml','.yml','.toml','.conf','.service','.timer'}
for fs in M['filesystems']:
 for line in gzip.open(fs['ledger'],'rt'):
  r=json.loads(line);p=r['p']
  if r['k']!='file'or r['s']>4*1024**2 or pathlib.PurePosixPath(p).suffix.lower()not in extensions:continue
  if not(p.startswith('/root/mgs-agent/')or p.startswith('/root/.hermes/profiles/')):continue
  if any(x in pathlib.PurePosixPath(p).parts for x in ['.git','node_modules','site-packages','__pycache__','.venv','venv','cache','browser-profiles','sessions','checkpoints']):continue
  if any(x in p for x in ['/data/storage-','/work/storage-','/reports/storage-']):continue
  if p not in paths:paths.add(p);additional+=1
rows=[{'path':p,'native_executable_or_config':p in native,'native_sha256':native.get(p)}for p in sorted(paths)]
with gzip.open(P/'consumer-source-index.json.gz','wt')as f:json.dump(rows,f,separators=(',',':'))
print(json.dumps({'sources_indexed':len(rows),'native_code_config_sources':len(native),'historical_report_work_json_sources_added':additional,'source_contents_not_printed':True}))

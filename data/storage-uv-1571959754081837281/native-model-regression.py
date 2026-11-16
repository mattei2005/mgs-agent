"""Retrospective read-only regression of the omitted native CLI source phase."""
import pathlib,json,gzip,os,collections,subprocess
OUT=pathlib.Path(__file__).parent;PRIVATE=pathlib.Path('/root/.hermes/secure-backups/storage-uv-1571959754081837281');CACHE=pathlib.Path('/root/.cache/uv')
cli=(PRIVATE/'uv-cache-prune-cli.rs').read_text();source=(PRIVATE/'uv-distribution-source-mod.rs').read_text();gate=(OUT/'prune-gate.py').read_text();m=json.load(open(OUT/'prune-manifest.json'));d=json.load(gzip.open(PRIVATE/'classification.json.gz','rt'));rows=[json.loads(x)for x in gzip.open(m['metadata_index'],'rt')];payloads=json.load(gzip.open(m['retained_payload_index'],'rt'))
assert cli.index('uv_distribution::prune')<cli.index('.prune(ci)')and 'revision.rev' in source and 'revision.http' in source
children=collections.defaultdict(list)
for r in rows:
 if r['kind']=='directory':children[str(pathlib.PurePosixPath(r['relative']).parent)].append(r['relative'])
stale=[];unknown=[];pointer_count=0
for r in rows:
 rel=pathlib.PurePosixPath(r['relative'])
 if r['kind']!='file'or not str(rel).startswith('sdists-v9/')or rel.name not in {'revision.rev','revision.http'}:continue
 dirs=children[str(rel.parent)]
 if not dirs:continue
 path=CACHE/str(rel);assert path.exists();h=subprocess.check_output(['sha256sum',str(path)],text=True).split()[0];assert h==payloads[str(path)],'Pointer bytes changed since original freeze';raw=path.read_bytes();matches=[x for x in dirs if pathlib.PurePosixPath(x).name.encode()in raw];pointer_count+=1
 if len(matches)!=1:unknown.append(str(rel));continue
 stale.extend(x for x in dirs if x!=matches[0])
assert not unknown,'Pointer projection incomplete; no future native cleanup may use it'
stale=sorted(set(stale));assert len(stale)==3
refs={target:[path for path in paths if not any(path==str(CACHE/s)or path.startswith(str(CACHE/s)+'/')for s in stale)]for target,paths in d['native_refs'].items()};new_orphans={str(CACHE/'archive-v0'/aid)for aid in d['archive_stats']if not refs.get(str(CACHE/'archive-v0'/aid))}
full=sorted(set(d['outdated_buckets']+[str(CACHE/s)for s in stale]+[str(CACHE/'environments-v2'/pathlib.PurePosixPath(os.path.relpath(x['path'],CACHE/'environments-v2')).parts[0])for x in d['environment_links']]+list(new_orphans)))
extra=set(full)-set(m['targets']);missing=json.load(open(OUT/'postcheck-path-difference.json'))['missing'];observed_roots=[]
for rel in sorted(missing,key=lambda x:(len(pathlib.PurePosixPath(x).parts),x)):
 if not any(rel==p or rel.startswith(p+'/')for p in observed_roots):observed_roots.append(rel)
assert extra=={str(CACHE/r)for r in observed_roots}and len(full)==199 and len(extra)==6
assert 'revision.rev'not in gate and 'uv_distribution'not in gate
result=dict(status='PASS_RETROSPECTIVE_REGRESSION',old_model_would_be_rejected=True,old_model_targets=193,complete_CLI_shadow_targets=199,source_revision_roots_missed=3,newly_orphaned_archives_missed=3,unplanned_root_set_matches_native_observation=True,pointers_verified_unchanged=pointer_count,uninterpreted_pointer_count=0,extra_roots=sorted(extra),native_calls_in_this_test=0,future_native_execution_authorized=False,original_executor_modified=False,limitations='Read-only replay of frozen original metadata and still-identical revision pointers; not another native dry-run or a new destructive approval. Old model remains quarantined.')
(OUT/'native-cli-model-regression.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

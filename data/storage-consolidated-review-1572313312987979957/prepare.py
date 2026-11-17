"""Freeze the single consolidated proposal only after recovery/closure/consumer observations; never delete."""
import pathlib,json,gzip,os,stat,re,subprocess,datetime,importlib.util,hashlib
R=pathlib.Path('/root/mgs-agent');O=pathlib.Path(__file__).parent;M=json.loads((O/'metadata-summary.json').read_text());P=pathlib.Path(M['own_analysis_excluded'][1]);assert not(O/'manifest.json').exists(),'SEALED_MANIFEST_DO_NOT_OVERWRITE';spec=importlib.util.spec_from_file_location('consolidated_gate',O/'gate.py');assert spec and spec.loader;g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
finance=json.loads((P/'closed-candidate-copied-json-selection.json').read_text());media=json.loads((O/'all-media-archive-join.json').read_text())['matches'];stream=[json.loads(x)for x in(O/'all-media-native-remote-readback.jsonl').read_text().splitlines()];expected={}
for r in stream:
 assert r['status']=='PASS'and r['native_resolver_guards_kept']and r['SA']=='mgsagent@mgs-core-prod.iam.gserviceaccount.com';expected[r['source_id']]={'provider_id':r['provider_id'],'stock_file_id':r['stock_file_id'],'size':int(r['hashes']['size']),'md5':r['hashes']['md5'],'sha256':r['hashes']['sha256']}
assert len(expected)==248;targets=[];providers={};owner_ids=set();roots=set()
for r in finance:
 p=r['relative_primary'];providers[p]={'metadata':g.meta(p),'sha256':g.sha(p)};assert providers[p]['sha256']==r['sha256'];targets.append({'path':r['path'],'kind':'copied_finance_JSON','metadata':r['metadata'],'sha256':r['sha256'],'retained_provider':p});match=re.fullmatch(r'(.+)/(?:candidate|stage)/private/.+',r['path']);assert match is not None;root=match.group(1);roots.add(root)
 for c in r['owner_checkpoints']:owner_ids.add(c['id'])
for r in media:
 choices=sorted(r['mapping_candidates'],key=lambda e:(e.get('name')!=pathlib.Path(r['path']).name,e['source_id']));sid=choices[0]['source_id'];assert expected[sid]['sha256']==r['sha256']and expected[sid]['size']==r['metadata']['size'];targets.append({'path':r['path'],'kind':'archived_media','metadata':r['metadata'],'sha256':r['sha256'],'source_id':sid,'all_verified_lineage_ids':[e['source_id']for e in choices]});parts=pathlib.Path(r['path']).parts
 if '/artifacts/meta-library/'in r['path']:root='/'.join(r['path'].split('/')[:8])
 else:root='/'.join(r['path'].split('/')[:7])
 if not pathlib.Path(root).is_dir():root=str(pathlib.Path(root).parent)
 roots.add(root)
paths={r['path']for r in targets};assert len(paths)==643;assert len(providers)==15
# Resolve real Git ownership before the final metadata freeze; never pass profile files to the institutional repository.
tracked=subprocess.check_output(['git','-C',str(R),'ls-files','-z','--',*[r['path']for r in targets if r['path'].startswith(str(R)+'/')]]);assert not tracked,'TRACKED_TARGET_REQUIRES_SEPARATE_NATIVE_VERSIONED_DELETION_GATE'
for r in targets:
 p=pathlib.Path(r['path']);assert p.resolve()==p and not p.is_symlink()and not os.path.ismount(p)and g.meta(p)==r['metadata']and g.sha(p)==r['sha256']and not os.listxattr(p,follow_symlinks=False)
 if not str(p).startswith(str(R)+'/'):
  assert not any((parent/'.git').exists()for parent in p.parents),'PROFILE_FILE_HAS_OWNING_GIT_REPOSITORY'
assert not g.ro.runtime_refs(sorted(paths));roots=sorted(roots);assert all(not a.startswith(b+'/')for a in roots for b in roots if a!=b)
# Capture the complete retained complement under precisely these historical roots.
complement={'directories':{},'files':[]};seen=set()
for root in roots:
 for parent,ds,fs in os.walk(root,followlinks=False,onerror=lambda e:(_ for _ in()).throw(e)):
  complement['directories'][parent]=g.dmeta(parent);keep=[]
  for name in ds:
   p=pathlib.Path(parent)/name
   if p.is_symlink():s=os.lstat(p);complement['files'].append({'path':str(p),'kind':'link','target':os.readlink(p),'dev':s.st_dev,'ino':s.st_ino})
   else:keep.append(name)
  ds[:]=keep
  for name in fs:
   p=pathlib.Path(parent)/name
   if str(p)in paths:continue
   s=os.lstat(p)
   if stat.S_ISLNK(s.st_mode):complement['files'].append({'path':str(p),'kind':'link','target':os.readlink(p),'dev':s.st_dev,'ino':s.st_ino})
   elif stat.S_ISREG(s.st_mode):complement['files'].append({'path':str(p),'kind':'file','metadata':g.meta(p),'sha256':g.sha(p)})
   else:raise RuntimeError('UNCLASSIFIED_SPECIAL_COMPLEMENT_NODE')
comp=P/'frozen-retained-complement.json.gz';assert not comp.exists()
with gzip.open(comp,'wt',compresslevel=6)as f:json.dump(complement,f,separators=(',',':'))
prior=json.loads((R/'data/storage-rollback-dumps-1572270579850153987/manifest.json').read_text());retained={r['path']:{'path':r['path'],'metadata':r['metadata'],'sha256':r['sha256']}for r in prior['retained_reviewed_files']+prior['retained_local_dumps']}
for p,e in providers.items():retained[p]={'path':p,**e}
for r in retained.values():assert g.meta(r['path'])==r['metadata']and g.sha(r['path'])==r['sha256']
cp=json.loads((R/'data/agent-checkpoints.json').read_text())['checkpoints'];owners={c['id']:{k:c.get(k)for k in ['id','state','source']}for c in cp if c.get('id')in owner_ids};assert len(owners)==len(owner_ids)
for c in owners.values():assert re.search(r'completed|conclu[ií]d|published_verified|published_and_verified|publicado.{0,20}validado',c['state'],re.I)and not re.search(r'pendente|pending|not.published|nao.publicado|não.publicado|bloque',c['state'],re.I),'OWNER_NOT_CLOSED'
evidence={str(O/name):g.sha(O/name)for name in ['all-media-native-remote-readback.jsonl','all-media-archive-join.json','candidate-primary-proof.json','consumer-scan-progress-v2.json','reference-unavailability-reconciliation.json']};evidence[str(comp)]=g.sha(comp)
reader_paths=[O/'retained-reader.py',O/'native-remote-preflight.py',g.OLD,R/'scripts/ares_archive_storage.py',R/'scripts/ares_archive_bridge.py',R/'scripts/ares_archive_locations.py',R/'scripts/ares_archive_namespace.py',R/'scripts/ares_archive_readonly_reconciliation.py',R/'scripts/ares_reupload_recovery.py',R/'scripts/ares_archive_backfill.py',R/'scripts/mgs_google_workspace_auth.py']
manifest={'status':'frozen_awaiting_new_exact_critical_confirmation','request_message_id':g.REQUEST,'thread_id':g.THREAD,'targets':sorted(targets,key=lambda r:r['path']),'file_count':643,'directory_count':0,'reclaim_bytes':sum(r['metadata']['blocks']*512 for r in targets),'semantic_target_sha256':hashlib.sha256(g.canonical(sorted((r['path'],r['kind'])for r in targets))).hexdigest(),'gate_sha256':g.sha(O/'gate.py'),'private_root':str(P),'local_providers':providers,'media_expected':expected,'review_roots':roots,'parent_directories':{str(pathlib.Path(p).parent):g.dmeta(pathlib.Path(p).parent)for p in paths},'retained_files':list(retained.values()),'complement_path':str(comp),'owner_checkpoints':owners,'evidence_hashes':evidence,'reader_source_hashes':{str(p):g.sha(p)for p in reader_paths},'runtime':g.ro.health(),'launcher':os.path.realpath('/root/.local/bin/hermes'),'future_retention_or_cron_changes':False,'caches_included':False,'original_historical_records_rewritten':False,'recovery_effect':'Only643 physical local file copies disappear.15 primary local JSON providers and248 native logical/archive/stock mappings remain. Historical helper replay may require first restoring old pathnames from these retained providers; original records/code/state/parent directories are not rewritten or removed. JSON file recovery is actual anonymous-RAM materialization; media proof is native guarded full provider stream, not a database/application restore.','frozen_at':datetime.datetime.now().astimezone().isoformat()}
index,refs,total=g.census(manifest,preparing=True);manifest['known_exact_executable_references']=refs;source_path=P/'frozen-relevant-source-census.json.gz';assert not source_path.exists()
with gzip.open(source_path,'wt',compresslevel=6)as f:json.dump(index,f,separators=(',',':'))
manifest.update(source_census_path=str(source_path),source_census_sha256=g.sha(source_path),source_census_entries=len(index),executable_sources_scanned=total);g.shape(manifest)
# Require quiet target and complement fingerprints after source/Git observations.
for r in targets:assert g.meta(r['path'])==r['metadata']
for r in complement['files']:
 if r['kind']=='file':assert g.meta(r['path'])==r['metadata']
(O/'manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n');digest=subprocess.check_output(['sha256sum',str(O/'manifest.json')],text=True).split()[0];(O/'manifest.sha256').write_text(digest+'  manifest.json\n');print(json.dumps({'manifest_sha256':digest,'gate_sha256':manifest['gate_sha256'],'targets':643,'kinds':{'copied_finance_JSON':339,'archived_media':304},'reclaim_GiB':round(manifest['reclaim_bytes']/1024**3,3),'review_roots':len(roots),'complement_files':len(complement['files']),'complement_directories':len(complement['directories']),'global_retained_files':len(retained),'source_census_entries':len(index),'executable_sources_scanned':total,'known_exact_code_references':len(refs),'source_files_deleted':0}))

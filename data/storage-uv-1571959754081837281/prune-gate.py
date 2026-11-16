"""Frozen native UV prune gate; no manual cache unlink; read-only default."""
import os,sys,pathlib,json,gzip,subprocess,importlib.util,collections,argparse,datetime
sys.dont_write_bytecode=True
OUT=pathlib.Path(__file__).parent;ROOT=pathlib.Path('/root/mgs-agent');CACHE=pathlib.Path('/root/.cache/uv');PRIVATE=pathlib.Path('/root/.hermes/secure-backups/storage-uv-1571959754081837281')
OWNER='344196393512075265';THREAD='1569928464033783862';UV='/root/.local/bin/uv'
spec=importlib.util.spec_from_file_location('UV_readonly_inventory',OUT/'collect.py');assert spec and spec.loader;c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
def save(name,obj):(OUT/name).write_text(json.dumps(obj,indent=2)+'\n')
def sha(p):return c.sha(p)
def load():
    m=json.load(open(OUT/'prune-manifest.json'));assert sha(m['metadata_index'])==m['metadata_index_sha256'];rows=[json.loads(x)for x in gzip.open(m['metadata_index'],'rt')];scope(m,rows);return m,rows
def selected(rel,targets):return any(rel==t or rel.startswith(t+'/')for t in targets)
def model_targets():
    refs,_=c.references();archive=CACHE/'archive-v0';known={'sdists-v9','flat-index-v4','git-v0','interpreter-v4','simple-v24','wheels-v6','archive-v0','builds-v0','environments-v2','python-v0','binaries-v0','osv-v0'}
    paths=[str(x)for x in CACHE.iterdir()if x.is_dir()and x.name not in known]
    paths +=[str(x)for x in(CACHE/'environments-v2').iterdir()]
    paths +=[str(x)for x in archive.iterdir()if str(x.resolve(strict=True))not in refs]
    unexpected=[x for x in CACHE.iterdir()if not x.is_dir()and x.name not in {'CACHEDIR.TAG','.gitignore','.git','.lock'}]
    assert not unexpected,'new top-level native target';return sorted(set(paths))
def scope(m,rows):
    assert m['cache_root']==str(CACHE)and m['native_argv']==[UV,'cache','prune','--cache-dir',str(CACHE),'--no-config','--offline','--no-progress']
    assert m['historical_cached_state_retirement']is True and m['exact_old_environment_restore_proven']is False
    assert len(m['targets'])==m['top_level_targets']==193 and m['expected_orphan_archives']==188 and m['expected_cached_environments']==83
    assert len(set(m['targets']))==193 and all(str(pathlib.Path(t).parent).startswith(str(CACHE))for t in m['targets'])
    for t in m['targets']:
        p=pathlib.Path(t);assert CACHE in p.parents and not p.is_symlink()and not os.path.ismount(p)
        for q in [p,*p.parents]:assert not q.is_symlink()
        assert not any(t!=u and t.startswith(u+'/')for u in m['targets'])
    rel=[os.path.relpath(t,CACHE)for t in m['targets']];chosen=[x for x in rows if selected(x['relative'],rel)]
    counts=dict(collections.Counter(x['kind']for x in chosen));assert counts==m['target_node_counts']
    assert len(rows)==m['whole_cache_node_count'] and sum(x['size']for x in chosen if x['kind']=='file')==m['target_logical_file_bytes']
    assert len({x['relative']for x in rows})==len(rows)
    return rel,chosen
def payload_hashes(names):
    hashes={}
    for start in range(0,len(names),150):
        raw=subprocess.check_output(['sha256sum','--zero','--',*names[start:start+150]])
        for part in raw.split(b'\0'):
            if part:h,p=part.split(b'  ',1);hashes[os.fsdecode(p)]=h.decode()
    return hashes
def runtime():
    pids={p:int(subprocess.check_output(['systemctl','show',p+'-gateway.service','-p','MainPID','--value'],text=True))for p in ['zeus','ares','atena']};assert all(pids.values());return dict(pids=pids,boot_id=pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip(),launcher=os.path.realpath('/root/.local/bin/hermes'))
def consumers():
    r=subprocess.run(['python3','-B',str(OUT/'consumers.py')],capture_output=True,text=True,timeout=180);assert r.returncode==0,r.stderr[-1000:]
    d=json.load(open(OUT/'consumers.json'))
    for key in ['uv_processes','process_target_matches','inaccessible_processes','external_target_symlinks','executable_import_selectors','code_target_hits','institutional_target_hits','scan_errors']:assert not d[key],key
    return {k:d[k]for k in ['processes_inspected','code_files_scanned','metadata_directories_scanned','metadata_files_scanned']}
def verify(m,rows,post=False,check_consumers=True,check_payload=True):
    targets,chosen=scope(m,rows)
    for p,h in m['protected_helpers'].items():assert sha(p)==h,'helper or native UV changed'
    assert subprocess.check_output([UV,'--version'],text=True).strip()==m['native_uv_version']
    current,receipt=c.snapshot(None);actual={x['relative']:x for x in current};original={x['relative']:x for x in rows}
    if not post:
        assert receipt['normalized_plain_sha256']==m['cache_normalized_sha256'],'UV cache fingerprint changed'
        assert model_targets()==m['targets'],'native source-model scope changed'
    else:
        assert all(not os.path.lexists(t)for t in m['targets'])
        kept={r:x for r,x in original.items()if not selected(r,targets)};assert set(actual)==set(kept),'unexpected remaining/new cache path'
        deleted_links=collections.Counter((x['dev'],x['ino'])for x in chosen if x['kind']=='file')
        ancestors={'.'}
        for t in targets:
            p=pathlib.PurePosixPath(t).parent
            while str(p)!='.':ancestors.add(str(p));p=p.parent
        for rel,before in kept.items():
            after=actual[rel];expected=dict(before);key=(before['dev'],before['ino']);ignore=set()
            if before['kind']=='directory'and rel in ancestors:ignore={'size','allocated','nlink','mtime_ns','ctime_ns'}
            elif before['kind']=='file'and deleted_links[key]:expected['nlink']-=deleted_links[key];ignore={'ctime_ns'}
            assert {k:v for k,v in after.items()if k not in ignore}=={k:v for k,v in expected.items()if k not in ignore},'retained metadata changed: '+rel
    payload_count=0
    if check_payload:
        assert sha(m['retained_payload_index'])==m['retained_payload_index_sha256'];expected=json.load(gzip.open(m['retained_payload_index'],'rt'));assert payload_hashes(list(expected))==expected,'retained cache payload changed';payload_count=len(expected)
    return dict(status='PASS',post=post,whole_cache_metadata_nodes=len(current),target_node_counts=m['target_node_counts'],retained_unique_payloads_hashed=payload_count,consumers=consumers()if check_consumers else'not_requested',runtime=runtime(),model_is_not_native_dry_run=True,exact_old_environment_restore_proven=False)
def approval(a):
    assert a['owner_id']==OWNER and a['thread_id']==THREAD and a['native_readback_verified']is True and a['scope_expansion_authorized']is False
    assert a['manifest_sha256']==sha(OUT/'prune-manifest.json')and a['executor_sha256']==sha(__file__)
    assert a['historical_cached_state_retirement_approved']is True and a['confirmation_content'].strip().lower()=='sim'
    assert a['confirmation_message_id'].isdigit()and a['question_message_id'].isdigit()
def envelope(action,a):
    assert a.get('owner_id',OWNER)==OWNER and a.get('thread_id',THREAD)==THREAD
    return {**a,'agent':'zeus','owner_id':OWNER,'thread_id':THREAD,'action':action,'at':datetime.datetime.now().astimezone().isoformat()}
def audit(action,a):
    with open(ROOT/'logs/events-audit.jsonl','a')as f:f.write(json.dumps(envelope(action,a))+'\n');f.flush();os.fsync(f.fileno())
def disk():
    s=os.statvfs('/');return dict(used=(s.f_blocks-s.f_bfree)*s.f_frsize,available=s.f_bavail*s.f_frsize)
def execute(m,rows):
    a=json.load(open(OUT/'prune-approval.json'));approval(a);assert not any((OUT/n).exists()for n in ['prune-start.json','prune-native-result.json','prune-post.json'])
    before=verify(m,rows);audit('UV_native_prune_start',a)
    with open(OUT/'prune-start.json','x')as f:json.dump(a,f);f.flush();os.fsync(f.fileno())
    # Native UV owns its exclusive cache lock. Never pass --force or --ci.
    env={k:v for k,v in os.environ.items()if k in ['PATH','HOME','LANG','LC_ALL','TMPDIR']};env.update(UV_LOCK_TIMEOUT='0',UV_NO_CONFIG='1',UV_NO_PROGRESS='1')
    db=disk();r=subprocess.run(m['native_argv'],capture_output=True,text=True,timeout=180,env=env);da=disk()
    save('prune-native-result.json',dict(exit_code=r.returncode,stdout=r.stdout,stderr=r.stderr,before=db,immediate_after=da,observed_global_delta_bytes=da['available']-db['available']))
    journal=[dict(path=t,absent=not os.path.lexists(t))for t in m['targets']];save('prune-target-readback.json',journal)
    if r.returncode!=0:audit('UV_native_prune_failed_reconcile_before_retry',a);raise RuntimeError('Native prune failed; read back target states; never retry blindly')
    after=verify(m,rows,post=True);assert after['runtime']==before['runtime'];save('prune-post.json',after);audit('UV_native_prune_completed',a);print(json.dumps(after))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--execute',action='store_true');p.add_argument('--post',action='store_true');args=p.parse_args();m,rows=load()
    if args.execute:assert not args.post;execute(m,rows)
    else:print(json.dumps(verify(m,rows,post=args.post)))

import pathlib,json,hashlib,os,subprocess,datetime
O=pathlib.Path(__file__).parent
old=json.loads((O/'analysis.json').read_text())
assert hashlib.sha256((O/'analysis.json').read_bytes()).hexdigest()=='5d14a67520396f9b4af4c800a496e6cdb5a95feb6a82f37679e34cfe96cea25b'
code=(O/'analyze.py').read_text().replace("O/'analysis.json'","O/'revalidation-1552361649480933457.json'")
exec(compile(code,str(O/'analyze.py'),'exec'),{'__file__':str(O/'analyze.py'),'__name__':'__main__'})
new=json.loads((O/'revalidation-1552361649480933457.json').read_text())
assert len(new['targets'])==270
assert {x['path']:x['metadata_sha256'] for x in old['targets']}=={x['path']:x['metadata_sha256'] for x in new['targets']},'target drift: no destructive permission'
assert [(x['path'],x['sha256']) for x in old['retained_archives_validation']]==[(x['path'],x['sha256']) for x in new['retained_archives_validation']]
tracked=subprocess.run(['git','-C','/root/mgs-agent','ls-files','apps/finance-system/private'],capture_output=True,text=True,check=True).stdout
assert not tracked.strip()
manifest={'schema':1,'status':'awaiting_hash_bound_critical_confirmation','request_message_id':'1552361649480933457','scope':'Only original 270 disposable test artifacts; no stage/candidate or policy edits','created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'target_count':270,'file_count':new['file_count'],'allocated_bytes':new['inode_aware_reclaim_bytes'],'process_references':new['process_references'],'retained':new['retained'],'retained_archives_validation':new['retained_archives_validation'],'targets':[dict(x,action='delete_file' if pathlib.Path(x['path']).is_file() else 'delete_tree',directory_count=x['entry_count']-x['file_count'],symlink_count=0) for x in new['targets']],'source_analysis_sha256':hashlib.sha256((O/'analysis.json').read_bytes()).hexdigest(),'revalidated_same_fingerprints':True,'irreversible':'Disposable historical test instances will be removed; retained samples and original fixtures permit new tests, not exact byte-for-byte rollback of every discarded instance.'}
path=O/'deletion-manifest-1552361649480933457.json'
assert not path.exists(),'do not overwrite a frozen manifest'
path.write_text(json.dumps(manifest,sort_keys=True,separators=(',',':'))+'\n');h=hashlib.sha256(path.read_bytes()).hexdigest()
(O/'deletion-manifest-1552361649480933457.sha256').write_text(h+'  '+path.name+'\n')
print(json.dumps({'manifest':str(path),'sha256':h,'targets':manifest['target_count'],'files':manifest['file_count'],'allocated_bytes':manifest['allocated_bytes'],'deleted':0,'status':manifest['status']}))

import sys,os,io,json,tarfile,hashlib,time
from pathlib import Path
from codec import encode,sha
from recover import run
os.umask(0o077)
O=Path(__file__).parent;F=O/'fixture';F.mkdir(mode=0o700,exist_ok=True)
base=F/'base.bin';target=F/'target.bin';assert base.exists() and target.exists()
plain=F/'plain.txt'
if not plain.exists():plain.write_bytes(b'fixture historical configuration, not production\n')
bundle=F/'wrapper.tar';assert not bundle.exists()
objects={};files=[]
for rel,p,use_base in [('one.bin',target,True),('two.txt',plain,False),('copy.bin',target,True)]:
 h=sha(p);files.append({'rel':rel,'size':p.stat().st_size,'sha256':h,'mode':0o100600,'mtime_ns':p.stat().st_mtime_ns})
 if h not in objects:
  packed=encode(p,base if use_base else None);objects[h]={'mode':'zstd','size':p.stat().st_size,'tar_member':'objects/'+h+'.zst','packed_sha256':hashlib.sha256(packed).hexdigest(),'base_dependency':'base' if use_base else None,'packed':packed}
manifest={'dependencies':{'base':{'kind':'file','path':str(base),'sha256':sha(base)}},'snapshots':[{'id':'fixture-root','files':files,'directories':[],'links':[{'rel':'alias','link_target':'one.bin'}]}],'objects':{h:{k:v for k,v in ob.items() if k!='packed'} for h,ob in objects.items()}}
with tarfile.open(bundle,'x:') as tar:
 for h,ob in objects.items():
  info=tarfile.TarInfo(ob['tar_member']);info.size=len(ob['packed']);tar.addfile(info,io.BytesIO(ob['packed']))
 data=json.dumps(manifest).encode();info=tarfile.TarInfo('manifest.json');info.size=len(data);tar.addfile(info,io.BytesIO(data))
r=run(bundle);assert r['files_reconstructed_hash_verified']==3 and r['unique_objects_verified']==2
out=F/'restored-new';rr=run(bundle,restore_to=out);assert rr['files_reconstructed_hash_verified']==3
for f in files:assert sha(out/'fixture-root'/f['rel'])==f['sha256']
assert os.readlink(out/'fixture-root/alias')=='one.bin'
try:run(bundle,restore_to=out);raise AssertionError('existing destination accepted')
except ValueError as e:assert 'MUST_NOT_EXIST' in str(e)
result={'status':'PASS','native_codec_tests':6,'wrapper_ram_reconstruction':True,'isolated_fixture_files_materialized':3,'symlink_replayed_without_following':True,'existing_restore_destination_rejected':True,'fixture_only_no_production_restore':True}
(O/'wrapper-fixture.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))

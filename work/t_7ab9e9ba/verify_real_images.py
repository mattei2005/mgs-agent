"""Verify the exact requested bytes read-only, without reservation or upload."""
import concurrent.futures
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from urllib.request import Request,urlopen
B=Path('/root/mgs-agent');sys.path.insert(0,str(B/'work/t_7ab9e9ba/candidate/scripts'))
from ares_campaign_v3.shein_media_handoff import _ops
from ares_campaign_v3.image_prestage import validate_local_image
r=json.loads((B/'data/ares/meta-ads/audit/shein/campaigns/intake/shein-1565747351543480374/request.json').read_text())
names=[f for g in r['campaign_groups'] for f in g['files']]
inv=[json.loads(line) for line in (B/'data/ares/creative-ops/inventory/assets.jsonl').read_text().splitlines() if line.strip()]
rows={n:[x for x in inv if x.get('canonical_filename')==n] for n in names};assert all(len(x)==1 for x in rows.values())
ops=_ops(B);token,_=ops.drive_runtime_token();directory=Path(os.environ['TMPDIR'])/'shein-img-t_7ab9e9ba';directory.mkdir(parents=True,exist_ok=True)
def check(name):
    row=rows[name][0];f=ops.drive_file_readback(token,row['asset_drive_id'])
    assert f['name']==name and f['parents']==[r['manager_media_folder_id']] and not f.get('trashed')
    assert (f.get('properties') or {}).get('reference_only') not in {True,'true','1'}
    path=directory/name
    if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest()!=row['clean_checksum']:
        with urlopen(Request('https://www.googleapis.com/drive/v3/files/'+f.get('provider_id',f['id'])+'?alt=media&supportsAllDrives=true',headers={'Authorization':'Bearer '+token}),timeout=120) as response:path.write_bytes(response.read())
    raw=path.read_bytes();assert hashlib.sha256(raw).hexdigest()==row['clean_checksum'] and hashlib.md5(raw).hexdigest()==f['md5Checksum']==row['clean_md5'] and len(raw)==int(f['size'])
    validate_local_image(path,row['clean_checksum'])
    result=subprocess.run(['python3',str(B/'scripts/clean-creative-metadata.py'),'verify',str(path)],capture_output=True,text=True,timeout=45)
    assert result.returncode==0 and 'clean: true' in result.stdout
    return {'filename':name,'asset_id':row['asset_id'],'checksum_verified':True,'drive_md5_size_verified':True,'static_format_verified':True,'metadata_clean_verified':True,'reservation_request_id':row.get('reservation_request_id')}
try:
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:proof=list(pool.map(check,names))
    receipt={'request_id':r['request_id'],'verified':len(proof),'images':proof,'writes_meta':0,'writes_drive':0,'inventory_reservations':0,'local_media_directory':str(directory)}
    (B/'work/t_7ab9e9ba/real-image-bytes.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'verified':len(proof),'sha256_md5_size_clean_static':'PASS','meta_drive_writes':0,'inventory_reservations':0}))
except Exception as exc:
    print(json.dumps({'status':'FAILED','error_type':type(exc).__name__,'meta_drive_writes':0}));sys.exit(1)

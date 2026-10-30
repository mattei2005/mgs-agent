"""Account-scoped static image pre-stage. No campaign writer or Drive mutation.

Legacy video registry records remain unchanged. Upload ambiguity is fail-closed:
a durable intent and exact deterministic image name must reconcile before retry.
Signed image URLs and tokens are never persisted.
"""
from __future__ import annotations
import hashlib
import json
import re
from pathlib import Path
import requests
from .media_registry import MediaNotReady
from .prestage import MediaUploadError


def read_account_images(common, token, account_id, *, hashes=None):
    params = {'fields':'hash,name,original_width,original_height,status', 'limit':500}
    if hashes:
        params['hashes'] = json.dumps(sorted(set(hashes)))
    rows=[];seen=set()
    for _ in range(100):
        http, page, _ = common.graph_get('act_'+str(account_id).removeprefix('act_')+'/adimages', token, params)
        if http != 200 or not isinstance(page, dict):
            raise MediaNotReady('exact-account image association readback unavailable')
        rows.extend(page.get('data') or [])
        if not (page.get('paging') or {}).get('next'):
            return rows
        after=(page.get('paging',{}).get('cursors') or {}).get('after')
        if not after or after in seen:
            raise MediaNotReady('exact-account image association pagination incomplete')
        seen.add(after);params['after']=after
    raise MediaNotReady('exact-account image association pagination limit exceeded')


def require_image(rows, image_hash, *, name=None):
    matches=[r for r in rows if r.get('hash') == image_hash]
    if len(matches)!=1:
        raise MediaNotReady('exact-account image hash missing or ambiguous')
    row=matches[0]
    if (not re.fullmatch(r'[a-fA-F0-9]{32}', str(image_hash))
            or (name is not None and row.get('name') != name)
            or int(row.get('original_width') or 0)<=0 or int(row.get('original_height') or 0)<=0
            or str(row.get('status','ACTIVE')).upper() not in {'ACTIVE'}):
        raise MediaNotReady('image name/dimensions/status mismatch')
    return row


def validate_local_image(path, checksum):
    from PIL import Image
    path=Path(path)
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=checksum:
        raise MediaNotReady('image file checksum mismatch')
    ext=path.suffix.lower()
    with Image.open(path) as image:
        if image.format != ('PNG' if ext == '.png' else 'JPEG' if ext in {'.jpg','.jpeg'} else '') or image.width<=0 or image.height<=0:
            raise MediaNotReady('image format/dimensions mismatch')
        if getattr(image, 'n_frames', 1)!=1:
            raise MediaNotReady('static image required; animated images prohibited')
        image.verify()


def image_title(asset_id, checksum, filename):
    name=f'V3 IMAGE {asset_id} {checksum[:12]}{Path(filename).suffix.lower()}'
    if len(name)>100:
        raise ValueError('deterministic image filename exceeds Meta name limit')
    return name


class AdAccountImageUploader:
    def __init__(self, *, common, user_token, account_id, graph_version='v26.0'):
        self.common=common;self.token=user_token
        self.account_id=str(account_id).removeprefix('act_');self.graph_version=graph_version

    def inventory(self, hashes=None):
        return read_account_images(self.common,self.token,self.account_id,hashes=hashes)

    def upload(self, path, name):
        path=Path(path);edge='act_'+self.account_id+'/adimages'
        self.common._enforce_operational_account_scope(edge, {}, 'POST')
        self.common._throttle_before_request()
        try:
            with path.open('rb') as handle:
                response=requests.post('https://graph.facebook.com/'+self.graph_version+'/'+edge,
                    data={'access_token':self.token,'name':name},
                    files={'filename':(name,handle,'image/png' if path.suffix.lower()=='.png' else 'image/jpeg')},timeout=180)
        except (OSError,requests.RequestException) as exc:
            raise MediaUploadError('image upload outcome ambiguous; reconcile durable intent before any retry') from None
        try:payload=response.json()
        except ValueError:payload={}
        self.common.record_response_usage(dict(response.headers),response.status_code,payload,logical_points=3)
        images=payload.get('images') if isinstance(payload,dict) else None
        values=list(images.values()) if isinstance(images,dict) else []
        if response.status_code not in {200,201} or len(values)!=1 or not re.fullmatch(r'[a-fA-F0-9]{32}',str(values[0].get('hash') or '')):
            code=(payload.get('error') or {}).get('code') if isinstance(payload,dict) else None
            raise MediaUploadError(f'image upload unconfirmed http={response.status_code} code={code}; no automatic replay')
        return values[0]['hash']


def prestage_images(assets, *, account_id, registry, uploader, proof_dir, atomic_json):
    """All identities/bytes verified before first upload. Serialized by caller account lock."""
    assets=list(assets)
    if not assets:return {'assets':[], 'registry_hits':0}
    if len({a['asset_id'] for a in assets})!=len(assets):
        raise ValueError('image pre-stage requires unique lineage')
    for a in assets:validate_local_image(a['vertical_file'],a['checksum'])
    library=uploader.inventory();records=[];hits=0
    proof_dir=Path(proof_dir);proof_dir.mkdir(parents=True,exist_ok=True)
    for a in assets:
        aid=a['asset_id'];checksum=a['checksum'];name=image_title(aid,checksum,a['canonical_filename'])
        digest=hashlib.sha256((str(account_id)+'|'+aid+'|'+checksum).encode()).hexdigest()
        intent_path=proof_dir/('image-upload-'+digest+'.json')
        intent=json.loads(intent_path.read_text()) if intent_path.exists() else None
        if intent and any(intent.get(k)!=v for k,v in {'account_id':str(account_id),'asset_id':aid,'checksum':checksum,'name':name}.items()):
            raise MediaNotReady('image upload intent identity mismatch')
        try:
            ready=registry.require_ready(account_id,aid,checksum,media_type='image')
        except MediaNotReady:ready=None
        if ready:
            require_image(library,ready['image_hash'],name=name);hits+=1;records.append({'registry':ready});continue
        matches=[r for r in library if r.get('name')==name]
        if len(matches)>1:raise MediaNotReady('deterministic image name ambiguous; no upload')
        image_hash=matches[0].get('hash') if matches else None
        if intent and intent.get('image_hash'):
            image_hash=intent['image_hash']
        if not image_hash:
            if intent:
                raise MediaNotReady('previous image upload intent unresolved; no blind replay')
            intent={'account_id':str(account_id),'asset_id':aid,'checksum':checksum,'name':name,'status':'UPLOAD_INTENT'}
            atomic_json(intent_path,intent)
            image_hash=uploader.upload(a['vertical_file'],name)
            atomic_json(intent_path,{**intent,'image_hash':image_hash,'status':'READBACK_PENDING'})
        readback=uploader.inventory([image_hash])
        require_image(readback,image_hash,name=name)
        record=registry.register_image(account_id=account_id,asset_id=aid,checksum=checksum,image_hash=image_hash,ready=True,association_verified=True)
        if registry.require_ready(account_id,aid,checksum,media_type='image')['image_hash']!=image_hash:
            raise MediaNotReady('image registry commit readback mismatch')
        atomic_json(intent_path,{'account_id':str(account_id),'asset_id':aid,'checksum':checksum,'name':name,'image_hash':image_hash,'status':'READY'})
        records.append({'registry':record});library.extend(r for r in readback if r not in library)
    return {'assets':records,'registry_hits':hits}

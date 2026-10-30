"""Read-only reconciliation of mutable adimages names after confirmed upload.

No suffix pattern is identity. The strict name contract remains the default;
only durable account/hash/lineage/byte evidence can supersede a changed label.
No registry, intent, input, manifest or Meta name is rewritten here.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from .media_registry import MediaNotReady
from .image_prestage import image_title, require_image, validate_local_image


def require_prepared_image(rows, image_hash, *, account_id, asset, registry_record, proof_dir):
    name = image_title(asset['asset_id'], asset['checksum'], asset['canonical_filename'])
    # Always enforce unique exact hash, dimensions and status; never catch these failures.
    row = require_image(rows, image_hash)
    if row.get('name') == name:
        return row
    try:
        account_id = str(account_id).removeprefix('act_')
        aid, checksum = asset['asset_id'], asset['checksum']
        if str(row.get('status', '')).upper() != 'ACTIVE':
            raise ValueError('explicit active image required')
        for key,value in {'account_id':account_id, 'image_hash':image_hash}.items():
            if asset.get(key) is not None and asset[key] != value:
                raise ValueError('asset identity')
        expected = {'account_id': account_id, 'asset_id': aid, 'checksum': checksum,
                    'image_hash': image_hash, 'media_type': 'image', 'ready': True,
                    'association_verified': True, 'upload_edge': 'ad_account_adimages',
                    'source': 'v3-ad-account-image-prestage'}
        if any(registry_record.get(k) != v for k, v in expected.items()):
            raise ValueError('registry identity')
        if registry_record.get('vertical_video_id') or registry_record.get('square_video_id'):
            raise ValueError('mixed media')
        root = Path(proof_dir)
        preparation = json.loads((root / 'media-preparation.json').read_text())
        if preparation['account_id'] != account_id or preparation['request_id'] != root.name:
            raise ValueError('preparation scope')
        matches = [a for a in preparation['assets'] if a.get('asset_id') == aid]
        if len(matches) != 1:
            raise ValueError('preparation ambiguity')
        prepared = matches[0]
        if any(prepared.get(k) != v for k,v in {
            'checksum': checksum, 'canonical_filename': asset['canonical_filename'],
            'media_type': 'image', 'metadata_clean': True}.items()):
            raise ValueError('preparation identity')
        digest = hashlib.sha256((account_id+'|'+aid+'|'+checksum).encode()).hexdigest()
        intent = json.loads((root / ('image-upload-'+digest+'.json')).read_text())
        if intent != {'account_id':account_id, 'asset_id':aid, 'checksum':checksum,
                      'name':name, 'image_hash':image_hash, 'status':'READY'}:
            raise ValueError('confirmed upload receipt')
        path = Path(prepared['vertical_file'])
        validate_local_image(path, checksum)
        raw = path.read_bytes()
        md5 = hashlib.md5(raw).hexdigest()
        if not raw or prepared.get('drive_md5') != md5:
            raise ValueError('prepared bytes')
        for key in ('drive_md5', 'clean_md5'):
            if asset.get(key) is not None and asset[key] != md5:
                raise ValueError('asset bytes')
        if asset.get('asset_drive_id') is not None and asset['asset_drive_id'] != prepared.get('drive_id'):
            raise ValueError('asset Drive identity')
        from PIL import Image
        with Image.open(path) as image:
            if (int(row['original_width']), int(row['original_height'])) != image.size:
                raise ValueError('exact image dimensions')
    except (KeyError, TypeError, ValueError, OSError) as exc:
        raise MediaNotReady('renamed image lacks exact confirmed account/hash/lineage/byte binding') from None
    return row

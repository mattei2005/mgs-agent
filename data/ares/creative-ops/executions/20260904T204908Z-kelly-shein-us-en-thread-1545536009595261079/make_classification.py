#!/usr/bin/env python3
import json
from pathlib import Path

BASE = Path('/root/mgs-agent/data/ares/creative-ops/executions/20260904T204908Z-kelly-shein-us-en-thread-1545536009595261079')
MANIFEST = BASE / 'frame-samples/20260904T205103Z/video-frame-sample-manifest.json'
manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
person_by_index = {
    1:'PERSON',2:'PERSON',3:'PERSON',4:'PERSON',5:'PERSON',6:'NO_PERSON',7:'PERSON',8:'NO_PERSON',
    9:'PERSON',10:'PERSON',11:'PERSON',12:'PERSON',13:'NO_PERSON',14:'PERSON',15:'PERSON',16:'PERSON',
    17:'PERSON',18:'PERSON',19:'PERSON',20:'NO_PERSON',21:'PERSON',22:'PERSON',23:'NO_PERSON',24:'NO_PERSON',
    25:'PERSON',26:'NO_PERSON',27:'PERSON',28:'PERSON',29:'NO_PERSON',30:'PERSON',31:'PERSON',32:'PERSON',
}
product_rules = [
    ('ROBO ASPIRADOR','ROBOT_VACUUM','FREE_ROBOT_VACUUM','FREE ROBOT VACUUM'),
    ('CHAVEIRO CARREGADOR','KEYCHAIN_CHARGER','FREE_KEYCHAIN_CHARGER','FREE KEYCHAIN CHARGER'),
    ('SUPORTE CELULAR','PHONE_HOLDER','FREE_PHONE_HOLDER','FREE PHONE HOLDER'),
    ('DRONE','DRONE','FREE_DRONE','FREE DRONE'),
]
classification = {}
review = []
for idx, item in enumerate(manifest['items'], 1):
    name = item['original_filename']
    matches = [r for r in product_rules if r[0] in name]
    if len(matches) != 1:
        raise RuntimeError(f'product rule mismatch for {name}: {matches}')
    _, product, angle, claim = matches[0]
    cls = {'product_type': product, 'angle': angle, 'person': person_by_index[idx], 'claim': claim}
    classification[name] = cls
    review.append({'index': idx, 'original_filename': name, **cls, 'evidence': 'five-frame visual timeline at 0.5s, 2.0s, 3.2s, 4.5s, 6.0s'})
if len(classification) != 32 or set(person_by_index) != set(range(1,33)):
    raise RuntimeError('classification count/index mismatch')
(BASE / 'classification.json').write_text(json.dumps(classification, ensure_ascii=False, indent=2), encoding='utf-8')
(BASE / 'visual-review.json').write_text(json.dumps({'manifest': str(MANIFEST), 'reviewed_items': 32, 'items': review}, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'classification': str(BASE / 'classification.json'), 'visual_review': str(BASE / 'visual-review.json'), 'count': len(classification)}, indent=2))

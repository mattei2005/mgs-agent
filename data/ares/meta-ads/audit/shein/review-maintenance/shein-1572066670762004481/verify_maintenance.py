"""Read-only regression using exact, previously validated review artifacts."""
import copy
import importlib.machinery
import importlib.util
import json
from pathlib import Path
import sys

sys.path.insert(0, '/root/mgs-agent/scripts')
from ares_campaign_v3.shein_continuation import APPROVED_RESUME
from ares_campaign_v3 import reviewed_copy_targeting, image_sourcing, creative_media

HERE = Path(__file__).parent
D = Path('/root/mgs-agent/data/ares/meta-ads/state/shein-campaigns/single-clone/shein-1572066670762004481')
B = Path('/root/mgs-agent/data/ares/meta-ads')
if '--candidate' in sys.argv:
    for name in ['reviewed_copy_targeting', 'image_sourcing']:
        full = 'ares_campaign_v3.' + name
        loader = importlib.machinery.SourceFileLoader(full, str(HERE / (name + '.py.candidate')))
        spec = importlib.util.spec_from_loader(full, loader)
        module = importlib.util.module_from_spec(spec)
        sys.modules[full] = module
        loader.exec_module(module)

state = json.loads((D / 'state.json').read_text())
checkpoint = json.loads((B / 'engine-v3/state/checkpoints/shein-1572066670762004481-1829406761389732.json').read_text())
descriptor = json.loads((D / 'targeting-continuation.json').read_text())
verified = json.loads((D / 'targeting-descriptor-verified.json').read_text())
fixtures = json.loads((D / 'sourcing-regression-fixtures.json').read_text())
diag = json.loads((D / 'sourcing-live-diagnostic.json').read_text())
context = {'descriptor': descriptor, 'state': state, 'checkpoint': checkpoint, 'verified': verified}
checks = []

def rejected(actual, expected, label):
    try:
        value = creative_media.matches(actual, expected)
    except ValueError:
        value = False
    assert value is False, label
    checks.append(label)

for fixture, row in zip(fixtures, diag, strict=True):
    actual, expected = copy.deepcopy(fixture['actual']), fixture['expected']
    actual['id'] = row['creative_id']
    rejected(actual, expected, 'outside review remains strict')
    marker = APPROVED_RESUME.set(context)
    try:
        assert creative_media.matches(actual, expected), 'exact preserved GenAI package must match in genuine review context'
        checks.append('exact reviewed slot passes')
        mutations = [
            ('primary hash', lambda a: a['object_story_spec']['link_data'].__setitem__('image_hash', 'different')),
            ('source variant', lambda a: a['media_sourcing_spec']['images'][0].__setitem__('hash', 'different')),
            ('source enrollment', lambda a: a['media_sourcing_spec']['images'][0].__setitem__('opt_in_status', 'opt_out')),
            ('copy', lambda a: a['object_story_spec']['link_data'].__setitem__('message', 'changed')),
            ('tracking', lambda a: a['object_story_spec']['link_data'].__setitem__('link', 'https://example.invalid/changed')),
            ('page', lambda a: a['object_story_spec'].__setitem__('page_id', '1')),
            ('creative identity', lambda a: a.__setitem__('id', '1')),
            ('extra media', lambda a: a['media_sourcing_spec'].__setitem__('videos', [{'video_id': '1'}])),
            ('tags', lambda a: a.__setitem__('url_tags', 'changed=1')),
        ]
        for label, mutate in mutations:
            changed = copy.deepcopy(actual)
            mutate(changed)
            rejected(changed, expected, label)
        altered = copy.deepcopy(expected)
        altered['object_story_spec']['link_data']['message'] = 'changed'
        rejected(actual, altered, 'sealed expected payload drift')
    finally:
        APPROVED_RESUME.reset(marker)
print(json.dumps({'status': 'PASS', 'checks': len(checks), 'real_slots': len(fixtures), 'meta_writes': 0}))

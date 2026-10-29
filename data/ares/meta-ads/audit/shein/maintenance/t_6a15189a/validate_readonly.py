"""Exercise REAL reviewed descriptor and existing objects; GET only, fail closed."""
import copy
import json
import sys
from pathlib import Path
from datetime import datetime, timezone
ROOT = Path('/root/mgs-agent')
sys.path.insert(0, str(ROOT/'scripts'))
from ares_campaign_v3 import shein_continuation as continuation
from ares_campaign_v3 import shein_reviewed_targeting as reviewed
from ares_campaign_v3 import shein_single_clone as route
from ares_campaign_v3 import shein_channel_authority as discord
from ares_campaign_v3.activation import validate_live
from ares_campaign_v3.schema import Manifest
HERE = Path(__file__).resolve().parent


def main():
    descriptor = json.loads((HERE/'continuation-reviewed-device-004-005.json').read_text())
    rid, aid = descriptor['continuation_of'], descriptor['account_id']
    state_path = ROOT/'data/ares/meta-ads/state/shein-campaigns/single-clone'/rid/'state.json'
    checkpoint_path = ROOT/'data/ares/meta-ads/engine-v3/state/checkpoints'/(rid+'-'+aid+'.json')
    state = json.loads(state_path.read_text()); checkpoint = json.loads(checkpoint_path.read_text())
    before = copy.deepcopy((state, checkpoint, descriptor))
    discord_gets = []
    discord_messages = []
    raw_discord_get = discord._get
    def get_message(path):
        value = raw_discord_get(path)
        discord_gets.append(path)
        if '/messages/' in path:
            discord_messages.append({'id':value.get('id'), 'channel_id':value.get('channel_id'),
                'author_id':(value.get('author') or {}).get('id'),
                'bot':bool((value.get('author') or {}).get('bot')),
                'content_digest':continuation.content_digest(value.get('content')),
                'timestamp':value.get('timestamp')})
        return value
    # Instrument the existing identity only; record also live permission GETs.
    discord._get = get_message
    proof = continuation.validate_descriptor(descriptor, state, checkpoint, get_message=get_message)
    assert proof['accepted_targeting']['authority']['source'] == 'live_discord_effective_permissions'
    common = route._load_common()
    config = json.loads((ROOT/'data/ares/meta-ads/engine-v3/config.json').read_text())
    token, field = common.get_token_from_1password(config['accounts'][aid]['token_item'])
    assert token, 'existing corporate runtime identity unavailable'
    logical_gets = []
    raw_get, raw_batch = common.graph_get, common.graph_batch_get
    def graph_get(path, token, params=None):
        logical_gets.append({'method':'GET', 'path':path})
        return raw_get(path, token, params)
    def graph_batch_get(token, requests):
        logical_gets.extend({'method':'GET', 'path':r['path']} for r in requests)
        return raw_batch(token, requests)
    def forbidden(*args, **kwargs):
        raise AssertionError('Meta write forbidden in maintenance validation')
    common.graph_get, common.graph_batch_get = graph_get, graph_batch_get
    common.graph_post = common.graph_post_once = forbidden
    def read(path, fields):
        http, value, _ = common.graph_get(path, token, {'fields':fields})
        assert http == 200 and 'error' not in value, 'live GET rejected'
        return value
    identity = read('me', 'id,name,client_business_id')
    assert identity['id'] == route.SYSTEM_USER_ID and identity['client_business_id'] == route.BUSINESS_ID, 'runtime identity mismatch'
    account = read('act_'+aid, 'id,currency,timezone_name,user_tasks')
    assert account['id'] == 'act_'+aid and account['currency'] == 'USD' and account['timezone_name'] == 'America/New_York'
    assert 'ADVERTISE' in account['user_tasks'], 'live account permission missing'
    source_campaign = read(state['source']['campaign']['id'], 'id,account_id')
    assert source_campaign['account_id'] == aid
    source_set = read(state['source']['adset']['id'], 'id,account_id,campaign_id,targeting')
    assert source_set['account_id'] == aid and source_set['campaign_id'] == source_campaign['id']
    assert source_set['targeting'] == state['source']['adset']['targeting'], 'source targeting drift'
    marker = continuation.APPROVED_RESUME.set({'descriptor':descriptor,'state':state,'checkpoint':checkpoint,'verified':proof})
    trees, warnings = [], []
    try:
        creation = Manifest.from_dict(state['manifest']); target = Manifest.from_dict(state['target_manifest'])
        for i, cid in enumerate(proof['campaign_ids']):
            tree = route._readback(common, token, cid)
            assert all(n['status'] == 'PAUSED' for n in [tree['campaign']]+tree['adsets']['data']+tree['ads']['data'])
            payload = {**state['manifest'], 'campaigns':[state['manifest']['campaigns'][i]]}
            warnings.extend(route.verify_readback(payload, state['source'], tree))
            validate_live(tree, tree, target.campaigns[i], rid)
            trees.append(tree)
        activation_proof = {'trees':trees}
        assert continuation.activation_authorization(target, creation, activation_proof)['accepted_targeting']
    finally:
        continuation.APPROVED_RESUME.reset(marker)
    assert before == (state, checkpoint, descriptor)
    assert json.loads(state_path.read_text()) == state and json.loads(checkpoint_path.read_text()) == checkpoint
    result = {'verified':True,'validated_at':datetime.now(timezone.utc).isoformat(),'descriptor':str(HERE/'continuation-reviewed-device-004-005.json'),
              'continuation_proof':proof,'discord_gets':discord_gets,'discord_messages':discord_messages,'runtime_identity_id':identity['id'],
              'account_live_permission':'ADVERTISE','logical_meta_gets':logical_gets,'meta_writes':0,
              'source_targeting_unchanged':True,'manifests_mutated':False,'clock_reset':False,
              'status_by_id':{n['id']:n['status'] for t in trees for n in [t['campaign']]+t['adsets']['data']+t['ads']['data']},
              'warnings':warnings,'semantic_readback':'PASS','activation_pre_read_guards':'PASS',
              'rendered_media_qa':'NOT_EXECUTED; remains mandatory downstream','activation':'NOT_EXECUTED'}
    (HERE/'live-validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'verified':True,'semantic_readback':'PASS','existing_campaigns':len(trees),'meta_writes':0,'status':'PAUSED'}))


if __name__ == '__main__':
    main()

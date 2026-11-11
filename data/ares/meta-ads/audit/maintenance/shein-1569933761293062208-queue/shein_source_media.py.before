"""Typed, fresh READ_ONLY source-media evidence for pure-clone queue scheduling.

Not a staging receipt or campaign manifest. Never reserve, transfer or upload media.
Only live account-scoped observations may exempt an inert historical review.
"""
from __future__ import annotations
import fcntl
import hashlib
import json
import re
import time
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path

MAX_AGE_SECONDS = 120


def request_digest(request):
    return hashlib.sha256(json.dumps(request, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def inventory_path(base):
    return base / 'data/ares/creative-ops/inventory/assets.jsonl'


def same_resume_request(base, persisted, original):
    if persisted == original:
        return True
    if original.get('mode', 'pure_clone') != 'pure_clone':
        return False
    # Compare only the runner's canonical defaults, not arbitrary field subsets.
    # Never materialize these into the immutable intake/job.
    from .shein_single_clone import apply_request_defaults
    operation = json.loads((base / 'data/ares/meta-ads/operations/SHEIN-US-DIRECT.json').read_text())
    return persisted == apply_request_defaults(original, operation)


def expand(identities, rows):
    from .shein_decision_wait import _media
    result = set(identities)
    linked = []
    remaining = list(rows)
    while True:
        matched = [row for row in remaining if _media(row) & result]
        if not matched:
            return result, linked
        for row in matched:
            result.update(_media(row))
            linked.append(row)
            remaining.remove(row)


def primary_media(creative):
    """Only actual image/video slots, never thumbnails, posts or ad lineage."""
    found = set()
    story = creative.get('object_story_spec') or {}
    for key, field in [('link_data', 'image_hash'), ('video_data', 'video_id')]:
        if key in story:
            value = story[key].get(field)
            if not isinstance(value, str) or not value:
                raise ValueError('source primary media slot is incomplete')
            found.add(('identity', value))
    feed = creative.get('asset_feed_spec') or {}
    for key, field in [('images', 'hash'), ('videos', 'video_id')]:
        for slot in feed.get(key) or []:
            value = slot.get(field)
            if not isinstance(value, str) or not value:
                raise ValueError('source media variant is incomplete')
            found.add(('identity', value))
    if not found:
        raise ValueError('source actual media unavailable')
    return found


@dataclass(frozen=True)
class SourceMediaProof:
    kind: str
    request_sha256: str
    account_id: str
    channel_id: str
    observed_at: float
    inventory_sha256: str
    source_campaign_id: str
    source_number: int
    ad_bindings: tuple
    identities: frozenset
    reservations_json: str
    historical_json: str

    def validate(self, request, account_id, base):
        from .shein_decision_wait import digest, record_path, _engine_root
        if (self.kind != 'PURE_CLONE_SOURCE_MEDIA_READ_ONLY_V1'
                or request.get('mode', 'pure_clone') != 'pure_clone'
                or request.get('asset_refs') or request.get('campaign_groups')
                or self.request_sha256 != request_digest(request)
                or self.account_id != str(account_id) or str(request.get('account')) != self.account_id
                or self.channel_id != request.get('source_channel_id')
                or self.source_number != request.get('source_number')
                or not 0 <= time.time() - self.observed_at <= MAX_AGE_SECONDS
                or not self.source_campaign_id or not self.ad_bindings or not self.identities
                or self.inventory_sha256 != digest(inventory_path(base))):
            raise ValueError('pure-clone source media evidence missing, stale or mismatched')
        historical = json.loads(self.historical_json)
        if not historical:
            raise ValueError('pure-clone historical live evidence missing')
        for rid, record in historical.items():
            state_path = base / 'data/ares/meta-ads/state/shein-campaigns/single-clone' / rid / 'state.json'
            cp = _engine_root(base) / 'checkpoints' / (rid + '-' + self.account_id + '.json')
            from . import shein_manual_takeover as manual
            pinned_record = manual.path(base,rid) if record.get('classification') == manual.STATUS else record_path(base,rid)
            if record.get('classification') == manual.STATUS:
                manual.validate(base,rid)
            if (record['state_sha256'] != digest(state_path)
                    or record['record_sha256'] != digest(pinned_record)
                    or record['checkpoint_sha256'] != digest(cp)):
                raise ValueError('pure-clone historical evidence changed')
        return self

    @property
    def reservations(self):
        return json.loads(self.reservations_json)

    def receipt(self):
        return {**self.__dict__, 'identities': sorted(self.identities),
                'reservations_json': self.reservations,
                'historical_json': json.loads(self.historical_json)}


def resolve(request, account_id, base, *, held_accounts=frozenset()):
    """No cached proof is trusted. Missing locks, source or media fail closed."""
    from . import shein_request_queue as q, shein_single_clone as driver
    from .shein_decision_wait import _media, _engine_root, digest, evidence, materialized_media
    account_id = str(account_id)
    if (request.get('mode', 'pure_clone') != 'pure_clone' or request.get('asset_refs')
            or request.get('campaign_groups') or str(request.get('account')) != account_id
            or not isinstance(request.get('source_number'), int) or request['source_number'] <= 0):
        raise ValueError('source media requires exact pure-clone source account and number')
    # Reuse the canonical live authority, profile, domain and positive account gates.
    account = q.authorize_queue_request(request, base)
    if account['account_id'] != account_id:
        raise ValueError('source media account partition mismatch')
    inv = inventory_path(base)
    engine = _engine_root(base)
    with ExitStack() as stack:
        locks = []
        if account_id not in held_accounts:
            locks.append((q.root(base) / 'single-clone' / ('account-' + account_id + '.lock'), fcntl.LOCK_EX))
        locks += [(engine / 'writer-leases' / (account_id + '.lock'), fcntl.LOCK_SH),
                  (inv.with_suffix(inv.suffix + '.lock'), fcntl.LOCK_SH)]
        for path, mode in locks:
            handle = stack.enter_context(path.open('rb'))
            fcntl.flock(handle, mode | fcntl.LOCK_NB)
        lease = json.loads((engine / 'writer-leases' / (account_id + '.json')).read_text())
        from .shein_manual_takeover import lease_idle
        idle = lease_idle(engine, lease)
        resume = q.state(base, request['request_id'])
        own = (lease.get('request_id') == request['request_id'] and lease.get('blocks_readers') is True
               and lease.get('status') in {'IN_PROGRESS', 'DEFERRED_QUOTA', 'READBACK_DEFERRED', 'RECOVERY_PENDING', 'ACTIVATION_PENDING', 'ACTIVATION_DEFERRED'}
               and same_resume_request(base, resume.get('request'), request) and resume.get('phase') in q.ACTIVE)
        if lease.get('account_id') != account_id or not (idle or own):
            raise ValueError('source media account writer lease is not idle or exact resume')
        config = json.loads((base / 'data/ares/meta-ads/engine-v3/config.json').read_text())
        common = driver._load_common()
        token, _ = common.get_token_from_1password(config['accounts'][account_id]['token_item'])
        started = time.time()
        pre = driver._batch(common, token, [{'name': 'campaigns', 'path': 'act_' + account_id + '/campaigns',
              'params': {'fields': 'id,account_id,name,status', 'limit': 500}}])
        campaigns = driver._complete_edge(pre['campaigns'])
        sources = [c for c in campaigns if re.match(r'^([0-9]+)\s*-', c.get('name', ''))
                   and int(re.match(r'^([0-9]+)\s*-', c['name'])[1]) == request['source_number']]
        if (len(sources) != 1 or sources[0].get('account_id') != account_id
                or sources[0].get('status') not in {'ACTIVE', 'PAUSED'}):
            raise ValueError('source media campaign missing, ambiguous or wrong account')
        cid = sources[0]['id']
        raw = driver._batch(common, token, [
            {'name': 'adsets', 'path': cid + '/adsets', 'params': {
                'fields': 'id,account_id,campaign_id,status', 'limit': 50}},
            {'name': 'ads', 'path': cid + '/ads', 'params': {
                'fields': 'id,account_id,campaign_id,adset_id,status,source_ad_id,creative{id,object_story_id,effective_object_story_id,object_story_spec,asset_feed_spec,media_sourcing_spec}', 'limit': 50}}])
        sets = [x for x in driver._complete_edge(raw['adsets']) if x.get('status') not in {'DELETED', 'ARCHIVED'}]
        ads = [x for x in driver._complete_edge(raw['ads']) if x.get('status') not in {'DELETED', 'ARCHIVED'}]
        if (len(sets) != 1 or not 1 <= len(ads) <= 5
                or any(x.get('account_id') != account_id or x.get('campaign_id') != cid
                       or x.get('status') not in {'ACTIVE', 'PAUSED'} for x in sets + ads)
                or any(x.get('adset_id') != sets[0]['id'] for x in ads)
                or len({x['id'] for x in ads}) != len(ads)):
            raise ValueError('source media child coverage or partition mismatch')
        identities = set()
        primary_ids = set()
        bindings = []
        for ad in ads:
            creative = ad.get('creative') or {}
            # Post/creative/lineage alone is not proof of the actual media. Inherited
            # source_ad_id is intentionally not a media key: new-media clones reuse it.
            primary = primary_media(creative)
            if not creative.get('id'):
                raise ValueError('source media definition unavailable; no empty-set exemption')
            primary_ids.update(primary)
            identities.update(_media(creative))
            bindings.append((ad['id'], sets[0]['id'], creative['id'], ad.get('source_ad_id')))
        rows = [json.loads(line) for line in inv.read_text().splitlines() if line.strip()]
        for identity in primary_ids:
            aliases = [row for row in rows if identity in _media(row)]
            if (not aliases or len({row.get('asset_id') for row in aliases}) != 1
                    or any(not row.get('asset_id') or not (row.get('clean_checksum') or row.get('checksum')) for row in aliases)):
                raise ValueError('source media inventory lineage missing or ambiguous')
        identities, linked = expand(identities, rows)
        historical = {}
        from . import shein_manual_takeover as manual
        historical_records = list((q.root(base) / 'queue/decision-waits').glob('*.json'))
        historical_records += list((q.root(base) / 'queue/manual-takeovers').glob('*.json'))
        for path in historical_records:
            pinned = json.loads(path.read_text())
            if pinned.get('account_id') != account_id or path.stem == request['request_id']:
                continue
            previous = q.state(base, path.stem)
            evidence(base, previous, resume_request=request)
            if previous['request'].get('source_channel_id') != request['source_channel_id']:
                raise ValueError('source media historical partition mismatch')
            if manual.present(base, path.stem):
                historical[path.stem] = manual.verify_live(base,path.stem,common,token)
                continue
            cp_path = engine / 'checkpoints' / (path.stem + '-' + account_id + '.json')
            cp = json.loads(cp_path.read_text())
            expected_ads = {x for b in cp.get('bundles', []) for x in b.get('ad_ids', [])}
            expected_sets = {x for b in cp.get('bundles', []) for x in b.get('adset_ids', [])}
            observed_ads, observed_sets, observed_media = set(), set(), set()
            pinned_media, _ = expand(materialized_media(previous), rows)
            for historical_id in previous['engine_result']['campaign_ids']:
                live = driver._readback(common, token, historical_id)
                if (live['campaign'].get('id') != historical_id
                        or live['campaign'].get('account_id') != account_id
                        or live['campaign'].get('status') != 'PAUSED'):
                    raise ValueError('historical campaign is not the pinned paused object')
                old_ads = driver._complete_edge(live['ads'])
                old_sets = driver._complete_edge(live['adsets'])
                if not old_ads or not old_sets or any(x.get('status') != 'PAUSED' for x in old_ads + old_sets):
                    raise ValueError('historical paused child coverage changed')
                for ad in old_ads:
                    if not primary_media(ad.get('creative') or {}).issubset(pinned_media):
                        raise ValueError('historical primary media changed since pinned decision')
                    observed_media.update(_media(ad.get('creative') or {}))
                observed_ads.update(x['id'] for x in old_ads)
                observed_sets.update(x['id'] for x in old_sets)
            if not expected_ads or observed_ads != expected_ads or not expected_sets or observed_sets != expected_sets:
                raise ValueError('historical live child IDs do not match checkpoint')
            historical[path.stem] = {'state_sha256': digest(q.root(base) / 'single-clone' / path.stem / 'state.json'),
                'record_sha256': digest(path), 'checkpoint_sha256': digest(cp_path),
                'campaign_ids': previous['engine_result']['campaign_ids'], 'ad_ids': sorted(observed_ads),
                'adset_ids': sorted(observed_sets), 'identities': sorted(observed_media)}
        reservations = [{'asset_id': x.get('asset_id'), 'reservation_request_id': x.get('reservation_request_id')}
                        for x in linked]
        proof = SourceMediaProof('PURE_CLONE_SOURCE_MEDIA_READ_ONLY_V1', request_digest(request),
            account_id, request['source_channel_id'], started, digest(inv), cid,
            request['source_number'], tuple(sorted(bindings)), frozenset(identities),
            json.dumps(reservations, sort_keys=True), json.dumps(historical, sort_keys=True))
        proof.validate(request, account_id, base)
        # Audit only; no cache consumer, inventory reservation or manifest mutation.
        driver.atomic_json(q.root(base) / 'queue/source-media' / (request['request_id'] + '.json'), proof.receipt())
        return proof

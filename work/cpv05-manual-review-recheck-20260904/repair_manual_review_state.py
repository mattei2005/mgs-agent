#!/usr/bin/env python3
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

SP = ZoneInfo('America/Sao_Paulo')
STATE = Path('/root/.hermes/profiles/ares/state/creditoparaveiculo-account05-creative-cut24h.json')
STATE_LOCK = Path('/root/.hermes/profiles/ares/state/creditoparaveiculo-account05-creative-cut24h-runner.lock')
AUDIT_ROOT = Path('/root/mgs-agent/data/ares/meta-ads/audit/automated-actions/Creditoparaveiculo-BR-CAR-BR-05/creative-cut-24h')
TARGETS = {
    '120248535536910046': 8,
    '120248535536940046': 9,
    '120248557516840046': 11,
    '120248557516850046': 12,
}


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f'.{path.name}.', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write('\n')
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
        dir_fd = os.open(str(path.parent), os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


STATE_LOCK.parent.mkdir(parents=True, exist_ok=True)
with STATE_LOCK.open('a+') as lock_handle:
    fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
    before_raw = STATE.read_bytes()
    state = json.loads(before_raw)
    if str(state.get('account_id')) != '2039876850230678':
        raise SystemExit('account identity mismatch')
    changed = []
    before_records = {}
    after_records = {}
    corrected_at = datetime.now(SP)
    for campaign_id, number in TARGETS.items():
        record = state['campaigns'].get(campaign_id)
        if not isinstance(record, dict) or int(record.get('campaign_number', -1)) != number:
            raise SystemExit(f'campaign assignment mismatch C{number:02d}')
        if record.get('current_stage') != 'MANUAL_REVIEW':
            raise SystemExit(f'C{number:02d} is not in MANUAL_REVIEW')
        previous = record.get('last_action') or {}
        if previous.get('action') != 'MANUAL_REVIEW':
            raise SystemExit(f'C{number:02d} lacks the expected manual-review evidence')
        metrics = previous.get('window_metrics') or {}
        review_at = datetime.fromisoformat(str(previous.get('at_sp'))).astimezone(SP)
        active_ids = [str(value) for value in record.get('active_ad_ids') or []]
        stage = {3: 'THREE_ADS_ACTIVE', 2: 'TWO_ADS_ACTIVE', 1: 'ONE_AD_ACTIVE'}.get(len(active_ids))
        if not stage:
            raise SystemExit(f'C{number:02d} has invalid active-ad cardinality')
        spend_by_ad = {str(k): float(v or 0) for k, v in (metrics.get('spend_by_active_ad') or {}).items()}
        if set(spend_by_ad) != set(active_ids):
            raise SystemExit(f'C{number:02d} window spend identity mismatch')
        before_records[campaign_id] = json.loads(json.dumps(record))
        baseline_meta = {str(k): float(v or 0) for k, v in (record.get('baseline_meta_spend_by_ad') or {}).items()}
        for ad_id in active_ids:
            baseline_meta[ad_id] = baseline_meta.get(ad_id, 0.0) + spend_by_ad[ad_id]
        record['current_stage'] = stage
        record['window_started_at_sp'] = review_at.isoformat()
        record['next_checkpoint_at_sp'] = (review_at + timedelta(hours=24)).isoformat()
        record['baseline_meta_spend_by_ad'] = baseline_meta
        record['baseline_sb_investment_usd'] = float(record.get('baseline_sb_investment_usd') or 0) + float(metrics.get('sb_investment_usd') or 0)
        record['baseline_sb_net_revenue_usd'] = float(record.get('baseline_sb_net_revenue_usd') or 0) + float(metrics.get('sb_net_revenue_usd') or 0)
        record['last_action'] = {
            'action': 'MANUAL_REVIEW_RECHECK_SCHEDULED',
            'at_sp': review_at.isoformat(),
            'stage_preserved': stage,
            'next_checkpoint_at_sp': record['next_checkpoint_at_sp'],
            'window_metrics': metrics,
            'decision': previous.get('decision') or {},
            'correction': {
                'authorized_by': 'Nicolas Holanda',
                'authorized_at_sp': corrected_at.isoformat(),
                'reason': 'repair manual-review terminal-state defect and resume 24h re-evaluation',
                'source_thread_id': '1545576394388414565',
            },
        }
        after_records[campaign_id] = json.loads(json.dumps(record))
        changed.append({'campaign': f'C{number:02d}', 'stage': stage, 'next_checkpoint_at_sp': record['next_checkpoint_at_sp']})
    state['updated_at_sp'] = corrected_at.isoformat()
    atomic_json(STATE, state)
    after_raw = STATE.read_bytes()
    if digest(after_raw) == digest(before_raw):
        raise SystemExit('state did not change')
    audit = {
        'kind': 'cpv05_manual_review_recheck_state_repair',
        'status': 'state_repaired_pending_live_runner',
        'authorized_by': 'Nicolas Holanda',
        'authorization_source': 'discord:thread:1545576394388414565',
        'corrected_at_sp': corrected_at.isoformat(),
        'account_id': '2039876850230678',
        'before_sha256': digest(before_raw),
        'after_sha256': digest(after_raw),
        'campaigns': changed,
        'before_records': before_records,
        'after_records': after_records,
        'meta_writes': 0,
    }
    stamp = corrected_at.astimezone(ZoneInfo('UTC')).strftime('%Y%m%dT%H%M%S%fZ')
    audit_path = AUDIT_ROOT / f'{stamp}-manual-review-recheck-state-repair.json'
    atomic_json(audit_path, audit)
    print(json.dumps({'status': 'ok', 'campaigns': changed, 'state_sha256': digest(after_raw), 'audit': str(audit_path)}, ensure_ascii=False))

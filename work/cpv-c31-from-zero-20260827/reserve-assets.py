from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path('/root/mgs-agent')
sys.path.insert(0, str(ROOT / 'scripts'))

from ares_campaign_v3.daily_cpv import atomic_inventory, atomic_json, utc_now

REQUEST_ID = 'cpv-c31-from-zero-20260827'
ASSET_IDS = {
    'asset_5966c098f64de6d561ab',
    'asset_dea92e6bba464578897b',
    'asset_303bb59d1847ccd47afe',
}
INVENTORY = ROOT / 'data/ares/creative-ops/inventory/assets.jsonl'
AUDIT = ROOT / 'data/ares/creative-ops/audit/lifecycle/cpv-c31-from-zero-reservation-20260827.json'


def load_rows() -> list[dict]:
    return [json.loads(line) for line in INVENTORY.read_text().splitlines() if line.strip()]


def main() -> int:
    rows = load_rows()
    selected = [row for row in rows if str(row.get('asset_id') or '') in ASSET_IDS]
    if len(selected) != 3:
        raise RuntimeError('reservation requires exactly three assets')
    previous = []
    for row in selected:
        if row.get('status') != '01_READY' or row.get('metadata_clean') is not True:
            raise RuntimeError(f"asset not technically ready: {row['asset_id']}")
        if row.get('used_by') not in {None, 'ARES_V3_IN_FLIGHT'}:
            raise RuntimeError(f"asset already used: {row['asset_id']}")
        if row.get('used_by') is None and row.get('reservation_status') != 'RESERVADO_PELO_GESTOR':
            raise RuntimeError(f"unexpected original reservation: {row['asset_id']}")
        previous.append({
            'asset_id': row['asset_id'],
            'reservation_status': row.get('reservation_status'),
            'ares_eligible': row.get('ares_eligible'),
            'used_by': row.get('used_by'),
            'campaign_owner': row.get('campaign_owner'),
        })
        row.update(
            reservation_status='RESERVADO_PELO_ARES_V3_C31',
            ares_eligible=False,
            used_by='ARES_V3_IN_FLIGHT',
            campaign_owner='Ares',
            reservation_audit=str(AUDIT),
            reservation_request_id=REQUEST_ID,
            release_authority='Rodolfo Mattei',
            release_scope='C31 from_zero_prestaged only',
            last_reconciled_at=utc_now(),
        )
    audit = {
        'schema_version': 1,
        'request_id': REQUEST_ID,
        'authorized_by': 'Rodolfo Mattei',
        'authorization_source': 'discord:thread:1542573475104034936',
        'authorization_scope': 'use the three newly treated MOTO creatives for C31 from zero via v3',
        'recorded_at_utc': utc_now(),
        'previous': previous,
        'reserved': [
            {
                'asset_id': row['asset_id'],
                'canonical_filename': row['canonical_filename'],
                'asset_drive_id': row['asset_drive_id'],
                'clean_checksum': row['clean_checksum'],
                'reservation_status': row['reservation_status'],
                'ares_eligible': row['ares_eligible'],
                'used_by': row['used_by'],
            }
            for row in selected
        ],
    }
    atomic_json(AUDIT, audit)
    atomic_inventory(INVENTORY, rows)
    readback = {row['asset_id']: row for row in load_rows() if str(row.get('asset_id') or '') in ASSET_IDS}
    if set(readback) != ASSET_IDS or any(row.get('used_by') != 'ARES_V3_IN_FLIGHT' for row in readback.values()):
        raise RuntimeError('inventory reservation readback failed')
    print(json.dumps({'status': 'ASSETS_RESERVED_FOR_C31', 'count': len(readback), 'audit': str(AUDIT)}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

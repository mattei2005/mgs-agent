from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path

ROOT = Path('/root/mgs-agent')
WORK = ROOT / 'work/cpv-c31-from-zero-20260827'
PREFLIGHT = json.loads((WORK / 'live-batch-preflight.json').read_text())
PREPARED = json.loads((WORK / 'prepared-media.json').read_text())


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def main() -> int:
    reference_ads = [row for row in PREFLIGHT['reference_ads'] if re.match(r'^AD 0[123] - ', str(row.get('name') or ''))]
    reference_ads.sort(key=lambda row: int(re.match(r'^AD (\d+)', row['name']).group(1)))
    if len(reference_ads) != 3:
        raise RuntimeError('reference must resolve exactly AD01/AD02/AD03')
    templates = []
    for row in reference_ads:
        creative = row.get('creative') or {}
        creative_payload = {
            key: copy.deepcopy(creative[key])
            for key in ('object_story_spec', 'asset_feed_spec', 'degrees_of_freedom_spec')
            if creative.get(key) is not None
        }
        templates.append({
            'source_ad_id': row['id'],
            'source_ad_name': row['name'],
            'source_creative_id': creative.get('id'),
            'creative_payload': creative_payload,
        })
    campaign = PREFLIGHT['reference_campaign']
    adset = PREFLIGHT['reference_adset']
    source_selection = {
        'source_campaign_id': campaign['id'],
        'source_adset_id': adset['id'],
        'source_campaign': campaign,
        'source_adset': adset,
        'templates': templates,
        'vehicle_type': 'MOTO',
        'reference_only': True,
        'selection_reason': 'live compliant MOTO hierarchy used only as field/copy reference for from_zero_prestaged; no copy edge permitted',
        'selected_at_source': 'live-batch-preflight.json',
    }
    source_snapshot = {
        'status': 'FROM_ZERO_REFERENCE_SNAPSHOT',
        'request_id': 'cpv-c31-from-zero-20260827',
        'campaign_vehicle_types': ['MOTO'],
        'sources_by_vehicle': {'MOTO': source_selection},
    }
    source_snapshot['snapshot_digest'] = digest(source_snapshot['sources_by_vehicle'])
    targeting = copy.deepcopy(adset['targeting'])
    targeting.pop('age_range', None)
    targeting.pop('brand_safety_content_filter_levels', None)
    promoted = copy.deepcopy(adset['promoted_object'])
    promoted.pop('smart_pse_enabled', None)
    campaign_create = {
        'objective': campaign['objective'],
        'buying_type': campaign['buying_type'],
        'daily_budget': '2500',
        'bid_strategy': 'LOWEST_COST_WITHOUT_CAP',
        'special_ad_categories': campaign['special_ad_categories'],
        'special_ad_category_country': campaign['special_ad_category_country'],
    }
    adset_create = {
        'billing_event': adset['billing_event'],
        'optimization_goal': adset['optimization_goal'],
        'targeting': targeting,
        'promoted_object': promoted,
        'attribution_spec': adset['attribution_spec'],
        'regional_regulated_categories': adset['regional_regulated_categories'],
        'regional_regulation_identities': adset['regional_regulation_identities'],
        'is_dynamic_creative': bool(adset.get('is_dynamic_creative', False)),
    }
    create_specs = {
        'request_id': 'cpv-c31-from-zero-20260827',
        'from_zero_specs': [{
            'campaign_create': campaign_create,
            'adset_create': adset_create,
        }],
    }
    create_specs['spec_digest'] = digest(create_specs['from_zero_specs'])
    assets = {
        'request_id': 'cpv-c31-from-zero-20260827',
        'assets': [
            {
                'asset_id': row['asset_id'],
                'checksum': row['checksum'],
                'canonical_filename': row['canonical_filename'],
                'asset_drive_id': row['asset_drive_id'],
                'drive_readback': row['drive_readback'],
            }
            for row in PREPARED['assets']
        ],
    }
    copy_reference = {
        'primary_texts': [
            '🏍️ Moto Sem Entrada, Parcelas Acessíveis!',
            '✅ Saia de moto nova! Zero entrada e parcelas apartir de R$249.',
            '🏍️ Moto Nova Sem Entrada',
        ],
        'headlines': [
            '✔️ Entrada Zero - Moto Nova - Parcela Baixa',
            '✅ R$249/MÊS',
            '✅ ZERO ENTRADA',
        ],
        'descriptions': ['⭐⭐⭐⭐⭐'],
        'call_to_actions': ['LEARN_MORE'],
        'optimize_text_per_person': 'DISABLED',
        'base_url': 'https://creditoparaveiculo.com/quiz-moto-parcelas-g006/',
        'target_url': 'https://creditoparaveiculo.com/quiz-moto-parcelas-g006/?utm_source=facebook&utm_medium=g006-s&utm_campaign=b01fb13c31&utm_adgroup=b01fb13c31g01',
        'screenshot': '/root/.hermes/profiles/ares/cache/images/img_23579f8f9b9b.webp',
    }
    for name, payload in (
        ('source-reference.json', source_snapshot),
        ('from-zero-specs.json', create_specs),
        ('assets-input.json', assets),
        ('copy-reference.json', copy_reference),
    ):
        (WORK / name).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'status': 'C31_INPUTS_READY', 'templates': len(templates), 'assets': len(assets['assets']), 'source_digest': source_snapshot['snapshot_digest'], 'spec_digest': create_specs['spec_digest']}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

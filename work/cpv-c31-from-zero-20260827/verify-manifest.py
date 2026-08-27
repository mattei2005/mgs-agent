from __future__ import annotations

import json
from pathlib import Path

ROOT = Path('/root/mgs-agent')
WORK = ROOT / 'work/cpv-c31-from-zero-20260827'
EXPECTED_BODIES = [
    '🏍️ Moto Sem Entrada, Parcelas Acessíveis!',
    '✅ Saia de moto nova! Zero entrada e parcelas apartir de R$249.',
    '🏍️ Moto Nova Sem Entrada',
]
EXPECTED_TITLES = [
    '✔️ Entrada Zero - Moto Nova - Parcela Baixa',
    '✅ R$249/MÊS',
    '✅ ZERO ENTRADA',
]
EXPECTED_URL = 'https://creditoparaveiculo.com/quiz-moto-parcelas-g006/?utm_source=facebook&utm_medium=g006-s&utm_campaign=b01fb13c31&utm_adgroup=b01fb13c31g01'


def has_key(value: object, names: set[str]) -> bool:
    if isinstance(value, dict):
        return bool(set(value) & names) or any(has_key(item, names) for item in value.values())
    if isinstance(value, list):
        return any(has_key(item, names) for item in value)
    return False


def main() -> int:
    manifest = json.loads((WORK / 'manifest-sealed.json').read_text())
    registry = json.loads((ROOT / 'data/ares/meta-ads/engine-v3/media-registry.json').read_text())
    campaign = manifest['campaigns'][0]
    checks = {
        'prevalidated': manifest.get('prevalidated') is True,
        'mode_from_zero': campaign.get('mode') == 'from_zero_prestaged',
        'no_lineage_keys_in_campaign': not has_key(campaign, {'source_campaign_id', 'source_adset_id', 'source_ad_id'}),
        'campaign_name': campaign.get('name') == '31 - 28-08 - Garagem Brasil - MOTO - (b01fb13c31) event_Subscribe - MAXVOL',
        'adset_name': campaign.get('adset_name') == '01 - AdGroup - (b01fb13c31g01) event_Subscribe - MAXVOL',
        'start_time': campaign.get('start_time') == '2026-08-28T00:30:00-03:00',
        'campaign_status_paused': campaign.get('status') == 'PAUSED',
        'budget_25_usd': campaign.get('campaign_create', {}).get('daily_budget') == '2500',
        'maxvol': campaign.get('campaign_create', {}).get('bid_strategy') == 'LOWEST_COST_WITHOUT_CAP',
        'one_by_one_by_three': len(manifest.get('campaigns') or []) == 1 and len(campaign.get('ads') or []) == 3,
        'adset_event_subscribe': campaign.get('adset_create', {}).get('promoted_object', {}).get('custom_event_type') == 'SUBSCRIBE',
        'adset_pixel': campaign.get('adset_create', {}).get('promoted_object', {}).get('pixel_id') == '1033279451747443',
        'targeting_writable': 'age_range' not in campaign.get('adset_create', {}).get('targeting', {}) and 'brand_safety_content_filter_levels' not in campaign.get('adset_create', {}).get('targeting', {}),
        'regional_identity': campaign.get('adset_create', {}).get('regional_regulation_identities') == {'universal_beneficiary': '1580679396253124', 'universal_payer': '1580679396253124'},
    }
    registry_values = registry.get('records') or {}
    if not isinstance(registry_values, dict):
        raise RuntimeError('media registry records must be an object')
    registry_rows = {(row['account_id'], row['asset_id'], row['checksum']): row for row in registry_values.values()}
    ad_checks = []
    for index, ad in enumerate(campaign['ads'], start=1):
        feed = ad['creative_payload']['asset_feed_spec']
        media = ad['media']
        reg = registry_rows.get((campaign['account_id'], media['asset_id'], media['checksum']))
        row = {
            'slot': index,
            'name_exact': ad['name'].startswith(f'AD {index:02d} - CAR_BR_BR_VID_MOTO_SEM_ENTRADA_NV_00{index + 4}'),
            'bodies_exact': [item.get('text') for item in feed.get('bodies') or []] == EXPECTED_BODIES,
            'titles_exact': [item.get('text') for item in feed.get('titles') or []] == EXPECTED_TITLES,
            'description_exact': [item.get('text') for item in feed.get('descriptions') or []] == ['⭐⭐⭐⭐⭐'],
            'cta_exact': feed.get('call_to_action_types') == ['LEARN_MORE'],
            'url_exact': [item.get('website_url') for item in feed.get('link_urls') or []] == [EXPECTED_URL],
            'media_registry_exact': bool(reg) and media.get('vertical_video_id') == reg.get('vertical_video_id') and media.get('square_video_id') == reg.get('square_video_id') and reg.get('ready') is True and reg.get('association_verified') is True,
        }
        ad_checks.append(row)
    checks['all_ad_checks'] = all(all(item.values()) for item in ad_checks)
    if not all(checks.values()):
        raise RuntimeError(json.dumps({'checks': checks, 'ads': ad_checks}, ensure_ascii=False))
    output = {'status': 'C31_SEALED_MANIFEST_VERIFIED', 'checks': checks, 'ads': ad_checks, 'content_digest': manifest.get('content_digest')}
    (WORK / 'manifest-verification.json').write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'status': output['status'], 'checks': len(checks), 'ads': len(ad_checks), 'content_digest': output['content_digest']}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

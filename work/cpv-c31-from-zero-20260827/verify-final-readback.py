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


def has_key(value: object, target: str) -> bool:
    if isinstance(value, dict):
        return target in value or any(has_key(item, target) for item in value.values())
    if isinstance(value, list):
        return any(has_key(item, target) for item in value)
    return False


def main() -> int:
    readback = json.loads((WORK / 'final-live-readback.json').read_text())
    video_readback = json.loads((WORK / 'final-video-readback.json').read_text())
    manifest = json.loads((WORK / 'manifest-sealed.json').read_text())
    prewrite = json.loads((WORK / 'prewrite-live.json').read_text())
    campaign_spec = manifest['campaigns'][0]
    campaign = readback['campaign']
    adsets = readback['adsets']
    ads = readback['ads']
    creatives = {str(row['id']): row for row in readback['creatives']}
    checks = {
        'request_mode_from_zero': readback['execution_mode'] == 'from_zero_prestaged',
        'campaign_id_new': campaign['id'] == '120250952825350632' and campaign['id'] != readback['old_c31']['id'],
        'campaign_name_exact': campaign['name'] == campaign_spec['name'],
        'campaign_paused': campaign.get('configured_status') == 'PAUSED' and campaign.get('status') == 'PAUSED',
        'campaign_budget_usd25': campaign.get('daily_budget') == '2500',
        'campaign_maxvol': campaign.get('bid_strategy') == 'LOWEST_COST_WITHOUT_CAP',
        'campaign_start_exact': campaign.get('start_time') == '2026-08-28T00:30:00-0300',
        'campaign_structure': len(adsets) == 1 and len(ads) == 3 and len(creatives) == 3,
        'old_c31_terminal': str(readback['old_c31'].get('configured_status') or '').upper() in {'DELETED', 'ARCHIVED'},
        'account_healthy': readback['account'].get('account_status') == 1 and readback['account'].get('disable_reason') == 0,
        'active_budget_unchanged_paused': readback['active_budget_minor_after'] == prewrite['active_budget_minor_before'],
        'asset_global_assignment_exact': len(readback['asset_ads_account']) == 3 and {str((row.get('campaign') or {}).get('id') or '') for row in readback['asset_ads_account']} == {campaign['id']},
    }
    adset = adsets[0] if len(adsets) == 1 else {}
    checks.update({
        'adset_name_exact': adset.get('name') == campaign_spec['adset_name'],
        'adset_under_campaign': adset.get('campaign_id') == campaign['id'],
        'adset_active_under_paused': adset.get('configured_status') == 'ACTIVE' and adset.get('effective_status') in {'CAMPAIGN_PAUSED', 'PENDING_REVIEW', 'IN_PROCESS', 'WITH_ISSUES'},
        'adset_start_exact': adset.get('start_time') == '2026-08-28T00:30:00-0300',
        'adset_event_pixel': (adset.get('promoted_object') or {}).get('custom_event_type') == 'SUBSCRIBE' and (adset.get('promoted_object') or {}).get('pixel_id') == '1033279451747443',
        'adset_maxvol_no_bid': not adset.get('bid_amount') and not (adset.get('bid_constraints') or {}),
        'adset_attribution_exact': adset.get('attribution_spec') == campaign_spec['adset_create']['attribution_spec'],
        'adset_regional_identity_exact': adset.get('regional_regulation_identities') == campaign_spec['adset_create']['regional_regulation_identities'],
        'adset_issues_clear': not adset.get('issues_info'),
    })
    spec_ads_by_name = {row['name']: row for row in campaign_spec['ads']}
    verified_videos = {str(item['video']['id']): item for item in video_readback['results']}
    ad_checks = []
    for ad in ads:
        spec = spec_ads_by_name.get(ad.get('name'))
        creative_id = str((ad.get('creative') or {}).get('id') or '')
        creative = creatives.get(creative_id) or {}
        feed = creative.get('asset_feed_spec') or {}
        story = creative.get('object_story_spec') or {}
        expected_videos = {str(row.get('video_id') or '') for row in (spec or {}).get('creative_payload', {}).get('asset_feed_spec', {}).get('videos', [])}
        actual_videos = {str(row.get('video_id') or '') for row in feed.get('videos') or []}
        row_checks = {
            'spec_found': spec is not None,
            'direct_create_no_source_lineage': str(ad.get('source_ad_id') or '0') == '0',
            'adset_binding': ad.get('adset_id') == adset.get('id'),
            'configured_active': ad.get('configured_status') == 'ACTIVE',
            'creative_binding': creative_id in creatives and str(creative.get('name') or '').startswith(str((spec or {}).get('creative_payload', {}).get('name') or '') + ' '),
            'copy_bodies': [item.get('text') for item in feed.get('bodies') or []] == EXPECTED_BODIES,
            'copy_titles': [item.get('text') for item in feed.get('titles') or []] == EXPECTED_TITLES,
            'copy_description': [item.get('text') for item in feed.get('descriptions') or []] == ['⭐⭐⭐⭐⭐'],
            'copy_cta': feed.get('call_to_action_types') == ['LEARN_MORE'],
            'url_exact': [item.get('website_url') for item in feed.get('link_urls') or []] == [EXPECTED_URL],
            'video_lineage_ready': len(actual_videos) == 2 and actual_videos.issubset(set(verified_videos)) and all((verified_videos[video_id].get('expected') or {}).get('asset_id') == (spec or {}).get('media', {}).get('asset_id') for video_id in actual_videos),
            'identity_exact': story.get('page_id') == '621037101089579' and story.get('instagram_user_id') == '17841418924864919',
            'effective_story_present': bool(creative.get('effective_object_story_id')),
            'standard_enhancements_absent': not has_key(creative, 'standard_enhancements'),
            'issues_clear': not ad.get('issues_info'),
        }
        ad_checks.append({'ad_id': ad.get('id'), 'ad_name': ad.get('name'), 'creative_id': creative_id, 'checks': row_checks})
    checks['all_ads_exact'] = len(ad_checks) == 3 and all(all(row['checks'].values()) for row in ad_checks)
    if not all(checks.values()):
        raise RuntimeError(json.dumps({'checks': checks, 'ads': ad_checks}, ensure_ascii=False))
    output = {
        'status': 'C31_FINAL_READBACK_VERIFIED',
        'campaign_id': campaign['id'],
        'adset_id': adset.get('id'),
        'ad_ids': [row['ad_id'] for row in ad_checks],
        'creative_ids': [row['creative_id'] for row in ad_checks],
        'checks': checks,
        'ads': ad_checks,
        'active_budget_usd_after': readback['active_budget_usd_after'],
        'projected_if_activated_usd': prewrite['projected_budget_if_activated_usd'],
        'effective_envelope_usd': prewrite['effective_envelope_usd'],
        'remaining_within_envelope_usd': prewrite['remaining_within_envelope_usd'],
    }
    (WORK / 'final-verification.json').write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'status': output['status'], 'campaign_id': output['campaign_id'], 'checks': len(checks), 'ads': len(ad_checks), 'active_budget_usd_after': output['active_budget_usd_after']}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

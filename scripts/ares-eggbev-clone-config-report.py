#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path('/root/mgs-agent')
OP_PATH = ROOT / 'data/ares/meta-ads/operations/Eggbev-US-CC-EN-BOT.json'
OP_V3_PATH = ROOT / 'data/ares/meta-ads/operations/Eggbev-US-CC-EN-BOT-v3.json'
ACCOUNT_PATH = ROOT / 'data/ares/meta-ads/accounts/1034081997659047.json'
ENGINE_PATH = ROOT / 'data/ares/meta-ads/engine-v3/config.json'
PROMPT_PATH = ROOT / 'data/ares/discord/thread-prompts/1543333373945053184.txt'
ACCOUNT_ID = '1034081997659047'


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def check() -> dict:
    operation = load(OP_PATH)
    operation_v3 = load(OP_V3_PATH)
    account = load(ACCOUNT_PATH)['accounts'][0]
    engine = load(ENGINE_PATH)
    cloning = operation['campaign_cloning_policy']
    expected_modes = {'pure_clone', 'clone_prestaged', 'clone_page_switch'}
    engine_modes = set(engine.get('supported_modes') or [])
    contract_modes = set(cloning.get('allowed_modes') or {})
    checks = {
        'thread_id': cloning.get('thread_id') == '1543333373945053184',
        'prompt_exists': PROMPT_PATH.exists() and bool(PROMPT_PATH.read_text().strip()),
        'account_registered': ACCOUNT_ID in (engine.get('accounts') or {}),
        'account_alias_matches': (engine.get('accounts') or {}).get(ACCOUNT_ID, {}).get('alias') == 'Eggbev-US-CC-EN-01-G006',
        'engine_release_3_3': engine.get('release_version') == '3.3.0',
        'engine_modes_complete': expected_modes <= engine_modes,
        'contract_modes_complete': expected_modes <= contract_modes,
        'v3_operation_account_matches': str(operation_v3.get('account_id')) == ACCOUNT_ID,
        'account_route_registered': account['runtime_routes']['campaign_cloning'].get('engine_account_registered') is True,
        'default_active_midnight': operation_v3['delivery_policy'].get('status') == 'ACTIVE' and operation_v3['delivery_policy'].get('start_time') == 'next_day_00:00_America/New_York',
        'manager_budget_selection': 'manager' in operation_v3['budget_policy'].get('selection', '').lower(),
        'financial_gate_preserved': 'Rodolfo/Geizian' in operation_v3['budget_policy'].get('write_authority', ''),
    }
    return {'status': 'ok' if all(checks.values()) else 'blocked', 'checks': checks}


def render() -> str:
    result = check()
    operation_v3 = load(OP_V3_PATH)
    modes = operation_v3['mode_contract']
    lines = [
        '🧬 **Eggbev-US-CC-EN — Configuração de Clonagem**',
        '',
        f"- Thread: `Eggbev-US-CC-EN Clonar Campanhas` (`{operation_v3['thread_id']}`).",
        f"- Conta: `{operation_v3['account_alias']}` | USD | `{operation_v3['timezone']}`.",
        f"- Engine: v{operation_v3['release_version']} | onboarding: {'OK' if result['checks']['account_registered'] else 'PENDENTE'}.",
        '- Modos: `duplicação exata`, `criativos novos`, `troca de página`.',
        '- Exata: preserva estrutura, público, placements, estratégia, Page, JSON, mídia, copy, links e UTMs.',
        '- Criativos novos: 1–5 ads, mídia aprovada/reconciliada/pre-stageada.',
        '- Troca de página: preserva mídia/copy; troca Page, pg/UTM e JSON; exige lineage dos ads.',
        '- Naming: nome-base original + `DUP01`, `DUP02`, `DUP03`…; dup de dup usa o próximo número livre.',
        '- Budget: escolhido e confirmado pelo gestor por campanha; write respeita o gate financeiro vigente.',
        '- Produção: `ACTIVE`, início no próximo dia às `00:00 America/New_York`.',
        '- Sem cron de clonagem. Cada request exige preflight, manifest prevalidado, resumo final, OK explícito e readback.',
        '',
        f"Readiness: `{result['status']}`",
    ]
    if result['status'] != 'ok':
        lines.append('Bloqueios: ' + ', '.join(key for key, value in result['checks'].items() if not value))
    return '\n'.join(lines) + '\n'


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()
    result = check()
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(render(), end='')
    return 0 if result['status'] == 'ok' else 2


if __name__ == '__main__':
    raise SystemExit(main())

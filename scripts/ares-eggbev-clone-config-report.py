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
    account_modes = set(((engine.get('accounts') or {}).get(ACCOUNT_ID) or {}).get('supported_modes') or [])
    contract_modes = set(cloning.get('allowed_modes') or {})
    main_page_policy = ((cloning.get('allowed_modes') or {}).get('clone_page_switch') or {}).get('target_page_selection') or {}
    v3_page_policy = ((operation_v3.get('mode_contract') or {}).get('clone_page_switch') or {}).get('target_page_policy') or {}
    page_switch_naming = v3_page_policy.get('campaign_naming') or {}
    prompt_text = PROMPT_PATH.read_text() if PROMPT_PATH.exists() else ''
    checks = {
        'thread_id': cloning.get('thread_id') == '1543333373945053184',
        'prompt_exists': PROMPT_PATH.exists() and bool(PROMPT_PATH.read_text().strip()),
        'account_registered': ACCOUNT_ID in (engine.get('accounts') or {}),
        'account_alias_matches': (engine.get('accounts') or {}).get(ACCOUNT_ID, {}).get('alias') == 'Eggbev-US-CC-EN-01-G006',
        'engine_release_3_4': engine.get('release_version') == operation_v3.get('release_version') == '3.4.1',
        'engine_modes_complete': expected_modes <= engine_modes,
        'account_safe_modes_enabled': {'pure_clone', 'clone_prestaged'} <= account_modes,
        'page_switch_fail_closed_before_write': (
            'clone_page_switch' not in account_modes
            and operation_v3['mode_contract']['clone_page_switch'].get('write_enabled') is False
            and account['runtime_routes']['campaign_cloning'].get('clone_page_switch_write_enabled') is False
        ),
        'contract_modes_complete': expected_modes <= contract_modes,
        'v3_operation_account_matches': str(operation_v3.get('account_id')) == ACCOUNT_ID,
        'account_route_registered': account['runtime_routes']['campaign_cloning'].get('engine_account_registered') is True,
        'default_active_midnight': operation_v3['delivery_policy'].get('status') == 'ACTIVE' and operation_v3['delivery_policy'].get('start_time') == 'next_day_00:00_America/New_York',
        'manager_budget_selection': 'manager' in operation_v3['budget_policy'].get('selection', '').lower(),
        'nicolas_budget_authority': 'Nicolas has standing Eggbev authority' in operation_v3['budget_policy'].get('write_authority', ''),
        'page_switch_requires_manager_page': v3_page_policy.get('required_from_manager') is True,
        'page_switch_automatic_inference_disabled': v3_page_policy.get('automatic_inference') is False and 'forbidden' in str(main_page_policy.get('automatic_selection') or '').lower(),
        'page_switch_missing_page_pauses': 'pause' in str(v3_page_policy.get('when_omitted') or '').lower() and 'pausar o intake' in prompt_text.lower(),
        'page_switch_missing_page_blocks_write': 'no Meta write' in str(v3_page_policy.get('write_gate') or ''),
        'page_switch_automatic_target_page_naming': (
            page_switch_naming.get('automatic') is True
            and 'target_page_sequence' in str(page_switch_naming.get('pattern') or '')
            and page_switch_naming.get('preserve') == 'source Cnnn only'
            and 'não selar manifest' in prompt_text.lower()
        ),
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
        '- Modos com write: `duplicação exata` e `criativos novos`; a substituição revisada é um branch explícito de `clone_prestaged`.',
        '- Exata: preserva estrutura, público, placements, estratégia, Page, JSON, mídia, copy, links e UTMs.',
        '- Criativos novos: 1–5 ads, mídia aprovada/reconciliada/pre-stageada.',
        '- Troca de página: **fail-closed antes de qualquer write Meta**. O modo saiu da allowlist desta conta após os erros live 1885090/2238280; permanece bloqueado até arquitetura determinística aprovada por Rodolfo.',
        '- Page obrigatória: se não vier no pedido, pausar e perguntar qual Page/pg exata será usada; nunca inferir automaticamente.',
        '- Substituição revisada: preserva a linhagem visual, rematerializa copy/evento/targeting aprovados e só deleta a fonte após readback completo da sucessora.',
        '- Naming comum: `pure_clone`/`clone_prestaged` preservam o nome-base e usam o próximo `DUPnn` livre.',
        '- Naming com troca de Page: automático para `[sequência da Page alvo] - [Page alvo] - ENG - US - ([pg alvo]) [Cnnn da fonte] [próximo DUPnn]`; sequência/Page/pg antigos são substituídos e somente `Cnnn` é preservado.',
        '- Budget: escolhido e confirmado por Nicolas por campanha; ele pode reduzir ou aumentar sem nova aprovação do Rodolfo, com pré-leitura e readback Meta.',
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

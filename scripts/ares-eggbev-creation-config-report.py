#!/usr/bin/env python3
"""Relatório determinístico da rota Eggbev Criar Campanhas."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parents[1]
OP_PATH = BASE / "data/ares/meta-ads/operations/Eggbev-US-CC-EN-BOT.json"
ACCOUNT_PATH = BASE / "data/ares/meta-ads/accounts/1034081997659047.json"
ENGINE_PATH = BASE / "data/ares/meta-ads/engine-v3/config.json"
MEDIA_PATH = BASE / "data/ares/meta-ads/engine-v3/media-registry.json"
OP_V3_PATH = BASE / "data/ares/meta-ads/operations/Eggbev-US-CC-EN-BOT-v3.json"


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def yes_no(value: bool) -> str:
    return "sim" if value else "não"


def build_report() -> str:
    op = load_json(OP_PATH)
    account_doc = load_json(ACCOUNT_PATH)
    engine = load_json(ENGINE_PATH)
    media = load_json(MEDIA_PATH)
    op_v3 = load_json(OP_V3_PATH)

    account = account_doc["accounts"][0]
    route = op["discord"]["route_contracts"]["campaign_creation"]
    structure = op["campaign_structure"]
    campaign = structure["campaign"]
    adset = structure["adset"]
    creation = op["campaign_creation_policy"]
    objective = op["objective_and_optimization"]
    budget = op["budget_policy"]
    creative = op["creative_policy"]
    runtime = account["runtime_routes"]["campaign_creation"]
    template = creation["message_template"]

    expected_ref = "act_1034081997659047"
    expected_id = "1034081997659047"
    if route["thread_id"] != "1541578556037927053":
        raise RuntimeError("thread_id canônico divergente")
    if account["meta_account_ref"] != expected_ref:
        raise RuntimeError("conta Meta canônica divergente")
    if op["account_timezone"] != "America/New_York":
        raise RuntimeError("timezone canônico divergente")

    engine_registered = expected_id in engine.get("accounts", {})
    from_zero_onboarded = "from_zero_prestaged" in (op_v3.get("supported_modes") or [])
    media_serialized = json.dumps(media, sort_keys=True)
    media_registered = expected_id in media_serialized or expected_ref in media_serialized or op["operation_id"] in media_serialized
    write_enabled = bool(runtime.get("write_enabled")) and engine_registered and media_registered

    placements_status = (
        "MANUAL_ONLY; a lista exata de posições ainda não está materializada no contrato "
        "canônico. Isso bloqueia manifest/write até importar e validar o payload aprovado; "
        "não copiar placements de outra operação."
    )

    lines = [
        "# Eggbev-US-CC-EN — configuração de Criar Campanhas",
        "",
        "## Escopo e readiness",
        f"- Thread: `{route['thread_name']}` (`{route['thread_id']}`).",
        "- Escopo: criação normal do zero. Clonagem fica exclusivamente na thread `1543333373945053184`.",
        f"- Conta: `{account['account_alias']}` (`{account['meta_account_ref']}`), ativa, USD, `America/New_York`.",
        f"- Estratégia/destino: `{account['strategy']}` / `{account['channel']}`.",
        f"- Contrato de criação aprovado: {yes_no(bool(runtime['contract_approved']))}.",
        f"- Runner Eggbev de criação construído: {yes_no(bool(runtime['runner_built']))}.",
        f"- Conta cadastrada no Engine v3: {yes_no(engine_registered)}.",
        f"- Modo `from_zero_prestaged` onboarded para Eggbev: {yes_no(from_zero_onboarded)}.",
        f"- Mídia Eggbev pre-stageada no registry v3: {yes_no(media_registered)}.",
        f"- Write de criação habilitado: {yes_no(write_enabled)}.",
        "- Estado real: a conta está onboarded no Engine v3 para clones. Intake, validação do briefing e preparação do resumo from-zero são possíveis, mas manifest executável/dry-run/write continuam bloqueados até onboardar `from_zero_prestaged`, construir o runner, materializar placements e pre-stagear a mídia.",
        "",
        "## Estrutura fixa",
        f"- Campaign: `{campaign['buying_type']}` | `{campaign['objective']}` | `{campaign['budget_level']}` | `{campaign['bid_strategy']}` | `{campaign['delivery_type']}`.",
        f"- Categoria especial: `{campaign['special_ad_category']}` — `{campaign['special_ad_category_country']}`.",
        f"- Estrutura: 1 campanha × {campaign['adsets_per_campaign']} ad set × {structure['ads_per_adset'][0]} ou {structure['ads_per_adset'][1]} anúncios (`1×1×3` ou `1×1×5`).",
        f"- Ad set: `{adset['name']}` | destino `{adset['conversion_location']}` | início padrão `{adset['start']}` | `{adset['end']}`.",
        f"- Público: `{adset['country']}`, {adset['minimum_age']}+, gênero `{adset['gender']}`, expansão={str(adset['targeting_expansion']).lower()}.",
        f"- Otimização: `{adset['performance_goal']}` | `{adset['conversion_count']}` | bid `{adset['bid_strategy']}` | value rules={str(adset['value_rules']).lower()}.",
        f"- Placements: {placements_status}",
        f"- Pixel: `{objective['pixel_name']}` (`{objective['pixel_id']}`), universal para esta operação.",
        f"- Advertiser/Payer: `{objective['advertiser_payer']}`.",
        "",
        "## Variáveis obrigatórias por solicitação",
        "1. Página Facebook e token `pg_XXXXX` reconciliados.",
        "2. Data/hora; padrão = próximo dia às `00:00` em `America/New_York`.",
        "3. Estrutura `1×1×3` ou `1×1×5`.",
        "4. Budget diário exato; criação normal não possui valor default.",
        "5. Criativos novos e linhagem Drive → Meta.",
        "6. Referência/template canônico de criação ou nomes de campanha/anúncios, copy completa, placements e tracking explicitamente fornecidos.",
        "7. Copy completa significa `Primary text`, `Headline`, `Description` e `CTA`.",
        "8. Links, `url_tags`/UTMs e qualquer exceção de público, placement ou estratégia.",
        "",
        "## Criativos e copy",
        f"- Fonte: `{creative['drive_operation']}/01_READY`, após reserva e reconciliação Meta × Drive.",
        f"- Origem: `{creative['creative_source']}`; criação normal exige criativo sempre novo e nunca reutilizado.",
        f"- Instagram: `{creative['instagram_account']}`; partnership ad={str(creative['partnership_ad']).lower()}.",
        f"- Advantage+ creative={str(creative['advantage_plus_creative']).lower()}; multi-advertiser={str(creative['multi_advertiser_ads']).lower()}.",
        "- Copy não é criativo: copy são os quatro campos textuais do anúncio; imagens e vídeos são os assets criativos.",
        f"- Naming de criação do zero: `{op['campaign_naming']['creation_from_zero']['status']}`; `DUPnn` é somente clone.",
        f"- Requisitos de naming: {', '.join(op['campaign_naming']['creation_from_zero']['required_before_manifest'])}.",
        f"- Referência canônica default: `{'N/D' if creation['creation_reference_policy']['default_reference_campaign'] is None else creation['creation_reference_policy']['default_reference_campaign']}`; ausente, pedir uma referência/template explícito sem escolher campanha silenciosamente.",
        "- Copy default: nenhuma; pedir campanha/template de referência ou os quatro campos.",
        f"- Tracking: {creation['tracking_policy']['links_and_utms']}; {creation['tracking_policy']['readback']}.",
        "",
        "## Messenger JSON obrigatório",
        f"- Tipo: `{template['template_type']}`.",
        f"- Texto: `{template['text'].replace(chr(10), ' / ')}`.",
        f"- Botão: `{template['button_type']}` | payload `{template['button_payload']}` | título `{template['button_title']}`.",
        f"- Performance booster={str(template['performance_booster_enabled']).lower()}; deprecate quick replies={str(template['ctm_deprecate_quick_replies_enabled']).lower()}.",
        "- Qualquer mudança no template exige mostrar a versão integral e obter aprovação de Nicolas.",
        "",
        "## Budget, status e publicação",
        f"- Budget: `{budget['daily_budget']}`; confirmar antes da criação e nunca assumir valor de referência.",
        "- Não existe budget fixo por modo: criação e clones exigem valor selecionado/confirmado pelo gestor para o pedido; o write financeiro continua sujeito ao gate vigente de Rodolfo/Geizian.",
        "- Produção normal aprovada: campanha, ad set e anúncios configurados `ACTIVE` com `start_time` futuro; entrega começa somente no horário aprovado.",
        "- Canário técnico: `PAUSED` até aprovação separada; não usar como padrão de produção.",
        "- Nunca publicar diretamente. A instrução atual do pedido vence prints e referências históricas.",
        "",
        "## Fluxo obrigatório",
        "1. Receber a solicitação e confirmar conta 01/autoridade.",
        "2. Validar página, `pg_XXXXX`, estrutura, budget, horário, copy e criativos novos.",
        "3. Validar pixel, payer, destino Messenger, JSON e placements exatos.",
        "4. Fazer preflight read-only e snapshot da conta/estado relevante.",
        "5. Reconciliar Drive × Meta, reserva, naming, sequência, links e UTMs.",
        "6. Materializar manifest idempotente com lock e request ID.",
        "7. Executar validate/plan/dry-run quando o runner, placements e mídia pre-stageada estiverem prontos; o onboarding v3 da conta já está concluído.",
        "8. Mostrar resumo final: página, horário/estrutura, budget, criativos, copy, JSON, naming, tracking e status.",
        "9. Esperar o OK explícito de Nicolas; existência da thread não autoriza write.",
        "10. Criar somente após todos os gates; recuperar falhas por readback-first, sem repetir POST às cegas.",
        "11. Fazer GET/readback de campanha, ad set, anúncios, creatives, status, start_time, budget, Page, tracking e JSON.",
        "12. Só então reportar sucesso e persistir auditoria/recovery data.",
        "",
        "## Separação de rotas",
        "- `pure_clone`, `clone_prestaged` e `clone_page_switch` não são criação normal e não são executados nesta thread.",
        "- Corte/ROAS, Diário e Limite de Leads entram apenas depois do lançamento e têm threads próprias.",
    ]
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="valida fontes e gera o relatório")
    parser.parse_args()
    print(build_report(), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

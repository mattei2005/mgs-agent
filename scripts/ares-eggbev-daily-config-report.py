#!/usr/bin/env python3
"""Relatório determinístico da configuração da rota Eggbev Diário."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parents[1]
OP_PATH = BASE / "data/ares/meta-ads/operations/Eggbev-US-CC-EN-BOT.json"
ACCOUNT_PATH = BASE / "data/ares/meta-ads/accounts/1034081997659047.json"


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def state(value: bool) -> str:
    return "sim" if value else "não"


def build_report() -> str:
    operation = load_json(OP_PATH)
    account_doc = load_json(ACCOUNT_PATH)
    account = account_doc["accounts"][0]
    route = operation["discord"]["route_contracts"]["daily_reporting"]
    policy = operation["daily_reporting_policy"]
    runtime = account["runtime_routes"]["daily_reporting"]

    if route["thread_id"] != "1541578596253175858":
        raise RuntimeError("thread Diário canônica divergente")
    if account["meta_account_ref"] != "act_1034081997659047":
        raise RuntimeError("conta Meta canônica divergente")
    if policy["timezone"] != "America/New_York":
        raise RuntimeError("timezone Diário divergente")

    meta_metrics = ", ".join(policy["required_meta_metrics"])
    sb_metrics = ", ".join(policy["requested_smart_bidding_metrics"])
    renderer = policy["renderer_contract"]
    anomaly = policy["revenue_anomaly_detection"]
    limitations = policy["remaining_limitations"]

    lines = [
        "# Eggbev-US-CC-EN — configuração do Diário",
        "",
        "## Escopo e conta",
        f"- Thread: `{route['thread_name']}` (`{route['thread_id']}`).",
        "- Escopo: relatórios Diário e sob demanda; não é a rota de criação, clone, ROAS ou limite de leads.",
        f"- Conta: `{account['account_alias']}` (`{account['meta_account_ref']}`), ativa, USD, `America/New_York`.",
        f"- Estratégia/destino: `{account['strategy']}` / `{account['channel']}`.",
        f"- Modo: `{policy['mode']}`; o Diário não executa qualquer write Meta.",
        "",
        "## Horários e rotas",
        "- Horário desenhado e aprovado para o Diário: `08:00 America/New_York`.",
        f"- Período principal: `{policy['primary_period']}`.",
        "- No mesmo run, o sinal atual de 08:00 compara somente snapshots de 08:00; nunca compara parcial atual com dia histórico fechado.",
        f"- Estado do schedule: `{policy['schedule_status']}`.",
        f"- Separação obrigatória: {policy['schedule_policy']}",
        f"- Relatório sob demanda a qualquer momento: {state(bool(policy['report_on_demand']))}.",
        "- O desenho de horário não liga automação: cron e post automático permanecem desabilitados até review do dry-run e autorização separada do Nicolas.",
        "- Escopo isolado em Eggbev; nenhum runner, prompt, regra ou schedule CPV é alterado.",
        "",
        "## Como obter dados atuais",
        "- Hoje/agora: `python3 scripts/ares-eggbev-daily-report.py --period today`.",
        "- Ontem: `python3 scripts/ares-eggbev-daily-report.py --period yesterday`.",
        "- Data específica: `python3 scripts/ares-eggbev-daily-report.py --period YYYY-MM-DD`.",
        "- Nunca reutilizar números de mensagens antigas; cada pedido consulta as fontes vivas.",
        "",
        "## Fontes e métricas",
        f"- Meta: {policy['sources']['meta']}.",
        f"- Métricas Meta contratadas: {meta_metrics}.",
        f"- Smart Bidding: {policy['sources']['smart_bidding']}.",
        f"- Pricing/monetização por campanha: {policy['sources']['pricing']}.",
        f"- Métricas Smart Bidding solicitadas: {sb_metrics}.",
        f"- Gate Smart Bidding: {policy['smart_bidding_policy']}.",
        "- `Custo/msg iniciada` usa somente `onsite_conversion.messaging_conversation_started_7d` da Meta.",
        "- RPS, CPM, EPC e demais métricas de monetização preferem campos diretos da Smart Bidding via vertical, Messenger Pages ou domain.",
        "- RPS/EPC calculados localmente são somente fallback explícito e rotulado quando a rota selecionada não expuser o campo direto.",
        "- ROI real/estimado ou dados sem freshness verificável aparecem `N/D`; nunca zero inventado.",
        "- A rota Messenger por campanha exige UTM Meta = UTM Smart Bidding e Meta Page ID = Smart Bidding `FB_PAGE_ID`; vertical/domain exigem mapping explícito equivalente de operação, identidade e período.",
        "- Em divergência válida, Meta Purchase ROAS vence ROI Smart Bidding; fonte ausente não vira divergência válida.",
        "",
        "## Fique de olho — anomalias de receita",
        f"- Estado: `{anomaly['status']}`; modo somente leitura.",
        f"- D-1 fechado: {anomaly['comparisons']['closed_day']}.",
        f"- Mesmo horário: {anomaly['comparisons']['same_clock']}.",
        f"- Baseline: até {anomaly['baseline_days']} snapshots; mínimo de {anomaly['minimum_comparable_samples']} comparáveis por página.",
        f"- Faixas iniciais de alerta: atenção a partir de {anomaly['warning_drop_percent']}% abaixo; crítico a partir de {anomaly['critical_drop_percent']}% abaixo.",
        "- As faixas geram somente alerta humano; não clonam, pausam, alteram budget nem configuram disparo/bloco/funil.",
        "- Freshness, data, UTM ou Page ID inválidos geram alerta de cobertura e `N/D`, nunca receita zero inventada.",
        f"- Saída visível: uma visão desktop consolidada em grupos de Página/UTM Z→A + no máximo {anomaly['maximum_visible_bullets']} bullets curtos abaixo.",
        "",
        "## Runtime atual",
        f"- Runner construído: {state(bool(runtime['runner_built']))}.",
        f"- Consulta sob demanda: {state(bool(runtime['report_on_demand']))}.",
        f"- Post automático habilitado: {state(bool(runtime['post_enabled']))}.",
        f"- Cron Diário habilitado: {state(bool(runtime['cron_enabled']))}.",
        f"- Writes habilitados: {state(bool(runtime['writes_enabled']))}.",
        "- Alterar cron ou post exige plano, aprovação explícita e readback de schedule/script/no_agent/deliver.",
        "",
        "## Ações proibidas nesta rota",
        f"- {policy['action_policy']}.",
        "- Criação, clone, cortes/reativações ROAS, limite de leads e Automated Rules pertencem às respectivas threads.",
        "",
        "## Renderer, cobertura e limitações",
        f"- Layout contratado: {policy['layout']}.",
        f"- Escopo de campanhas: {renderer['campaign_scope']}.",
        f"- Limite silencioso de linhas: {state(bool(renderer['silent_row_limit']))}.",
        f"- Truncamento do nome da campanha: {state(bool(renderer['campaign_name_truncation']))}.",
        f"- Identidade visual da campanha: {renderer['campaign_identity_display']}.",
        f"- Campos por campanha: {', '.join(renderer['per_campaign_fields'])}.",
        f"- Política sem entrega: {renderer['no_delivery_policy']}.",
        f"- Campos Meta por página: {', '.join(renderer['per_page_meta_fields'])}.",
        f"- Campos Smart Bidding por página: {', '.join(renderer['per_page_smart_bidding_fields'])}.",
        f"- Join técnico: {renderer['source_join']['primary']}; {renderer['source_join']['identity_confirmation']}.",
        f"- Freshness Smart Bidding visível: {', '.join(renderer['smart_bidding_freshness_visible'])}.",
        f"- Paginação: {renderer['pagination']}.",
        f"- Fixture de alto volume: {renderer['high_volume_fixture_campaigns']} campanhas, todas preservadas.",
        *[f"- Limitação {index}: {limitation}." for index, limitation in enumerate(limitations, start=1)],
    ]
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="valida as fontes e gera o relatório")
    parser.parse_args()
    print(build_report(), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

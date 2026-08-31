---
name: eggbev-campaign-creation
description: "Cria campanhas Eggbev BOT pelo Engine v3."
version: 1.0.0
author: Rodolfo Mattei, Ares
license: internal
platforms: [linux]
metadata:
  hermes:
    tags: [eggbev, meta-ads, campaign-creation, bot]
    related_skills: [meta-campaign-engine-v3]
---

# Eggbev Campaign Creation

Rota funcional para criar campanhas do zero na operação `Eggbev-US-CC-EN-BOT`. Não cobre clone, Corte e ROAS, Diário ou guardrails de página.

## When to Use

Use para pedidos na thread `1541578556037927053`, configuração da criação, intake, preparação, manifest, execução ou recovery de campanhas novas.

## Fontes canônicas

- Prompt exato: `data/ares/discord/thread-prompts/1541578556037927053.txt`
- Contrato da rota: `discord.route_contracts.campaign_creation` em `data/ares/meta-ads/operations/Eggbev-US-CC-EN-BOT.json`
- Contrato v3: `data/ares/meta-ads/operations/Eggbev-US-CC-EN-BOT-v3.json`
- Conta: `data/ares/meta-ads/accounts/1034081997659047.json`
- Configuração: `scripts/ares-eggbev-creation-config-report.py`
- Intake: `scripts/ares-eggbev-creation-intake-simulate.py`
- Runner: `scripts/ares-eggbev-creation.py`

## Disclosure progressivo

1. Leia primeiro o prompt exato e somente `discord.route_contracts.campaign_creation`.
2. Para pergunta de configuração, execute `python3 scripts/ares-eggbev-creation-config-report.py --check` e pare; não carregue o contrato inteiro.
3. Para intake, execute o simulador read-only e consulte apenas os campos ausentes.
4. Carregue `meta-campaign-engine-v3` somente depois de fechar Page, quantidade, budget, criativos, copy, horário e modo.
5. Nunca faça busca ampla por scripts: os três comandos acima são as rotas canônicas.

## Procedimento

1. Confirmar conta, Page, quantidade e budget exato sem herdar outra operação.
2. Reconciliar e reservar apenas os assets do request; mídia deve estar pre-stageada antes do manifest.
3. Materializar e prevalidar o manifest com o runner Eggbev.
4. Mostrar resumo final e aguardar o OK aplicável do request.
5. Executar exclusivamente pelo Campaign Engine v3.
6. Fazer readback consolidado e concluir o pós-processamento; recovery reutiliza request e IDs persistidos.

## Guardrails

- Criação do zero nunca usa a rota de clone nem mídia da campanha-modelo.
- Nenhum POST não idempotente é repetido sem readback.
- Cron não é criado dentro da transação. Qualquer cron futuro segue `context/cron-scheduling-policy.md`.
- Credenciais, IDs técnicos extensos e paths de audit não entram no texto humano.

## Verification

- manifest validado e digestado;
- Engine v3 é o único writer;
- Page, UTM, JSON, budget, status, start time e todos os anúncios confirmados por GET;
- inventário e reserva atualizados somente após readback.

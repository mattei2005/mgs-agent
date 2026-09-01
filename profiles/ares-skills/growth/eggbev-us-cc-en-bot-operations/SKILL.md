---
name: eggbev-us-cc-en-bot-operations
description: "Roteia operações Eggbev BOT para a função correta."
version: 1.0.0
author: Rodolfo Mattei, Ares
license: internal
platforms: [linux]
metadata:
  hermes:
    tags: [eggbev, usa, credit-cards, english, meta-ads, messenger, bot]
    related_skills: [eggbev-campaign-creation, eggbev-campaign-cloning, eggbev-roas-operations, eggbev-daily-reporting, eggbev-page-guardrails]
---

# Eggbev US-CC-EN BOT Operations

Camada de identidade, autoridade e roteamento da operação `Eggbev-US-CC-EN-BOT`. As regras funcionais ficam nas cinco skills dedicadas e nos prompts exatos das threads.

## When to Use

Use para pedidos gerais, regras, ownership, readiness ou para identificar a rota funcional correta. Em pedidos funcionais, carregue somente a skill da rota e pare de usar esta umbrella como contrato completo.

## Identidade e autoridade

```text
Operação    Eggbev-US-CC-EN-BOT
Conta       Eggbev-US-CC-EN-01-G006
Estratégia  BOT/Messenger; nunca tráfego direto por inferência
Gestão      Rodolfo Mattei e Nicolas
Timezone    America/New_York
Moeda       USD
```

Nicolas pode operar a conta e definir budgets Eggbev conforme a autoridade vigente, mas cada write exige valor exato, pre-read, request identificável e GET/readback. Billing, credencial, `account_spend_limit`, pixel crítico, ChatPion e expansão de escopo permanecem separados.

## Mapa determinístico de rotas

```text
Pedido / thread          Skill principal                 Dependência eventual
-----------------------  ------------------------------  ---------------------------
Regras / geral           esta skill                      nenhuma
Criar Campanhas          eggbev-campaign-creation       meta-campaign-engine-v3
Clonar Campanhas         eggbev-campaign-cloning        meta-campaign-engine-v3
Corte e ROAS             eggbev-roas-operations         meta-ads-intraday-operations
Diário                    eggbev-daily-reporting          meta-ads-intraday-operations
Página e Limites         eggbev-page-guardrails          meta-ads-intraday-operations
```

Threads fixas:

```text
Regras            1543280854024060999
Corte e ROAS      1541578606076231750
Diário             1541578596253175858
Criar Campanhas   1541578556037927053
Clonar Campanhas  1543333373945053184
Página e Limites  1543312825890381865
```

## Roteamento obrigatório

1. Classifique o pedido pela thread e pelo verbo principal.
2. Carregue uma única skill funcional.
3. A skill funcional abre somente seu prompt, nós de contrato e runner.
4. Carregue dependência genérica apenas quando a etapa realmente exigir.
5. Não buscar globalmente por scripts, snapshots ou regras históricas.
6. Se o pedido atravessar duas rotas, conclua a primeira e carregue a segunda explicitamente; não abra todas por antecipação.

## Fontes gerais

- Registry de rotas: `data/ares/discord/eggbev-fixed-routes.json`
- Contrato operacional: `data/ares/meta-ads/operations/Eggbev-US-CC-EN-BOT.json`
- Contrato Engine: `data/ares/meta-ads/operations/Eggbev-US-CC-EN-BOT-v3.json`
- Conta: `data/ares/meta-ads/accounts/1034081997659047.json`
- Prompts: `data/ares/discord/thread-prompts/<thread_id>.txt`

Abra o contrato operacional inteiro somente para auditoria estrutural da operação. Uma ação normal usa o nó exato declarado pela skill funcional.

## Invariantes transversais

- **Gate permanente de Page:** antes de criar, clonar, ativar ou reativar qualquer campanha/ad set/anúncio Eggbev, consultar `page_eligibility_policy` e a denylist canônica. Qualquer Page com histórico atual ou passado de restrição é inelegível; fazer zero write e solicitar outra Page. Fonte ausente, inválida ou identidade ambígua também falha fechada. Relatórios e pausas continuam permitidos. Esse gate é separado do critério DTR+SB do pause automático.
- Runtime/API/dados vivos vencem para estado atual; MGS OS vence para autoridade.
- Seção histórica não reativa regra supersedida.
- Criar/clone usam exclusivamente Campaign Engine v3.
- Original e tratado pertencem à mesma linhagem criativa.
- Falha após possível side effect exige readback e recovery no mesmo request; nunca repetir POST às cegas.
- Cron é gatilho, não fonte de estratégia. Criação ou alteração de cron segue `context/cron-scheduling-policy.md` e nunca ocorre dentro da transação de campanha.
- IDs técnicos e credenciais ficam em audit.

## Verification

- a thread resolve para exatamente uma skill principal;
- contrato, prompt e registry declaram a mesma skill;
- runner é conhecido antes da ação;
- nenhuma rota funcional depende de busca ampla;
- qualquer write tem readback real e audit correspondente.

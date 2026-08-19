---
name: meta-ads-account-visualization
description: "Visualização read-only de contas Meta Ads para Ares: conta, campanhas, adsets, ads, insights, creatives leves, pixels e relatório executivo sem expor token."
version: 1.0.0
author: Ares
license: internal
metadata:
  hermes:
    tags: [meta-ads, read-only, visualization, reporting, campaigns, mgs]
---

# Meta Ads Account Visualization — Ares/MGS

Use esta skill quando Rodolfo pedir para Ares acessar/visualizar uma conta Meta Ads, confirmar permissões read-only, listar campanhas/adsets/ads, puxar insights ou gerar relatório de auditoria da conta.

## Princípios

1. Read-only por padrão; não executar write por esta skill.
2. Nunca imprimir token Meta, app secret, cookie ou credencial no chat/log.
3. Buscar token no 1Password apenas internamente; se reportar, mostrar só item/campo/len/status.
4. Salvar dados brutos em `/root/mgs-agent/data/ares/meta-ads/audit/` e relatórios derivados em `/root/mgs-agent/data/ares/meta-ads/reports/`.
5. Usar throttle/backoff do `ares-meta-common.py` para todas as chamadas Meta API.
6. Evitar `object_story_spec` em massa em creatives; começar com leitura leve e buscar detalhes por creative/ad ID quando necessário.
7. Meta API é sensível a payload grande: por padrão, nunca pedir "tudo". Fazer poucas chamadas leves, com campos mínimos, e expandir apenas quando houver uma pergunta operacional específica.

## Fontes e scripts

```text
Arquivo / script                                                Uso
---------------------------------------------------------------- ---------------------------------------------
/root/mgs-agent/scripts/ares-meta-common.py                      token 1P + Graph GET + throttling/backoff
/root/mgs-agent/scripts/ares-meta-auth-check.py                  smoke read-only da conta
/root/mgs-agent/scripts/ares-meta-fetch-campaigns.py             inventário de campanhas
/root/mgs-agent/data/ares/meta-ads/accounts/<account_id>.json    config da conta
/root/mgs-agent/data/ares/meta-ads/metrics/*.json                mapping de métricas, subs e CPS
/root/mgs-agent/data/ares/meta-ads/audit/                        dumps auditáveis read-only
/root/mgs-agent/data/ares/meta-ads/reports/                      resumos derivados
```

## Fluxo read-only recomendado

1. Rodar auth check:

```bash
/root/mgs-agent/scripts/ares-meta-auth-check.py --account-id <ACCOUNT_ID> --out /root/mgs-agent/data/ares/meta-ads/audit/auth-check-<ACCOUNT_ID>-$(date -u +%Y%m%dT%H%M%SZ).json
```

2. Buscar inventário básico com chamadas leves e campos mínimos: campanhas, adsets, ads, insights e pixels usando `common.graph_get()`.
3. Para análises de período, preferir primeiro `insights` em nível `campaign` com summary e, se necessário, `time_increment=1`; não abrir creatives/adsets/ads detalhados se a pergunta é performance agregada.
4. Para creatives, primeiro usar campos leves:

```text
id,name,status,object_type,effective_object_story_id
```

4. Só buscar `object_story_spec` por ID ou em lotes pequenos quando houver necessidade real de revisar criativo/anúncio.
5. Derivar `subs` pela ordem definida por Rodolfo e `CPS = spend / subs`.
6. Responder com resumo executivo em tabela alinhada, sem despejar JSON bruto.

## Métricas canônicas atuais

### Operações Europa/GDPR

```text
Métrica | Definição
--------|------------------------------------------------------------
MO      | actions.complete_registration
CPMO    | spend / MO; se MO=0, CPMO nulo/não comparável
```

Para Espanha/Europa, não usar subscribe como norte intraday quando a Meta não expõe esse dado de forma confiável por GDPR/burocracias regionais. O norte operacional passa a ser `Complete Registration` no Ads Manager.

### Operações onde subscribe é confiável

```text
Métrica | Definição
--------|------------------------------------------------------------
subs    | primeira action válida na ordem canônica abaixo
CPS     | spend / subs; se subs=0, CPS nulo/não comparável
```

Ordem de `subs`:

```text
1. onsite_conversion.messaging_conversation_started_7d
2. onsite_conversion.total_messaging_connection
3. complete_registration
4. offsite_complete_registration_add_meta_leads
5. lead
6. offsite_conversion.fb_pixel_lead
```

## Throttling e rate limit

- Todas as chamadas devem passar por `ares-meta-common.py`.
- Há espaçamento mínimo entre chamadas para evitar rajadas.
- Ao detectar rate limit, backoff: 30s, 60s, 120s, 240s, e último intervalo limitado para completar no máximo 600s acumulados.
- Se ainda houver rate limit após 10 minutos acumulados, parar e alertar Rodolfo no canal/thread atual quando estiver em sessão interativa; em execução autônoma, registrar erro de rate limit para o cron/gateway entregar.

## Pitfalls

- **Status Deleted no Ads Manager × ARCHIVED na Graph API.** Na conta `Creditoparaveiculo-BR-CAR-BR-13-G006`, campanhas exibidas pelo Ads Manager sob `Campaign delivery = Deleted` retornam `status/effective_status/configured_status = ARCHIVED` na Graph API. Relatórios para gestor devem mostrar `DELETED`; audit técnico preserva `api_raw_status=ARCHIVED` e `ads_manager_status=DELETED`. Nunca contradizer a UI chamando essas campanhas de arquivadas sem explicar o mapeamento.
- **Status é hierárquico, mas o relatório operacional usa o nível campanha.** Campanha com `status=ACTIVE` continua sendo reportada como ativa. Se adset/anúncios estiverem pausados, registrar somente uma observação de inconsistência quando isso for relevante para entrega; não criar um status sintético. Pausa/reativação da operação deve ocorrer no nível campanha.
- `amount_spent`, `balance` e budgets vêm em unidade menor da moeda da conta em alguns endpoints; não interpretar sem normalização.
- `date_preset=today` depende do timezone da conta, não do VPS.
- `complete_registration` pode ser a primeira action válida hoje, mas nos últimos 7 dias pode aparecer `messaging_conversation_started_7d` antes na prioridade; sempre aplicar a ordem canônica.
- `adcreatives` com `object_story_spec` em massa pode retornar erro por payload pesado; usar leitura leve e detalhar por ID.
- Para a Meta API, legibilidade e velocidade não justificam payload amplo: pedir campos demais aumenta chance de erro e rate limit. A sequência correta é `mínimo necessário → resumo → detalhe por ID/lote pequeno`.
- Em análise de mês para thresholds intraday, poucas chamadas bastam: account light, campaigns light, adsets light, insights campaign summary e insights campaign daily.
- Não confundir acesso read-only com autorização para pausar/reativar; write exige aprovação explícita.

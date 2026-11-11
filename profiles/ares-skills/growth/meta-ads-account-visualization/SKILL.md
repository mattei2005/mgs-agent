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

Use esta skill quando um operador autorizado pedir para Ares acessar/visualizar uma conta Meta Ads, identificar a campanha mais recente em operação, consultar configuração de campanha/conjunto/anúncio, confirmar permissões read-only, listar objetos, puxar insights ou gerar relatório de auditoria da conta.

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

1. Resolver conta e credencial pelo catálogo positivo da operação e pelo binding vigente da conta no runtime; não presumir que o arquivo individual de `accounts/` seja a única fonte. Aplicar o checker de conta e validar identidade/BM/moeda/fuso no GET real antes de consultar os objetos. Rodar auth check com o item explicitamente vinculado:

```bash
/root/mgs-agent/scripts/ares-meta-auth-check.py --account-id <ACCOUNT_ID> --item '<item corporativo vinculado à conta>' --out /root/mgs-agent/data/ares/meta-ads/audit/auth-check-<ACCOUNT_ID>-$(date -u +%Y%m%dT%H%M%SZ).json
```

2. Buscar inventário básico com chamadas leves e campos mínimos: campanhas, adsets, ads, insights e pixels usando `common.graph_get()`.
3. Para análises de período, preferir primeiro `insights` em nível `campaign` com summary e, se necessário, `time_increment=1`; não abrir creatives/adsets/ads detalhados se a pergunta é performance agregada.
4. Para creatives, primeiro usar campos leves:

```text
id,name,status,object_type,effective_object_story_id
```

5. Só buscar `object_story_spec` por ID ou em lotes pequenos quando houver necessidade real de revisar criativo/anúncio.
6. Derivar `subs` pela ordem definida por Rodolfo e `CPS = spend / subs` quando o pedido envolver performance.
7. Responder em PT-BR com resumo executivo e bullets/blocos por nível no Discord, sem tabela Markdown crua nem JSON bruto. Em configuração, agrupar campos comuns aos anúncios uma única vez e separar apenas suas diferenças; informar horário da consulta no fuso da conta e que nenhuma alteração foi feita.

## Campanha mais recente e configuração por nível

- Para “última campanha rodando”, paginar as campanhas ativas e ordenar por `created_time` em código; mencionar empates de criação/lote em vez de inventar precedência temporal. `ACTIVE` comprova status, não entrega: confirmar impressões/gasto em Insights do período antes de afirmar veiculação.
- Para configuração, seguir a sequência `campanha → conjuntos/anúncios paginados → detalhes dos creatives únicos`. Conferir contagens e vínculos entre níveis antes de declarar cobertura completa. Receita e campos: `references/campaign-configuration.md`.
- Interpretar objetivo, evento de conversão e estratégia por campos reais, nunca pelos sufixos do nome; objetivo Vendas não implica otimização para compra, e uma marcação de app no nome não comprova destino app.
- Não converter campo ausente em “desativado”, “ilimitado” ou “automático confirmado”. Informar o que a API efetivamente retornou; traduzir códigos de idioma somente com mapping validado. HTTP 200 não valida a semântica de uma busca: resultados de interesses não são rótulos de locale.
- Inspecionar `degrees_of_freedom_spec.creative_features_spec` por recurso: `advantage_plus_creative=OPT_OUT` não significa todos os aprimoramentos desligados, pois recursos individuais podem permanecer `OPT_IN`.

## Inventário de criação, agendamento e UTMs para cadastro

- Para “criadas hoje e agendadas amanhã”, resolver as datas pelo relógio real no fuso do pedido e formar a união dos conjuntos por campaign ID. Informar separadamente criadas, agendadas e sobreposição; uma campanha que pertence aos dois conjuntos não vira duas campanhas.
- Fazer seleção e cobertura pelo catálogo positivo, resolver a credencial vinculada a cada conta e agrupar leituras por esse vínculo antes de consultar campanhas. Não usar uma credencial de uma família como default silencioso para contas sem binding; catálogo autorizado e grant remoto são provas diferentes.
- Ler primeiro identidade e campanhas leves em Graph Batch paginado; buscar anúncios e tracking somente das campanhas selecionadas. Reconciliar contas previstas, consultadas integralmente e indisponíveis, além das quantidades de campanhas/anúncios, antes de declarar completude.
- Extrair os valores do tracking efetivamente instalado, incluindo `url_tags`, links de `object_story_spec` e `asset_feed_spec.link_urls` quando presente; não gerar UTMs pelo nome. Preservar literalmente zeros e sufixos e deduplicar por domínio/chave/estratégia.
- Em inventário retrospectivo solicitado, não filtrar automaticamente campanhas pausadas ou anúncios rejeitados: valores já instalados podem precisar de cadastro, mas o relatório deve separar existência do tracking de aprovação/veiculação. Isso não autoriza anunciar como concluído um pedido de criação ainda pendente.
- Entregar todos os blocos de cadastro pedidos, um por domínio/estratégia, sem exigir `próximo`. A regra de um modelo por turno aplica-se à revisão interativa de modelos, não à entrega de um inventário consolidado. Formato canônico: `paid-acquisition-operations/SKILL.md`, seção de mensagem para Iris/AdOps.

Receita de coleta, campos e aceite: `references/scoped-generic-reporting.md`, seção `Inventário por criação/agendamento e extração de tracking`.

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

## Relatórios genéricos de contas, gastos, cobranças e faturas

Para contagem consolidada diária de campanhas novas SHEIN por gestor/site, carregar `direct-traffic-shein-operations` → `references/daily-creation-counts.md`; não herdar exclusões dos relatórios financeiros D-1/Intraday.

Seguir `references/scoped-generic-reporting.md` e o executor read-only `ares-scoped-report.py`. O plano nasce do cadastro positivo; indisponibilidade da Meta não autoriza consulta a outro portfólio, outro agente ou fonte administrativa. Não usar o audit global compartilhado como fonte de relatório.

## Relatório de BM por forma de pagamento

- Antes de consultar qualquer conta, use o catálogo positivo `data/ares/asset-scope.json` e exija `allowed=true` no checker `mgs-ares-asset-scope.py check-account <ID> --json`. O escopo atual Digital Trust prevalece sobre relatórios históricos e sobre as instruções genéricas de inventário abaixo: não reenumere outros portfólios nem amplie o catálogo por capacidade do token. Consulte somente os IDs autorizados e valide `business.id` no readback.
- Valide os nomes de fuso retornados pela Meta antes do lote Insights. Se a base IANA local não disponibilizar `Canada/Eastern`, calcule a data por seu alias equivalente `America/Toronto`, preservando o literal Meta no relatório; teste a equivalência de data/offset e retome apenas a etapa ausente, sem refazer a coleta já salva.
- `spend_cap=0` significa ausência de teto acumulado da conta nesse campo, não crédito ilimitado nem saldo disponível da linha de faturamento. Não derive limite da linha ou headroom de `balance`/`amount_spent`.
- Para repetir um relatório de billing, recupere o checkpoint/registry e somente a metodologia/artefato positivo registrado para Ares. Não procurar sessões, relatórios ou inventários privados de outros agentes como fallback. Se a referência anterior não tiver projeção autorizada, reconstruir a consulta exclusivamente pelas contas do cadastro positivo e pela credencial corporativa vinculada; falta de acesso produz cobertura indisponível, nunca busca de outro portfólio ou credencial administrativa.
- Para pedidos genéricos de contas, gastos, cobranças ou faturas, a seleção nasce exclusivamente de `data/ares/asset-scope.json`, sem descoberta global de contas/BMs. Deduplique o cadastro, aplique o gate antes de cada conta e valide `business.id` no readback. Leia somente os campos necessários da conta permitida; forma de pagamento atual e gasto publicitário não comprovam o instrumento efetivamente cobrado nem a existência de fatura. Não publique IDs de fontes, dados de cartão ou payload financeiro desnecessário. Campos/lançamentos não expostos ficam indisponíveis, nunca zero inventado nem fallback externo.
- Use Graph v26.0 e o helper comum `graph_batch_get` em lotes bounded, exclusivamente com filhos GET; o POST de transporte não é autorização de mutação. Valide HTTP/body, identidade/moeda e paginação de cada filho e salve progresso por lote sem URLs com tokens.
- Para gasto do mês, derive dia 1 e data atual no fuso de cada conta; consulte Insights account-level diário e agregado para o mesmo intervalo e reconcilie com Decimal. Consulte também contas sem fonte visível para medir a lacuna financeira; some moedas separadamente e conte contas com gasto versus zeradas em código.
- Informe que o dia corrente é parcial e que o agrupamento representa a **forma de pagamento atual**: gasto publicitário do mês não é cobrança liquidada no cartão nem prova de que toda a despesa foi faturada nessa fonte histórica. Liste contas com gasto e declare a contagem/valor comum das zeradas.

## Throttling e rate limit

- Todas as chamadas devem passar por `ares-meta-common.py`.
- Há espaçamento mínimo entre chamadas para evitar rajadas.
- Ao detectar rate limit, backoff: 30s, 60s, 120s, 240s, e último intervalo limitado para completar no máximo 600s acumulados.
- Se ainda houver rate limit após 10 minutos acumulados, parar e alertar Rodolfo no canal/thread atual quando estiver em sessão interativa; em execução autônoma, registrar erro de rate limit para o cron/gateway entregar.

## Pitfalls

- **Status Deleted no Ads Manager × literais terminais da Graph API.** Na conta `Creditoparaveiculo-BR-CAR-BR-13-G006`, edges de listagem já devolveram `ARCHIVED` para campanhas sob `Campaign delivery = Deleted`, enquanto o GET direto da C23 após `POST status=DELETED` em 25/08/2026 devolveu `status/effective_status/configured_status = DELETED`. Aceitar `DELETED` ou `ARCHIVED` como terminal, mostrar `DELETED` ao gestor e preservar o literal real em `api_raw_status` com `ads_manager_status=DELETED`. Nunca contradizer a UI chamando essas campanhas de arquivadas sem explicar o mapeamento.
- **Status é hierárquico, mas o relatório operacional usa o nível campanha.** Campanha com `status=ACTIVE` continua sendo reportada como ativa. Se adset/anúncios estiverem pausados, registrar somente uma observação de inconsistência quando isso for relevante para entrega; não criar um status sintético. Pausa/reativação da operação deve ocorrer no nível campanha.
- No edge `act_<id>/campaigns`, incluir `DELETED` em `effective_status` pode rejeitar toda a consulta com código 100/subcódigo 1815001 (objetos excluídos não aceitos). Para inventário por data de criação, pagine os estados aceitos `ACTIVE,PAUSED,ARCHIVED,IN_PROCESS,WITH_ISSUES`, deduplique por ID e filtre `created_time` no fuso/janela solicitados. `ARCHIVED` preserva os terminais expostos no edge; não prometa cobertura de objetos que a API não expõe. Teste live: lote das 12 contas Yolo/Mavroa paginado até esgotar cursores, com identidades e BM conferidas.
- `amount_spent`, `balance` e budgets vêm em unidade menor da moeda da conta em alguns endpoints; não interpretar sem normalização.
- `date_preset=today` depende do timezone da conta, não do VPS.
- `complete_registration` pode ser a primeira action válida hoje, mas nos últimos 7 dias pode aparecer `messaging_conversation_started_7d` antes na prioridade; sempre aplicar a ordem canônica.
- `adcreatives` com `object_story_spec` em massa pode retornar erro por payload pesado; usar leitura leve e detalhar por ID.
- Para a Meta API, legibilidade e velocidade não justificam payload amplo: pedir campos demais aumenta chance de erro e rate limit. A sequência correta é `mínimo necessário → resumo → detalhe por ID/lote pequeno`.
- Em análise de mês para thresholds intraday, poucas chamadas bastam: account light, campaigns light, adsets light, insights campaign summary e insights campaign daily.
- Não confundir acesso read-only com autorização para pausar/reativar; write exige aprovação explícita.

# Estratégia de corte sequencial por criativo — 24h

## Identidade

```text
strategy_id       CREATIVE_CUT_24H
strategy_version  1.0.0
scope             tráfego direto CPV, CBO 1×1×3
unidade de decisão intermediária  anúncio vinculado ao criativo
unidade de encerramento terminal  campanha
fonte da ideia     prática operacional relatada por Rodolfo/Nicolas
```

Esta referência formaliza uma estratégia de gerenciamento por campanha. Ela não altera a estrutura de criação, o evento, as UTMs, a reconciliação, o budget ou a origem dos criativos.

O ChatPion não integra esta estratégia. A prática externa foi apenas a origem histórica da hipótese; a execução pertence exclusivamente ao tráfego direto do Creditoparaveiculo.

## Escopo aprovado em 28/08/2026

- Conta-alvo: conta operacional **05** do Creditoparaveiculo BR-CAR-BR.
- A conta **13 não recebe esta estratégia** por esta decisão e preserva `CAMPAIGN_LEVEL_D1_D3` até nova instrução explícita.
- Estado inicial: `DOCUMENTED_NOT_ACTIVATED`.
- Ativação depende do readback da conta 05, dos IDs das três threads fixas, do contrato de budget/write e da atribuição explícita da estratégia às campanhas.
- Documentar a estratégia não cria campanha, cron, write Meta ou migração de campanha existente.

## Seleção por campanha

Cada campanha possui exatamente um `management_strategy` persistido antes do primeiro spend decisório:

```text
CAMPAIGN_LEVEL_D1_D3  estratégia tradicional no nível campanha
CREATIVE_CUT_24H      eliminação sequencial de anúncios por janelas de 24h
```

O modo de criação é independente da estratégia de gerenciamento. `from_zero_prestaged`, `clone_prestaged` e `pure_clone` podem receber qualquer modo autorizado, mas a atribuição precisa estar explícita no manifest/state/audit.

Campanha existente só entra em `CREATIVE_CUT_24H` após instrução explícita. A mudança começa uma janela nova e não reinterpreta dados anteriores como se já pertencessem à estratégia.

## Métricas e janelas

### ROI decisório

- Métrica: ROI real da campanha no Smart Bidding Adgroup.
- Moeda, revenue share e chave de junção devem estar reconciliados no contrato da conta.
- Fórmula: `(SUM(NET_REVENUE) - SUM(INVESTIMENT)) × 100 / SUM(INVESTIMENT)`.
- O ROI de cada estágio usa somente a janela iniciada no primeiro spend ou no último pause/readback; o acumulado completo continua visível, mas não substitui a janela pós-intervenção.
- ROI estimado, RPS e Meta ROAS são sinais auxiliares e não substituem o ROI real da campanha.

### Início de janela

```text
janela 1  primeiro spend positivo da campanha
janela 2  readback PAUSED do primeiro anúncio dominante
janela 3  readback PAUSED do segundo anúncio dominante
```

Cada decisão exige **24 horas completas** desde o início da janela correspondente. Falta de spend, atraso de fonte, divergência Meta×SB ou identidade incompleta falha fechado e não gera pause.

## Fluxo operacional

### Estágio A — três anúncios ativos

Após 24 horas completas:

1. Se `ROI real > 0`, manter os três anúncios. A campanha volta ao processo normal de escala no próximo checkpoint autorizado; não escalar imediatamente fora da agenda.
2. Se `ROI real = 0`, observar; nenhuma pausa automática.
3. Se `ROI real < 0`, calcular a participação de spend de cada anúncio dentro da janela.
4. A concentração fica comprovada quando:
   - o anúncio dominante possui pelo menos **80%** do spend; e
   - cada um dos outros dois possui no máximo **10%**.
5. Com ROI negativo + concentração comprovada, pausar somente o anúncio dominante, fazer GET/readback `PAUSED`, persistir a evidência e abrir a janela 2.
6. Sem concentração comprovada, não pausar anúncio nem campanha; enviar para revisão manual mantendo o estágio.

### Estágio B — dois anúncios ativos

Após 24 horas completas desde o primeiro pause confirmado:

1. Se `ROI real > 0`, manter os dois anúncios ativos e retomar a escala normal no próximo checkpoint autorizado.
2. Se `ROI real = 0`, observar; nenhuma pausa automática.
3. Se `ROI real < 0`, a nova concentração fica comprovada quando:
   - o dominante possui pelo menos **90%** do spend dos dois anúncios ativos; e
   - o outro possui no máximo **10%**.
4. Com ROI negativo + concentração comprovada, pausar o dominante, validar por GET e abrir a janela 3 com um anúncio ativo.
5. Sem concentração comprovada, não executar write; revisão manual obrigatória.

### Estágio C — um anúncio ativo

Após 24 horas completas desde o segundo pause confirmado:

1. Se `ROI real > 0`, manter a campanha e retomar a escala normal no próximo checkpoint autorizado.
2. Se `ROI real = 0`, observar; nenhuma decisão automática.
3. Se `ROI real < 0`, executar corte terminal no nível da campanha:
   - persistir a decisão;
   - pausar a campanha e confirmar por GET;
   - finalizar classificação, Drive e inventário dos três criativos;
   - somente depois enviar `status=DELETED` uma vez;
   - aceitar `DELETED` ou `ARCHIVED` no readback terminal.

## Classificação dos criativos

- Um anúncio pausado por ROI negativo + concentração comprovada recebe `evaluation_status=REJEITADO_CORTE_SEQUENCIAL_24H`.
- O asset só sai de `02_TESTING` quando não houver uso Meta ativo e Drive↔inventário↔Meta estiver reconciliado.
- O asset rejeitado vai para `05_REJECTED`; o pause não apaga a linhagem nem os IDs técnicos.
- Criativos subentregues permanecem `02_TESTING` enquanto continuam ativos e recebem sua própria janela; nunca são chamados de ruins antes do teste.
- Se a campanha recuperar com dois ou um anúncio, os sobreviventes continuam no lifecycle normal. `04_WINNERS` exige a política vigente de vencedor e não nasce apenas de uma janela positiva.
- No corte terminal, todos os três assets precisam fechar com estado consistente antes da exclusão da campanha.

## Estado obrigatório

```json
{
  "management_strategy": "CREATIVE_CUT_24H",
  "strategy_version": "1.0.0",
  "strategy_started_at": "ISO-8601",
  "current_stage": "THREE_ADS_ACTIVE",
  "window_started_at": "ISO-8601",
  "next_checkpoint_at": "ISO-8601",
  "active_ad_ids": [],
  "paused_ad_ids": [],
  "window_roi_pct": null,
  "window_spend": null,
  "spend_share_by_ad": {},
  "last_action": null,
  "last_readback_at": null
}
```

Estados válidos:

```text
THREE_ADS_ACTIVE
TWO_ADS_ACTIVE
ONE_AD_ACTIVE
RECOVERED_KEEP
MANUAL_REVIEW
TERMINAL_PENDING_CREATIVE_FINALIZATION
TERMINAL_COMPLETE
```

## Guardrails

- Pause intermediário é somente no nível do anúncio e somente para campanha explicitamente atribuída a `CREATIVE_CUT_24H`.
- Budget, ativação, escala e término continuam obedecendo à autoridade da operação.
- Anúncio pausado pela sequência não é reativado automaticamente na mesma campanha.
- Nunca pausar conjunto como substituto.
- Não usar ROI cumulativo antigo para avaliar uma janela pós-pause.
- Não inferir ROI por criativo: Smart Bidding decide no nível campanha; Meta ROAS ad-level é proxy auxiliar.
- Erro ambíguo exige GET antes de qualquer retry. Reutilizar o mesmo estado/request e escrever somente a camada ausente.
- Campanha sem estratégia registrada permanece no modo canônico da sua operação; silêncio nunca migra estratégia.

## Threads e reporting da conta 05

A conta 05 terá três threads fixas separadas:

```text
Intraday
Diário
Criar campanhas
```

Os IDs permanecem pendentes até Rodolfo criá-las e informá-las/readback real. Nenhum cron ou roteamento pode ser ativado com placeholders.

Diário e Intraday devem exibir `management_strategy`, estágio, início da janela, próximo checkpoint, anúncios ativos/pausados, ROI da janela e concentração por spend. Dados acumulados ficam separados dos dados da janela decisória.

## Checklist de ativação

- [ ] Meta account ID e alias exato da conta 05 confirmados por API
- [ ] moeda e timezone confirmados por API
- [ ] referência 1Password da conta registrada sem copiar segredo
- [ ] IDs das threads Intraday, Diário e Criar campanhas confirmados
- [ ] manager, budget, write mode e autoridade registrados
- [ ] campanha(s) piloto explicitamente atribuída(s) à estratégia
- [ ] state store e idempotência implementados
- [ ] dry-run com fixture 80/10/10, 90/10, recuperação e terminal aprovado
- [ ] readback Meta de pausa ad-level validado em canário PAUSED antes de produção
- [ ] crons permanecem ausentes/desabilitados até liberação específica

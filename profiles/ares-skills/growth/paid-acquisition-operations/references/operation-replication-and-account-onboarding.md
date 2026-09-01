# Replicação de operação e onboarding de nova conta

Use quando a MGS quiser “clonar o agente”, replicar uma operação validada para outra conta ou abrir uma operação semelhante na mesma vertical.

## Distinção obrigatória

- **Clone de operação/agente:** replica arquitetura, contratos, rotas, skills, runners, guardrails e método de auditoria.
- **Clone de campanha:** duplica objetos de mídia dentro de uma conta pelo Campaign Engine v3.

Nunca tratar os dois como o mesmo pedido.

## Princípio central

> Copiar a arquitetura; parametrizar a operação alvo; nunca copiar estado técnico da operação fonte.

Mesma vertical não autoriza herdar conta, autoridade, budget, threshold, Page, evento, copy, JSON, horários ou automações sem validação explícita.

## Três classes de informação

### 1. Arquitetura replicável

- separação de identidade, operação, execução e continuidade;
- rotas funcionais distintas para regras, criação, clone, performance/ROAS, relatório e guardrails de Page quando a complexidade justificar;
- uma skill e um prompt específico por rota;
- contrato operacional e contrato Engine por operação;
- manifest → validate → plan → resumo final → OK → execute → readback;
- recovery readback-first no mesmo request;
- Drive × Meta × inventário;
- state, audit, locks e reports isolados;
- crons determinísticos `no_agent=true`;
- Knowledge Registry, checkpoints e supersessão explícita.

### 2. Parâmetros que precisam ser fechados novamente

- operation_id, site, domínio, país, vertical, idioma e estratégia;
- alias, moeda, timezone, app/tier e capabilities da conta;
- owners, gestores, autoridade de budget e aprovação de início imediato;
- objetivo, evento, CBO/ABO, bid strategy, estrutura e placements;
- Page/PBIA, UTM, destino, copy e Messenger JSON;
- pasta, formatos e política de criativos;
- thresholds, horários, limites, Fase 3 e políticas de reativação;
- threads, participantes, schedules e destinos de relatório.

### 3. Estado proibido de copiar

- tokens, cookies, credenciais e referências de billing;
- account/Page/pixel/campaign/adset/ad/creative/media/source IDs da fonte;
- request IDs, cron IDs, thread IDs, leases, locks e states resumíveis;
- denylist, holds, baselines, snapshots, métricas e performance históricas;
- autorização financeira ou autonomia concedida apenas à operação fonte.

## Sequência de onboarding

1. **Aprovar identidade e ownership.** Novo profile/agente é mudança estrutural; nova operação na arquitetura existente também precisa owner e escopo explícitos.
2. **Registrar e validar a conta read-only.** Confirmar status, moeda, timezone, capabilities, Page access, app/tier e fonte de credencial sem expor segredo.
3. **Criar contratos isolados.** Começar fail-closed; declarar `supported_modes`, `ad_serving_route`, Page policy, naming, budget/start gates e lineage requirements.
4. **Criar rotas Discord.** Registrar IDs próprios, prompts e skills; confirmar membros obrigatórios por readback; preservar histórico e títulos manuais.
5. **Materializar relatórios read-only.** Validar Meta, Smart Bidding, UTM, Page, freshness e métricas antes de qualquer writer.
6. **Preparar criação/clone.** Reconciliar criativos, pre-stagear mídia, materializar manifest, executar validate/plan e mostrar resumo final.
7. **Executar canário pequeno.** PAUSED quando técnico, ou ACTIVE futuro somente sob autorização; validar todos os níveis por GET.
8. **Provar serving real.** `ACTIVE`/sem issues não basta: confirmar impressão, gasto ou outro insight real.
9. **Liberar controlled-write.** Começar com mudança pequena, reversível e account-scoped.
10. **Liberar automação por último.** Inventariar schedulers, escolher minutos sem colisão, aplicar locks, observar o primeiro tick e fazer readback do cron.

## Roteamento funcional recomendado

Para operações BOT/Meta com criação, otimização e proteção de Page, considerar seis rotas:

1. Regras/identidade;
2. Criar campanhas;
3. Clonar campanhas;
4. Corte/ROAS;
5. Diário/read-only;
6. Page e limites.

A rota de Regras não executa trabalho funcional. Cada pedido carrega uma única skill principal; dependências genéricas entram somente quando a etapa exigir.

## Gates antes de copiar uma operação validada

- Comparar versão do Engine central, contrato da operação e validador de configuração. Qualquer drift bloqueia onboarding até reconciliação; nunca copiar um contrato stale.
- Revalidar `supported_modes` na conta alvo. Um modo que funcionou na fonte pode falhar por Page, PBIA, promoted object, app tier ou serving route.
- Não promover `clone_page_switch` ou outro fluxo de troca de identidade apenas porque schema/plan aceita. Exigir canário live e arquitetura determinística aprovada.
- Revalidar JSON/template, placements e evento na conta alvo; nenhuma evidência de outra conta substitui readback local.
- Autoridade de budget e início imediato é operation-scoped, nunca transferida implicitamente.

## Validação pós-write

Confirmar por readback:

- campaign: nome, status, effective status, budget, start e objetivo;
- ad set: Page promovida, evento, targeting e placements;
- ads: quantidade, nomes, status, issues e lineage quando exigida;
- creatives: Page/PBIA, mídia, copy, CTA, JSON/template e URL tags;
- inventário: asset/checksum/Drive/IDs Meta e lifecycle;
- delivery: impressão/gasto antes de declarar que está rodando.

## Recovery

Quando houver possível side effect:

1. reler checkpoint/state;
2. consultar objetos persistidos;
3. reconciliar nomes, IDs e filhos;
4. corrigir somente payload/camada divergente;
5. criar apenas o ausente;
6. fazer readback final;
7. manter o mesmo request e preservar audit.

Nunca repetir POST não idempotente às cegas nem abrir um segundo request para esconder a falha.

## Critérios de go-live

- conta e autoridade validadas;
- contratos e rotas isolados;
- skills/prompts alinhados;
- Page/UTM/PBIA/evento/placements comprovados;
- Drive e inventário reconciliados;
- manifest validado e dry-run revisado;
- canário concluído com readback e serving real;
- recovery testado;
- crons sem colisão e com lock;
- relatórios na thread correta;
- Knowledge Registry/checkpoint/REPORT-INFRA atualizados quando aplicável.

## Pitfalls

- Não clonar uma conta apenas porque pertence à mesma vertical.
- Não usar uma campanha live da fonte como prova de compatibilidade da conta alvo.
- Não confundir `ACTIVE` com delivery.
- Não copiar denylist, performance, baselines ou holds.
- Não criar cron dentro da transação da campanha.
- Não transformar teste emergencial de reativação ou gasto em regra permanente sem política própria aprovada.

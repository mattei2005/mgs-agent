---
name: chatpion-bot-campaign-operations
description: "Opera campanhas Meta BOT/Messenger por contrato."
version: 0.1.1
author: Rodolfo Mattei, Ares
license: internal
platforms: [linux]
metadata:
  hermes:
    tags: [chatpion, bot, messenger, meta-ads, campaign-ops]
    related_skills: [meta-campaign-engine-v3, meta-ads-intraday-operations]
---

# ChatPion BOT Campaign Operations

Contrato operacional reutilizável para campanhas Meta com destino Messenger apoiadas por uma estrutura ChatPion/DigitalTrChat. A skill controla Campaign Ops, relatórios e guardrails; não configura usuários, flows, drip, broadcast ou infraestrutura do ChatPion/DigitalTrChat.

## When to Use

Use quando uma operação estiver vinculada à família `chatpion_bot_messenger` e o pedido tratar de:

- regras e readiness da operação;
- criação ou clonagem de campanhas Meta;
- Corte e ROAS;
- Diário e relatórios read-only;
- elegibilidade, restrições e limites de Page;
- alteração durável da estratégia ou de um parâmetro operacional;
- sincronização das projeções canônicas nas threads Discord.

Não use para tráfego direto, quiz/SMS ou configuração do ChatPion/DigitalTrChat.

## Fontes canônicas

- Família: `data/ares/meta-ads/strategy-families/chatpion-bot-messenger.json`
- Consumidores: `data/ares/meta-ads/strategy-families/chatpion-bot-messenger-consumers.json`
- Operação: caminho `operation_contract` resolvido no registro de consumidores
- Conta: caminho declarado pelo contrato da operação
- Threads: registry e prompts declarados pelo consumidor
- Engine de criação/clone: `meta-campaign-engine-v3`
- Política global de limites internos: `data/ares/meta-ads/policies/global-budget-limit-policy.json`
- Estado real: APIs, runtime, state e audit da operação

Enquanto a política global estiver `INACTIVE_UNTIL_EXPLICIT_REACTIVATION`, nenhum cap, piso, envelope, pool ou teto interno pode bloquear ou reduzir um pedido autorizado de qualquer consumidor ChatPion. O budget exato continua obrigatório; autoridade, pre-read/readback, billing, `account_spend_limit`, credenciais e automatic scaling permanecem separados.

Nunca inferir identidade, conta, Page, UTM, budget, threshold, horários, autoridade, cron ou write-enabled a partir desta skill.

## Resolução obrigatória

1. Resolver a thread ou `operation_id` no registro de consumidores.
2. Confirmar que o consumidor está `active`; candidato de onboarding não é operação ativa.
3. Abrir o contrato da família e o contrato exato da operação.
4. Carregar somente a rota pedida: `rules`, `campaign_creation`, `campaign_cloning`, `roas_cycle`, `daily_reporting` ou `page_guardrails`.
5. Consultar conta, runner, state e audit declarados pela operação somente quando a rota exigir.
6. Falhar fechado quando houver binding ausente, ambíguo ou divergente.

## Responsabilidade operacional e encaminhamentos

Ares é responsável por conduzir os pedidos de Campaign Ops nas próprias threads, incluindo reconciliação de conta, finalidade, contratos e instruções dentro da autoridade vigente. Não mencionar nem transferir rotineiramente a Zeus a gestão de campanhas ou ajustes operacionais que Ares pode resolver. Divergência entre registro antigo e decisão autorizada não cria, por si só, uma dependência de Zeus: reconciliar as fontes no escopo permitido, preservando histórico e os gates próprios de publicação e budget. Encaminhar somente quando houver bloqueio real fora da autoridade ou capacidade de Ares, ou pedido explícito do usuário; nunca tratar o encaminhamento como conclusão. Esta autonomia não amplia contas, permissões, orçamento, credenciais ou Critical Subset.

## Definição de conta e finalidade da thread

Quando o operador apenas definir a conta e a finalidade de uma conversa:

1. Separar nome operacional, ID literal e observações internas. Não promover texto entre parênteses a alias operacional sem confirmação explícita; uma nota de referência não determina conta, estratégia, naming ou roteamento.
2. Validar o ID no checker de escopo corporativo e registrar o binding específico da thread na fonte canônica. Não usar a conta histórica do canal pai como fallback quando a declaração atual aponta outra conta.
3. Registrar somente o escopo solicitado. Definir uma thread para criação, clone ou duplicação não solicita execução Meta, migração de rotinas, ativação, budget ou automação, nem comprova readiness do contrato.
4. Se o operador corrigir a classificação de uma observação, corrigir o binding canônico e superseder explicitamente a interpretação anterior. Preservar nome e ID operacionais; não ampliar a correção a outras contas ou threads por semelhança de rótulos.
5. Validar o registro e responder brevemente com a conta e a finalidade confirmadas. Manter observações internas fora da identificação operacional; deixar preflight live e contrato exato para o pedido de execução correspondente.

## Precedência

```text
pedido atual explícito e autorizado
→ override ativo do contrato da operação
→ mecanismo da família
→ runtime/API para estado vivo
→ histórico somente para auditoria
```

Um parâmetro específico nunca sobe automaticamente para a família. Uma regra familiar nunca copia state, IDs ou autorização entre consumidores.

## Classificação de mudanças

### Mudança de família

É mudança no mecanismo reutilizável: sequência de gates, semântica de uma rota, contrato de readback, recovery, estrutura de aprovação ou política de projeção.

- atualizar skill e contrato da família;
- validar todos os consumidores ativos;
- atualizar as rotas afetadas e a thread Regras de cada consumidor;
- não copiar valores, IDs, schedules ou autoridade entre operações.

### Mudança de operação

É mudança de valor ou exceção: threshold, horário, budget, Page, evento, layout, hold, cron, fonte, autoridade ou capability de uma operação.

- atualizar somente o contrato, runtime e prompts da operação afetada;
- atualizar a rota funcional afetada e a thread Regras desse consumidor;
- não alterar outros consumidores;
- registrar a versão anterior como superseded.

### Regra de extração

Quando uma mudança específica revelar um procedimento reutilizável, promover somente o procedimento para a família. O valor continua no contrato da operação.

## Rotas funcionais

### Regras

Mantém identidade, autoridade, precedência, readiness e mapa das rotas. Não executa trabalho funcional de outra rota.

### Criar campanhas

Fluxo: preflight vivo → Page/UTM → criativos reconciliados → pre-stage → manifest → validate/plan → resumo final → OK do request → Engine v3 → GET/readback. Defaults e campos obrigatórios vêm do contrato da operação.

### Clonar campanhas

O contrato da operação declara os modos suportados. Fonte, colisão de naming, Page, mídia, copy, JSON, budget e start são lidos ao vivo. Reconcilie a hierarquia com paginação completa e conte conjuntos/anúncios e seus estados em código; um sufixo no nome da campanha não comprova quantidade nem autoriza reativar filhos pausados. Schema/plan não prova readiness live; recovery reutiliza request e IDs.

### Corte e ROAS

A família define isolamento, idempotência, proveniência, lane de corte e lane de reativação. Thresholds, comparadores, fases, horários, níveis de write, métricas e budgets são parâmetros obrigatórios da operação.

### Diário

Rota read-only. Período, schedule, fontes, joins, métricas, renderer e postagem automática são definidos por operação. Ausência, staleness ou ambiguidade vira `N/D`, nunca zero inventado.

### Page e limites

A família exige identidade exata, freshness, plano idempotente, fail-closed e readback. Métrica, threshold, Page policy, hold, ações e schedules pertencem à operação.

## Invariantes de execução

- Original e tratado são uma única linhagem criativa.
- Criação e clone usam somente o Campaign Engine v3.
- Mídia nova é enviada para a Meta somente depois que o pedido resolve a conta exata; BOT exige vertical+square e usa pipeline paralelo. Reconciliar títulos determinísticos uma vez por lote, reutilizar variante parcial, subir somente a ausente, dividir wait-ready em chunks de 50 e verificar associação uma vez antes de gravar o registry. Nunca pre-stage global ou upload para contas inferidas.
- BOT não pode depender de importar/atribuir o acervo de aproximadamente 3 mil Pages a um Business Manager. Cada perfil anunciante usa seu próprio User Access Token porque é essa identidade que enxerga as Pages linkadas; System User, token compartilhado ou token de outro anunciante são fallbacks proibidos. Resolver somente o `pg_XXXXX` pedido, obter `access_token` por GET direto da Page, mantê-lo apenas em memória, validar PBIA e remover o token antes de persistir state/audit.
- Todo write exige autoridade, pre-read, request persistido e GET/readback.
- Falha após possível efeito parcial inicia recovery readback-first; nunca repetir POST às cegas.
- `ACTIVE` não prova serving; exigir impressão, gasto ou insight real quando a afirmação for de entrega.
- Credenciais, IDs técnicos extensos e billing permanecem fora do texto humano.
- Cron é gatilho, não fonte de estratégia, e segue a política global anti-colisão.
- Configuração do ChatPion/DigitalTrChat permanece fora do escopo padrão do Ares.

## Sincronização das threads

Uma alteração durável aprovada inclui, no mesmo request, a atualização das projeções Discord correspondentes; não exige uma segunda confirmação apenas para refletir a regra já aprovada.

1. Classificar `family` ou `operation`.
2. Persistir e validar primeiro a fonte canônica.
3. Executar `scripts/ares-chatpion-bot-strategy-sync.py --check` para detectar drift.
4. Atualizar prompt/config local da operação.
5. Projetar a mudança na rota funcional afetada e em `rules`.
6. Fazer GET/readback de cada mensagem criada/editada.
7. Persistir IDs/digests e audit da projeção.

A sincronização edita somente a mensagem de projeção controlada pelo Ares. Mensagens humanas, eventos de sistema, rotas e histórico não são deletados. Limpeza destrutiva exige autorização própria e não faz parte do sincronizador.

## Onboarding de nova operação

1. Registrar identidade, ownership, escopo e autoridade sem copiar state da fonte. Separar vínculo da thread, aprovação de onboarding, delegação financeira/ativação e OK final do request; uma camada não comprova as demais. Interpretar uma confirmação curta pelo pedido de aprovação ao qual ela responde, sem usá-la para resolver outra pergunta pendente de horário.
2. Validar conta e capabilities em read-only, incluindo Business, moeda e timezone. Resolver a Page pela hierarquia da campanha exata. Acesso à conta não comprova acesso à Page nem identifica, sozinho, o perfil anunciante correto; não transformar um token que lê a conta em credencial operacional por conveniência.
3. Criar contrato isolado começando fail-closed. Se houver cadastro parcial, manter o consumidor como candidato, sem modos executáveis ou credencial presumida, até validar as dependências. Registrar separadamente autoridade aprovada e readiness pendente, para não cobrar novamente uma autorização já concedida. Receita e aceite: `references/operation-contract-schema.md`, seção de cadastro parcial.
4. Registrar threads, prompts e membros obrigatórios sem alterar consumidores ou rotas de outras contas.
5. Validar relatórios read-only e as dependências necessárias à modalidade solicitada; não usar erro de Page como prova automática de scope ausente nem ampliar permissões no onboarding sem o gate próprio.
6. Preparar criação/clone por manifest somente após readiness. Manter o request original e os parâmetros literais durante a preparação; resolver ambiguidades comerciais e apresentar o resumo para OK antes do write.
7. Executar canário somente com autorização específica e distinguir status configurado de serving comprovado.
8. Liberar controlled-write somente após os gates aplicáveis e verificar que contas e consumidores preexistentes permaneceram inalterados.
9. Liberar automação por último, após inventário de cron e autorização própria. No fechamento, distinguir cadastro salvo, validação read-only, execução liberada e campanha efetivamente criada; configuração parcial nunca é onboarding concluído.

Nunca herdar implicitamente IDs, budgets, thresholds, Pages, pixels, eventos, JSON, horários, denylist, holds, baselines ou autonomia financeira.

## Verification

- skill e contrato da família não contêm identidade de consumidor;
- consumidor resolve para um único contrato e conjunto de threads;
- onboarding parcial permanece candidato e falha antes do transporte; autoridade aprovada não é confundida com readiness ou OK de publicação;
- conta e Page são verificadas separadamente, e a contagem da hierarquia vem da API, não do nome da campanha;
- nome operacional + ID com nota interna entre parênteses mantém o mesmo binding e não cria alias a partir da nota;
- definição de finalidade da thread não dispara execução, e correção de nota interna não altera a conta nem outras threads;
- cada parâmetro obrigatório tem origem explícita na operação;
- mudança de operação afeta somente um consumidor;
- mudança de família valida todos os consumidores ativos;
- rota funcional e Regras têm projeção com digest/readback;
- existe somente uma versão ativa por chave canônica;
- testes de arquitetura, prompts e operação passam sem Meta write.

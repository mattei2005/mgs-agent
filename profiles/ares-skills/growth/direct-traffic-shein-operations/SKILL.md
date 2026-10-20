---
name: direct-traffic-shein-operations
description: Use quando Ares operar tráfego direto SHEIN nos EUA.
version: 0.2.3
author: Rodolfo Mattei, Hermes Agent
license: Proprietary
platforms: [linux]
metadata:
  hermes:
    tags: [mgs, ares, shein, direct-traffic, meta-ads, campaign-ops]
    related_skills: [paid-acquisition-operations, creative-operations-mgs, creative-taxonomy-mgs, meta-campaign-engine-v3]
---

# Direct Traffic SHEIN Operations — MGS/Ares

Skill específica da vertical SHEIN em tráfego direto Meta para os Estados Unidos. Ela isola o segmento SHEIN das regras operacionais de financiamento veicular: ambos usam tráfego direto, mas não compartilham contas, nomes, eventos, bids, budgets, schedules, learning policy, relatórios, criativos ou automações.

## Padrão global vigente — todas as 36 contas SHEIN

Por autorização explícita de Rodolfo nesta Diretoria e reforço na mensagem `1561784289786466416`, as últimas mudanças passaram a valer para **todos os seis sites, seis gestores e 36 threads Intraday**, não somente YOLO. Fonte única: `SHEIN-US-DIRECT.json#/reporting/on_demand_default_layout/account_report_overrides` e perfil `format_profiles.SHEIN_ALL36_UNIFORM_G001_CAPS_V1`, política `ARES-SHEIN-ALL36-UNIFORM-CAPS-20261019`. Cada binding conta/nome/thread precisa coincidir com o catálogo e o GET Meta atual.

Colunas vigentes para próximos snapshots: **R/E → Início → Nº → St → Produto → Quiz → RPS → Bid → Gasto → B.U.% → Rev → Saldo → Health → ROI → ROI E. → ROAS → Lance**. Grade principal fixa de 157 posições visuais, Nº13, Produto12 sem reticências, separadores nas mesmas posições nos 36 relatórios. **St:** ACTIVE=A, PAUSED=P, DELETED=D, ARCHIVED=A apenas na apresentação; manter os estados técnicos distintos. **RPS:** copiar da coluna visível da dash SB por conta/campanha/data/moeda, sem API/fórmula local. **B.U.%:** gasto Meta da campanha no dia civil do relatório/daily_budget Meta da própria campanha ×100, conforme vigência de `account_budget_display_overrides` e `budget_used_standard`; não é orçamento restante. **Principal:** ROI estimado real decrescente, n/d ao final. **Histórico:** número da campanha crescente, sete datas e Média7d. Marcadores COPY continuam; avisos de origem somente no audit.

Tetos de exibição somente nas linhas principais: ROI/ROI E.999,99% sem `+`, negativos com `-`; ROAS9,99x; Rev9.999,99. Dados brutos, cores, soma, ROI consolidado, ranking e histórico não recebem teto. Rodapé curto explica a limitação visual. Nunca truncar outro número nem alargar automaticamente a grade: validar perfil antes da publicação e tratar eventual exceção explicitamente.

Lote global exige fontes novas por conta/publisher, gate dos seis domínios, identidade/moeda/timezone Meta, RPS UI com filtros e paginação completos, 36IDs de conta/thread únicos e seis relatórios por gestor/site. Contas sem entrega conservam os cabeçalhos principal/histórico e n/d de receita/ROI, sem linhas inventadas. Distinguir zero SB explícito de linha ausente. Persistir cada fonte/modelo/recibo e confirmar cada parte por GET. Retomar somente a fonte/parte ausente após falha, com journal e nonce. Pedido de relatórios novos não autoriza excluir antigos, criar cron, mudar Meta ou republicar em outro destino. O rollout foi exercitado com 87 testes e entrega integral dos36bindings; contagens incidentais de campanhas/partes não são defaults.

### Budget Used — padrão global36 aprovado

Rodolfo aprovou expressamente a extensão de **B.U.% às36contas/threads SHEIN**, seis sites e seis gestores, na thread `1558146725376557126`, após a confirmação de escopo associada à mensagem `1561845294080204821`. Fonte única: `on_demand_default_layout.budget_used_standard` e `account_budget_display_overrides`, política `ARES-SHEIN-ALL36-BUDGET-USED-20261019`. Aplicar prospectivamente pelo horário financeiro registrado no contrato; `previous_rule` conserva a semântica dos snapshots anteriores, inclusive a exceção inicial Geizian/YolokfxG002. A mudança substitui somente a métrica/rótulo B.R.% por B.U.%, preservando colunas, ordenações, largura, histórico, Meta, crons e relatórios remotos anteriores. O nome lógico `Budget R.` e perfis históricos continuam como compatibilidade interna; o renderer produz o rótulo efetivo B.U.% para fontes novas. Não ampliar globalmente a posição de RPS por essa autorização. Procedimento e testes em `references/canonical-report-renderer.md`, seção Budget Used.

### Exceção visual — Gasto adaptativo na Yolokfx G002

Por autorização de Geizian nesta conta/thread, `account_width_overrides.7840111366055613` permite ampliar somente **Gasto** conforme o maior número formatado do relatório, preservando os valores e demais colunas. A grade global157 continua para as demais contas; nesta conta cresce apenas pelo delta necessário de Gasto. Consultar a seção `Gasto adaptativo autorizado` da referência canônica antes de bloquear um relatório por esse campo. A autorização posterior supersede a negativa anterior, sem alterar finanças/Meta nem promover o ajuste globalmente.

## Histórico supersedido — compacto global de quinze colunas

Rodolfo aprovou na Diretoria `1560303769680355525` o padrão compacto para os próximos relatórios de **todas as 36 contas**, distribuídas em **36 threads Intraday dentro de seis canais de relatórios**, seis contas por gestor. Usar as **15 colunas visíveis**, nesta ordem: **R/E → Início → Nº → Produto → Quiz → Bid → Gasto → B.R. → Rev → Saldo → Health → ROI → ROI E. → ROAS → Lance**. Produto tem no máximo **12 caracteres incluindo espaços, sem reticências**. `B.R.` = `budget_remaining` real da campanha Meta; `Bid` = `bid_amount` real em COST_CAP, demais estratégias `—`; `Rev` = receita líquida SB; `Health` conserva Est.Health; `ROI E.` conserva ROI estimado. São aliases de apresentação, sem trocar fórmulas. Preservar os separadores, cores, alinhamento, famílias COPY, histórico de sete datas e Média 7d.

Fonte única: `SHEIN-US-DIRECT.json#/reporting/on_demand_default_layout`, política `ARES-SHEIN-REPORT-GLOBAL-COMPACT12-20261016`, com `header_aliases` e `product_column`. Relatórios normais usam render/validate **sem flags de prévia** e modelos completos de configuração. O limite anterior20, os treze campos e a limitação inicial das duas colunas à Conta02 G006 estão explicitamente supersedidos; exemplos históricos abaixo não são defaults ativos. Não herdar a data ou o financeiro de outro relatório quando o usuário pedir atualização. Para lote de36, persistir cada fonte/conta, tratar as contas sem entrega com cabeçalhos e n/d sem inventar receita, validar36IDs de conta/thread únicos e confirmar cada parte por GET antes de concluir. Não apagar/editar relatórios antigos, ativar cron ou fazer write Meta por esse pedido.

## Histórico supersedido — padrão exclusivo das seis YOLO

A limitação às seis YOLO e aos perfis `YOLO_UNIFORM_G001_CAPS_V1` está supersedida pelo padrão global das36contas acima. O bloco abaixo preserva a adoção anterior, não restringe o alcance vigente.

Rodolfo promoveu as mudanças desta Diretoria para os próximos relatórios das **seis contas Yolokfx G001–G006**, sem nova confirmação por pedido: **St sem ponto antes de Produto; RPS copiado da coluna visível da dash SB imediatamente antes de Bid; B.R.% em vez de valor monetário; principal por ROI estimado maior → menor; histórico por número crescente; avisos de origem COPY somente no audit, preservando os marcadores**. Em St, a correção expressa de Rodolfo usa **ACTIVE=A, PAUSED=P, DELETED=D e ARCHIVED=A**; o audit mantém os estados técnicos distintos. Fonte única: `SHEIN-US-DIRECT.json#/reporting/on_demand_default_layout/account_report_overrides`, política `ARES-YOLO-REPORT-UNIFORM-CAPS-20261019`, sucessora de `ARES-YOLO-REPORT-ST-20261019`. A tabela principal das seis YOLO usa o perfil canônico `YOLO_UNIFORM_G001_CAPS_V1`: Nº com 13 posições e uma única grade de 157 posições visuais, referenciada no G001, com as mesmas margens/separadores em todas as contas. Tetos **somente de exibição nas linhas principais**: ROI/ROI E. 999,99% sem `+`, preservando negativos; ROAS 9,99x; Rev 9.999,99. Dados brutos, cores, cálculo, total, ranking e histórico continuam reais, sem cap. Rodapé curto informa os tetos; valor não coberto por cap que exceda sua coluna bloqueia publicação, sem cortar dado ou alargar silenciosamente a grade. Os overrides conferem conta/nome/thread e têm vigência prospectiva por horário do snapshot financeiro; snapshots anteriores e as outras 30 contas conservam suas regras. O gate exige RPS da UI: autorização do layout não substitui autenticação nem libera API/cálculo local. Distinguir **padrão aplicado** de **relatório publicado** e manter a substituição anterior pendente até ter fonte válida. Detalhes em `references/canonical-report-renderer.md`.

## Quando usar

Carregue esta skill quando o pedido vier de um canal `shein-g001`…`shein-g006` ou mencionar simultaneamente SHEIN, Meta e tráfego direto nos EUA.

Não use `direct-traffic-cbo-operations` como fonte única da operação SHEIN. Essa skill mantém mecanismos genéricos e regras específicas de outras operações, inclusive Creditoparaveiculo; nenhum valor ou lifecycle veicular é herdado.

## Fontes obrigatórias

1. Contrato vivo da operação: `data/ares/meta-ads/operations/SHEIN-US-DIRECT.json`.
2. Conta Meta: runtime/API real e registro account-scoped criado após o primeiro readback.
3. Criativos: `data/ares/creative-ops/inventory/assets.jsonl` + Shared Drive `MGS-AGENTS`.
4. Autoridade: `data/authorized-users.json` e `context/permissions-matrix.md`.
5. Criação/clone/lote: skill `meta-campaign-engine-v3` e seu executor central.
6. Contrato v3 da operação: `data/ares/meta-ads/operations/SHEIN-US-DIRECT-v3.json`.
7. Adapter/runner determinístico: `ares_campaign_v3.shein` + `scripts/ares-shein-campaigns.py`.
8. Catálogo de lookup dos seis gestores: `data/ares/meta-ads/operations/SHEIN-US-DIRECT-accounts.json`; nome completo → ID Meta → gestor/canal, sem expansão de autoridade.
9. Pipeline comum para todos os gestores/contas SHEIN: `ares-shein-campaigns.py campaign` + compiler `ares_campaign_v3.shein_general`, mesmo Engine v3. Carregar `references/general-campaign-fast-route.md`. `SHEIN-US-DIRECT-profiles.json` informa parâmetros e pré-requisitos materiais, não privilégio de solicitante.

O Engine v3 contém apenas mecânica universal de campanha. SHEIN materializa naming, UTMs, prova social, payload Graph v26, fontes, criativos e pós-processamento no adapter/runner próprio; relatórios e estratégia não entram no executor. Não criar v4 nem um campaign writer paralelo para separar nichos.

Conclusão: contrato, gestor/canal e conta alvo estão reconciliados antes de interpretar valores históricos como vigentes.

## Identidade da operação

Resolver sites, idiomas, gestores, canais e authority sempre no contrato vivo. O desenho vigente permite ao mesmo gestor operar simultaneamente os sites EN e ES, mas mantém contas e perfis anunciantes isolados por canal/gestor.

Regras:

- site EN exige campanha/copy/criativo compatível com EN;
- site ES exige campanha/copy/criativo compatível com ES;
- uma conta ou perfil de outro gestor nunca é fallback;
- canal preparado não prova que uma conta já foi onboardada;
- Pages SHEIN autorizadas podem estar atribuídas no Business Manager; isso não substitui GET ao vivo da Page, tarefas e identidade antes do write;
- toda conta recebe alias curto somente depois de GET Meta de nome, moeda, timezone, acesso e saúde.
- Para Escalatepower, carregar `SHEIN-US-DIRECT.json#/escalatepower_asset_onboarding`: a autorização de Rodolfo e os bindings conta → Page → gestor estão persistidos. Não pedir nova autorização só porque um catálogo antigo não mostrava o ativo; reconciliar as fontes apontadas e validar acesso vivo. Esse vínculo aprovado não impõe exclusividade global nem substitui a Page da fonte exata em uma duplicação.
- Separar prontidão de acesso de especificação da campanha: `ASSETS_ACCESS_READY_CAMPAIGN_SPEC_REQUIRED` confirma conta/Page/pixel e não é falta de autorização. Conta vazia continua exigindo os parâmetros materiais do pedido e a rota central compatível; não inventar campanha-fonte, tracking, referência de outro gestor ou serving validado. Relatar uma limitação do runner como limitação técnica, nunca como nova aprovação de cadastro.
- Em onboarding, reler o timezone atual e reconciliar catálogo, profile e registro do Engine somente nas contas exatas. Preservar o snapshot antigo e adicionar evidência scoped; não apresentar atualização parcial como novo inventário global. Validar os seis lookups pelo runner e fazer readback das tarefas e do acesso de Page com a identidade corporativa original após qualquer delegação.

Conclusão: nenhum write depende de conta, perfil ou idioma inferido por semelhança.

## Rollout e superfícies autorizadas

Resolva o escopo atual pelo contrato vivo e pelos bindings específicos da conversa. Não use o rótulo inicial `PHASE_1_CAMPAIGN_CREATION_ONLY` como veto a relatórios on-demand em threads Intraday já vinculadas canonicamente: o estado de onboarding e a autorização posterior de leitura são controles distintos.

- Execute o relatório read-only solicitado na thread cuja conta estiver confirmada pelo índice Intraday, preservando título e destino; sua existência não autoriza write Meta, cron ou otimização automática.
- Não crie Diário, Intraday/Otimização, Criativos, destinos ou recorrência por inferência; ampliar a superfície exige autorização própria.
- Não bloqueie criação autorizada por ausência de estrutura de relatório.
- Preserve rotas excluídas; um binding vigente de outra conversa não autoriza recriar as antigas.
- Verifique o inventário atual antes de criar pasta de idioma; não trate ausência registrada no onboarding como estado presente.
- EN e ES usam a mesma operação, mantendo copy e assets separados por idioma.

Conclusão: use a superfície atualmente autorizada para o pedido, sem transformar histórico de rollout em bloqueio nem em autorização adicional.

## Autoridade por canal

Por decisão vigente de Rodolfo, qualquer pessoa humana com permissão efetiva de comunicação em `shein-g001`…`shein-g006` pode solicitar e autorizar Campaign Ops no respectivo canal e nas suas threads, sobre as contas/perfis vinculados àquele canal. O gestor titular identifica a partição das contas, não o único solicitante permitido. Geizian não deve ser recusado por ser nominalmente G002 quando tem permissão no canal da conta. A regra é `SHEIN-US-DIRECT.json#/channel_authorization_policy`; validar ID real do remetente, canal pai, permissões efetivas e origem da thread, nunca display name, mera presença na thread ou flag fornecida no pedido. O runner usa `shein_channel_authority` read-only e relê a autorização antes da criação/ativação; não altera o cadastro global de usuários nem permissões Discord.

Dentro desse recorte, continuam disponíveis por pedido explícito:

- criar, duplicar e clonar campanhas;
- pedir relatórios e organizar threads;
- otimizar, pausar e reativar;
- excluir ou arquivar campanhas;
- definir ou alterar budget;
- definir schedule e ativar campanhas.

Budget, ativação e retomada autorizados pelo humano elegível do canal não exigem uma segunda aprovação de Rodolfo dentro desse escopo; budget continua exigindo valor e moeda exatos, pre-read, menor write possível e GET/readback. Antes de repetir uma pergunta de ativação após atraso, confira se já existe resposta humana explícita ao pedido de recuperação do mesmo request. Uma resposta curta pode confirmar o escopo da mensagem respondida: valide autor, origem, conteúdo e vínculo da resposta pela rota central, sem confundir essa aprovação específica com autonomia genérica para pedidos futuros. Preserve o SLA e seus registros; reutilizar aprovação válida não significa desativar o gate.

Geizian (`321263240782807040`) tem autoridade integral de Campaign Ops nos seis canais SHEIN e nas threads deles, não somente G002. A mesma autoridade vale para review de continuação/ativação tardia explicitamente pedida na origem: usar `channel_authorization_policy.late_recovery_review` e `shein_continuation`, com permissões live forçadas. Não exigir review exclusivo de Rodolfo por um atraso técnico. Preservar SLA e relógio original, QA semântico/mídia, manifests, request/IDs, budget/lance e Critical Subset; uma aprovação de ativação não autoriza recriar objetos. Validar a mensagem humana exata por readback; revalidar o solicitante e o reviewer antes de ativar. Nos seis `discord.channel_prompts`, reconciliar instruções com o contrato vivo para que texto legado “somente gestor” não volte a bloquear autoridade registrada.

Continuam fora da delegação: billing, `account_spend_limit`, credenciais, ownership, permissões de app, pixel/CAPI estrutural, WordPress, quiz, SMS Funnel, ChatPion, contas/perfis fora da partição do canal de origem e automação recorrente sem política própria. O fato de o solicitante ter outro código de gestor não é acesso cruzado quando a conta pertence ao canal do pedido.

Conclusão: solicitante, canal, conta e ação estão dentro da mesma faixa de autoridade.

## Tokens e rate limits

Resolva a arquitetura de credencial sempre no contrato vivo `data/ares/meta-ads/operations/SHEIN-US-DIRECT.json`; não herde o desenho histórico por perfil. A decisão vigente de Rodolfo para `SHEIN-US-DIRECT` usa **Business Integration System User access token** associado ao Business Portfolio cliente, com delegação explícita de ativos; BOT/Messenger continua em User Access Tokens e não faz parte dessa migração. Tokens ficam no 1Password; contrato e registry guardam somente referência do item, alias e metadata segura. Token, App Secret e authorization code nunca entram no Discord, arquivo operacional ou log comum.

Não criar um app por gestor nem tokens adicionais para contornar throttling. Granularidade por finalidade/ativo só é definida depois do inventário e da delegação do Business Portfolio cliente. A Marketing API continua limitada pelo conjunto conta, app, Business Use Case, Access Tier, burst de mutações e frequência por objeto.

No onboarding de cada conta, registrar e monitorar `X-Ad-Account-Usage`, `X-Business-Use-Case-Usage` e, quando aplicável, `X-App-Usage`/`X-FB-Ads-Insights-Throttle`, além dos códigos/subcodes de throttling.

Para a emissão vigente, seguir `paid-acquisition-operations/references/meta-facebook-login-for-business-callback.md`: Authorization Code, `config_id`, `response_type=code`, `override_default_response_type=true`, `state` single-use, troca server-to-server, armazenamento direto no 1Password e readback de `client_business_id`, permissões e ativos. O playbook histórico `references/facebook-login-for-business-onboarding.md` permanece apenas para contexto e não pode sobrescrever o contrato vivo.

Conclusão: a identidade e os ativos são delegados explicitamente pelo Business Portfolio cliente, enquanto quota continua governada pelo conjunto conta + app + BUC + tier + objeto.

## Intake natural de campanha

Os três pedidos-padrão humanos oficiais — criar do zero, clonar com criativos novos e duplicar igual — estão em `references/standard-campaign-requests.md`. Preserve o texto aprovado; verificações internas de conta, compatibilidade site/idioma e evento da fonte continuam no preflight e não devem ser transferidas ao gestor como campos obrigatórios.

Extraia do pedido e do estado live:

```text
Campo                 Regra
--------------------  --------------------------------------------------
gestor/canal          binding exato do contrato
conta/perfil          alvo Meta exato; onboard por readback se novo
site/idioma           yolokfx/vizioid EN ou mavroa ES, conforme contrato
modo                   criar do zero / duplicar igual / clonar com delta
objetivo/evento        fixo SHEIN: OUTCOME_SALES / OFFSITE_CONVERSIONS / ADD_TO_WISHLIST; não pedir ao gestor
estrutura              CBO/ABO, adsets e ads; nunca herdar de CAR
bid                    estratégia e valor quando aplicável
budget/moeda           exatos antes do write
schedule/status        exatos; default final ACTIVE após QA completo, PAUSED somente quando expresso
copy                   Primary text, Headline, Description e CTA
criativos              imagens/vídeos reconciliados e language-matched
URL/UTM                destino e parâmetros completos
fonte de clone         campanha/conta exatas quando houver
```

Pergunte somente o campo ausente que bloqueia a ação. Em `SHEIN-US-DIRECT`, o objetivo/evento não é um campo de intake: toda criação, clonagem e duplicação usa `OUTCOME_SALES` com otimização `OFFSITE_CONVERSIONS` e evento `ADD_TO_WISHLIST` (Add to Wishlist). Nos modelos visíveis ao gestor, apresente domínio e idioma juntos em uma única linha no formato exato `Site/idioma: dominio.com - EN|ES`. Pedido vago que mudaria materialmente bid, estrutura, budget, schedule ou destino recebe entendimento curto + pergunta normal; não use formulário obrigatório.

### Pedidos com várias campanhas-fonte

Mantenha o mapa explícito fonte → quantidade → alvos, sem aplicar a configuração da primeira fonte às demais. Quando o intake central aceitar uma fonte por execução, vincule os subpedidos determinísticos à mesma mensagem humana e consolide a conclusão do pedido inteiro; não apresente a primeira execução concluída como sucesso global. Preserve os gates de QA/ativação e o relógio original, sem fracionar um grupo de mídia ou contornar limites. Use a receita `Pedidos com várias fontes na mesma conta` em `references/general-campaign-fast-route.md` para sequenciamento e verificação agregada.

No fechamento, gere primeiro o recibo agregado a partir de `source`, `activation_result.trees`, `media_qa` e `qa_warnings` de cada subpedido; derive desse mesmo recibo tanto o checkpoint final quanto a resposta. Preserve as ressalvas por fonte: `qa_proof` comprova QA, mas não é a origem do campo `qa_warnings`; procurar somente `qa_proof.warnings` e assumir lista vazia pode ocultar normalizações reais da Meta. Registre por fonte a estratégia/cap reais, os números-alvo e a cardinalidade de anúncios: budget igual e origem histórica comum não implicam lance ou estrutura iguais, pois cada fonte pode ter sido alterada independentemente. Só resuma um lance como comum ao lote depois de testar igualdade dos pares `(bid_strategy, bid_amount)` de todos os alvos; se houver diferenças, informe-as por fonte, sem normalizar os anúncios. Antes de encerrar, confronte checkpoint e resposta com esses grupos e corrija qualquer generalização divergente; um recibo correto não impede que um resumo escrito separadamente registre um cap incorreto.

### Correções do pedido antes do write

Consolide as mensagens autorizadas mais recentes antes de executar: mudança de quantidade substitui a quantidade anterior; retirada expressa do ajuste de Cost per result goal remove `bid_strategy` e `bid_usd` do JSON de intenção, em vez de reenviar o valor inicialmente citado. Preserve budget, fonte e início que não foram alterados. Herdar o lance significa ler e conservar a estratégia e o cap reais da fonte, não presumir que coincidem com o primeiro valor informado; confira fonte × cada cópia no readback e informe o valor efetivamente preservado no resumo. Aplique essa edição somente enquanto não houver execução/manifest selado; após possível efeito parcial, reconcilie o mesmo request/IDs antes de interpretar a correção como novos writes.

### Horário explícito do dia já vencido

Na política `SHEIN-US-DIRECT.json#/request_defaults/expired_explicit_start_policy`, horário explícito que já passou no próprio dia civil do timezone verificado da conta vira início imediato após QA, sem pedir nova autorização ao gestor/CEO somente por esse atraso. Usar o horário atual com o buffer técnico normal de NOW; guardar o horário solicitado literalmente e o motivo no audit/resolved_request. Data/horário futuros permanecem literais; não transferir implicitamente para o dia seguinte. PAUSED expresso continua PAUSED. Horário omitido mantém a próxima meia-noite; data anterior a hoje não entra nessa conversão automática.

Essa normalização é do intake/preflight antes do write; jamais regenerar campanha, sobrescrever manifest selado ou trocar IDs depois de efeito parcial. Se já há objetos, reconciliar e continuar o mesmo request/IDs pela recuperação central. O estado da execução e o relógio E2E original são preservados; a regra não remove QA, quotas ou outros gates.

### Recovery de responsabilidade do Ares

Antes de pedir autorização de reparo de delegação, consultar `SHEIN-US-DIRECT.json#/page_delegation_repair_authorizations` pela Page e conta exatas. Quando Rodolfo conceder autorização durável, persistir o recorte canônico e validar o registro; não repetir a pergunta dentro desse recorte nem ampliar a autorização para outros ativos. Separar aprovação de acesso técnico: após o operador informar que resolveu o acesso, refazer as leituras corporativa e administrativa atuais, aplicar somente as tarefas ausentes já autorizadas e validar com a identidade corporativa original. Uma falha corporativa remanescente não comprova que a correção administrativa falhou. Retomar o pedido original, não abrir nova duplicação nem substituir sua origem pela mensagem de recuperação. Usar a receita de preflight e delegação em `references/general-campaign-fast-route.md`.

Ares diagnostica e resolve falhas de pedidos já autorizados, preservando request, IDs, fonte, parâmetros, QA e readback. Não mencionar/acionar Zeus nem transferir o reparo para ele como fallback rotineiro. A delegação histórica de recovery não é obrigação de handoff nem motivo para abandonar a execução; seguir `context/routes.md#Recovery-operacional-do-Ares`. Rodolfo pode solicitar expressamente uma intervenção separada, mas erro técnico por si só não autoriza essa transferência.

Antes de retomar, recuperar o input original mesmo quando o bloqueio ocorreu antes de existir state do runner; consultar também os registros de preflight pela receita `Retomar pedido referenciado após interrupção` em `references/general-campaign-fast-route.md`. Filtrar registry/checkpoint pela thread ou request antes de trazer conteúdo ao contexto. Fazer readback e reconciliar efeitos parciais; não repetir POST não idempotente, criar writer paralelo, novas cópias ou exclusões implícitas. Restauração de acesso ao modelo ou ao serviço comprova somente acesso, nunca execução de campanha. Quando um humano autorizado pedir para concluir um pedido anterior, recuperar a especificação e a identidade originais, registrar a nova mensagem como autorização de recuperação separada e continuar pelo mesmo request; não transformar a retomada em uma nova duplicação nem importar parâmetros de outro pedido concluído na thread. Usar a receita `Retomar pedido referenciado após interrupção` em `references/general-campaign-fast-route.md`. Correção técnica autorizada é etapa de manutenção separada do hot path; retomar somente pela rota central depois da validação. Se existir bloqueio externo incontornável ou gate crítico, preservar checkpoint resumível e informar a Rodolfo causa comprovada e próxima decisão exata na thread de origem, sem menção automática ao Zeus. Critical Subset, credenciais, billing e ampliação de escopo continuam com gates próprios.

Conclusão: o manifest pode ser materializado sem inventar campos.

## Numeração visível obrigatória

Toda campanha SHEIN nova começa com **três dígitos**, preenchidos com zeros à esquerda: `001`, `007`, `099`, `100` — nunca `1`, `7` ou `99`. Gerar pelo formatter central `shein_naming.campaign_name` e validar o prefixo nos account policies antes de write, em criação do zero, duplicação e clone. Aceitar nomes legados somente como fonte; não exigir renomear a origem. Padding do prefixo não altera tracking/UTMs nem `COPY C<fonte>`. Ao atingir número fora de `001–999`, bloquear antes de write, sem truncar, reciclar ou reiniciar sequência. Pedido de corrigir campanha existente altera somente `name` no ID exato e exige GET/readback de status, budget, lance, início e filhos inalterados. Preservar manifests históricos; registrar recibo separado da correção. Fonte: `SHEIN-US-DIRECT.json#/campaign_naming_policy/visible_campaign_number`. Regressão: `test_shein_number_padding.py`.

## Marcador US_APP — somente próximos pedidos US-SHEIN

Por decisão de Rodolfo na thread `1560359535175143545`, toda campanha de próximos pedidos das contas US-SHEIN recebe o marcador literal `(US_APP)`, depois de `COPY C<FONTE>` quando houver esse marcador de origem ou imediatamente depois de `(TRACKING)` quando não houver COPY, sempre antes de `event_add_to_wishlist`:

```text
NNN - DATA - QUIZ - PRODUTO - LANCE - (TRACKING) - COPY C<FONTE> - (US_APP) - event_add_to_wishlist
NNN - DATA - QUIZ - PRODUTO - LANCE - (TRACKING) - (US_APP) - event_add_to_wishlist
```

Gerar pelo formatter central `shein_naming.campaign_name`; não inserir o marcador em produto, tracking ou UTMs e não duplicá-lo ao usar uma fonte já marcada. A regra é prospectiva: não renomear campanhas existentes nem modificar manifests já selados ou pedidos em recuperação. O parser aceita fontes históricas sem o marcador; a compatibilidade do validador com manifests anteriores não autoriza omitir `(US_APP)` nos próximos pedidos. Não transportar essa regra para CAR/BOT/outras operações. Fonte canônica: `SHEIN-US-DIRECT.json#/campaign_naming_policy/us_app_marker`. Regressão offline: `tests/test_shein_us_app_naming.py`.

## Renomeação literal agendada

Quando Rodolfo autorizar uma troca de texto no nome de campanhas existentes, preservar literalmente todo o restante do nome; não reconstruir pelo formatter de novas campanhas nem inserir outros campos por inferência. Em agendamento, resolver data/fuso, fixar a lista autorizada de contas por ID, impedir qualquer write antes do horário e refazer o inventário paginado no disparo. Separar ativas/pausadas do histórico terminal. Usar tarefa determinística `no_agent=true`, saída curta em PT-BR e readback da agenda; não publicar wrappers técnicos. Sob lease da conta, persistir nome anterior/desejado e IDs antes do write exclusivo de `name`; reler nome, status, budget, lance, início e filhos, e reconciliar a mesma camada após resposta incerta, sem replay cego. Preservar pedidos de criação e manifests existentes. Testes de literalidade, escopo, horário, drift e resposta perdida: `tests/test_shein_scheduled_name_replacement.py`.

## Correção de número/tracking em campanha existente

Quando o pedido autorizar somente nome + link e preservar o restante, editar os IDs existentes; não criar campanha, conjunto, anúncio, mídia ou alterar budget/lance/schedule/status configurado. Construir o nome pelo `shein_naming.campaign_name`, com a data de início e o quiz/bid reais. Não renomear conjuntos/anúncios sem escopo expresso.

Para conservar o mesmo post e sua prova social ao corrigir UTMs embutidas no link original, usar um pacote AdCreative standalone com `object_story_id=<effective_object_story_id original>` e `url_tags` corrigidos e anexá-lo ao **mesmo ad_id**. `url_tags` não é campo mutável do AdCreative existente: o ID do pacote técnico muda, não o asset nem o post. Os parâmetros de URL do anúncio sobrescrevem chaves duplicadas da Website URL segundo a Meta; o link histórico do post permanece original, enquanto o link efetivo do anúncio pago recebe os parâmetros corrigidos. Não afirmar que o link do post foi editado. Preservar parâmetros não alvo, Page, Instagram, `contextual_multi_ads`, tracking/conversion specs, `source_ad_id` e todas as configurações individuais de `degrees_of_freedom_spec` expostas pela fonte; não usar o normalizador mínimo de clone para descartar features em uma correção.

Não reenviar `standard_enhancements`: a Meta rejeita esse campo legado com subcode `3858504`. Remover somente essa chave descontinuada e preservar cada feature individual. No readback, exigir igualdade de **todos** os campos individuais originais; aceitar features novas materializadas pela Meta somente quando forem exatamente `OPT_OUT`, registrando a normalização. Qualquer mudança em feature original ou novo `OPT_IN` bloqueia o attach e exige reconciliação.

Validar os payloads por `execution_options=[validate_only]` no edge direto de adcreatives e fazer readback de todos os pacotes antes de anexar o primeiro. Persistir imediatamente IDs; após falha, procurar/reutilizar o pacote por ID ou nome determinístico com paginação account-scoped. O edge `/adcreatives` não aceita filtro `name EQUAL`: paginar `id,name`, filtrar localmente e reler o ID exato. Nunca repetir criação não idempotente às cegas. Comparar snapshot antes/depois de campanha, conjuntos, anúncios, posts e tags; relatar `IN_PROCESS`/revisão automática separado de `status=ACTIVE` preservado.

Fontes públicas: Meta Business Help Center `1016122818401732` (URL parameters overriding duplicate Website URL parameters), Graph API v26 AdCreative (campos mutáveis) e Ad (attach de creative_id). Verificação obrigatória: GET do mesmo post nos três anúncios, UTMs alvo sem chaves duplicadas, parents e fields não alvo iguais, normalização de features auditada. Testes de preservação devem reprovar feature original alterada, feature nova OPT_IN, mudança de post e tracking divergente.

## Estratégia de lance e delta explícito

Use os aliases exatos MAXVOL → `LOWEST_COST_WITHOUT_CAP`, COCAP → `COST_CAP`, BIDCAP → `LOWEST_COST_WITH_BID_CAP`. MAXVOL prioriza volume Add to Wishlist nesta operação, não otimização por valor/ROAS. COCAP é meta de custo médio por resultado, não CPA máximo garantido. BIDCAP é teto de lance por leilão, não teto de CPA. Orçamento, custo por resultado e lance são campos distintos.

“Duplicar a MAXVOL e trocar para COCAP com bid X” é duplicação com delta explícito: preservar mídia, copy, público e demais configurações não alteradas; aplicar estratégia e cap somente ao alvo novo; manter a fonte intacta. Sem delta no pedido atual, omitir `bid_strategy` e `bid_usd` da intenção e herdar estratégia e valor reais da API. Em pedidos sucessivos na mesma thread, distinguir uma correção do request ainda aberto de uma nova duplicação: não transportar cap, estratégia, quantidade ou budget de um request concluído, mesmo quando a fonte ou a conta se repetirem. Histórico/memória de ajuste de lance não comprova a configuração atual da fonte nem constitui delta para o novo pedido; conferir fonte × cada alvo no readback e informar o lance efetivamente herdado. Pedir somente o valor/moeda ausente que bloqueia COCAP/BIDCAP; MAXVOL não recebe valor de cap e limpa o cap herdado no alvo quando for uma mudança expressa de estratégia. O alias do nome novo vem da estratégia resolvida do alvo, nunca do rótulo da fonte. Dropdown aberto/hover não comprova seleção salva.

Na rota comum, materializar `bid_strategy` com o alias e `bid_usd` com decimal USD exato, conforme a moeda live. O compiler converte em unidades menores, marca `bid_override=true` e limita `adset_updates` exclusivamente a `bid_amount` + reset de `bid_constraints`. Esse delta SHEIN usa o mesmo Engine v3, sem writer paralelo. QA/readback e pré-ativação comparam estratégia e valor/reset; alteração de targeting ou outro campo não cabe na exceção. Implementação validada offline; serving e aceitação Meta de cada pedido exigem o readback live daquele pedido, sem canário implícito.

## Criação, duplicação e clone

1. Faça GET da conta, campanha fonte e hierarquia dependente quando aplicável.
2. Classifique o modo solicitado; copiar campos para objetos novos não deve ser chamado de clone se a rota não preserva a linhagem da fonte.
3. Feche site, idioma, URL/UTM, copy, criativos, estrutura, bid, budget, status e schedule; materialize sempre `ADD_TO_WISHLIST` e rejeite fonte de clone/duplicação cujo conjunto use outro evento.
4. Reserve criativos e repita a conciliação Drive × Meta imediatamente antes do write.
5. Faça upload sob demanda da mídia nova somente depois que a conta exata do pedido estiver resolvida; para o contrato SHEIN atual, envie apenas a variante vertical em batch paralelo e obtenha IDs Meta prontos. Nunca pre-stagear globalmente nem inferir múltiplas contas.
6. Materialize o manifest e execute validate/plan pelo `meta-campaign-engine-v3`.
7. Execute apenas o pedido autorizado: novas campanhas são construídas PAUSED e, após QA de todo o pedido, o status final padrão é ACTIVE conforme request_defaults aprovado por Rodolfo. PAUSED/revisão expresso prevalece; não aplicar a regra a campanhas existentes.
8. Faça GET/readback consolidado de campanha, adsets, ads, budget, status, schedule, URL/UTM, copy e mídia. Antes de concluir um lote, conte programaticamente os campaign IDs únicos contra a quantidade pedida e confira budget/status/início e prova de mídia de cada campanha; um resumo do primeiro item não comprova o lote inteiro. Se o core concluiu PAUSED e o QA acusou mismatch, confirme primeiro a cobertura dos campos do creative e a frescura do snapshot: uma árvore compacta não comprova drift, e repetir imediatamente a mesma leitura pode reproduzir o falso mismatch. Retome QA no mesmo request somente com leitura completa ou snapshot expirado, comparando os conjuntos de campaign/adset/ad IDs antes e depois. Para o procedimento e falhas transitórias de prévia, siga `references/general-campaign-fast-route.md`, seção `Retomada de QA sem replay de criação`.
9. Em `pure_clone`, verifique o Ad setup real antes de prometer prova social: `source_definition_two_phase` preserva mídia/copy/lineage e a localização do tracking, mas gera posts novos. Declare posts novos no resumo; não descreva a cópia como post/prova social preservados. Somente quando o manifest exigir post existente preservado, compare posts fonte × alvo e leia os contadores diretamente com a identidade da própria Page, não com o token corporativo de Campaign Ops. Carregue somente a seção `Leitura de engajamento de posts usados em anúncios` de `paid-acquisition-operations/references/meta-facebook-login-for-business-token-selection.md`; resolva o Page token uma vez por Page, mantenha-o em memória e agrupe os posts únicos. Não repita a tentativa corporativa conhecida como inválida, nem classifique `code=10` sozinho como falta de scope. `shares` ausente é indisponível, nunca zero.

Falha após possível efeito parcial inicia readback-first com o mesmo request/IDs. Nunca repetir POST não idempotente às cegas.

Conclusão: todos os objetos e deltas do pedido têm IDs persistidos e estado live validado.

## Criativos SHEIN

- Original e tratado são uma única linhagem.
- Upload humano começa `RESERVADO_PELO_GESTOR` e `ares_eligible=false`.
- `01_READY` prova prontidão técnica, não ineditismo ou liberação.
- A pasta EN vigente é resolvida no contrato; a existência dela não cria automaticamente um pool ES.
- Nunca usar criativo EN em anúncio ES como se fosse espanhol.
- Antes de selecionar, cruzar Drive IDs, checksums/fingerprint, inventário e IDs Meta/histórico de uso.
- Pastas humanas `USADOS` são evidência de uso, não um novo status canônico nem fonte elegível.
- Drift Drive-only, inventory-only, status divergente ou filename duplicado fica fail-closed até reconciliação.

Ao responder “quantos criativos existem”, separar obrigatoriamente: linhagens tratadas vivas, tratados em `01_READY`, tratados em pastas `USADOS`, originais físicos em `99_LEGACY` e total físico. Original e tratado nunca são somados como dois criativos. Informar horário/fonte do snapshot. Se o operador mostrar uma contagem divergente da interface, refazer inventário API e identificar a pasta/filtro exatos; não atribuir a diferença a paginação ou limite visual quando o contador não estiver visível na evidência.

Conclusão: cada anúncio usa uma linhagem única, compatível com o idioma e comprovadamente elegível.

## Copy e produto

Na linguagem MGS, copy são os campos Meta `Primary text`, `Headline`, `Description` e `CTA`; criativos são somente imagens e vídeos.

O produto/ângulo mostrado no vídeo deve ser identificado por evidência visual da timeline, não apenas pelo filename de upload. Para inventário em lote, amostrar múltiplos frames por vídeo, revisar todo item e ampliar individualmente qualquer ambiguidade antes de consolidar a lista de produtos.

Conclusão: produto visual, idioma e claim não dependem do nome bruto.

## Relatórios e otimização

### Gate obrigatório — renderer único e vínculo da thread

Em pedido de campanhas ativas agora, selecionar pela configuração Meta `status=ACTIVE`, guardar também `effective_status` e manter as ativas sem entrega ou sem linha SB; gasto positivo e presença no Adgroup não substituem o filtro solicitado. Revalidar os IDs e estados antes da entrega quando a coleta demorar, informando o horário de status separado do financeiro. Conferir cedo as células de configuração contra as larguras do perfil vigente, antes da paginação UI custosa; um overflow visual não autoriza omitir campanhas, alterar métricas ou declarar o relatório entregue. Diagnóstico e retomada em `references/canonical-report-renderer.md`.

Na descoberta das fontes, projetar o contrato por chave e pelo ID exato da conta/thread, em vez de imprimir `reporting` inteiro; o objeto contém overrides de outras contas e histórico que encobrem a regra necessária. Para diagnosticar a UI do Smart Bidding, retornar somente identidade, período/moeda, cabeçalhos, paginação e linhas já filtradas do recorte solicitado; não despejar `body.inner_text()` completo nem abrir arquivos `*state*.json` como se fossem evidência financeira. Separar captura sanitizada de sessão autenticada conforme `references/canonical-report-renderer.md`, seção `Receita DOM do Adgroup e recuperação por camada`.

Antes de cada pedido e novamente antes da entrega, ler o contrato atual `SHEIN-US-DIRECT.json#/reporting/on_demand_default_layout`. Nas threads Intraday, começar pelo índice `data/ares/discord/shein-intraday-report-bindings.json` para resolver thread → conta e conferir a mesma conta no catálogo `SHEIN-US-DIRECT-accounts.json`, antes de procurar runners ou arquivos individuais. Para relatório read-only, arquivo individual de conta ausente não prova falta de acesso: seguir o binding corporativo vigente e confirmar a conta exata por GET Meta, conforme a receita de coleta integral. Histórico do Discord ou contexto de sessão antigo não substitui o contrato atual; apagar mensagens remotas não apaga automaticamente contexto interno.

Não montar o relatório padrão manualmente nem reutilizar um renderer específico antigo. Após a coleta live, materializar o modelo normalizado conforme `references/canonical-report-renderer.md`, executar `/root/.hermes/profiles/ares/scripts/shein-report-layout.py render --thread-id <ID> --input <modelo.json> --output <report.md>` e, imediatamente antes da entrega, `validate --thread-id <ID> --input <modelo.json> --report <report.md> --receipt <recibo.json>`. Entregar o texto gerado sem reescrever cabeçalhos, tabelas, cores, agrupamentos ou média. Falha de validação bloqueia publicação, não a correção local. O recibo comprova layout/modelo/contrato, não coleta live nem entrega Discord; essas evidências continuam separadas. Contas vazias conservam ambos os cabeçalhos, sem inventar linhas. O renderer é offline: nunca consulta nem escreve Meta/SB/Discord e não altera schedule/cron.

### Histórico supersedido — acréscimos inicialmente autorizados por conta

A aprovação global compacta no início desta skill substitui o escopo exclusivo descrito abaixo. As mesmas leituras Meta agora são exigidas em todas as36contas e os rótulos atuais são Bid/B.R.

Antes de renderizar, consultar também `on_demand_default_layout.account_column_overrides`. Para Yolokfx Conta 02 G006 (`1583000095650153`, thread `1558147479432601670`), Rodolfo autorizou **Bid antes de Gasto** e **Budget R. antes de Receita**. Usar os campos Meta reais e os dois horários, conforme `references/canonical-report-renderer.md#colunas-meta-por-conta--bid-e-budget-r`. Esse recorte não altera as treze colunas globais das demais contas e não autoriza write de orçamento/lance/status. Completar o modelo com as configurações live antes do gate, preservando o financeiro em pedidos de acréscimo.

### Continuidade e alterações incrementais do relatório

1. Para pedido genérico de relatório de qualquer conta de anúncio SHEIN, independentemente de domínio, canal, gestor ou solicitante autorizado, use as dezessete colunas do padrão global vigente, seguidas do histórico diário de sete datas e Média 7d. Consulte os `account_report_overrides` vigentes: principal por ROI estimado decrescente e histórico por número crescente são ordenações independentes, preservando todos os IDs e rótulos COPY. Os antigos `account_sort_overrides` ficam como compatibilidade histórica, abaixo da política global vigente e de um pedido explícito autorizado. Modelos históricos de sete ou treze colunas e antigos agrupamentos específicos da conversa não substituem o contrato atual por inferência. Um pedido explícito diferente pode adaptar colunas, agrupamento e ordenação; um complemento do relatório já emitido preserva seu snapshot e recorte. Para Meta × Smart Bidding, carregue `references/smartbidding-product-analysis.md` antes de procurar runners ou snapshots; recupere a referência quando o pedido for explicitamente aquele relatório/modelo. Não remover colunas expressamente pedidas nem trocar agrupamento sem pedido.
2. Distinga atualização integral de complemento: “de agora” exige novas métricas financeiras na mesma janela; “esse mesmo relatório, adiciona uma coluna” conserva seleção, valores, totais e ordem do snapshot e consulta somente o atributo novo. Informe separadamente os horários financeiro e de configuração para não apresentar dados preservados como uma coleta financeira atualizada.
3. Aplique o drill-down expressamente pedido: ao separar campanhas de um produto, mantenha as outras colunas e a ordenação do modelo, substituindo apenas a dimensão Produto pela identificação de cada campanha. Não interprete esse drill-down como mudança permanente de todos os relatórios.
4. Acrescente `Bid` antes de `Custo` e `Orç./dia` imediatamente após `Gasto $` quando essas posições forem solicitadas. Leia configuração real por campanha e seus conjuntos; não derive bid ou orçamento de nomes, gastos ou custo por resultado. A receita das campanhas sem entrega fica separada quando esse for o recorte financeiro aprovado, e campanhas pausadas sem gasto podem ser relacionadas fora da tabela principal.
5. Separe coleta, cálculo e apresentação: persista cada fonte concluída e o consolidado validado antes de renderizar. Corrija falhas de formatação a partir desses arquivos, sem repetir consultas financeiras nem misturar snapshots. Gere cabeçalho, linhas, total e rodapé do mesmo consolidado; calcule a largura de cada coluna pelo maior valor entre cabeçalho e células já formatadas, incluindo quantidade de campanhas e sufixos. Valide IDs únicos, cobertura, ordem das colunas, conservação dos totais e tamanho de cada mensagem completa. Use `references/smartbidding-product-analysis.md` para coleta paralela recuperável, leitura de Bid/orçamento e consolidação financeira.

### Histórico supersedido — padrão anterior de treze colunas e Produto20

O padrão atual é o compacto global de quinze colunas e Produto12 no início desta skill. O texto desta subseção documenta o estado anterior; algoritmos de ROI, cores, família e histórico que não foram alterados continuam válidos.

Por decisão explícita de Rodolfo na thread `1560303769680355525`, todo pedido genérico de relatório de uma conta de anúncio SHEIN usa exatamente os rótulos e a ordem **R/E → Início → Nº → Produto → Quiz → Gasto → Receita → Saldo → Est.Health → ROI → ROI est. → ROAS → Lance**. R/E é a primeira coluna, com duas bolinhas independentes: ROI real e depois ROI estimado. A primeira mantém positivo 🟢, negativo 🔴 e exatamente zero 🟡. A segunda usa ROI estimado <+10% 🔴, de +10% a +40% inclusive 🟡, acima de +40% 🟢; indisponível/inválido ⚪ para ambas. Comparar antes de arredondar. Não são ações nem status. Logo abaixo de todo o relatório principal, incluir histórico de ROI real de sete datas (dia do relatório + seis anteriores), mesmas campanhas e mesma ordem, datas crescentes no fuso da conta; marcar hoje com * e informar horário parcial. Usar diário Meta × receita líquida SB, sem transportar o denominador SB ou a estratégia CPV. `Dia` no histórico é idade civil desde primeira entrega comprovada, inclusive, não lifecycle CPV. Acrescentar `Média 7d` na extrema direita: média aritmética dos ROIs reais diários válidos das mesmas sete datas, calculada sem arredondar; excluir n/d sem imputar zero, mostrar cobertura n/7 quando incompleta e n/d sem dias válidos. Incluir hoje parcial se válido e marcar a média com *, mantendo o horário de corte explícito. Vale independentemente de domínio, gestor, canal ou solicitante autorizado, incluindo Geizian e todos os gestores. Substitui o antigo padrão provisório de sete colunas e seus defaults por conta; esses modelos permanecem somente como histórico. Pedido explícito diferente pode adaptar o relatório sem alterar o padrão global.

Usar cabeçalho curto com conta/período/moeda, tabela alinhada em bloco `text` e rodapé breve. No principal e no histórico, separar todas as colunas com ` | ` (barra vertical ASCII U+007C), sem barras externas, moldura ou linhas horizontais. Rodolfo aprovou a prévia como padrão na thread `1560303769680355525`. Validar posição visual de cada separador, largura Unicode e tamanho de cada mensagem completa; preservar dados, colunas e famílias. Centralizar cabeçalhos e células de R/E, Início, Nº, Quiz e todas as colunas à direita (Gasto até Lance); somente Produto fica à esquerda. No histórico, centralizar todas as colunas, incluindo Média 7d. Usar largura visual Unicode para não deslocar as bolinhas. Fonte do alinhamento: Rodolfo, mensagem `1560315984261287949`. Separar Nº e Produto; produto é rótulo do nome, não prova visual. Limitar a célula Produto a **20 caracteres no total, contando espaços, sem acrescentar reticências ou outro sufixo**; manter uma única linha e largura visual máxima de 20. Rodolfo aprovou esse visual na thread `1560303769680355525`, supersedendo o limite anterior de 25 com `...`. Truncar apenas a apresentação, preservando o produto completo no modelo, na ordenação e na identidade das famílias; não alterar nomes Meta nem unir produtos que passem a ter o mesmo prefixo. Não incluir legenda explicativa por padrão: manter somente rodapé curto com fontes/fórmulas essenciais, corte parcial e limitações relevantes. Ordenar por Produto A–Z e, dentro de cada produto, por famílias: campanha de origem seguida imediatamente por suas cópias em bloco contíguo (ex.: 97 → 113 COPY C97). Ordenar somente as raízes das famílias por primeira entrega crescente, número e ID; entre cópias irmãs, usar os mesmos desempates. A posição abaixo da origem prevalece sobre a cronologia plana; em várias gerações, percorrer pai antes dos filhos, preservando a origem direta no rótulo COPY. Aplicar exatamente a mesma ordem ao histórico. Na paginação, prevalece a política posterior `discord_pagination`: preencher a mensagem com o máximo de linhas completas até o limite real de 2000, preservando a ordem/adjacência da família, mas permitindo que ela continue na mensagem seguinte; não antecipar uma quebra só para manter a família na mesma página. Resolver vínculos apenas pelo marcador COPY explícito, pai único do mesmo produto/conta no recorte; detectar ciclos e origem ausente/ambígua sem inventar nem omitir campanhas. Essa correção posterior de Rodolfo na mesma thread supersede a ordenação plana anterior. Na célula Nº, preservar o número e acrescentar `COPY Cxx` quando esse marcador constar no nome atual verificado da campanha; mostrar a origem direta literal, sem inferir pela UTM ou buscar a raiz recursivamente. Sem marcador, mostrar somente o número, sem afirmar inexistência de cópia histórica. São ajustes de apresentação, nunca autorização de renomear campanhas na Meta. Fontes: Rodolfo, mensagens `1560341636741861550` e `1560341816447082708`. Receita é `NET_REVENUE` SB, Saldo = Receita − gasto Meta; ROI normal e ROI estimado (`REVENUE_ESTIMATED`) permanecem distintos. Quiz e Lance exigem readback real; Lance é MAXVOL/COCAP/BIDCAP ou misto. Sem base, conservar a coluna com `n/d` e explicar, sem inventar nem omitir silenciosamente. Não acrescentar Custo/Res., orçamento ou cards por padrão, salvo pedido explícito.

Período, filtros e agrupamento seguem o pedido atual, sem herdar Health <95%, ordem da imagem ou recorte de outra consulta. Domínios e acesso continuam sujeitos aos gates existentes: independência do domínio na apresentação não amplia autorização. O padrão é on-demand, não cron, nova cadência ou automação. Fonte estrutural: `SHEIN-US-DIRECT.json#/reporting/on_demand_default_layout`; definições, procedimento e histórico: `references/smartbidding-product-analysis.md`.

### Atraso GAM/SB obrigatório no cabeçalho

Todos os relatórios de contas de anúncio SHEIN incluem **⏱️ ATRASO GAM/SB: <Hh MMmin ou Mmin>** em destaque acima da tabela, mantendo as dezessete colunas do padrão global vigente. Rodolfo pediu o mesmo indicador do CPV na thread `1560303769680355525`; copiar somente a leitura/apresentação, nunca thresholds, cortes, escala ou automações CAR. Fonte canônica: `SHEIN-US-DIRECT.json#/reporting/on_demand_default_layout/gam_delay`.

Consultar read-only `POST /estimated/delay` pelo helper Smart Bidding com `publisherIds` reais do domínio autorizado do relatório e moeda correspondente; usar `totalMinutes`, salvar horário da observação e escopo. O indicador é atraso dos dados GAM conforme reportado pelo SB, em nível de publisher, não atraso individual de campanha nem medição direta pela API GAM. Em múltiplos publishers, separar leituras. Sem leitura válida, negativa/não finita ou falha, mostrar `n/d` com motivo; zero somente se a fonte retornar zero válido. Em complemento, preservar o financeiro e declarar o novo horário; em relatório histórico, não chamar a leitura atual de atraso histórico. Receita/Saldo/ROI podem estar sujeitos à defasagem; não compensar valores artificialmente. Procedimento e teste live em `references/smartbidding-product-analysis.md`.

### Rota curta para Estimated Health — YOLO por gestor

Para listar campanhas YOLO abaixo de Estimated Health e completar Gasto, Custo/resultado, ROI, ROAS e Início, execute o runner account-scoped `/root/.hermes/profiles/ares/scripts/shein-health-report.py --manager g00N --account <ID exato do contrato> --output <diretório do pedido>`. Faça `--self-test` ao validar manutenção da rota. O runner valida domínio, binding do gestor, identidade Meta, data/moeda, evento web Add to Wishlist, paginação, custo da action exata e primeira entrega; coleta Meta/SB em paralelo e gera `report.json` + `report.md`. Seu renderizador legado de sete colunas não é o padrão vigente e não deve ser entregue como relatório final genérico: reutilizar a coleta e completar Receita, Saldo, ROI est., Quiz e Lance com a receita account-scoped da referência, renderizando R/E + as doze colunas originais e o histórico de sete datas logo abaixo, conforme o contrato vigente. É on-demand/read-only, não cron nem campaign writer. Preservar o filtro explicitamente pedido e a separação de sem-base; não converter ausência de denominador em 0%. Usar essa rota somente quando a seleção pedida for por Health: aumentar o threshold não transforma o runner em coleta completa por produto, pois campanhas sem denominador ou sem correspondência SB continuam fora da seleção.

Não redescobrir endpoints em relatórios CAR/CPV, não carregar registry completo e não criar/editar scripts temporários durante relatórios rotineiros. Para continuidade, filtrar registry/checkpoint em código pela chave/thread e carregar somente os apontadores pertinentes. Se apenas completar uma coleta anterior, reutilizar o snapshot ou declarar explicitamente a atualização integral.

Todo relatório informa:

- período e timezone da conta;
- moeda;
- fonte Meta e, quando houver ROI, fonte de receita;
- conta/alias e gestor;
- data de início da campanha nos cards e na tabela consolidada: usar a primeira data com entrega comprovada por Insights (impressões ou gasto), no fuso da conta; não substituir por `created_time`, data no nome ou schedule atual; sem evidência, mostrar início de veiculação não confirmado e identificar o schedule separadamente;
- fórmula de ROI/ROAS/custo;
- limitações e divergências.

Não somar contas com moedas ou janelas incomparáveis. Não ativar cron, corte, escala ou otimização automática porque outra operação possui essa regra. Até existir política SHEIN própria, relatórios e ações são on-demand por gestor.

Antes de culpar a campanha por queda, conferir anomalias de entrega, monetização e join de receita quando essas fontes estiverem disponíveis. Ao interpretar Est.Health de 0%, distinguir ausência de denominador de zero calculado por divergência CDP/GAM; conservar ROI real e estimado separados, sem converter o alerta de mensuração em diagnóstico causal do criativo ou autorização de corte. Aplicar a verificação dos contadores em `references/smartbidding-product-analysis.md`, seção `HEALTH separado de ROI`.

Para análises SHEIN de campanha, criativo e produto, carregar `references/smartbidding-product-analysis.md` quando envolver Pricing, HEALTH, ranking de produtos ou mudança de regime de monetização.

Para análises SHEIN de campanha, criativo e produto:

- reconciliar Meta e Smart Bidding por `CAMPAIGN_ID` + conta, comparando `spend` Meta com `INVESTIMENT` antes de calcular ROI;
- filtrar novamente o campo `DATE` retornado pelo Smart Bidding, porque janelas ISO em UTC podem incluir a data civil anterior da conta;
- calcular o ROI líquido reconciliado como `(NET_REVENUE - spend_Meta) / spend_Meta`, comparando e declarando a diferença para `INVESTIMENT` SB; usar `REVENUE_ESTIMATED` em vez de `NET_REVENUE` somente na coluna ROI estimado. Agregar numeradores e denominadores do mesmo conjunto de campanhas antes de calcular percentuais; tratar `purchase_roas.omni_purchase` da Meta como sinal complementar, não como substituto da receita líquida;
- não usar `PRODUCT` vazio nem nome de campanha como prova visual final: o rótulo do nome é provisório até revisar a mídia;
- quando `GET /<video_id>?fields=source` retornar HTTP 200 sem `source`, usar `GET /<video_id>/thumbnails`, amostrar quadros distintos do início/meio/fim e manter o produto como não validado se a variedade visual for insuficiente;
- ROI externo existe no nível de campanha/ad set quando o tracking não carrega identidade do anúncio; nesse caso, ranquear criativo por ROAS Meta e gasto, mostrando o ROI apenas como contexto da campanha, nunca como ROI direto do asset.

Conclusão: recomendação ou write usa dados do mesmo período, moeda e chave de junção.

## Discord

### Acompanhamento comum das landing pages

A rota SHEIN de criação/duplicação permanece exatamente a atual: não carregar referência de acompanhamento, não preparar fila/landing, não trocar o transporte da resposta e não adicionar wrapper/callback. Criar, validar e responder normalmente; somente um processo independente posterior pode consumir a conclusão já existente. O isolamento e o estado vigente vivem em `data/ares/meta-ads/policies/direct-traffic-landing-followup.json`; o acompanhamento usa leitor externo da entrega nativa, GET da resposta e provas já salvas, sem modificar pedidos ou consultar novamente a Meta. A integração antiga pela barreira de resposta foi supersedida por Rodolfo e retirada. Somente o processo separado usa `direct-traffic-cbo-operations/references/landing-followup.md`; nenhuma herança CAR de budget/lifecycle/evento, nenhuma disputa de lane/quota com campanhas e nenhum alerta do acompanhamento ao gestor.

### Fechamento de criação e duplicação

Após validar o lote inteiro, responda com confirmação curta de fonte + quantidade + conta e bullets de números novos, orçamento diário por campanha e total do lote, início no fuso verificado, lance efetivamente herdado/aplicado, status e quantidade real de anúncios validados. Separe a ressalva de posts novos/prova social e qualquer normalização de público comprovada; não declare cópia literalmente idêntica quando houver omissão de flags. Use as árvores finais e a prova de QA como fonte, não os números previstos pelo dry-run nem a cardinalidade do pedido anterior. Data futura com status ACTIVE significa habilitada/programada, não entrega já comprovada.

Separe conclusão operacional de cumprimento do SLA: confira `phase`, `activation_result.trees`, cobertura de `media_qa` e `original_request_e2e_ms` antes de classificar o resultado. Um readback final pode terminar após o alvo mesmo com ativação já concluída; nesse caso, confirme o estado real validado e preserve a medição de atraso, sem anunciar SLA cumprido, repetir ativação ou abrir continuação desnecessária. Somente o estado efetivo `ACTIVATION_DEFERRED` com revisão pendente segue a receita de continuação; não o deduza apenas da duração total. Não altere relógio, limite ou manifests para reconciliar essa diferença.

Distinga orçamento do lote, delta do request e orçamento ativo total da conta. Some os budgets dos IDs novos verificados para informar o lote; não calcule o delta autorizado subtraindo dois snapshots globais da conta, pois outras campanhas podem mudar entre as leituras. Quando informar o total ativo da conta, use o readback consolidado e identifique-o separadamente do lote.

- Responder na thread atual.
- Toda thread inclui Zeus e Rodolfo; a lista operation-scoped adiciona Geizian e o gestor do canal.
- Confirmar membros somente por readback real.
- Título: 3–6 palavras, assunto + contexto; não sobrescrever título manual.
- Responder no destino vigente do tipo de pedido: criação na sua origem e relatório on-demand na thread vinculada à conta. Não criar ou ativar novas rotas de relatório/otimização por inferência; preservar o histórico e os títulos manuais.
- As seis threads fixas deletadas por Rodolfo não podem ser recriadas por inferência ou recovery.

Conclusão: resposta, thread e participantes pertencem ao canal/gestor corretos, sem reabrir rotas removidas.

## Pitfalls

1. Herdar `1×1×3`, evento, bid, data ou lifecycle de Creditoparaveiculo só porque ambos são tráfego direto.
2. Tratar autorização de campanha como autorização de billing, credencial ou pixel.
3. Considerar `01_READY` ou uma pasta `USADOS` prova suficiente de elegibilidade.
4. Misturar os três sites sem registrar idioma e URL final por anúncio.
5. Reutilizar conta/perfil de outro gestor para contornar falta de acesso.
6. Criar cron/otimização recorrente a partir de um pedido pontual.
7. Reportar ROI sem fonte de receita, período, moeda ou timezone comparáveis.
8. Usar o pacote legado G005 `prepare-live/materialize` no intake normal de outros gestores ou criar um fast lane RODO/G002. Todo pedido equivalente usa `campaign --input` e o mesmo core. Resolver perfil/autoridade/conta/canal; não remontar manifest, editar scripts ou redescobrir a BM durante a transação.
9. Declarar targeting literalmente idêntico após native copy sem comparar GET fonte × alvo. A Meta pode omitir `targeting_automation.individual_setting` mesmo após update com o targeting exato. Preservar `age_range` e `user_age_unknown` expostos pela fonte, reconciliar somente o alvo e registrar qualquer normalização residual; não remover esses campos presumindo que são output-only. Post ID igual comprova preservação do post, mas não substitui contadores sociais quando `pages_read_engagement` estiver indisponível.

## Auditoria read-only de UTM duplicada

- Transcrever o `utm_adgroup` literalmente da evidência e resolver o site pelo contrato antes do gate; não inferir a campanha somente pelo número contido na UTM.
- Para busca em todas as contas SHEIN autorizadas, usar o catálogo account-scoped, confirmar identidade live e paginar anúncios com campanha, conjunto e creative (`url_tags`, `object_story_spec`, `asset_feed_spec`, `link_url`). Aplicar `url_tags` sobre os parâmetros da URL ao determinar o tracking efetivo; ocorrência somente no nome do conjunto não prova UTM no destino.
- Incluir uma passagem explicitamente filtrada por `effective_status IN [ARCHIVED, DELETED]`, com paginação completa. A listagem padrão pode omitir origens arquivadas que reutilizam a mesma UTM e produzir falso negativo; informar separadamente duplicidade histórica e campanhas atualmente aptas a entregar.
- Persistir lotes de evidência sem credenciais, agregar por UTM + campaign ID único e validar cobertura do catálogo. Fazer GET dos IDs exatos antes do resumo; múltiplos anúncios do mesmo conjunto/campanha não são múltiplas campanhas duplicadas. Não alterar tracking por um pedido de localizar.
- Testar cobertura integral das duas passagens, unicidade dos campaign IDs, precedência de `url_tags`, ocorrência da UTM em destino e igualdade de conta/nome/status no readback. Procedimento exercitado em consulta live com ambas as passagens completas e duplicidade histórica confirmada.

## Verificação

- [ ] Contrato SHEIN vivo carregado
- [ ] Canal, gestor, conta e perfil reconciliados
- [ ] Site e idioma compatíveis com copy/criativos
- [ ] Objetivo/evento fixos `OUTCOME_SALES` / `OFFSITE_CONVERSIONS` / `ADD_TO_WISHLIST`; estrutura, bid, budget e schedule resolvidos
- [ ] Authority do pedido confirmada sem ampliar escopo
- [ ] Criativos reservados e conciliados Drive × Meta
- [ ] Engine v3 validate/plan concluído para criação/clone/lote
- [ ] Write mínimo e GET/readback completos
- [ ] Período, moeda, timezone e fontes declarados em relatório
- [ ] Zero herança implícita de CAR/CPV ou de outro gestor

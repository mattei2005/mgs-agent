---
name: direct-traffic-cbo-operations
description: "Use quando Ares estruturar, validar ou analisar campanhas Meta de tráfego direto por CBO para quiz/chat, com ou sem captura, incluindo UTMs MGS, estrutura 1x1x3 e reconciliação de receita Smart Bidding + SMS com custo de SMS."
version: 1.0.33
author: Ares
license: internal
metadata:
  hermes:
    tags: [mgs, growth, meta-ads, direct-traffic, cbo, quiz, sms, utm, smart-bidding]
    related_skills: [paid-acquisition-operations, meta-ads-account-visualization, creative-taxonomy-mgs]
---

# Direct Traffic CBO Operations — MGS/Ares

## Overview

Esta skill governa a frente de **tráfego direto no link**. Ela é separada da estratégia DTR/ChatPion e cobre campanhas CBO para quatro variantes:

```text
Experiência | Captura | Receita a reconciliar
------------|---------|-------------------------------------------
Quiz        | Sim     | Aquisição + SMS; descontar custo de SMS
Quiz        | Não     | Aquisição; SMS só se houver envio real
Chat        | Sim     | Aquisição + SMS; descontar custo de SMS
Chat        | Não     | Aquisição; SMS só se houver envio real
```

Ares pode ler, validar, analisar e recomendar. Criar/editar campanha, budget, pixel, tracking ou credencial em produção exige autorização explícita de Rodolfo. Billing/pagamento exige double-confirm.

## When to use

Carregue esta skill quando o pedido mencionar:

- tráfego direto, link direto ou CBO;
- quiz/chat com ou sem captura;
- nomenclatura `b01fb01c01`, `...g01` ou gestor `gXXX`;
- Smart Bidding em `Reports > Adgroup` ou `Reports > SMS`;
- SMS Funnel, custo de SMS ou relatório `mgs-quiz-report`;
- lucro/ROAS/receita total de campanha com captura.

Não use como dona da configuração do quiz, ChatPion, SMS Funnel, pixel ou WordPress. Nesses sistemas, Ares faz leitura e reconciliação; alterações de produto/tracking pertencem ao responsável técnico e exigem o fluxo de autorização aplicável.

## Progressive disclosure

1. Para criar, clonar, executar em lote ou otimizar throughput, carregue primeiro `meta-campaign-engine-v3/SKILL.md`; não faça busca ampla nem altere runner dentro da transação.
2. Para montar ou revisar URL/naming, abra `references/campaign-naming-and-utm.md`.
3. Para performance, receita e custo, abra `references/revenue-and-dashboard-reconciliation.md`.
4. Para validar uma URL deterministicamente, execute `scripts/validate_direct_traffic_utm.py`.
5. Só carregue outra referência se a pergunta realmente atravessar as duas áreas.

### Campaign Engine v3

Toda criação/clonagem nova usa o executor central v3. Esta skill define estratégia CBO, evento, naming, UTM, ROI e regras da operação; ela não implementa outro campaign writer. O v2 existe somente como rollback explícito até o canário v3 ser promovido.

Conclusão antes do hot path: operação, manifest, mídia pre-stageada, source, budget, status e horário estão fechados; durante o hot path não existe `Searching`, patch, teste, criação de cron ou releitura global de portfólio.

## Fluxo operacional

### 1. Classificar a estratégia

Registrar antes da campanha:

```text
Campo                  | Valores
-----------------------|------------------------------------------
Canal                  | Meta/Facebook
Compra                 | CBO
Destino                | Link direto
Experiência            | quiz / chat
Captura                 | com captura / sem captura
Formato dos criativos  | imagem / vídeo / mix
Gestor                 | gXXX
BM / conta / campanha  | sequência numérica confirmada
Adset                   | sequência numérica confirmada
```

Conclusão: nenhum campo estrutural está implícito ou inferido do nome do site.

### 2. Aplicar estrutura padrão

Padrão normal informado por Rodolfo:

```text
Nível Meta | Quantidade | Regra
-----------|------------|-------------------------------------
Campanha   | 1          | CBO e link direto
Adset      | 1          | código `gNN` dentro da campanha
Anúncios   | 3          | imagem, vídeo ou mix permitido
```

### 2.1 Tipos de estratégia de lance

```text
Tipo operacional          | UI Meta                        | Campaign API              | Adset API
--------------------------|--------------------------------|---------------------------|-----------------------------
Meta de custo por resultado| Meta de custo por resultado   | COST_CAP                  | bid_amount obrigatório
Valor/volume mais alto     | Valor ou volume mais alto     | LOWEST_COST_WITHOUT_CAP   | omitir bid_amount
```

**Meta de custo por resultado:** define uma meta de CPA/custo médio por resultado. Não é um teto rígido por conversão: a própria Meta informa que alguns resultados podem custar mais e outros menos. Um alvo excessivamente baixo pode restringir fortemente a entrega e o gasto. Referência CPV: C07 com `bid_amount=50` em USD.

**Valor ou volume mais alto:** não configura meta de CPA no conjunto; a Meta busca maximizar conversões/volume dentro do orçamento, com mais latitude de entrega e aprendizado. Referência CPV: C08 com `LOWEST_COST_WITHOUT_CAP` e sem `bid_amount`.

Regras:

1. Campanha criada do zero exige o tipo explicitamente informado pelo solicitante; se faltar, perguntar antes do write.
2. Clone herda exatamente `bid_strategy` e presença/valor de `bid_amount` da campanha/adset fonte.
3. Não usar “com bid/sem bid” como única classificação técnica: todo leilão possui lances; a diferença é meta de custo configurada versus maximização sem meta de CPA.
4. Nomenclatura aprovada: sufixos de campanha/adset `COSTCAP-0.50` versus `MAXVOL`; coluna de relatório `Lance` com `CPA 0,50` versus `MAXVOL`.
5. Se o adset expuser `bid_constraints.roas_average_floor`, classificar provisoriamente como `ROAS` no relatório e não renomear como MAXVOL; é uma terceira estratégia que ainda exige definição explícita de Rodolfo. C11 é a exceção viva identificada.

Evento de conversão obrigatório no **adset/conjunto**, independentemente de haver captura:

```text
Estratégia | Com/sem captura | Evento operacional informado | Meta Graph `promoted_object.custom_event_type`
-----------|-----------------|-------------------------------|-----------------------------------------------
Chat       | obrigatório     | `event_add_to_wishlist`       | `ADD_TO_WISHLIST`
Quiz       | obrigatório     | `event_Subscribe`             | `SUBSCRIBE`
```

O evento é definido pela experiência, não pela captura. Validar no adset `optimization_goal=OFFSITE_CONVERSIONS`, pixel presente e `promoted_object.custom_event_type` correto. Esses literais não precisam integrar o nome da campanha, salvo regra de naming separada e explícita.

Qualquer desvio do 1×1×3 deve estar explícito no pedido/spec. Antes de campanha, cada criativo precisa passar pelo metadata sanitizer canônico do Ares.

### 3. Construir e validar UTMs

Valores obrigatórios:

```text
Parâmetro      | Formato
---------------|---------------------------------
utm_source     | facebook
utm_medium     | gXXX-f para chat; gXXX-s para quiz
utm_campaign   | bNNfbNNcNN
utm_adgroup    | bNNfbNNcNNgNN
```

Exemplo canônico informado:

`?utm_source=facebook&utm_medium=g002-f&utm_campaign=b01fb01c01&utm_adgroup=b01fb01c01g01`

Nunca aceitar espaço depois de `=`. O valor `utm_medium= gXXX-f` é inválido; o espaço mostrado em prosa não integra a nomenclatura.

Conclusão: o validador retorna `VALID` e confirma que o prefixo de `utm_adgroup` é idêntico a `utm_campaign`.

### 4. Gate read-only antes de recomendar

Coletar fontes reais do mesmo período/timezone:

```text
Fonte                         | Uso
------------------------------|-------------------------------------------
Meta Ads                      | spend, entrega, cliques, CTR/CPC e eventos
Smart Bidding > Adgroup       | receita/conversões por adgroup/campanha
Smart Bidding > SMS           | receita de SMS quando houver captura
SMS Funnel                    | volume/custo real disponível do fornecedor
WP mgs-quiz-report            | leads absorvidos e custo estimado base WP
```

Não misturar custo estimado WordPress com custo efetivamente faturado pelo fornecedor. Se o dado de vendor não existir, nomear claramente a estimativa.

### 5. Reconciliar o resultado

Para uma janela comparável:

```text
Receita bruta = receita de aquisição + receita de SMS elegível
Custo SMS     = mensagens cobradas × custo unitário confirmado
Margem        = receita bruta − gasto Meta − custo SMS
ROAS bruto    = receita bruta ÷ gasto Meta
ROAS líquido  = (receita bruta − custo SMS) ÷ gasto Meta
```

Nunca calcular sem moeda, período, timezone e chave de junção confirmados. Não somar SMS para uma estratégia sem captura apenas por existir uma tela de SMS.

Conclusão: totais por fonte fecham com o consolidado, e divergências ficam visíveis em vez de serem arredondadas/ocultadas.

### 6. Relatar e agir

- Reportar aquisição, SMS e custo de SMS em colunas separadas.
- Exibir fonte e status de reconciliação.
- Recomendar antes de escrever na Meta, salvo quando Rodolfo autorizar explicitamente `autonomous_guarded` para uma operação e a fonte canônica da operação registrar `write_enabled=true`.
- Em `autonomous_guarded`, executar somente ações e tiers nomeados na configuração da operação, sobre IDs imutáveis explicitamente allowlisted. Fazer plano completo antes do write, somar todo budget CBO configurado-ativo da conta em centavos inteiros, validar conta/moeda/fuso/saúde/hierarquia e falhar o lote de escalas se o plano combinado exceder o cap.
- Persistir estado `in_flight` com fsync antes do POST. Budget/status usa um único POST absoluto sem retry automático; após resposta ambígua/crash/timeout, fazer GET antes de qualquer retry e aceitar somente valor original ou valor desejado — terceiro valor ou `updated_time` alterado bloqueia por possível ação humana.
- Relatórios recorrentes em thread fixa usam chave idempotente por dia/checkpoint e readback Discord por GET, validando thread, mensagem e conteúdo. Tabela cercada que ultrapassar o chunk seguro deve falhar fechada em vez de publicar bloco quebrado.
- Alterar o cap da conta, billing, credenciais, criação/clone/replacement e outras operações continuam fora do escopo salvo autorização própria.
- Depois de qualquer write autorizado, validar via GET real a campanha, CBO/budget, status e os campos afetados; para criação, validar também adset, três anúncios e parâmetros da URL.
- Na rotina diária CPV, reservar 20% do cap USD300 para campanhas novas: pool padrão USD60, normalmente 2 campanhas de USD30. Iniciar o ciclo às 17:00 São Paulo e preparar entre 17:00–23:30. A estratégia padrão autorizada é `MAXVOL` (`LOWEST_COST_WITHOUT_CAP`) até nova decisão explícita. A data exibida no nome é sempre a **data de entrega/início**, não a data de criação: se preparar em 20/08 para iniciar 21/08 00:30, nomear `NN - 21-08 ...`. A rota alvo é agendamento nativo: criar/duplicar o adset já com `start_time=00:30` do dia seguinte, validar o horário por GET e só então deixar a campanha `ACTIVE`; o adset futuro governa a entrega e elimina um job posterior de ativação. Nunca aceitar horário atual herdado da fonte. Se o adset já iniciou tecnicamente, a Meta bloqueia mudança de `start_time` (`code=100/subcode=1487057`); nesse caso não reconstruir perto da virada sem nova decisão — manter campanha PAUSED e usar o fallback pontual de ativação já validado. Antes do write, validar espaço real no cap; campanha do zero exige estratégia explícita e clone herda a fonte. Testes de capacidade pedidos como desativados permanecem PAUSED sem agendamento até aprovação.
- A numeração diária CPV é estritamente sequencial. Por correção de Rodolfo em 20/08/2026, a próxima campanha é C12; saltos para slots livres altos como C50/C49 são proibidos. Em lote de duas campanhas, exigir C12 e C13 contíguas; se C13 já existir e não estiver `DELETED`, falhar fechado e pedir decisão explícita entre criar somente C12 ou executar replacement controlado de C13.
- Quando Rodolfo pedir clone na rotina CPV, usar clone nativo raso da campanha e adset fonte C08 MAXVOL (`/copies`, sem copiar ads legados), validar a shell clonada e então anexar três novos creatives do Drive por campanha. Copiar campos da C08 para objetos criados do zero não pode ser descrito como clone. Replacement sequencial valida as novas campanhas PAUSED antes de deletar/readback as antigas uma por uma.
- Sempre que criar campanhas CPV, selecionar somente linhagens únicas liberadas e reconciliadas do Shared Drive, mover os assets usados de `01_READY` para `02_TESTING` após readback Meta e informar na thread de criação: quantidade usada, total restante em `01_READY` por IMG/VID e total restante de criativos únicos já liberados/reconciliados. Essa atualização de estoque é obrigatória mesmo quando o volume bruto do Drive for maior que o pool imediatamente elegível.
- O formato do relatório pode substituir `ID REC` pela própria coluna/número da campanha quando o contrato específico da operação registrar essa exceção; nunca aplicar a remoção globalmente por inferência.
- Em Discord, o layout é definido por tipo de relatório e pela referência visual explícita mais recente do operador. Quando Rodolfo disser “quero assim” acompanhando screenshot, reproduzir a estrutura dessa referência em vez de aplicar preferência genérica por cards/linhas. Tabela aprovada pode ser usada tanto no Diário quanto no Intraday; novas colunas devem declarar fonte e fórmula.
- Emoji fica no início da coluna `Sinal`; o renderer deve calcular largura visual Unicode, não `len()`, e toda linha do resumo recebe sinal explícito para evitar recuo variável. `ID REC` permanece apenas no audit quando a operação o removeu da apresentação.
- Quando a cadência de relatório mudar, não deslocar silenciosamente outro tipo de relatório nem o checkpoint de ação. Separar `Daily schedule`, `Intraday schedule` e `action-only checkpoint`, registrar a agenda vigente na fonte canônica e superseder explicitamente a anterior. Em Creditoparaveiculo BR-CAR-BR: o **Diário das 07:00** referencia o dia anterior fechado; os **Diários das 08:00, 11:00, 14:00 e 20:00** referenciam o próprio dia até o horário do envio. O **Intraday** permanece contínuo a cada 2 horas nas horas ímpares de São Paulo (`01/03/05/07/09/11/13/15/17/19/21/23`); a escala autorizada continua às 08:00 em checkpoint separado. O snapshot de continuidade às 03:00 é diário, local, sem reset, e arquiva exclusivamente as três threads fixas de criação, Diário e Intraday registradas na operação; qualquer outra thread segue o padrão definido com Zeus.
- Cabeçalhos compactos aprovados devem ser preservados. Quando `Campanha` virar `Camp`, exibir também a data operacional no mesmo campo (`CNN-DD/MM`, como `C07-20/08`) usando data persistida/naming validado, não a data presumida do relatório.
- Quando o Diário exibir `Budget`, rotular como budget atual da Meta se o período for histórico; `Custo` deve declarar a ação/fórmula usada, por exemplo `spend ÷ omni_purchase`.

## Guardrails de credenciais

- Credenciais e tokens ficam no 1Password; nunca transcrever valores em chat/log.
- Reportar apenas item, campo utilizado, status e comprimento.
- Acesso válido à dashboard não autoriza alteração de configuração.
- Se login exigir 2FA, CAPTCHA, reset de senha ou nova permissão, parar e pedir a intervenção/autorização necessária.

## Common pitfalls

1. **Confundir `-f` e `-s`.** Nesta taxonomia, `-f` identifica chat e `-s` identifica quiz.
2. **Configurar evento errado no adset.** Chat exige `ADD_TO_WISHLIST`; quiz exige `SUBSCRIBE`, com ou sem captura. Não confundir evento de conversão com texto de naming.
3. **Confundir gestor e adset.** `gXXX` em `utm_medium` é gestor; `gNN` no final de `utm_adgroup` é o número do conjunto.
4. **Duplicar sequência.** `utm_adgroup` deve copiar `utm_campaign` integralmente antes de acrescentar o adset.
5. **Misturar DTR/ChatPion.** A campanha desta skill é link direto por CBO, não a estratégia de bot.
6. **Somar receita sem captura.** Receita SMS só entra quando houver captura/envio atribuível no mesmo recorte.
7. **Usar R$ 0,08 como fatura real.** O relatório WordPress atual estima 8 centavos por linha filtrada; isso não prova evento cobrado no vendor.
8. **Cruzar datas diferentes.** Meta, SB, SMS Funnel e WP precisam do mesmo período/timezone ou da divergência declarada.
9. **Concluir por login.** Acesso é validado só depois de abrir as páginas/relatórios e observar dados/filtros esperados.
10. **Copiar criativo legado com `standard_enhancements`.** Em Graph v25, `/copies` pode falhar com `3858504` quando o `degrees_of_freedom_spec` da fonte ainda contém `creative_features_spec.standard_enhancements`; é erro de parâmetro não transitório, não recebe retry.
11. **Reconstruir criativo dinâmico só pelo story ID.** Fontes com `asset_feed_spec` podem exigir `catalog_id`/`product_set_id`; story-only pode falhar com `1815017`. Extrair o payload dinâmico gravável real e nunca inventar esses IDs.
12. **Tratar HTTP 200 sem ID como sucesso.** Em write não idempotente, `success=false`, payload com `error` ou ausência de ID não confirma criação. Fazer GET por nome exato + linhagem antes de qualquer retry; se nada aparecer, classificar como falha. `execution_options=[validate_only]` retorna `success=true` sem ID por definição e nunca prova write real.
13. **Assumir que o token que cria também deleta.** Validar a capacidade de cleanup no preflight. Se o token anunciante não remover o artefato, usar somente uma credencial de cleanup já autorizada e confirmar `DELETED` por GET.
14. **Interpretar `code=31`/`error_subcode=3858385` como problema de payload ou IP da VPS.** A Meta documenta tokens como portáveis entre navegador e servidor. Esse subcode é um checkpoint de autenticação do anunciante; o prompt pode ficar oculto até editar/criar um anúncio e tentar publicar no Ads Manager. Procurar `Verifying your changes → Start Authentication`, concluir e-mail/SMS e só então repetir `validate_only`. Se a API continuar bloqueada sem ação visível, registrar como variante API-only e escalar com as threads/bug report oficiais.
15. **Exigir o mesmo `video_id` ou ordem ao reconstruir criativo dinâmico.** A Meta pode materializar novos IDs e reordenar vídeos. Reconciliar como conjunto/bijeção por título, duração, dimensão e evidência visual pixel-idêntica de frame, além de manter textos, links, CTA, formatos e regras exatos.
16. **Criar anúncio imediatamente após o criativo.** Criativo recém-criado pode precisar de propagação. Aplicar espera limitada, executar `validate_only` e só então o POST real; erro de parâmetro ou segurança não recebe retry.
17. **Limpar criativo antes do anúncio/campanha.** A ordem segura é anúncios → campanha/adset → criativos → assets técnicos. Remover o criativo primeiro pode bloquear o cleanup da campanha com `2446289` (`Ad Creative Is Incomplete`).
18. **Ignorar tier e role do app.** Header `ads_api_access_tier=development_access` indica tier limitado/desenvolvimento. Conferir no App Dashboard o Marketing API Access Tier, acesso de `ads_management` e se o usuário anunciante é Admin/Developer/Tester. Limited serve a pilotos por app roles; produção com usuários externos exige o acesso/review aplicável.
19. **Tratar System User como única arquitetura.** Facebook Login for Business suporta User Access Token que herda os assets atuais do usuário, sem mover todas as Pages para uma única BM. System User/BISU exige assets owned/shared ou explicitamente designados em business portfolios e pode ser inviável em alto volume; escolher arquitetura com Rodolfo.
20. **Trocar de token/app sem readback durante o cleanup.** Se anúncios falharem com `2446289` antes de a campanha ficar `DELETED`, fazer GET e, depois da exclusão confirmada da campanha, repetir uma única vez com a credencial de cleanup já autorizada: anúncios → readback `DELETED` → criativos. Para vídeos técnicos da Página, se User Token retornar `code=10/subcode=1363055`, resolver internamente o Page Access Token via `/me/accounts` e excluir somente os IDs técnicos allowlisted; nunca registrar o token. Concluir apenas quando anúncios/criativos estiverem `DELETED`, os vídeos retornarem `100/33` ou sumirem do edge da Página e o gasto permanecer zero.
21. **Criar adset `BRAZIL_REGULATION` só com DSA beneficiary/payor.** Esses textos não satisfazem `3858634` (`Advertiser is missing`). Ler `regional_regulation_identities` do adset fonte compliant e enviar junto com `regional_regulated_categories`; para BR, exigir `universal_beneficiary` e `universal_payer`, podendo usar o mesmo verified identity ID. Rodar `validate_only` antes do write e confirmar as identidades no readback.
22. **Rejeitar cópia HTTP 200 sem `success`/`id` mesmo quando há ID específico.** `/copies` pode retornar somente `copied_campaign_id` ou `copied_adset_id` (e `ad_object_ids`). Aceitar apenas essas chaves reconhecidas, persistir o ID imediatamente e fazer GET antes de qualquer nova tentativa; nunca repetir a cópia só porque `success` não veio.
23. **Tratar `PENDING_REVIEW` como anúncio desligado por herança sem conferir configuração.** O gate correto para campanha de revisão é: campanha `configured_status=PAUSED`; adset/anúncio `configured_status=ACTIVE`; effective do filho pode estar `CAMPAIGN_PAUSED`, `PENDING_REVIEW`, `IN_PROCESS` ou `WITH_ISSUES` durante materialização/revisão. O pai PAUSED continua sendo o bloqueio de entrega.
24. **Tratar `ARCHIVED` como campanha ainda arquivada.** Em Creditoparaveiculo, `ARCHIVED` no Graph representa campanha `DELETED` no Ads Manager. Relatórios e respostas humanas usam `DELETED`; `ARCHIVED` fica apenas como `api_raw_status` no audit. Não contar esses objetos como campanhas vivas, pausadas ou reutilizáveis sem nova criação.
25. **Adicionar geração/sufixo fora do wrapper para reciclar número.** O wrapper UTM é imutável (`bNNfbNNcNN` / `...gNN`); `rNN` ou equivalente é proibido. Segundo Ciro, dev da SB, deletar a campanha antiga basta para reutilizar a UTM canônica. O estado final nunca pode manter duas campanhas não deletadas com a mesma UTM. Fluxo: confirmar antiga PAUSED e terminal → criar substituta PAUSED e validar → deletar antiga e confirmar `DELETED` → ativar substituta após revisão. Campanha antiga ACTIVE bloqueia o rollover.
26. **Usar outro objeto Graph do mesmo número como prova de publicação de um rascunho.** Quando o Ads Manager mostra `Em rascunho`, `Conferir e publicar` ou sufixo `— Cópia`, aquela campanha ainda não foi publicada. Um objeto Graph PAUSED separado, mesmo com o mesmo número, não prova a publicação do draft. Reconciliar o objeto exato por UI/ID/estado; screenshot e confirmação manual do operador vencem a inferência. Drafts do Ads Manager não são campanhas normais da Graph e exigem `Conferir e publicar` ou `Descartar rascunhos` na própria UI.
27. **Validar remoção de `standard_enhancements` por substring.** `standard_enhancements_catalog` é uma chave diferente e pode aparecer como `OPT_OUT`. O gate procura recursivamente a chave JSON exata `standard_enhancements`; não reprovar criativo apenas porque outra chave contém o mesmo prefixo.
28. **Não tratar `code=17`/`subcode=2446079` no readback final como erro definitivo.** Se todos os POSTs já produziram IDs, persistir campanha/adset/anúncio/creative/vídeos e assignments como `readback_deferred`, manter assets reservados e retomar o GET somente após cooldown. Não fazer cleanup apenas porque o GET final foi limitado; cleanup é para erro de write/validação ou estado terminal comprovadamente inválido. Um reconciliador determinístico deve finalizar readback, movimento `01_READY→02_TESTING`, inventário e estoque antes de liberar o próximo ciclo.
29. **Não reportar o total bruto de `01_READY` como estoque disponível.** `01_READY` prova prontidão técnica, não elegibilidade. Sempre separar: total físico live por IMG/VID, total com identidade Drive↔inventário íntegra e total único `ares_eligible=true` após current+paused+archived Meta. Gaps Drive-only, inventory-only ou filename duplicado ficam fail-closed e não entram no saldo utilizável até reparo da identidade/status.
30. **Comparar bulk do Ads Manager com a capacidade de uma app `development_access`.** O header BUC vivo pode expor `ads_api_access_tier=development_access`, sujeito a limite incompatível com automação de alto volume. Não concluir que “40 campanhas funcionam” prova a mesma capacidade da rota API atual sem identificar UI/API, app e tier. No curto prazo, separar reconciliação, staging de mídia, preparo e ativação; usar batch readiness/readback, budget de chamadas por estágio e estado resumível. Para escala, auditar e obter o acesso Standard/Advanced aplicável antes do teste de 10/40 campanhas.
31. **Não executar reconciliação global dentro do campaign writer.** A baseline Drive×Meta pode ler centenas de ads/media, mas roda uma vez e depois incrementalmente em job separado. Dry-run e retry de duas campanhas nunca repetem todo o portfólio. Graph batch reduz conexões HTTP, porém seus subrequests continuam consumindo quota lógica. Um incidente CPV repetiu seis full scans, 1.436 video subrequests e 984 linhas de ads antes de o writer ser pausado; esse padrão é proibido.
32. **Não confundir redução de transport calls com redução de quota.** Cada child de Graph batch continua contando logicamente. O helper deve registrar `X-Ad-Account-Usage` separado do BUC e, quando a Meta não enviar esse header, usar um ledger local rolling de 300s que só libera write após warmup completo. Projetar reads×1 + mutations×3 + reserva de readback antes de qualquer write. Em `development_access`, se duas campanhas não couberem mas uma couber, preparar somente a primeira PAUSED e persistir a segunda como `preflight_deferred` para a próxima janela; se nem uma couber, não fazer upload/write. A rota diária de novos criativos continua clone raso de campaign/adset + creatives do Drive. Deep copy assíncrono por `async_batch_requests` fica disponível apenas para clone fiel explícito, sempre PAUSED e com polling bounded; não é bypass de quota.
33. **Tratar `validate_only` como idempotente, não como write real.** `validate_only` é idempotente e pode receber no máximo duas retentativas com espera fixa de 10s exclusivamente para HTTP `5xx` (inclusive `code=1` genérico), além do retry bounded de propagação `2446289`. O POST real que cria campanha/adset/anúncio continua single-attempt; erro de parâmetro, permissão, segurança ou compliance nunca recebe retry automático.

## Verification checklist

- [ ] Estratégia classificada como quiz/chat e com/sem captura
- [ ] Adset de chat usa `ADD_TO_WISHLIST` (`event_add_to_wishlist`)
- [ ] Adset de quiz usa `SUBSCRIBE` (`event_Subscribe`)
- [ ] Adset usa `OFFSITE_CONVERSIONS` e pixel presente
- [ ] Campanha CBO e estrutura esperada 1×1×3 documentadas
- [ ] BM, conta, campanha, adset e gestor confirmados
- [ ] `utm_source=facebook`
- [ ] `utm_medium` válido e sem espaços
- [ ] `utm_campaign` e `utm_adgroup` consistentes
- [ ] Criativos sanitizados antes de uso
- [ ] Período, timezone e moeda iguais/explicados nas fontes
- [ ] Receita de aquisição e SMS separadas
- [ ] Custo SMS rotulado como vendor real ou estimativa base WP
- [ ] Nenhum write executado sem autorização explícita
- [ ] Qualquer write validado por leitura pós-ação
- [ ] Tier, BUC, X-Ad-Account-Usage ou ledger local maduro registrados antes do write
- [ ] Score lógico projetado cabe na janela com reserva de readback
- [ ] Fallback development executa no máximo uma campanha por janela e preserva continuação

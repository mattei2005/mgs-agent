---
name: direct-traffic-cbo-operations
description: "Use quando Ares estruturar, validar ou analisar campanhas Meta de tráfego direto por CBO para quiz/chat, com ou sem captura, incluindo UTMs MGS, estrutura 1x1x3 e reconciliação de receita Smart Bidding + SMS com custo de SMS."
version: 1.0.15
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

1. Para montar ou revisar URL/naming, abra `references/campaign-naming-and-utm.md`.
2. Para performance, receita e custo, abra `references/revenue-and-dashboard-reconciliation.md`.
3. Para validar uma URL deterministicamente, execute `scripts/validate_direct_traffic_utm.py`.
4. Só carregue outra referência se a pergunta realmente atravessar as duas áreas.

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
- O formato do relatório pode substituir `ID REC` pela própria coluna/número da campanha quando o contrato específico da operação registrar essa exceção; nunca aplicar a remoção globalmente por inferência.
- Em Discord, o layout é definido por tipo de relatório e pela referência visual explícita mais recente do operador. Quando Rodolfo disser “quero assim” acompanhando screenshot, reproduzir a estrutura dessa referência em vez de aplicar preferência genérica por cards/linhas. Tabela aprovada pode ser usada tanto no Diário quanto no Intraday; novas colunas devem declarar fonte e fórmula.
- Emoji fica no início da coluna `Sinal`; o renderer deve calcular largura visual Unicode, não `len()`, e toda linha do resumo recebe sinal explícito para evitar recuo variável. `ID REC` permanece apenas no audit quando a operação o removeu da apresentação.
- Quando a cadência de relatório mudar, não deslocar silenciosamente o checkpoint de ação. Separar `report schedule` de `action-only checkpoint`. “A cada 2h começando 07:00, contínuo” significa sequência ímpar atravessando a meia-noite (`...21:00, 23:00, 01:00, 03:00, 05:00, 07:00...`), sem parada às 23:00; a escala autorizada às 08:00 continua em checkpoint separado sem relatório extra.
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
25. **Reutilizar a UTM ao reciclar um número de campanha.** Os slots Meta são `01–60`, mas `utm_campaign` e `utm_adgroup` precisam ser únicos por linhagem na Smart Bidding. Deletar a campanha antiga não torna a chave histórica reutilizável. Até Rodolfo aprovar o formato de geração e a compatibilidade do parser SB, falhar fechado ao tentar reciclar slot já usado. Depois da aprovação: fechar D3/reconciliação → criar nova geração PAUSED → readback → deletar campanha terminal antiga → ativar somente após revisão.

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

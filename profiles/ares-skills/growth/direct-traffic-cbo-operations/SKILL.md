---
name: direct-traffic-cbo-operations
description: "Use quando Ares estruturar, validar ou analisar campanhas Meta de tráfego direto por CBO para quiz/chat, com ou sem captura, incluindo UTMs MGS, estrutura 1x1x3 e reconciliação de receita Smart Bidding + SMS com custo de SMS."
version: 1.0.3
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
- Em `autonomous_guarded`, executar somente ações e tiers nomeados na configuração da operação, com lock/idempotência, preflight Meta vivo, holds, ceilings/caps, audit sanitizado e GET/readback. Persistir estado `in_flight` antes do POST; após crash/timeout, fazer GET antes de qualquer retry e aceitar somente valor original ou valor absoluto desejado — terceiro valor bloqueia por possível ação humana.
- Relatórios recorrentes em thread fixa usam chave idempotente por dia/checkpoint e readback Discord por GET, validando thread, mensagem e conteúdo. Tabela cercada que ultrapassar o chunk seguro deve falhar fechada em vez de publicar bloco quebrado.
- Alterar o cap da conta, billing, credenciais, criação/clone/replacement e outras operações continuam fora do escopo salvo autorização própria.
- Depois de qualquer write autorizado, validar via GET real a campanha, CBO/budget, status e os campos afetados; para criação, validar também adset, três anúncios e parâmetros da URL.
- O formato do relatório pode substituir `ID REC` pela própria coluna/número da campanha quando o contrato específico da operação registrar essa exceção; nunca aplicar a remoção globalmente por inferência.
- Em Discord, o layout é definido por tipo de relatório, não globalmente. Preserve tabela monoespaçada curta quando o operador aprovar o Diário dessa forma; para Intraday de alta frequência, prefira uma linha compacta por campanha quando tabela larga ou cards de três linhas ficarem repetitivos. Nunca reaproveitar automaticamente a preferência visual de um relatório no outro.
- Emoji fica no início da linha/coluna de sinal; `ID REC` permanece apenas no audit quando a operação o removeu da apresentação.

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

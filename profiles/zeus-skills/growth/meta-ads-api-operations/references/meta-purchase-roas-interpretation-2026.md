# Meta Purchase ROAS — interpretação e auditoria (2026)

Use esta referência quando Rodolfo pedir para explicar, validar ou conciliar a coluna **Purchase ROAS** no Meta Ads Manager ou o campo `purchase_roas` da Insights API.

## Definição operacional

```text
Purchase ROAS = purchase conversion value / amount spent
```

Interpretação: `0.61` significa 0,61 unidade monetária de valor de compras atribuído para cada 1 unidade monetária gasta. Não significa 61% de lucro. ROAS mede valor/receita atribuída contra mídia; não deduz produto, comissão, taxas, chargeback, equipe ou infraestrutura.

O resumo de várias linhas é a razão entre os totais, não a média aritmética dos ROAS individuais:

```text
ROAS agregado = soma(purchase conversion value) / soma(amount spent)
```

Se a UI arredonda o ROAS, qualquer valor de compras reconstruído por `spend × ROAS exibido` é apenas aproximado.

## O que compõe o numerador

A Meta consolidou métricas antigas de website/app na métrica omnicanal Purchase ROAS. O numerador pode combinar valores atribuídos provenientes de Pixel, Conversions API, SDK, eventos offline e superfícies Meta como Shops, Marketplace, Pages ou Messenger.

Para eventos `Purchase`, `value` deve ser monetário e `currency` deve ser um código ISO 4217. O ROAS só tem significado econômico real se `Purchase.value` representar o valor que a empresa decidiu tratar como receita. Em operações de afiliados/publishers, descobrir antes se o valor representa receita bruta, comissão, payout líquido, valor esperado ou proxy sintético.

## Atribuição

Purchase ROAS inclui somente compras atribuídas aos anúncios, não todas as compras do negócio. Verificar no Ad set:

- modelo padrão, incremental ou customizado;
- click-through de 1 ou 7 dias;
- view-through de 1 dia;
- engage-through de 1 dia, quando disponível.

A coluna isolada não revela essas escolhas. Não comparar Ad sets com modelos ou janelas diferentes como se fossem equivalentes.

## Modelagem e maturidade

A Meta pode modelar compras e valores quando os dados estão parciais ou ausentes e distribuir conversões modeladas entre campanha, Ad set e anúncio. Tratar Purchase ROAS como métrica de atribuição da plataforma, não como extrato financeiro.

Insights:

- atualizam aproximadamente a cada 15 minutos;
- podem continuar mudando por alguns dias;
- usam o fuso da conta;
- desde 10 de junho de 2025, o comportamento alinhado ao Ads Manager usa `action_report_time=mixed`: ações on-Meta por data da impressão; ações off-Meta, como compras no website, por data da conversão.

Evitar matar ou escalar anúncios somente pelo ROAS de `Today`; gasto amadurece antes de matching, deduplicação, atribuição e modelagem.

## Auditoria antes de confiar

1. Exibir juntos `Purchase ROAS`, `Purchases conversion value`, `Purchases` e `Amount spent`.
2. Registrar modelo e janelas de atribuição por Ad set.
3. Fazer uma compra controlada e confirmar um único `Purchase` com `value` e `currency` corretos.
4. Se Pixel + CAPI enviarem o mesmo evento, validar deduplicação por `event_name` + `event_id`.
5. Conferir Diagnostics, eventos redundantes, alertas de moeda/valor e Event Match Quality.
6. Definir institucionalmente o significado de `Purchase.value`.
7. Conciliar Meta × backend/pedidos × receita reconhecida no mesmo período, moeda e fuso.
8. Usar janela madura para decisão; intraday serve como sinal provisório.

## ROAS de equilíbrio

```text
ROAS de equilíbrio = 1 / margem de contribuição
```

Exemplo: margem de contribuição de 40% implica ROAS de equilíbrio de 2,50. ROAS 1,00 apenas iguala valor bruto atribuído e gasto de mídia.

## Fontes oficiais prioritárias

- Purchase ROAS: https://en-gb.facebook.com/business/help/274294333328345
- Consolidação das métricas: https://en-gb.facebook.com/business/help/metrics-removal
- Modelos e janelas de atribuição: https://www.facebook.com/business/help/460276478298895
- Métricas estimadas/modeladas: https://www.facebook.com/business/help/metrics-labeling
- Parâmetros CAPI `value`/`currency`: https://developers.facebook.com/docs/marketing-api/conversions-api/parameters/custom-data/
- Deduplicação Pixel/CAPI: https://en-gb.facebook.com/business/help/823677331451951
- Diferenças com ferramentas externas: https://www.facebook.com/business/help/147965221941551
- Timing e atualização de Insights: https://developers.facebook.com/documentation/ads-commerce/marketing-api/insights/best-practices
- Event Match Quality: https://www.facebook.com/business/help/765081237991954

## Pitfalls

- Não chamar ROAS de lucro ou ROI.
- Não assumir USD apenas pelo símbolo `$`; confirmar `account_currency`.
- Não assumir fuso pela data visível; confirmar timezone da conta.
- Não reconstruir valor exato usando ROAS arredondado.
- Não comparar ROAS Meta com GA4/backend sem alinhar moeda, fuso, período e atribuição.
- Não declarar prejuízo confirmado antes de validar `Purchase.value`, deduplicação e atribuição.

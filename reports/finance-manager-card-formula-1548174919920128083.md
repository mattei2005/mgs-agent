# Correção da fórmula e do desenho dos cards dos gestores

## Autoridade

- Correção direta de Rodolfo: `1548174919920128083`.
- Thread: `1545426987756298340`.
- Supersede a interpretação de `1548167344650461236` que ligou os cards à linha legada `row14`.

## Erro confirmado

A primeira versão reutilizou `row14` das planilhas como se fosse uma projeção válida. Para Nicolas, isso exibiu US$ 143.655,10, duplicou `Projeção do mês`/`Resultado líquido estimado` e gerou referências de comissão artificialmente altas. Essa fonte deixa de alimentar os cards.

## Regra ativa

A aba atual do gestor passa a ter cinco cards:

### Linha atual — dois cards

1. `Resultado líquido até DD/MM`
   - resultado líquido acumulado até o cutoff/dia preenchido;
   - USD principal e BRL abaixo.
2. `Comissão atual · 7%` ou `Comissão atual · 10%`
   - faixa escolhida pelo resultado líquido atual convertido para BRL;
   - abaixo de R$ 100.000: 7%;
   - a partir de R$ 100.000: 10%;
   - USD principal e BRL abaixo.

### Linha estimada — três cards

3. `Resultado líquido estimado`
   - `resultado líquido atual ÷ dias preenchidos × dias do mês`.
4. `Referência 7% estimada`
   - 7% do resultado líquido estimado.
5. `Referência 10% estimada`
   - 10% do resultado líquido estimado.

Os dias preenchidos vêm de `domain.realized.elapsed_days`; se esse campo não estiver disponível, o sistema usa o dia do cutoff da própria competência. Sem dias preenchidos, a estimativa permanece indisponível. Cada card já recebe USD e BRL no payload da API; a interface não inventa conversão.

O piso de remuneração de gestor permanece na regra de pagamento. O segundo card mostra a comissão/faixa corrente pedida por Rodolfo, não substitui o cálculo do pagamento.

## Readback de Nicolas — setembro/2026

Fonte viva após publicação:

- cutoff: 10/09/2026;
- dias preenchidos: 10;
- dias do mês: 30;
- resultado atual: US$ 14.537,54 / R$ 73.709,69;
- comissão atual vencedora: 7%, US$ 1.017,63 / R$ 5.159,68;
- resultado estimado: US$ 43.612,61 / R$ 221.129,07;
- referência 7% estimada: US$ 3.052,88 / R$ 15.479,03;
- referência 10% estimada: US$ 4.361,26 / R$ 22.112,91.

O valor anterior de US$ 143.655,10 não aparece mais nos cards.

## Arquivos publicados

- `apps/finance-system/manager-view.mjs`
- `apps/finance-system/public/operations.js`
- `apps/finance-system/public/operations.css`

Cobertura alterada:

- `apps/finance-system/tests/manager-current-period.test.mjs`
- `apps/finance-system/tests/manager-layout.test.mjs`
- `apps/finance-system/private/manager-tabs-audit-1548145007612137554/browser.mjs`
- `apps/finance-system/private/manager-tabs-audit-1548145007612137554/remote-audit.mjs`

## Validação

- Teste RED reproduziu ausência da nova fórmula e da estrutura 2+3.
- Focais: 11/11.
- Node integral: 130/130.
- Stage: cinco gestores, 2 cards atuais + 3 estimados, valores USD/BRL e fórmula conferidos, 390/1440px, zero erro JavaScript.
- Produção: mesma validação nos cinco gestores.
- API: 85/85 combinações de 17 competências × 5 gestores com `card_summary` válido.
- Reconciliação das abas e valores financeiros de origem: preservada.
- PostgreSQL: fingerprint idêntico antes/depois.
- Serviços financeiros: ativos após restart controlado.
- Gateway Hermes: não reiniciado.
- Backup: `/home/zeus/mgs-finance-backups/1548174919920128083/`.

## Falhas e rollback

1. O primeiro preflight incluiu por engano um arquivo CSS em `node --check`; falhou antes da publicação. Stage e backup foram preservados e validados, sem exclusão.
2. A primeira tentativa de cutover procurou o auditor temporário dentro do diretório final. O código chegou a ser trocado, mas o finalizador executou rollback dos três arquivos e restaurou os serviços antes de retornar a falha.
3. O auditor foi corrigido para rodar no stage após verificar os hashes exatos do diretório final. A publicação seguinte passou integralmente.

Nenhuma falha deixou estado parcial em produção.

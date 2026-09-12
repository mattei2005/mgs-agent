# Reconciliação das abas atuais de gestores

## Autoridade e fonte

Rodolfo `1548145007612137554`, thread `1545426987756298340`. Relatório completo: `/root/mgs-agent/reports/finance-manager-tabs-audit-1548145007612137554.md`. Evidência: `/root/mgs-agent/apps/finance-system/private/manager-tabs-audit-1548145007612137554/`.

## Cards atuais e estimados — correção de Rodolfo `1548174919920128083`

Esta regra supersede integralmente a interpretação de `1548167344650461236` que ligou os cards diretamente ao resumo legado `row=14`. Aquela implementação gerou valores altos e duplicou `Projeção do mês` com `Resultado líquido estimado`; `row14` não é mais fonte dos cards.

Mostrar cinco cards:

- linha atual: `Resultado líquido até DD/MM`, usando o row12 acumulado até o cutoff;
- linha atual: `Comissão atual · 7%` quando o resultado atual convertido para BRL estiver abaixo de R$ 100.000, ou `Comissão atual · 10%` a partir de R$ 100.000;
- linha estimada: `Resultado líquido estimado = resultado atual ÷ dias preenchidos × dias do mês`;
- linha estimada: `Referência 7% estimada = resultado estimado × 7%`;
- linha estimada: `Referência 10% estimada = resultado estimado × 10%`.

Usar `domain.realized.elapsed_days`; fallback somente para o dia do cutoff da própria competência. Zero dias preenchidos mantém a estimativa indisponível. Todos os cards exibem USD principal e BRL secundário pela cotação da competência. O piso permanece na regra de pagamento e não muda a comissão/faixa mostrada no segundo card.

Relatório e readback: `/root/mgs-agent/reports/finance-manager-card-formula-1548174919920128083.md`.

## Causa e regra ativa

A página usava apenas células legadas para os blocos diários. A receita GAM de setembro já existia em `domain.facts` e atualizava o total row12, mas não entrava nas colunas dos sites. Nunca conclua que coluna vazia significa receita zero sem comparar o bloco com fatos nativos por gestor/site/país/dia.

Para setembro/2026 e seguintes:

- preservar métricas legadas do bloco, principalmente mídia e receita anterior;
- somar fatos `native_addition` pelo gestor interno (`george` para Ícaro), site, país e dia;
- preservar origem não-USD pelo `addition` correspondente e Gross normalizado em USD;
- integrar `native_manager_spend` no próprio site com sinal negativo; não manter bloco `spend_only` quando existe o site financeiro;
- criar bloco completo para site nativo sem metadata legada;
- se houver exatamente um país legado e um país real diferente, usar o país real e transportar a mídia existente; múltiplos países continuam fail-closed, sem remapeamento arbitrário;
- dias posteriores ao cutoff ficam vazios;
- total mensal soma dias não arredondados; ROI mensal usa totais, nunca média de ROI diário;
- reconstruir resumos por site dos blocos corrigidos;
- exigir soma dos sites igual ao row12 da fonte dentro de USD 0,000001; divergência bloqueia a API em vez de maquiar ajuste;
- remuneração e caixa só podem ser declarados preservados quando row12 e fingerprint do banco permanecerem iguais.

Agosto continua no modo legado auditado. Janeiro–julho continuam no histórico fechado.

## Estado validado

- Setembro: 443 fatos nativos verificados.
- Blocos: Joe 6; Isliago 9; Kelly 7; Ícaro 11; Nicolas 9.
- Yolokfx completo 5/5; Portal Relevante presente para Ícaro; Openzed canônico; Creditoparaveiculo BR.
- Row12: 5/5 reconciliados; remuneração e caixa inalterados.
- Banco: fingerprint antes/depois idêntico.
- Produção: 85/85 APIs, 5/5 logins reais, owner 5/5, 390/1440px, zero JS errors.
- Testes: 130 Node e 87 Python; cards 2+3 validados nos cinco gestores, projeção por 10 dias preenchidos × 30 dias de setembro, faixa atual 7%/10%, USD/BRL exatos, 390/1440px e zero JS errors.

## Rateio das Despesas Gerais

Apresentação aprovada na mesma mensagem:

- coluna `Rateio das Despesas Gerais`;
- badge `Participa` ou `Não participa`;
- editor `Participa do rateio` ou `Não participa do rateio`.

`Não participa` preserva receitas/gastos e remove somente as cotas do rateio. Valores internos `ATIVO/INATIVO` permanecem para compatibilidade e nunca devem voltar a aparecer como rótulos nessa interface.

# Auditoria integral das abas de gestores — setembro/2026

## Autoridade e escopo

- Pedido: Rodolfo `1548145007612137554`, thread `1545426987756298340`.
- Escopo executado: cinco gestores, setembro/2026 em profundidade e regressão de todas as 17 competências de trabalho, agosto/2026–dezembro/2027.
- Também foi aplicada a nomenclatura aprovada para o rateio das Despesas Gerais.
- Nenhum valor financeiro, conta, pagamento, remuneração, fonte Google ou credencial foi alterado.

## Causa-raiz confirmada

A estrutura visual dos gestores estava correta, mas `manager-view.mjs` lia os blocos diários exclusivamente das células legadas em `scenario.result.results`. A receita GAM de setembro entrou como fatos nativos em `scenario.result.domain.facts`; esses fatos já atualizavam os totais por gestor, mas não eram materializados nas colunas diárias. Por isso o total/remuneração podia estar correto enquanto Gross, inválidos, líquido, imposto e lucro dos sites apareciam vazios.

A auditoria também encontrou:

- custos nativos de Yolokfx em um bloco separado `gastos das suas contas`, com sinal visual positivo;
- sites com receita nativa sem bloco próprio, como Portal Relevante para Ícaro e Yolokfx para todos;
- rótulos antigos de país, como Creditoparaveiculo `US` apesar da receita corrente `BR`;
- `Openzed US` como rótulo de bloco, embora o site canônico seja Openzed;
- linhas-resumo por site com distribuição antiga, embora o total row12 dos cinco gestores permanecesse exato.

## Correção aplicada

Para setembro/2026 e competências seguintes, a API do gestor agora:

1. preserva os valores legados já existentes no bloco detalhado, principalmente mídia e receita anterior;
2. soma cada fato nativo por gestor + site + país + dia;
3. preserva o valor bruto original em CAD/GBP/BRL quando existe e mantém o Gross normalizado em USD;
4. integra custos nativos no próprio site, com sinal negativo correto;
5. cria blocos completos para sites novos/dinâmicos em vez de blocos `spend_only`;
6. troca um único país legado pelo país real quando a fonte antiga está desatualizada, sem remapear casos multi-país;
7. mantém dias posteriores ao cutoff vazios;
8. recalcula os totais mensais e ROI a partir dos dias, nunca por média de ROI;
9. reconstrói as linhas-resumo por site a partir dos blocos corrigidos;
10. exige que a soma dos sites continue igual ao total financeiro row12 já usado por remuneração e caixa; divergência acima de USD 0,000001 bloqueia a resposta.

Agosto permanece no modo legado já auditado. Janeiro–julho continuam no histórico fechado. Nenhuma retropropagação foi feita.

## Resultado verificado

- Gestores: Joe, Isliago, Kelly, Ícaro e Nicolas.
- Setembro: 443 fatos nativos de gestores conferidos por site/país/dia/métrica.
- Blocos finais: Joe 6; Isliago 9; Kelly 7; Ícaro 11; Nicolas 9.
- Yolokfx aparece como bloco financeiro completo para os cinco.
- Portal Relevante aparece para Ícaro.
- Openzed aparece com identidade canônica e mantém a receita válida de Ícaro/Isliago conforme a atribuição.
- Creditoparaveiculo usa BR quando a receita corrente é BR.
- Cinco totais exibidos conciliam com row12; deltas absolutos máximos abaixo de `0.000000000002` por precisão de ponto flutuante da camada de apresentação.
- Remunerações e caixa permaneceram inalterados porque os totais row12 já estavam corretos.
- Banco de produção: fingerprint integral antes/depois idêntico.
- API real: 85/85 visões — 17 competências × 5 gestores.
- Logins reais: 5/5.
- Owner preview: 5/5 gestores.
- Desktop 1440px e móvel 390px: sem overflow global e zero erro JavaScript.
- Testes: 128/128 Node e 87/87 Python.

## Nomenclatura de rateio

Apresentação nova, mantendo os valores internos `ATIVO/INATIVO` apenas como compatibilidade técnica:

- coluna: `Rateio das Despesas Gerais`;
- `Participa`;
- `Não participa`;
- editor: `Participa do rateio` / `Não participa do rateio`.

`Não participa` mantém receitas e gastos nos resultados e retira apenas as cotas da divisão das Despesas Gerais.

## Recuperação e evidência

- Produção: `/home/mgsfinance/releases/pg-auth-1545934831664242748`.
- Backup: `/home/zeus/mgs-finance-backups/1548145007612137554`.
- Stage: `/var/tmp/mgs-finance-manager-tabs-1548145007612137554`.
- Evidência local: `/root/mgs-agent/apps/finance-system/private/manager-tabs-audit-1548145007612137554`.
- Arquivos publicados: `manager-view.mjs` e `public/app.js`.
- Serviço financeiro foi reiniciado de forma controlada; nenhum gateway Hermes foi reiniciado.

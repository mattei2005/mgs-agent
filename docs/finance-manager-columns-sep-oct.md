# Colunas e projeções dos gestores — setembro/outubro 2026

## Autoridade e escopo

Rodolfo, thread `1545426987756298340`, autorização final `1555702482557075539`. Complementa as decisões de rótulos/ordem `1555700481760952332`, escopo `1555700594298323067` e resumo com referências/projeção `1555701867911053384`. A pausa `1555700833750884464` foi respeitada; a autorização final reúne os dois pedidos.

Alvos: somente setembro (`2026-09`) e outubro (`2026-10`) para Ícaro, Isliago, Joe, Kelly e Nicolas, incluindo prévia administrativa e visão de gestor. Outros meses, resumo financeiro do proprietário, Pagamentos, regras financeiras, remuneração e permissões permanecem fora do escopo.

## Detalhamento diário por domínio

Ordem exata:

1. Dia
2. Receita bruta CAD
3. Receita bruta USD
4. Receita total bruta USD
5. Inválidos
6. Rev share
7. Impostos
8. Despesas Gerais
9. Gastos mídia
10. Gastos SMS
11. Lucro líquido
12. ROI Gross
13. ROI Net

CAD/USD são origens separadas; a receita total é a receita bruta normalizada em USD já calculada pela API. Não somar moedas sem conversão. O grupo TOTAL agrega as origens e o gross dos grupos de país, sem somar novamente as colunas TOTAL existentes. Rev share expõe a diferença existente `net - gross - invalid`; não altera a regra da rede. Despesas Gerais mostra o rateio já atribuído à visão. Não inventar rateio por país onde a fonte só atribui no total.

Lucro, mídia, SMS e ROI permanecem os da API. ROI mensal vem do valor mensal calculado, nunca soma/média dos ROIs diários. Dias futuros/sem dados continuam vazios; não interpretar ausência como zero financeiro. Em setembro, o fechamento mensal SMS continua exclusivamente no TOTAL; em outubro, os custos seguem os fatos diários. Não distribuir o fechamento mensal artificialmente pelos dias.

## Resumo Seus domínios

Colunas:

- Domínio
- Lucro líquido atual
- 7% atual
- 10% atual
- Lucro líquido estimado
- 7% estimado
- 10% estimado

Cabeçalhos agrupados `Realizado até DD/MM` e `Estimativa até o fim do mês`; preservar TOTAL. Remover Inválidos apenas deste resumo, mantendo-o no diário. Não adicionar receitas/custos ao resumo principal.

Projeção por domínio: lucro acumulado / dias completos carregados × dias do mês, usando `card_summary.elapsed_days` e `month_days`, a mesma competência/cutoff dos cards. Zero dias carregados mantém a projeção indisponível. Setembro completo tem fator 1. Referências estimadas de 7%/10% são alternativas explicativas, não pagamentos ou comissão devida por domínio; piso/faixa permanecem nos cards de remuneração. Não prometer a projeção como resultado garantido.

## Implementação e aceitação

A projeção é somente de apresentação em `public/operations.js`; o CSS específico é limitado à classe nova. API, banco, fórmulas, fontes e histórico são preservados. Escopo de mês explícito impede que o novo layout altere agosto/novembro por efeito lateral.

Validar os cinco gestores × dois meses × desktop/mobile, todos os domínios e grupos de país/TOTAL. Comparar cada linha e total com os dados reais; conciliar componentes com lucro; preservar os valores atuais e ROIs. Validar os meses adjacentes como controles negativos, sem overflow global, erros JS ou mutações financeiras. Em mobile, manter rolagem horizontal interna com indicação explícita de deslizar.

Estado de publicação pertence ao relatório `reports/finance-columns-1555702482557075539.md` e ao checkpoint `ZEUS-FINANCE-COLUMNS-1555702482557075539`, não a este contrato isoladamente.

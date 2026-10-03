# Colunas e projeções dos gestores — padrão permanente

## Autoridade e escopo

Rodolfo, thread `1545426987756298340`, autorização final `1555702482557075539`. Complementa as decisões de rótulos/ordem `1555700481760952332`, escopo `1555700594298323067` e resumo com referências/projeção `1555701867911053384`. A pausa `1555700833750884464` foi respeitada; a autorização final reúne os dois pedidos.

**Supersessão de vigência — Rodolfo `1555736746409459743`:** o layout aprovado em setembro/outubro passa a ser padrão também em **novembro/2026 e todos os meses posteriores**, para Ícaro, Isliago, Joe, Kelly e Nicolas, incluindo prévia administrativa e visão de gestor. A restrição anterior a setembro/outubro foi válida até esta nova autorização e permanece documentada no relatório original. Setembro/outubro continuam iguais; agosto/2026 e anteriores preservam a apresentação histórica. Resumo financeiro do proprietário, Pagamentos, regras financeiras, remuneração e permissões seguem fora do escopo.

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

A projeção é somente de apresentação em `public/operations.js`; o CSS específico é limitado à classe nova. API, banco, fórmulas, fontes e histórico são preservados. A vigência aceita somente competências válidas `YYYY-MM` desde `2026-09`, sem lista finita e sem teto de ano. A regra também alcança meses futuros quando forem cadastrados; não cria competências financeiras. Agosto/2026 e anteriores continuam excluídos.

Validar os cinco gestores × todos os meses já cadastrados abrangidos × desktop/mobile, todos os domínios e grupos de país/TOTAL. Comparar cada linha e total com os dados reais; conciliar componentes com lucro; preservar os valores atuais e ROIs. Testar períodos de anos posteriores na regra e agosto como controle negativo, sem overflow global, erros JS ou mutações financeiras. Em mobile, manter rolagem horizontal interna com indicação explícita de deslizar.

A primeira publicação, limitada a setembro/outubro, está em `reports/finance-columns-1555702482557075539.md`. Estado da ampliação permanente: relatório `reports/finance-columns-default-1555736746409459743.md` e checkpoint `ZEUS-FINANCE-COLUMNS-DEFAULT-1555736746409459743`. Este contrato registra autoridade, não prova isoladamente a publicação.

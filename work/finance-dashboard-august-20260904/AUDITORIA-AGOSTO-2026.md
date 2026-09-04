# Auditoria financeira — Agosto 2026

Status: fechamento técnico da dependência concluído; dashboard bloqueada até correção/decisão dos pontos abaixo.
Origem: Discord thread `1545426987756298340`.
Planilha principal: `16umGPmLukDGQtCEBh2inYLnE9xcqWbHa3gJCM9HG9ak`.

## Escopo auditado

- `Agosto 2026` da planilha principal.
- `CAIXA SINTETICO` da planilha principal.
- `Agosto 2026` de Kelly, Isliago, George, Nicolas e Joe.
- Todos os links/gids fornecidos por Rodolfo foram lidos via Sheets API HTTP 200 e apontam exatamente para a aba `Agosto 2026`.
- Nenhuma aba anterior é fonte da futura dashboard. Julho foi consultado somente como estrutura de comparação para detectar fórmulas ausentes em `CAIXA SINTETICO`.

## Cobertura comprovada

- 6 planilhas.
- 7 abas na dependência ativa de agosto.
- 51.319 células com fórmula inventariadas individualmente.
- 200.169 referências/dependências mapeadas.
- 29.058 células importadas nas planilhas dos gestores comparadas com a origem: paridade atual exata.
- 132 recomputações dos resumos dos gestores: zero falhas.
- 72 validações de mapeamento `site → inválido/lucro`: zero falhas.
- Fórmulas com erro visível (`#REF!`, `#VALUE!`, etc.) nas fontes auditadas: zero.
- Planilhas externas não resolvidas: zero.

Artefatos principais:

- `dependency-graph.jsonl` — SHA-256 `efaf929bfa4837bcea03d21dba693bd7c3068bbbf7d612cca77e03a861a8c01a`
- `formula-inventory.jsonl` — SHA-256 `ffe1271041e33da28323043db5269ef166a1e97c2954ff555f6e46fe3443cde2`
- `august-snapshot.json` — SHA-256 `b06402709fa665e3dab2211307c58578af8b2d7ed82199a281875cea8750823e`
- `caixa-snapshot.json` — SHA-256 `2e443b6dfa0850318012cdff3450c6b892f3fe97bbc5890e66c13804098f6822`

## Grafo funcional reconstruído

1. `Agosto 2026` usa `CAIXA SINTETICO!J2` para USD/BRL.
2. `Agosto 2026!H1` usa `GOOGLEFINANCE("USDCAD")`.
3. As cinco planilhas dos gestores importam blocos específicos da aba principal `Agosto 2026` e `CAIXA SINTETICO!J2`.
4. A planilha principal importa de volta quatro saídas de cada gestor (`H1`, `D16`, `E14`, `F14`) para calcular remuneração.
5. O ciclo é tecnicamente resolvido e atualmente sincronizado; a volatilidade cambial continua alterando o fechamento histórico.

## Defeitos confirmados

### 1. `CAIXA SINTETICO` de agosto está incompleta

- 45 fórmulas esperadas na coluna `J` estão vazias.
- Faltam receitas por rede/site, tráfego inválido, despesas da empresa, despesas de funcionários e social-media costs.
- Por consequência, subtotal, total, net e 50% de agosto aparecem zerados/vazios.
- Não é seguro copiar as fórmulas de julho: as posições dos sites mudaram materialmente em agosto.

### 2. Agosto não está fechado: câmbio continua vivo

- `CAIXA SINTETICO!J2 = GOOGLEFINANCE("USDBRL")*99%`.
- `Agosto 2026!H1 = GOOGLEFINANCE("USDCAD")`.
- Durante a auditoria, USD/BRL mudou de `5,069493` para `5,080482` (+0,216767%).
- `F1` afeta 20.004 fórmulas; `H1` afeta 18.005 fórmulas na aba principal.
- Assim, agosto, remunerações e planilhas de gestores continuam mudando depois do fim do mês.

### 3. ROI GROSS TOTAL omite receita de países

Impacto no total de agosto ao incluir todos os GROSS normalizados do próprio bloco:

- FinanceTopFeed: +3,6895 p.p.
- Wantabrand consolidado: +7,6365 p.p.
- Eggbev: +0,4182 p.p.
- Cliquet: +35,1423 p.p.
- Newsoun: +1,7801 p.p.
- Openzed: +0,0019 p.p.
- Fincgriffin: de -100,00% para +23,4611%.
- Helixenit: total usa colunas semanticamente erradas; correção estimada +0,3243 p.p.

### 4. Yolokfx usa GROSS no lugar de receita NET

- `AGT5:AGT35` referencia `AGL` (GROSS_USD), mas o cabeçalho é `RECEITA_NET_TOTAL` e deveria consolidar `AGN`.
- Receita net superestimada em USD 57,4399.
- Lucro superestimado em USD 57,4399.
- ROI net superestimado em 7,5279 pontos percentuais.

### 5. Fórmula isolada incorreta

- `CR23` (`INVALIDO_US`, TopFeed Finanzas) divide novamente por USD/CAD.
- As outras 30 linhas aplicam corretamente o percentual de inválido.
- Impacto financeiro é pequeno, mas a fórmula está objetivamente corrompida.

### 6. Lacunas estruturais para o próximo mês

- Faltam fórmulas de ROI no dia 31 em Marevelx (`ADW35`, `ADX35`) e em três blocos inativos.
- Contecta Geral tem o guard de data futura somente no primeiro dia; os dias 2–31 podem antecipar despesa ao duplicar a estrutura para um mês ainda aberto.
- Quatro planilhas de gestores ainda exibem `Julho` em `A1`, embora as fórmulas usem corretamente a aba `Agosto 2026`.

### 7. `ROI GERAL AGOSTO` existente não é confiável

- 653 de 749 referências auditadas apontam para colunas cujo cabeçalho não corresponde à métrica esperada.
- A causa é drift de coordenadas depois da expansão da aba mensal.
- Essa aba não será usada como fonte da dashboard.

## Conjunto de correção proposto

Total máximo: 347 células, dividido em:

- 306 células necessárias para fechamento/correção financeira de agosto.
- 41 células de higiene estrutural para evitar carregar defeitos à futura aba de setembro.

A escrita ainda não foi executada. Antes dela será criada cópia integral de backup e serão preservados snapshots com fórmulas e valores.

## Lacunas que exigem decisão do Rodolfo

1. Valor fixo de fechamento para USD/BRL e USD/CAD, ou autorização para congelar os valores vigentes no instante da correção.
2. Em `CAIXA SINTETICO`, a linha `M2 | wantabrand EN` não possui correspondência inequívoca na estrutura atual: o bloco disponível é `Wantabrand BR-CAR-BR`. É necessário confirmar se essa é a nova origem.

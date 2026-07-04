# Mapa de fórmulas e dependências — financeiro MGS
Gerado em: 2026-07-03T16:53:31
Fórmulas indexadas: 199854

## Resumo estrutural
| Planilha | Fórmulas | Fórmulas únicas | Padrões únicos | IMPORTRANGE | A3/mês | Caixa | Erros |
|---|---:|---:|---:|---:|---:|---:|---:|
| principal_2026 | 185159 | 58613 | 246 | 25 | 5288 | 6 | 0 |
| kelly | 387 | 136 | 34 | 99 | 0 | 4 | 0 |
| isliago | 12564 | 1694 | 53 | 240 | 0 | 4 | 0 |
| george | 196 | 53 | 8 | 76 | 0 | 4 | 0 |
| nicolas | 761 | 242 | 34 | 239 | 0 | 4 | 0 |
| joe | 787 | 254 | 34 | 236 | 0 | 4 | 0 |

## Interligações
- joe → historical (153 fórmulas)
- isliago → historical (151 fórmulas)
- nicolas → historical (131 fórmulas)
- isliago → principal_2026 (88 fórmulas)
- nicolas → principal_2026 (88 fórmulas)
- george → principal_2026 (76 fórmulas)
- joe → principal_2026 (61 fórmulas)
- kelly → principal_2026 (57 fórmulas)
- kelly → historical (42 fórmulas)
- principal_2026 → isliago (22 fórmulas)
- joe → isliago (22 fórmulas)
- principal_2026 → joe (20 fórmulas)
- principal_2026 → nicolas (20 fórmulas)
- principal_2026 → kelly (20 fórmulas)
- principal_2026 → george (20 fórmulas)
- nicolas → isliago (20 fórmulas)
- principal_2026 → unknown (6 fórmulas)
- principal_2026 → historical (1 fórmulas)
- isliago → isliago (1 fórmulas)

## Funções por área — top roles

### principal_2026 — MGS - Receita dos Sites 2026
- somatório/local total: 110442
- fórmula auxiliar/local: 68723
- rateia despesa pelo número de dias do mês: 5288
- cálculo de receita: 229
- cálculo de lucro: 229
- cálculo de gasto/despesa: 209
- importa outra planilha: 25
- somatório condicional: 10
- cálculo de margem/roi: 4

### kelly — Kelly - MGS - Receita dos Sites
- somatório/local total: 234
- importa outra planilha: 56
- importa bloco mensal com nome da aba: 39
- cálculo de lucro: 27
- cálculo de receita: 15
- fórmula auxiliar/local: 12
- importa caixa sintético: 4

### isliago — Isliago - MGS - Receita dos Sites
- somatório/local total: 11908
- fórmula auxiliar/local: 282
- importa outra planilha: 176
- cálculo de lucro: 107
- importa bloco mensal com nome da aba: 60
- cálculo de receita: 18
- cálculo de gasto/despesa: 9
- importa caixa sintético: 4

### george — George - MGS - Receita dos Sites
- somatório/local total: 72
- importa bloco mensal com nome da aba: 66
- cálculo de lucro: 36
- fórmula auxiliar/local: 12
- importa outra planilha: 6
- importa caixa sintético: 4

### nicolas — Nicolas - MGS - Receita dos Sites
- somatório/local total: 454
- importa outra planilha: 175
- importa bloco mensal com nome da aba: 60
- cálculo de lucro: 36
- cálculo de receita: 20
- fórmula auxiliar/local: 12
- importa caixa sintético: 4

### joe — Joe - MGS - Receita dos Sites
- somatório/local total: 495
- importa outra planilha: 193
- importa bloco mensal com nome da aba: 39
- cálculo de lucro: 24
- cálculo de receita: 20
- fórmula auxiliar/local: 12
- importa caixa sintético: 4

## Pontos críticos para virada Junho→Julho
- Principal usa A3 como número do mês em milhares de fórmulas de distribuição diária; mudar 6→7 é obrigatório.
- Principal usa B4 como ano junto com A3; confirmar 2026.
- Todas as abas de gestores dependem de paridade exata do nome da aba via SHEETNAME()/IMPORTRANGE.
- CAIXA SINTETICO precisa avançar da coluna de junho para a coluna de julho.
- Coluna B/datas do mês precisa ser reconstruída para 31 dias de julho.

## Possíveis inconsistências detectadas

### principal_2026
- month_literal_not_matching_tab em Junho 2026!E129: `=SUM('Abril 2026'!E132)`
- month_literal_not_matching_tab em Maio 2026!E129: `=SUM('Abril 2026'!E132)`
- month_literal_not_matching_tab em Abril 2026!E129: `=SUM('Marco 2026'!E133)`
- month_literal_not_matching_tab em Marco 2026!E130: `=SUM('Fevereiro 2026'!G131)`
- month_literal_not_matching_tab em Marco 2026!I151: `=SUM('Fevereiro 2026'!P140)`
- month_literal_not_matching_tab em Fevereiro 2026!G128: `=SUM('Janeiro 2026'!G131)`
- month_literal_not_matching_tab em Janeiro 2026!G128: `=IMPORTRANGE("https://docs.google.com/spreadsheets/d/1lXgLg541SPqTI7LHc6d05gIygJICxs1OsFWXMWyXLso/edit","Dezembro 2025!G131")`

### isliago
- month_literal_not_matching_tab em Maio 2025!N42: `=IMPORTRANGE("https://docs.google.com/spreadsheets/d/1lXgLg541SPqTI7LHc6d05gIygJICxs1OsFWXMWyXLso/edit";"Novembro 2024!KW95")/3`
- month_literal_not_matching_tab em Abril 2025!N42: `=IMPORTRANGE("https://docs.google.com/spreadsheets/d/1lXgLg541SPqTI7LHc6d05gIygJICxs1OsFWXMWyXLso/edit";"Novembro 2024!KW95")/3`
- month_literal_not_matching_tab em Marco 2025!N42: `=IMPORTRANGE("https://docs.google.com/spreadsheets/d/1lXgLg541SPqTI7LHc6d05gIygJICxs1OsFWXMWyXLso/edit";"Novembro 2024!KW95")/3`
- month_literal_not_matching_tab em Fevereiro 2025!N42: `=IMPORTRANGE("https://docs.google.com/spreadsheets/d/1lXgLg541SPqTI7LHc6d05gIygJICxs1OsFWXMWyXLso/edit";"Novembro 2024!KW95")/3`
- month_literal_not_matching_tab em Janeiro 2025!N42: `=IMPORTRANGE("https://docs.google.com/spreadsheets/d/1lXgLg541SPqTI7LHc6d05gIygJICxs1OsFWXMWyXLso/edit";"Novembro 2024!KW95")/3`
- month_literal_not_matching_tab em Dezembro 2024!N42: `=IMPORTRANGE("https://docs.google.com/spreadsheets/d/1lXgLg541SPqTI7LHc6d05gIygJICxs1OsFWXMWyXLso/edit";"Novembro 2024!KW95")/3`
- month_literal_not_matching_tab em Março 2024!N63: `=IMPORTRANGE("https://docs.google.com/spreadsheets/d/1xi7dx-eS678Zy4j3hoJvXedWY1Mnhhvo7jT_hkFqA2c/edit";"Fevereiro 2024!N67")`

### nicolas
- month_literal_not_matching_tab em Fevereiro 2026!O1: `=IMPORTRANGE("https://docs.google.com/spreadsheets/d/1xi7dx-eS678Zy4j3hoJvXedWY1Mnhhvo7jT_hkFqA2c/edit";"Julho 2024!N47")*-1`
- month_literal_not_matching_tab em Fevereiro 2026!P1: `=IMPORTRANGE("https://docs.google.com/spreadsheets/d/16umGPmLukDGQtCEBh2inYLnE9xcqWbHa3gJCM9HG9ak/edit";"Julho 2024!ER95")*-1`
- month_literal_not_matching_tab em Janeiro 2026!E1: `=IMPORTRANGE("https://docs.google.com/spreadsheets/d/16umGPmLukDGQtCEBh2inYLnE9xcqWbHa3gJCM9HG9ak/edit";"Fevereiro 2026!$E$1")`
- month_literal_not_matching_tab em Janeiro 2026!O1: `=IMPORTRANGE("https://docs.google.com/spreadsheets/d/1xi7dx-eS678Zy4j3hoJvXedWY1Mnhhvo7jT_hkFqA2c/edit";"Julho 2024!N47")*-1`
- month_literal_not_matching_tab em Janeiro 2026!P1: `=IMPORTRANGE("https://docs.google.com/spreadsheets/d/16umGPmLukDGQtCEBh2inYLnE9xcqWbHa3gJCM9HG9ak/edit";"Julho 2024!ER95")*-1`
- month_literal_not_matching_tab em Dezembro 2025!O1: `=IMPORTRANGE("https://docs.google.com/spreadsheets/d/1xi7dx-eS678Zy4j3hoJvXedWY1Mnhhvo7jT_hkFqA2c/edit";"Julho 2024!N47")*-1`
- month_literal_not_matching_tab em Dezembro 2025!P1: `=IMPORTRANGE("https://docs.google.com/spreadsheets/d/1lXgLg541SPqTI7LHc6d05gIygJICxs1OsFWXMWyXLso/edit";"Julho 2024!ER95")*-1`
- month_literal_not_matching_tab em Novembro 2025!O1: `=IMPORTRANGE("https://docs.google.com/spreadsheets/d/1xi7dx-eS678Zy4j3hoJvXedWY1Mnhhvo7jT_hkFqA2c/edit";"Julho 2024!N47")*-1`
- month_literal_not_matching_tab em Novembro 2025!P1: `=IMPORTRANGE("https://docs.google.com/spreadsheets/d/1lXgLg541SPqTI7LHc6d05gIygJICxs1OsFWXMWyXLso/edit";"Julho 2024!ER95")*-1`
- month_literal_not_matching_tab em Outubro 2025!O1: `=IMPORTRANGE("https://docs.google.com/spreadsheets/d/1xi7dx-eS678Zy4j3hoJvXedWY1Mnhhvo7jT_hkFqA2c/edit";"Julho 2024!N47")*-1`
- month_literal_not_matching_tab em Outubro 2025!P1: `=IMPORTRANGE("https://docs.google.com/spreadsheets/d/1lXgLg541SPqTI7LHc6d05gIygJICxs1OsFWXMWyXLso/edit";"Julho 2024!ER95")*-1`
- month_literal_not_matching_tab em Setembro 2025!O1: `=IMPORTRANGE("https://docs.google.com/spreadsheets/d/1xi7dx-eS678Zy4j3hoJvXedWY1Mnhhvo7jT_hkFqA2c/edit";"Julho 2024!N47")*-1`
- month_literal_not_matching_tab em Setembro 2025!P1: `=IMPORTRANGE("https://docs.google.com/spreadsheets/d/1lXgLg541SPqTI7LHc6d05gIygJICxs1OsFWXMWyXLso/edit";"Julho 2024!ER95")*-1`
- month_literal_not_matching_tab em Agosto 2025!O1: `=IMPORTRANGE("https://docs.google.com/spreadsheets/d/1xi7dx-eS678Zy4j3hoJvXedWY1Mnhhvo7jT_hkFqA2c/edit";"Julho 2024!N47")*-1`
- month_literal_not_matching_tab em Agosto 2025!P1: `=IMPORTRANGE("https://docs.google.com/spreadsheets/d/1lXgLg541SPqTI7LHc6d05gIygJICxs1OsFWXMWyXLso/edit";"Julho 2024!ER95")*-1`
- month_literal_not_matching_tab em Junho 2025!O1: `=IMPORTRANGE("https://docs.google.com/spreadsheets/d/1xi7dx-eS678Zy4j3hoJvXedWY1Mnhhvo7jT_hkFqA2c/edit";"Julho 2024!N47")*-1`
- month_literal_not_matching_tab em Junho 2025!P1: `=IMPORTRANGE("https://docs.google.com/spreadsheets/d/1lXgLg541SPqTI7LHc6d05gIygJICxs1OsFWXMWyXLso/edit";"Julho 2024!ER95")*-1`
- month_literal_not_matching_tab em Maio 2025!O1: `=IMPORTRANGE("https://docs.google.com/spreadsheets/d/1xi7dx-eS678Zy4j3hoJvXedWY1Mnhhvo7jT_hkFqA2c/edit";"Julho 2024!N47")*-1`
- month_literal_not_matching_tab em Maio 2025!P1: `=IMPORTRANGE("https://docs.google.com/spreadsheets/d/1lXgLg541SPqTI7LHc6d05gIygJICxs1OsFWXMWyXLso/edit";"Julho 2024!ER95")*-1`
- month_literal_not_matching_tab em Abril 2025!O1: `=IMPORTRANGE("https://docs.google.com/spreadsheets/d/1xi7dx-eS678Zy4j3hoJvXedWY1Mnhhvo7jT_hkFqA2c/edit";"Julho 2024!N47")*-1`

### joe
- month_literal_not_matching_tab em Janeiro 2026!D1: `=IMPORTRANGE("https://docs.google.com/spreadsheets/d/16umGPmLukDGQtCEBh2inYLnE9xcqWbHa3gJCM9HG9ak/edit";"Fevereiro 2026!$E$1")`
- month_literal_not_matching_tab em Maio 2025!O1: `=IMPORTRANGE("https://docs.google.com/spreadsheets/d/1xi7dx-eS678Zy4j3hoJvXedWY1Mnhhvo7jT_hkFqA2c/edit";"Julho 2024!N47")*-1`
- month_literal_not_matching_tab em Maio 2025!P1: `=IMPORTRANGE("https://docs.google.com/spreadsheets/d/1lXgLg541SPqTI7LHc6d05gIygJICxs1OsFWXMWyXLso/edit";"Julho 2024!ER95")*-1`
- month_literal_not_matching_tab em Maio 2025!U36: `=IMPORTRANGE("https://docs.google.com/spreadsheets/d/1lXgLg541SPqTI7LHc6d05gIygJICxs1OsFWXMWyXLso/edit";"Julho 2024!FB95")`
- month_literal_not_matching_tab em Maio 2025!V36: `=IMPORTRANGE("https://docs.google.com/spreadsheets/d/1lXgLg541SPqTI7LHc6d05gIygJICxs1OsFWXMWyXLso/edit";"Julho 2024!FB95")`
- month_literal_not_matching_tab em Maio 2025!W36: `=IMPORTRANGE("https://docs.google.com/spreadsheets/d/1lXgLg541SPqTI7LHc6d05gIygJICxs1OsFWXMWyXLso/edit";"Setembro 2024!FB95")`
- month_literal_not_matching_tab em Abril 2025!O1: `=IMPORTRANGE("https://docs.google.com/spreadsheets/d/1xi7dx-eS678Zy4j3hoJvXedWY1Mnhhvo7jT_hkFqA2c/edit";"Julho 2024!N47")*-1`
- month_literal_not_matching_tab em Abril 2025!P1: `=IMPORTRANGE("https://docs.google.com/spreadsheets/d/1lXgLg541SPqTI7LHc6d05gIygJICxs1OsFWXMWyXLso/edit";"Julho 2024!ER95")*-1`
- month_literal_not_matching_tab em Abril 2025!U36: `=IMPORTRANGE("https://docs.google.com/spreadsheets/d/1lXgLg541SPqTI7LHc6d05gIygJICxs1OsFWXMWyXLso/edit";"Julho 2024!FB95")`
- month_literal_not_matching_tab em Abril 2025!V36: `=IMPORTRANGE("https://docs.google.com/spreadsheets/d/1lXgLg541SPqTI7LHc6d05gIygJICxs1OsFWXMWyXLso/edit";"Julho 2024!FB95")`
- month_literal_not_matching_tab em Abril 2025!W36: `=IMPORTRANGE("https://docs.google.com/spreadsheets/d/1lXgLg541SPqTI7LHc6d05gIygJICxs1OsFWXMWyXLso/edit";"Setembro 2024!FB95")`
- month_literal_not_matching_tab em Marco 2025!O1: `=IMPORTRANGE("https://docs.google.com/spreadsheets/d/1xi7dx-eS678Zy4j3hoJvXedWY1Mnhhvo7jT_hkFqA2c/edit";"Julho 2024!N47")*-1`
- month_literal_not_matching_tab em Marco 2025!P1: `=IMPORTRANGE("https://docs.google.com/spreadsheets/d/1lXgLg541SPqTI7LHc6d05gIygJICxs1OsFWXMWyXLso/edit";"Julho 2024!ER95")*-1`
- month_literal_not_matching_tab em Marco 2025!U36: `=IMPORTRANGE("https://docs.google.com/spreadsheets/d/1lXgLg541SPqTI7LHc6d05gIygJICxs1OsFWXMWyXLso/edit";"Julho 2024!FB95")`
- month_literal_not_matching_tab em Marco 2025!V36: `=IMPORTRANGE("https://docs.google.com/spreadsheets/d/1lXgLg541SPqTI7LHc6d05gIygJICxs1OsFWXMWyXLso/edit";"Julho 2024!FB95")`
- month_literal_not_matching_tab em Marco 2025!W36: `=IMPORTRANGE("https://docs.google.com/spreadsheets/d/1lXgLg541SPqTI7LHc6d05gIygJICxs1OsFWXMWyXLso/edit";"Setembro 2024!FB95")`
- month_literal_not_matching_tab em Fevereiro 2025!O1: `=IMPORTRANGE("https://docs.google.com/spreadsheets/d/1xi7dx-eS678Zy4j3hoJvXedWY1Mnhhvo7jT_hkFqA2c/edit";"Julho 2024!N47")*-1`
- month_literal_not_matching_tab em Fevereiro 2025!P1: `=IMPORTRANGE("https://docs.google.com/spreadsheets/d/1lXgLg541SPqTI7LHc6d05gIygJICxs1OsFWXMWyXLso/edit";"Julho 2024!ER95")*-1`
- month_literal_not_matching_tab em Fevereiro 2025!U36: `=IMPORTRANGE("https://docs.google.com/spreadsheets/d/1lXgLg541SPqTI7LHc6d05gIygJICxs1OsFWXMWyXLso/edit";"Julho 2024!FB95")`
- month_literal_not_matching_tab em Fevereiro 2025!V36: `=IMPORTRANGE("https://docs.google.com/spreadsheets/d/1lXgLg541SPqTI7LHc6d05gIygJICxs1OsFWXMWyXLso/edit";"Julho 2024!FB95")`
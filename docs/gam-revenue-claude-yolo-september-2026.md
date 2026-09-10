# GAM — análise do consolidado e exceção Yolokfx, setembro 2026

Fonte autorizadora: Rodolfo, Discord `1545426987756298340/1547412068875894815`.
Dono financeiro: Rodolfo. Executor da análise: Zeus.
Escopo executado: leitura integral de quatro exports GAM de 7/8 setembro e do consolidado Claude; leitura Smart Bidding AdGroup e Domain nesses dois dias. Nenhum lançamento financeiro, configuração de e-mail ou backfill produtivo.
Evidência: `/root/mgs-agent/work/gam-claude-1547412068875894815/`.

## Decisão ativa — exceção de atribuição Yolokfx

Rodolfo informou ausência do cadastro de `utm_medium` no AdOps e determinou verificar a receita do Yolokfx entre 1 e 9 setembro de 2026 usando Smart Bidding Reports > AdGroup, filtrando site/data e resolvendo gestor pelo sufixo do `ACCOUNT_NAME` Facebook. Esta regra supersede a atribuição automática integral do Yolokfx a G002 no consolidado fornecido, para esse intervalo. Não transfere a titularidade do site nem autoriza distribuir resíduo por proporção de gasto.

A correção AdOps foi anunciada para meia-noite do dia 10 de setembro, mas sua ativação e o fuso desse corte ainda não foram verificados. Não declarar UTM confiável a partir dessa data sem inspecionar o primeiro export correspondente. Metadados dos exports examinados: America/Sao_Paulo. Não extrapolar a verificação de 7/8 aos dias 1–6/9. Os arquivos desses demais dias não foram fornecidos nesta fase.

## Resultado da reconciliação integral

`manifest.json` guarda os hashes SHA256 reais dos cinco arquivos; `raw.json` contém todas as 5.943 linhas brutas; `claude.json` contém as linhas do consolidado; `comparison-102.json` e `lineage-102.json` documentam todas as 102 saídas e a origem de cada uma. `reconcile.py` reproduziu exatamente todas as 102 linhas na precisão de seis casas decimais do Claude, atribuindo cada linha original uma única vez. A diferença máxima por grupo antes do arredondamento é 0,0000004995379395. Não houve perda ou duplicação de valor nos agregados por moeda/data. Isso prova reprodução matemática, NÃO aprovação empresarial de todos os mapeamentos.

- `Report_Digital_Trust_adx_2-2.xlsx`: 7/9, USD, 173 linhas, 6.033,113992892633140494.
- `Report_Digital_Trust_adx_2.xlsx`: 8/9, USD, 182 linhas, 5.269,1304295650139761260.
- `Digital_Trust-2.xlsx`: 7/9, CAD, 2.846 linhas, 25.900,32551516956391565567.
- `Digital_Trust.xlsx`: 8/9, CAD, 2.742 linhas, 24.484,51408319241768873309.
- Total USD: 11.302,2444224576471166200; total exibido Claude: 11.302,24.
- Total CAD: 50.384,83959836198160438876; total exibido Claude: 50.384,84.

Os quatro originais têm abas Properties/Propriedades, período real e moeda explícitos. O primeiro par é All Digital Marketing/USD; o segundo é 00-JBF Digital Server/CAD. Todos foram gerados no dia seguinte ao período informado, às 09h BRT. Não são duplicatas por idioma. O consolidado tem somente valores estáticos, sem fórmulas; a implementação original do Claude não foi fornecida. A reconstrução descreve regras compatíveis com todas as saídas, não acesso ao raciocínio interno dele.

## Mecanismo observado, não nova regra financeira

1. Ler a receita bruta Ad Exchange; não usar eCPM médio como receita nem descontar share/imposto/inválidos.
2. Manter CAD e USD separados, sem câmbio entre as abas.
3. Extrair site/país de Placement/Posição (`pl_digital-trust_<marca>_<pais>`), traduzir marca para domínio real e construir Vertical. Esses exports não têm dimensão geográfica independente de país do visitante.
4. Usar `utm_medium` válido como gestor, preservando `-s`/`-d` no arquivo de saída. A identidade G00X é distinta do sufixo de tráfego; isso não supersede a normalização de gestor de outros pipelines.
5. Aplicar fallback e exceções observadas abaixo.
6. Somar por moeda, data, site, vertical e gestor; agrupar campanhas/content/term no total, arredondar os grupos para seis casas, exibir TOTAL a duas casas. Colunas auxiliares não são necessárias para reproduzir esses cinco arquivos, mas não se conclui que Claude nunca as use em outros relatórios.

Mapeamento de domínio observado: `*finanzas` → `finanzas.<marca>.com`; Topfeed → `finance.topfeed.fun`; Topfeedfinanzas → `finanzas.topfeed.fun`; Newsounde → `de.newsoun.com`; demais marcas → `<marca>.com`. A matriz de defaults e exceções completa está em `reconcile.py`, apenas como reprodução da amostra.

### Escolhas que afetam atribuição e merecem validação

- Medium `-` ou `mg01-d` foi atribuído ao gestor padrão inferido do site, não descartado. Em sites compartilhados isso não prova origem. Infinitynexx preserva G001 e G004, mas linhas `-` vão a G004. Openzed preserva G001 e G003, mas `-` vai a G003. Creditoparaveiculo preserva os seis gestores, mas `-` vai a G002-s.
- Gamezonead: tudo foi para `br-game-br`/G002-s, incluindo USD310,55463977553199601 explicitamente marcados G001-s e USD0,041198554494 do placement `_mx`. Reproduzível, mas não presumir aprovação por totals corretos.
- Eggbev: placements `_gb` e `_us` foram consolidados em `us-cc-en`; CAD31,56301220201214047 do `_gb` entrou no US. Necessita validar a intenção de classificação.
- Openzedfinanzas e Topfeedfinanzas: `_es` e `_us` unificados em `us-cc-es`; CAD3.215,91137441190000974063 originários de placements `_es`. Idioma e país não são sinônimos; classificação pode ser comercial, mas não demonstrada pelo Excel isolado.
- Newsounde: G002-d CAD0,2314639938224172 foi transferido para G005-d, compatível com a regra histórica documentada desse site.
- Autocreditadx: saída `us-game-en` com CAD0,022123; o original identifica apenas placement `_us`. O arquivo não comprova a vertical GAME. Não corrigir automaticamente para CAR nem promover GAME por inferência.
- Vizioid e Yolokfx: valores sem medium foram atribuídos a G002-s e `us-shein-en`; Yolokfx exige a exceção ativa acima.

## Yolo — bruto GAM confirmado e dashboard não idêntica

Original 7/9: CAD2.605,5630324995379395, 47 linhas, todas com medium `-`.
Original 8/9: CAD2.929,678978045648383496, 51 linhas, todas com medium `-`.
Claude manteve esses valores em seis casas e atribuiu todos a G002-s por fallback; o próprio original não traz esse gestor.

Consulta autenticada e somente leitura da rota `/reports/adgroup`, endpoint observado `POST /report/performance_per_campaigns`. Filtro publisher `digital-trust_yolokfx`, currency `CAD`, datas 7/8 com instante seguro 15:00Z. `REVENUE` é usado como bruto, não `NET_REVENUE` nem `REVENUE_ESTIMATED`. Foram recebidas 100 PKs únicas: 47 no dia7 e 53 no dia8. Reconsulta separada de cada dia reproduziu todos os registros exatamente; não houve corte em 100 linhas.

Somas de REVENUE CAD por ACCOUNT_NAME/sufixo:
- G001/Ícaro: 7/9 119,73; 8/9 75,65.
- G002/MGS: 7/9 832,68; 8/9 875,47.
- G003/Isliago: 7/9 12,79; 8/9 23,39.
- G004/Joe: 7/9 701,18; 8/9 920,19.
- G005/Kelly: 7/9 501,78; 8/9 634,43.
- G006/Nicolas: 7/9 356,23; 8/9 377,16.
- Sem ACCOUNT_NAME: 8/9 0,02, UTM_ADGROUP `b01fb01c12g01`; não atribuído por prefixo.

AdGroup total: CAD2.524,39 no dia7 e CAD2.906,31 no dia8. Abaixo dos originais em CAD81,1730324995379395 e CAD23,368978045648383496 respectivamente. Não é reconciliação exata.

Verificação independente no `GET /report/performance_per_domain`, mesmo publisher/datas/CAD: CAD2.603,49 e CAD2.931,77. São valores diferentes tanto dos exports recebidos quanto da soma AdGroup. A causa exata da diferença entre snapshots/moedas/cobertura não foi comprovada; não atribuir a câmbio, rounding ou tráfego inválido sem evidência adicional.

### Ponte por campanha, sem rateio inventado

`yolo-campaign-lineage.json` cruza exatamente o `utm_campaign` do GAM com o código de campanha extraído do UTM_ADGROUP e validado contra CAMPAIGN_NAME, no mesmo dia, para obter ACCOUNT_NAME/gestor. Os valores continuam sendo do GAM original, não substituídos pelo AdGroup.

Ficaram sem atribuição segura no original:
- 7/9: CAD76,7543806023048, campanha `-`.
- 8/9: CAD25,577226841288223, campanha `-`, mais CAD0,019396225562649496 de `b01fb01c12`, sem ACCOUNT_NAME na dashboard.

A receita identificada por campanha também não é idêntica à dashboard: a diferença GAM menos AdGroup após retirar campanha `-` é CAD4,4186518972331395 em7/9 e CAD-2,208248795639839504 em8/9. Não explicar toda a diferença apenas por ausência de campanha. Não distribuir resíduo aos gestores ou sobrepor valores financeiros até haver regra autorizada e conciliação apropriada.

## Estado e próximos passos

Análise da amostra e conferência SB concluídas. Pendente para automatizar: validar exceções de classificação; regra para receita sem atribuição; explicar divergência de fontes; obter/verificar demais dias1–6/9; verificar primeiro export pós-correção AdOps; aprovar arquitetura de e-mail. Nenhuma destas pendências foi tratada como autorização para lançar ou instalar coleta.

Incidentes técnicos locais recuperados: consulta inicial a pack de continuidade no skill errado (resolvida lendo o pack canônico de mgs-company-os-architecture); `inspect.py` sombreou stdlib inspect (execução corrigida com Python safe-path `-P`); helper shell inicialmente invocado com Python (corrigido com Bash); sessão SB cache expirada (login pela credencial canônica 1Password concluído, identidade Zeus - Agent validada). Sem bloqueio restante de acesso ou cálculo por esses incidentes.

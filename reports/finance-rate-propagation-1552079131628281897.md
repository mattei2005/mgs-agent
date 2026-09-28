# Câmbio confirmado em Pagamentos e propagação mensal

Autoridade da correção: Rodolfo1552079131628281897. Diagnóstico adicional: Rodolfo1552080963356594188. Thread1545426987756298340.

## Resultado e causa-raiz

Publicado e validado no host financeiro RunCloud pelo controlador coordenado. O backend de Pagamentos gravava literalmente `status:'Provisório'` no payload e a interface repetia o status único para todos os câmbios. Não consultava os metadados de confirmação já salvos pelo usuário. Os valores e cálculos eram atualizados; o rótulo era incorreto.

`finance-ops.mjs` agora lê somente as adições de taxas da competência selecionada e resolve `fixed+confirmed` individualmente para USD/BRL, USD/CAD e GBP/USD. `public/operations.js` renderiza o status individual e o resumo misto. Ausência de confirmação permanece Provisório; não inferir confirmação de uma taxa fixa, de outro câmbio ou do encerramento cronológico. Histórico janeiro–julho permanece Fechado, com a fonte imutável. Invalids continuam fora da faixa de Pagamentos e presentes nos cálculos. Gestores permanecem sem indicadores globais. A confirmação dos câmbios não significa aprovação integral do mês.

## Validação realizada

- RED reproduziu ausência de confirmação individual; regressões de confirmado, automático, ausente e misto passaram.
- Gates completos:200 testes Node +156 Python =356, sem falhas/skips, com manifesto do candidato idêntico ao validado.
- Stage com snapshots reais de agosto/setembro e histórico real de julho: tela desktop/mobile de agosto mostra três Confirmado; edição real de USD/BRL5.08→5.18 e inválidos Rede2 0.12%→0.24% apenas na base isolada; resultado e payable refletem as mudanças.
- Confirmação-only CAD retorna `recalculated:false`, mantém resultado exato e mostra somente CAD Provisório. Setembro permanece idêntico.
- Dashboard, Relatório Diário, Câmbio e inválidos, Despesas Gerais e Funcionários leem a mesma revisão e o payload recalculado completo. Cinco APIs de gestores correspondem integralmente ao cenário atualizado.
- Produção autenticada:24 competências via API;48 combinações mês/viewport de Pagamentos;34 combinações de Relatório Diário; replay parcial, redirects e Conferência preservados. Zero erros JavaScript e zero POSTs financeiros.
- Agosto confirmado em produção:5.08,1.41708,1.3357, todos Confirmado; saldo Geizian permanece74376.81. Os indicadores dos17 workspaces coincidem, por valor e status, com Câmbio e inválidos. Os7 históricos continuam Fechado.
- Publicação: hashes locais/remotos conferidos, health/serviço/socket validados, fingerprints de todos os cenários idênticos antes/depois; zero escrita financeira pelo release. Nenhuma escrita em Google Sheets.

## Diferença de R$0,68 — diagnóstico independente

A diferença não decorre do rótulo Provisório e não é somente arredondamento.

Leitura live da planilha principal, aba Agosto2026:
- G103 / J137:74567.94268725596, exibido74567.94.
- G129, saldo anterior:−1090.0485236818495, exibido−1090.05.
- G105:G109, movimentos:899.60.
- G132:74377.49416357411, exibido74377.49.

Dashboard: líquido de50% bruto74567.255195158..., monetizado74567.26; anterior−1090.05; movimentos899.60; saldo74376.81. Diferença entre os valores exibidos:0.68. O delta entre o G132 não arredondado e o saldo em centavos do ledger é0.68416357411.

Bridge da participação de50%, planilha menos dashboard, antes da monetização do ledger:
1. Fincgriffin, líquido após imposto:+0.723489496462825 BRL.
2. Outras diferenças de receitas líquidas/impostos:+0.011154414935943 BRL.
3. Folha, Nicolas e Isliago:−0.047151813457940 BRL.
4. Soma:+0.687492097940828 BRL; reconcilia a diferença exata do líquido com resíduo numérico menor que1e−10 BRL. Depois considerar os arredondamentos próprios do devido e saldo anterior do ledger.

Causa principal comprovada: Fincgriffin na planilha usa L1/Rede1=0.10% (`AAH5=IF(AAG5="","",-AAG5*$L$1)` e as demais colunas de países). A dashboard de agosto usa Rede2=0.12%, ponte virtual XFD1. Receita gross Fincgriffin também conserva precisão distinta:1682.83 USD na planilha versus1682.833425801682038186 USD na dashboard. Net/imposto combinados respondem pelo primeiro item. Não mudar cadastro, rede, inválidos, salários ou fazer ajuste artificial de saldo sob esta autorização de apresentação.

K1/YMonetize difere, mas um contrafactual isolado comprovou impacto zero neste snapshot; não é a causa. Comparar somente células do grafo legado com os totais live produz falsos desvios grandes porque receitas nativas substituem fatos legados zerados. O diagnóstico usou o domínio consolidado efetivo.

## Recuperações de homologação

A primeira stage carecia da tabela/fixture imutável finance_history de julho. Foi materializada a fonte real, sem enfraquecer as asserções. O gate Python inicial passou156 casos, mas corretamente bloqueou porque o código de testes mudou durante o gate; os dois gates foram repetidos contra o candidato final. As verificações adicionais corrigiram o import de managerView, enumeraram managerKeys (icaro público, george interno), usaram os nomes reais das páginas e a rota histórica `/api/history`. Tentativa histórica pela rota live retornou400 e foi substituída pela rota canônica, sem alteração de produção. Todos os checks finais passaram; nenhuma falha pendente.

## Evidência, rollback e aprendizado

- Evidência privada: `apps/finance-system/private/rate-propagation-1552079131628281897/`.
- `stage-result.json`, `cross-view-result.json`, `published.json`, `browser-production.json`, `browser-production-general.json`, `production-ledger.json`.
- `sheet-live-full.json` conserva entrada/fórmula, valor efetivo e formatado; `sheet-cells.json`, `segment-differences.json`, `expense-differences.json`, `balance-bridge.json`, `balance-ledger-bridge.json` e `sheet-rate-counterfactual.json` sustentam o diagnóstico.
- Dumps completos e hashes foram verificados antes da publicação; originais e rollback journaled: `private/releases/rate-propagation-1552079131628281897/`.
- Skill `mgs-finance-dashboard` v0.1.71: confirmação individual, propagação intertelas, histórico/fixtures, namespace público do gestor e bridge antes de atribuir divergências a arredondamento. Preserva o histórico por supersessão explícita.
- Limite: não houve correção financeira na planilha ou reclassificação de Fincgriffin; apenas diagnóstico da diferença. Não declarar igualdade de saldos.

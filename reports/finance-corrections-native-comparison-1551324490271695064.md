# Agosto/2026 — correções parciais e comparação nativa

Autoridade: Rodolfo1551324490271695064 (pontos1,2,3); esclarecimento1551326866949013567 (comparação CAD/CAD, USD/USD, Facebook e Google; planilha estritamente intocada). Thread1545426987756298340.

## Estado confirmado

- Ponto1 aplicado: CPV16/G006, USD53.72 em01/08 e USD20.85 em02/08, total USD74.57, agora compõe o custo de Nicolas em vez de MGS. Nenhum valor ou data de mídia foi alterado.
- Ponto3 aplicado: somente workspace-2026-08 com a política autorizada passa a integrar fatos nativos preexistentes aos blocos de gestores. Nenhuma receita foi importada novamente. Cinco prévias de gestor autenticadas pelo owner em desktop/mobile e cinco APIs de setembro passaram; summary_control reconcilia dentro de1e-6. Zero erros JS e zero POST financeiro no teste público. Não equivale a login individual dos cinco gestores.
- Revisão de aplicação396; evento financeiro1530, AUGUST_CPV16_MANAGER_ATTRIBUTION_CORRECTED. Readback exato e replay idempotente passaram. Cotação automática394→395 foi reconciliada pelo evento1528/AUTO_QUOTES_UPDATED; apenas H1/I1 mudaram, sem alteração de lançamentos.
- Ponto2 permanece ABERTO: ainda não foi realizada a substituição completa das receitas AV/M2/mistas. A tabela solicitada foi refeita nas moedas originais de ambos os lados; não representa fechamento financeiro aplicado.

## Fonte intocada e reconciliação nativa

- Oito abas relidas ao final pela Service Account canônica, somente GET. Valores e fórmulas idênticos ao início. Zero escrita em Google Sheets.
- As85.868 source_cells da dash também permanecem idênticas à base pré-alteração restaurada em banco isolado; fingerprint confirmado em immutable-source-verification.json.
-46cadastros/domínios e1.556fatos com linhagem de moeda validada; CAD/FX+USD reproduz cada gross real e o consolidado, sem dupla contagem. Novo readback da revisão397 confirmou todos os valores nativos e gastos idênticos após as correções de atribuição/exibição; somente FX automático pode mudar equivalentes convertidos.
- CAD planilha292199.23584873759319471618; CAD dash295952.35100031599958929818; delta planilha−dash−3753.11515157840639458200.
- USD planilha198683.6514206297737614895; USD dash199754.9114206297737414895; delta−1071.2599999999999800000.
- Facebook USD286368.15 em ambos; Google BRL71174.24 em ambos; diferenças zero.
- Todos os resíduos subcentavo participam das somas. Apenas exibição arredondada. Diferença calculada antes do arredondamento pode variar um centavo em relação à subtração das duas colunas já exibidas.

## Gate dimensional ainda aberto — não executar fallback novo

O mapeamento conservador da auditoria ainda não comprova a vertical para1518linhas AV/USD3106.08. Outros28registros/USD3351.41 referenciam códigos que têm mais de uma vertical evidenciada no mês. Isso é pendência do mapeamento, não prova de erro da planilha. Mediums canônicos preservam o gestor/estratégia. Valores já fazem parte do detalhado AV; NÃO adicionar novamente.

A autorização anterior de maior vertical cobre exclusivamente C/D/E simultaneamente '-'. Não estender essa regra a códigos preenchidos ou ambiguidades sem confirmação de Rodolfo. Também não fabricar dia para ajuste mensal consolidado−detalhado AV. Fechamento só termina com domínio/vertical/gestor/detalhado simultaneamente conciliados.

## Validação e recuperação

-150testes Node únicos exercitados; falhas de fixtures isoladas recuperadas, incluindo os dois casos restantes reexecutados com PASS.
-103testes Python exercitados; único erro por fixture ausente recuperado com replay PASS.
- npm audit produção: zero vulnerabilidades.
- Falhas iniciais decorreram de fixtures/cotação ausentes no stage e do --vault obrigatório na CLI 1Password Service Account; recuperadas sem mudar regra financeira, credencial ou teste para mascarar resultado.
- Serviços remotos mgs-finance-dash, socket e PostgreSQL ativos. Arquivos live/local com hashes correspondentes.
- Backup custom completo validado por pg_restore --list, hash local/remoto e restauração real isolada; banco mgs_finance_verify_1551324490271695064 preservado.
- Recovery financeiro bloqueado: recovery-cpv16-1551324490271695064. Código anterior: /home/mgsfinance/backups/correct-1551324490271695064/code-before/. Nenhuma exclusão/limpeza destrutiva autorizada ou executada.
- Aplicação local: apps/finance-system/august_reconciliation.py, worker.py, manager-view.mjs; teste tests/august-adops-manager.test.mjs. Nenhuma mudança em auth, permissões, ledger de pagamentos ou fontes Google.

## Evidência

Diretório privado apps/finance-system/private/correct-1551324490271695064/:
- native-currency-comparison.json e .txt;
- native_comparison.py (linhagem de moeda, gastos e contagem);
- cpv-apply-readback.json e cpv-verify-readback.json;
- public-ui-verification.json;
- immutable-source-verification.json;
- all-tests-verification.json e dependency-audit.json;
- backup-readback.json e deployed-files.json;
- allocation-open-gate.json e av-dimension-evidence.json.

Próximo passo: devolver a comparação exata solicitada, esclarecer a regra para atribuições ainda não comprovadas e concluir o ponto2 somente com o gate dimensional aprovado e readback financeiro. Não declarar o fechamento integral concluído.

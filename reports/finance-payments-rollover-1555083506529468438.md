# Pagamentos — recuperação da virada mensal e proteção contra tela antiga

Autoridade/relato: Rodolfo `1555083506529468438`, thread `1545426987756298340`; continuação da correção autorizada `1555055743785373760`.
Release: `payments-rollover-1555083506529468438`.
Estado: **publicado e validado**.

## Diagnóstico real

O filtro mensal da release anterior estava ativo e correto. Porém, após a virada de setembro para outubro em America/New_York, a API passou a calcular o devido de outubro. O resultado Decimal real de outubro era a string `0E-30`, um zero válido em notação científica. O conversor `cents` aceitava somente notação decimal comum e devolvia `Valor monetário inválido`. Como todos os meses posteriores incluem outubro na memória de saldo, a falha alcançou outubro2026–dezembro2027.

O segundo defeito era de apresentação: quando a consulta falhava, o seletor mudava, mas cartões, lançamento e ações do mês anterior permaneciam. Isso produziu exatamente a aparência relatada: pagamento de setembro continuava visível ao escolher outubro. Não era um novo pagamento gravado em cada mês.

Leitura real de todos os13beneficiários ×17meses:206payloads funcionavam e15consultas de Geizian falhavam. Outros beneficiários usavam o mesmo conversor, mas seus valores reais não acionavam esta falha; a proteção e os testes cobrem todos.

### Lacuna da validação anterior

A aceitação anterior consultou todos os meses antes da meia-noite, quando outubro ainda era futuro e seu devido retornava zero sem passar pelo conversor. Ela não simulou outubro como mês atual nem uma falha da API após setembro ter sido renderizado. Os testes anteriores eram reais, mas insuficientes para essa transição. Esta release complementa, não revoga, o filtro por Referência.

## Correção

- Conversão exata de strings Decimal científicas para centavos com dígitos/BigInt, preservando half-up, sinal e limite. Não usa float como atalho, não transforma erros em zero e não altera a validação estrita de valores digitados nos formulários.
- Troca de competência limpa imediatamente o conteúdo anterior e suas ações; mostra carregamento.
- Falha deixa estado nulo, mensagem referente ao mês solicitado e botão Tentar novamente. Nenhuma tabela anterior permanece apresentada como atual.
- Retry bem-sucedido limpa o erro anterior.
- Respostas/erros de requests ultrapassados são descartados por sequência; competência/beneficiário da resposta são validados antes da apresentação.
- Nenhum lançamento, pagamento, data, valor, cenário, regra salarial ou histórico financeiro foi editado.

## Evidências executadas

- RED:3testes reproduziram Decimal científico rejeitado, preservação indevida da tela anterior e corrida de respostas. GREEN:12testes focados passaram.
- Replay do backend candidato sobre240resultados de consultas reais capturadas somente leitura:221payloads válidos,102projeções de perfis,15falhas recuperadas e206respostas anteriormente válidas exatamente preservadas.
-289combinações de mês atual simulado ×mês consultado passaram, cobrindo as17viradas nativas.
-103valores reais distintos reconciliados contra Python Decimal ROUND_HALF_UP independente.
- Browser baseline desktop/mobile reproduziu seletor outubro com linha de setembro e erro. Candidato provou ocultação, retry e descarte de resposta atrasada.
- Stage de apresentação:1054checks para owner, partner e cinco perfis manager,13beneficiários,17meses,1440/390px, zero JS errors/financial POSTs.
- Gates integrais:226Node +179Python =405testes PASS, sem skips; dependências produtivas sem vulnerabilidades reportadas pelo npm audit.
- Browser público autenticado real após publicação:442checks,13beneficiários ×17meses ×2larguras, zero erro JS/POST financeiro; health autenticado produtivo válido.
- Readback do pagamento `8f51d114-b5db-4707-a0d3-024ef95ba34f`: continua somente na referência2026-09, valor1231019centavos. Outubro/novembro/dezembro2027 têm zero linhas próprias e movimento mensal zero; só carregam o saldo anterior.
- Cenários completos por hash de linha/revisão e ledger completo idênticos imediatamente antes/depois do cutover sob admissão exclusiva. Cotações provisórias podem se atualizar fora da publicação; não atribuir suas variações ao ajuste de código.
- Hashes local/remoto: finance-ops.mjs `95d2e233499ef2f8590bf2c5d0a8a7c13873e62d54faef7382ba88f41d925f31`; public/operations.js `9a6d288a9a9bb0a790ee98af64c5a624f7ad11c812c46885aa963022414ff809`.
- Teste persistente finance-ops.test.mjs: `6b170a13f9a460a9f377babe1c93177a6e2c25f1b0d3e7914b0b1331d18212b7`.
- PostgreSQL, serviço financeiro e socket ativos. Somente serviço financeiro recarregado; nenhum restart de gateway. Sessão owner de validação encerrada.

## Continuidade e rollback

- Evidência privada: `apps/finance-system/private/payments-followup-1555083506529468438/`, incluindo diagnosis/query-fixture/backend-proof, testes de falha, browser público, manifests, gates e fingerprints.
- Backup/journal: `apps/finance-system/private/releases/payments-rollover-1555083506529468438/`; preservados.
- Skill canônica: mgs-finance-dashboard, references/payments-approvals-nicolas-pilot.md, complemento Virada mensal e dados antigos após erro.
- Checkpoint: `ZEUS-FINANCE-PAYMENTS-ROLLOVER-1555083506529468438`.
- A correção não promete ausência universal de novas falhas. O teste permanente cobre parsing Decimal, filtros e integridade de troca de consulta; o aviso fail-closed evita a apresentação silenciosa de dados antigos quando uma futura consulta falhar.

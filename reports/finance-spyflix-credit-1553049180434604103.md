# Finance — crédito/estorno SPYFLIX em agosto/2026

Autoridade: Rodolfo1553049180434604103. Thread1553040663069851781. Data:2026-09-25.

## Resultado
- Dash Financeira publicada com tipo explícito `debit`/`credit` em Despesas Gerais.
- Crédito permitido somente em `category=company`; pessoal continua fail-closed como débito.
- Agosto2026 `company|122` foi atualizado no próprio ID, sem segunda linha: `Crédito/estorno SPYFLIX — 26 lançamentos indevidos`, BRL2522, `direction=credit`, Conferido em2026-09-25.
- A linha anterior `Ferramenta ver artigos:` de -BRL97 deixou de operar. Setembro2026 em diante permanece arquivado e não foi reaberto.
- Revisão do cenário:547→548. Audit financeiro:2277. Release:`spyflix-credit-1553049180434604103`.

## Efeito calculado
- Variação de Despesas Gerais ao substituir -BRL97 por +BRL2522:+BRL2619.
- O crédito bruto de BRL2522 representa BRL1261 antes das regras dependentes, após divisão de50%.
- A remuneração automática dependente recalculou -BRL74,20; por isso, a variação real do indicador final de metade entre as revisões547 e548 foi +BRL1272,40. O crédito armazenado e exibido permanece exatamente +BRL2522.

## Validação
- Gate Node:208/208.
- Gate Python:165/165.
- Testes específicos: sintaxe JS, despesas, origem e `direction=credit` passaram.
- Finance release control validou manifest, hashes base e stage proof; publicação concluiu com `financial_writes=0` antes da alteração financeira separada.
- Backup PostgreSQL anterior verificado local/remoto:189494412bytes, SHA-256 `f16172d43ca474c4b89d2f1a0c6ba89d3be9f5ac649e368bdc9f44ad458a0c68`.
- Escrita financeira foi uma única alteração autenticada com revisão otimista.
- Readback independente por nova sessão confirmou revisão548, `company|122`, BRL2522 e `direction=credit`.
- Browser HTTPS confirmou uma única linha, sinal positivo, editor em Crédito/estorno, moeda BRL, valor2522, status Conferido, data2026-09-25 e zero erro JavaScript.

## Recuperação
- Evidência e scripts: `apps/finance-system/private/spyflix-credit-1553049180434604103/`.
- Dump anterior: `backup/mgs_finance-before.dump`; cópia remota registrada em `backup/backup.json`.
- Rollback, se necessário, deve ser limitado a `workspace-2026-08`/`company|122` com revisão e audit, usando `before.json`; nunca restaurar o dump completo sobre alterações concorrentes.

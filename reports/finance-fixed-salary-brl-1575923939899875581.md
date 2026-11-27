# Salários fixos — editor BRL — 1575923939899875581

## Autorização e escopo

Rodolfo344196393512075265, thread1545426987756298340, autorização1575923939899875581 verificada por leitura da mensagem original. Contrato: `docs/finance-fixed-salary-brl-editor.md`.

Apenas os cinco IDs personnel|155–159, com moeda nativa BRL e sem modo de comissão, usam “Salário fixo mensal — R$” no editor de novembro2026 em diante. Mantêm o valor original, moeda BRL não selecionável e explicação da conversão mensal. Listagens/totais USD, Kelly Gestor, demais comissões, pagamentos, permissões e meses anteriores preservados. Sem migração/redefinição salarial.

## Causa e solução

A apresentação USD desde novembro também convertia os campos de edição dos salários fixos em BRL. A correção cria uma exceção estritamente visual/de entrada para os cinco registros: ler o `edit_amount` nativo, sem conversão de ida/volta, e enviar BRL ao endpoint já existente. Nenhum backend ou fórmula financeira é alterado.

## Validação anterior à publicação

- Preparação source-only sob admissão compartilhada, manifestos de arquivos/fixtures explícitos, snapshot produtivo somente leitura.
- TDD: os dois novos testes falharam no código original e passaram após a correção; oito testes focados completos. Cobertura de valores originais/alterados, centavos, inatividade, mês anterior/futuro, ID estranho, moeda distinta e Kelly comissão.
- Banco isolado em memória, com snapshots reais: dez envios efetivos pelos formulários desktop/mobile, cinco sem alterar o valor e cinco com alteração de centavo; API200, leitura posterior BRL, equivalente USD, recarga e demais meses preservados.
- Stage autenticado: quarenta formulários (cinco pessoas × quatro meses × duas larguras), valores comparados à API; listopagem novembro em USD; Kelly Gestor sem campo monetário editável. Capturas desktop/mobile inspecionadas visualmente. Nenhuma escrita financeira produtiva.
- O primeiro ensaio de permissões falhou por expectativa errada do harness: Geizian já pode ler workspace global. Conferido contrato existente e corrigido apenas o teste; rerun passou, com Geizian200 e os cinco gestores403, sem mudança de autorização.
- Sessões temporárias de QA encerradas e cookies originais reexecutados com401.
- Gate Node:326/326, sem skips. Gate Python ainda em andamento no momento desta gravação. Auditoria de dependências produtivas: zero vulnerabilidades.

## Publicação e encerramento

Ainda pendentes nesta versão documental; seguir checkpoint ZEUS-FINANCE-SALARY-BRL-1575923939899875581. Não interpretar os testes de stage como publicação.

## Artefatos

Pacote `apps/finance-system/private/salary-brl-1575923939899875581/`: candidato, preparação, fixtures delimitadas, isolated-proof, stage-browser, stage-session-cleanup, manifest e gates. Backups/journal da futura publicação em `apps/finance-system/private/releases/salary-brl-1575923939899875581/`. Nenhuma remoção de evidências autorizada.

# Projeção e sincronização de threads

## Escopo

- `family`: valida e projeta em todos os consumidores ativos.
- `operation`: valida e projeta somente no consumidor selecionado.

Toda mudança projeta a rota afetada e `rules`. Se a rota alterada já for `rules`, existe uma única projeção.

## Ordem

1. readback da fonte canônica atual;
2. persistência com supersessão explícita;
3. validação do contrato e do consumer registry;
4. sincronização dos prompts/configs;
5. pre-read da mensagem de projeção;
6. PATCH da mensagem Ares conhecida ou POST se ainda não existir;
7. GET e comparação exata do conteúdo;
8. persistência de message ID, digest e audit.

## Preservação

O sincronizador nunca apaga mensagens. Só pode editar uma mensagem cujo ID esteja persistido e cujo autor seja o bot Ares. Mensagens humanas, eventos de sistema e conteúdo histórico permanecem intactos. Limpeza é uma operação separada e exige autorização específica.

## Drift

Qualquer diferença entre família, contrato da operação, registry, prompt, config ativo ou projeção Discord deixa a sincronização incompleta. Não declarar atualização antes de todos os readbacks aplicáveis fecharem.

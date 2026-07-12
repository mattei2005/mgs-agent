# Verificação live de arquivos preservados em UPLOAD MANUAL

Use quando Rodolfo/Kelly perguntar se arquivos que ainda aparecem em uma pasta de entrada foram verificados e colocados no destino correto.

## Princípio

`UPLOAD MANUAL` é fila de entrada e deve conter somente itens ainda pendentes. No fluxo canônico **tratar/mover**, Hera cria e valida a versão sanitizada no `01_READY` e só então move o original, preservando ID e nome, para `{OPERAÇÃO}/{IMG|VID}/99_LEGACY`; não apaga o bruto. A confirmação deve cruzar fonte live, relatório, `01_READY` e `99_LEGACY`, sem se apoiar apenas em histórico local. Somente mantenha o original na entrada quando o pedido disser explicitamente **copiar** ou **manter no upload**.

## Procedimento

1. Abrir o folder ID fornecido pela API do Drive e confirmar nome, ancestralidade e conteúdo atual.
2. Inventariar recursivamente os arquivos da entrada com `id`, nome, MIME, dimensão, duração, tamanho e checksum disponível.
3. Localizar o relatório de processamento pelo `source_drive_id`, não apenas pelo nome do arquivo.
4. Para cada origem atual, confirmar que existe exatamente um registro de destino esperado.
5. Consultar cada `dest_drive_id` diretamente e reconstruir sua ancestralidade live.
6. Validar a taxonomia atual da operação. Para CAR Brasil em português do Brasil, usar `CAR_BR_BR`; `PT` só representa Portugal quando isso for explícito.
7. Confirmar que os destinos estão diretamente em `{OPERAÇÃO}/{IMG|VID}/01_READY`, sem subpastas intermediárias de placement/idioma.
8. Fazer verificação forte quando o usuário pedir confirmação: baixar cada destino, comparar tamanho e SHA-256 com o relatório de sanitização e executar `clean-creative-metadata.sh verify` em todos os arquivos.
9. Reportar contagens consolidadas: originais na entrada, processados, destinos live, hashes/tamanhos válidos, `clean: true` e falhas.

## Critério de sucesso

```text
origens processadas == source_drive_id registrados
destinos live == total processado
ancestralidade dos destinos == MGS-AGENTS/CRIATIVOS/{OP}/{IMG|VID}/01_READY
ancestralidade dos originais == MGS-AGENTS/CRIATIVOS/{OP}/{IMG|VID}/99_LEGACY
itens pendentes no upload == 0
size_ok == total
sha256_ok == total
clean_true == total
falhas == 0
```

## Pitfalls

- Não deixar original processado na entrada no fluxo **tratar/mover**; isso cria falso backlog. Preserve-o em `99_LEGACY`.
- Não mover o original antes de a cópia limpa passar pelos gates de READY, readback, hash e `clean: true`.
- Não confirmar apenas porque existe um relatório antigo; validar `source_drive_id`, `dest_drive_id` e os dois caminhos atuais no Drive.
- Sanitização muda o checksum em relação ao bruto. Compare o destino com `clean_sha256`, não com o hash da origem.
- Um asset pode ter sido renomeado/movido depois do relatório. O ID do Drive continua sendo a chave confiável; use ancestralidade e nome live.
- Não reprocessar nem duplicar arquivos se todos os `source_drive_id` já tiverem destinos válidos.

## Formato de resposta

Responder de forma curta e operacional. Incluir contagens de processados, destinos READY, originais em LEGACY, `clean: true`, hashes/readback, pendências restantes no upload e links das pastas READY; não despejar a lista completa quando contagens resolvem.

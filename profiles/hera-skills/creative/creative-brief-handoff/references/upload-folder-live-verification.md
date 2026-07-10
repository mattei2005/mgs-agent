# Verificação live de arquivos preservados em UPLOAD MANUAL

Use quando Rodolfo/Kelly perguntar se arquivos que ainda aparecem em uma pasta de entrada foram verificados e colocados no destino correto.

## Princípio

A presença do original em `UPLOAD MANUAL` não indica pendência. O fluxo preserva o bruto e cria uma versão sanitizada no `READY`. A confirmação deve cruzar a fonte live, o relatório operacional e o destino live — não se apoiar apenas em histórico local.

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
origens atuais == source_drive_id registrados
destinos live == total processado
ancestralidade live == MGS-AGENTS/CRIATIVOS/{OP}/{IMG|VID}/01_READY
size_ok == total
sha256_ok == total
clean_true == total
falhas == 0
```

## Pitfalls

- Não dizer que a pasta de entrada deveria estar vazia; originais devem permanecer intactos.
- Não confirmar apenas porque existe um relatório antigo; validar `dest_drive_id` e caminho atuais no Drive.
- Sanitização muda o checksum em relação ao bruto. Compare o destino com `clean_sha256`, não com o hash da origem.
- Um asset pode ter sido renomeado/movido depois do relatório. O ID do Drive continua sendo a chave confiável; use a ancestralidade e o nome live.
- Não reprocessar nem duplicar arquivos se todos os `source_drive_id` já tiverem destinos válidos.

## Formato de resposta

Responder de forma curta e operacional, explicando explicitamente que os arquivos ainda visíveis são os originais preservados e não pendências. Incluir link da pasta READY e as contagens de validação; não despejar lista completa quando uma faixa de nomes resolve.

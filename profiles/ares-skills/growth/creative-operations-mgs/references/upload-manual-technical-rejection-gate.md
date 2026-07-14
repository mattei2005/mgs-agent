# UPLOAD MANUAL — gate de rejeição técnica

Use dentro do intake canônico quando um arquivo real da fila não contém material criativo utilizável e, portanto, não pode receber uma cópia final em `01_READY`.

## Gate probatório

1. Não rejeite por nome, tamanho ou thumbnail isoladamente.
2. Para vídeo, baixe o arquivo e amostre frames próximos de 20%, 50% e 80% da duração real.
3. Se a primeira amostragem parecer branca, uniforme, corrompida ou inconclusiva, a rejeição ainda não está autorizada. Faça uma segunda tentativa por outra abordagem antes de decidir:
   - verificar frames no início e no fim, além dos pontos intermediários;
   - varrer todos os frames decodificados e contar hashes/variação de luminância e cor;
   - comparar com uma renderização independente quando disponível, como a thumbnail gerada pelo próprio Drive ou outro decoder/player;
   - consultar revisões e possíveis cópias do arquivo no Drive para descartar versão errada ou upload incompleto.
4. Confirme o defeito por evidência técnica e visual de pelo menos duas abordagens independentes. Para vídeo uniforme/branco, registre total de frames, hashes distintos, luminância/crominância ou média RGB, variação entre frames e resultado visual; tamanho muito pequeno é apenas indício.
5. Se algum frame, revisão ou renderização alternativa mostrar conteúdo útil, interrompa a rejeição automática e faça classificação visual normal.
6. Se a classificação de ângulo/pessoa continuar incerta, tente novamente com frames adicionais/contact sheet antes de usar `UNKNOWN` ou rejeitar. Falha da primeira tentativa nunca encerra a análise.

## Tratamento do inválido

- Nunca criar um candidato em `01_READY` para satisfazer contagem.
- Não inventar ângulo de marketing como `TECHNICAL_BLANK`; use `ANGLE=UNKNOWN` apenas no inventário.
- Quando a hierarquia já tiver o status canônico `05_REJECTED`, mover o original para `{OP}/VID/05_REJECTED`, preservando Drive ID e nome exato. Não criar pasta nova para isso.
- Não produzir cópia limpa ou `canonical_filename` de campanha para um arquivo sem conteúdo. No registro, preservar o nome original como lookup técnico e marcar `metadata_clean=false`.
- Persistir `status=05_REJECTED`, `performance_label=REJECTED_TECHNICAL`, `reservation_status=RESERVADO_PELO_GESTOR` e `ares_eligible=false`, com a evidência resumida em `notes`.
- Validar por readback que o source ID saiu de `UPLOAD MANUAL`, está no parent `05_REJECTED`, mantém nome/ID e não está em lixeira.

## Substituição posterior de um rejeitado

Quando o gestor confirmar que o arquivo rejeitado anterior estava realmente defeituoso e enviar uma nova exportação em `UPLOAD MANUAL`:

1. Trate a nova exportação como um novo `source_drive_id`; não sobrescreva, renomeie nem reutilize o registro do rejeitado antigo.
2. Inspecione o novo arquivo normalmente por frames reais. Se estiver válido, sanitize, faça upload em `01_READY`, valide readback/hash/`clean=true`, mova o novo bruto para `99_LEGACY` e registre sua própria linhagem.
3. Relacione a substituição no relatório humano pelo contexto e evidência visual, sem declarar equivalência binária ou reutilizar o `asset_id` anterior.
4. O arquivo antigo permanece em `05_REJECTED` até uma autorização explícita de descarte. `05_REJECTED` nunca equivale a autorização para excluir.
5. Se o usuário pedir exclusão, consulte o ID antigo diretamente e mostre antes da ação: nome, pasta atual, tamanho, duração e `trashed`. A exclusão/lixeira segue o gate crítico de confirmação vigente; o pedido de processar a nova exportação não conta como essa confirmação adicional.
6. Não bloqueie o restante do lote enquanto a exclusão aguarda confirmação. Conclua e valide os novos assets independentes; reporte a exclusão antiga separadamente como pendente.
7. Após uma exclusão confirmada, valide `trashed=true` por readback e reconcilie inventário/auditoria para que o registro antigo não continue parecendo um candidato disponível.

## Final gate do lote

O lote pode concluir com:

- válidos: cópia limpa em `01_READY`, original em `99_LEGACY`;
- inválidos comprovados: original em `05_REJECTED`, sem candidato em READY;
- `UPLOAD MANUAL=0`;
- um registro de inventário por source ID;
- contagens separadas `ready`, `rejected_technical`, `sources_archived`, `sources_rejected`;
- mapa `original → final` somente para os enviados a READY e bloco separado para rejeitados.

## Pitfalls

- Um vídeo curto, pequeno ou com nome “Design sem nome” não é necessariamente inválido; a prova vem dos frames reais.
- Não usar frame inicial sozinho: intro/fade pode ser branco ou preto.
- Não mover o source antes de concluir o gate correspondente. Para válido, a cópia limpa deve passar readback, checksum e `clean=true`; para rejeitado, a evidência técnica deve estar registrada.
- `05_REJECTED` é status técnico/operacional, não autorização para deletar o original.

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

## Precedência do backend e continuidade

Entrada vigente: arquivos diretamente em UPLOAD MANUAL no MGS; _PROCESSAMENTO é temporário. Estoque permanente nos 30 TB, resolvido por ares_archive_storage/ares_archive_locations; não exigir driveId de Shared Drive em My Drive. Pedido geral da Kelly sem destinatário segue common/IMG ou VID/01_READY; entrega própria/gestor expresso segue Exclusivos e uso real confirmado segue Usados. Preservar RAW, mesmos IDs, bytes, reservas, elegibilidade e duplicatas. Agentes usam somente SA canônica; transporte owner isolado não é fallback de identidade. Upload não autoriza campanha ou exclusão. Neste guia, READY/LEGACY/REJECTED no staging são estados técnicos; o destino final e a preservação por mesmo ID seguem os helpers vigentes. Se a rota canônica não suportar a disposição de um rejeitado, conservar a fonte e registrar o bloqueio exato, sem inventar clean/ACK, fazer PATCH ad hoc ou travar os membros independentes válidos.

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
8. Persistir o descarte de forma inequívoca no inventário, preservando a linhagem anterior:
   - `status=TRASHED` e `prior_status=05_REJECTED`;
   - `source_path=null`, pois o arquivo não está mais disponível na pasta ativa;
   - `drive_trashed=true`, `trashed_at=<UTC ISO-8601>` e `trash_readback_verified=true`;
   - manter `source_drive_id`, checksum, nome original e `ares_eligible=false` para auditoria;
   - registrar `trash_authorized_by`, contexto/thread da autorização e atualizar `last_reconciled_at`;
   - não chamar de exclusão permanente: `trashed=true` significa enviado à lixeira e ainda pode ser restaurado.
9. Confirmar por listagem da pasta com `trashed=false` que o alvo não aparece mais entre os arquivos ativos. O gate final exige simultaneamente: GET direto com `trashed=true`, alvo ausente da listagem ativa e exatamente um registro de inventário atualizado.
10. Registrar evento de auditoria com estado anterior/posterior, autorização, readback do Drive e hash do inventário. Como há mudança de Drive e dados operacionais, emitir REPORT-INFRA pelo helper canônico e só reportar sucesso depois do retorno validado.
11. Tornar a atualização idempotente: se o Drive já estiver com `trashed=true` ou o inventário já estiver em `TRASHED`, não repetir o PATCH nem duplicar o evento; apenas validar e reconciliar campos faltantes.

## Final gate do lote

O lote pode concluir com:

- válidos: cópia limpa em `01_READY`, original em `99_LEGACY`;
- inválidos comprovados: original em `05_REJECTED`, sem candidato em READY;
- pendentes do conjunto congelado = 0; arquivos sem contexto ou de outros pedidos permanecem preservados e contados separadamente;
- um registro de inventário por source ID;
- contagens separadas `ready`, `rejected_technical`, `sources_archived`, `sources_rejected`;
- mapa `original → final` somente para os enviados a READY e bloco separado para rejeitados.

## Pitfalls

- Um vídeo curto, pequeno ou com nome “Design sem nome” não é necessariamente inválido; a prova vem dos frames reais.
- Não usar frame inicial sozinho: intro/fade pode ser branco ou preto.
- Não mover o source antes de concluir o gate correspondente. Para válido, a cópia limpa deve passar readback, checksum e `clean=true`; para rejeitado, a evidência técnica deve estar registrada.
- `05_REJECTED` é status técnico/operacional, não autorização para deletar o original.
- Descarte de rejeitado exige confirmação crítica exata e capacidade real do backend. Agente verifica pela SA canônica e só usa controlador isolado se aquela ação/classe tiver autorização própria; nunca testar identidades alternativas ou reutilizar aprovação antiga. Sem suporte/capacidade, preservar o arquivo e reportar o bloqueio.
- Se canTrash=false ou a API negar a ação, não simular exclusão removendo parent/deixando órfão/movendo, não trocar identidade nem ampliar ACL. Verificar o backend e as capacidades: a negação em My Drive pode ser legítima, não prova automática de drift. Concluir o saldo independente já autorizado e escalar somente o bloqueio exato.
- No Shared Drive, validar a capacidade do item e a identidade canônica; no arquivo My Drive, validar owner/root e o contrato isolado. Nenhuma localização ou nome de pasta dispensa autorização de exclusão, e o modo flat permanece sem DELETE/trash automático.
- Não substituir nem rotacionar silenciosamente a identidade canônica pela conta de um colaborador. Mudança de acesso exige inventário, piloto, rollback e aprovação explícita do Rodolfo. Ver `references/my-drive-collaborator-control-and-deletion.md`.

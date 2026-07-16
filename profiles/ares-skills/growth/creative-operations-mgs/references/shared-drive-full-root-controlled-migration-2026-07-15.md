# Migração controlada da raiz MGS-AGENTS — evidência 2026-07-15/16

## Valor reutilizável

Use este caso como implementação de referência quando uma árvore completa do My Drive precisar virar Shared Drive sem perder estrutura, linhagem, IDs preserváveis, hashes ou rollback.

## Decisões que evitaram perda

1. Resolver o link pela API e listar filhos diretos antes de definir escopo. O link enviado apontava para `MGS-AGENTS`, não apenas `CRIATIVOS`; incluía Creative Ops, referências da Atena, templates Meta e planilha financeira.
2. Quando o próprio Shared Drive foi renomeado para `MGS-AGENTS`, usar o Drive root como equivalente da raiz antiga. Recriar os filhos diretamente e impedir `MGS-AGENTS/MGS-AGENTS`.
3. Não usar arraste pelo Drive for desktop. O Google não suporta mover pasta My Drive → Shared Drive por esse caminho, e a Drive API respondeu HTTP 403 `teamDrivesFolderMoveInNotSupported` para pastas.
4. Separar por classe:
   - pasta → recriar e mapear `old_folder_id → new_folder_id`;
   - arquivo com `canMoveItemIntoTeamDrive=true` → `files.update(addParents/removeParents)`, preservando `fileId` e checksum;
   - arquivo de owner externo com move negado → `files.copy`, novo ID, `appProperties.mgs_source_id`, checksum e mapa old → new.
5. Não apagar a origem durante a cópia. Após validação integral e instrução expressa de Rodolfo, mover a árvore fonte **residual** — shells das pastas antigas e originals externos copiados — para um container de backup no My Drive; isso retira originals copiados da raiz operacional sem perder rollback.

## Runner/checkpoint robusto

- Inventário imutável antes do write: IDs, parents, paths, MIME, size, MD5, owner e capabilities.
- Vincular o checkpoint a schema, source/target, tag de migração e SHA-256 do inventário; rejeitar mapa/chaves/actions que não coincidam exatamente.
- Fresh-run gate: destino vazio + re-scan da origem sem drift de ID/nome/parent/size/MD5.
- Checkpoint atômico fora do Git após cada pasta/arquivo.
- Pastas e cópias recebem `appProperties` com source ID para recuperação idempotente após crash.
- Em retry, itens já concluídos são pulados; a validação final reconcilia todos os IDs.
- No gate final, validar item a item nome, MIME, parent mapeado, `driveId`, `trashed=false`, tamanho/MD5 e `appProperties`, não apenas contagens.
- Antes do backup, reenumerar a origem residual e exigir exatamente os folders antigos + originals copiados, comparando novamente os hashes com o destino.
- Se o processo morrer depois do PATCH e antes do checkpoint, fazer GET: se o arquivo já estiver no parent/drive corretos, considerar o move concluído.
- A listagem do Drive pode apresentar consistência eventual logo após um lote grande. Repetir a validação de contagem com backoff antes de declarar item ausente; neste caso a primeira leitura viu 1.442/1.443 e a leitura seguinte confirmou 1.443/1.443.

## Evidência da execução

```text
Origem                  My Drive/MGS-AGENTS
Destino                 Shared Drive/MGS-AGENTS
Itens                   1.443
Pastas recriadas        304
Arquivos                1.139
Moves com mesmo ID      1.035
Copies com novo ID      104
MD5 verificados         1.134
MD5 divergentes         0
Google-native same ID   5
```

O backup final reteve as 304 pastas antigas e os 104 originals externos. Os 1.035 arquivos movidos ficaram somente no Shared Drive.

## Cutover operacional após PASS

1. Atualizar defaults de scripts/watchdogs para o Shared Drive root somente depois do readback final.
2. Atualizar referências ativas de Ares/Atena com folder map; não reescrever relatórios históricos.
3. Manter `source_drive_id` histórico apontando para o original em backup; o mapa da migração identifica a cópia organizacional.
4. Reaplicar permissões diretas necessárias no novo `UPLOAD MANUAL`; recriar pastas não preserva ACL de folder.
5. Testar OAuth e service account no novo root, inventário read-only, capabilities e ausência de root duplicado.
6. Não reiniciar agentes quando a alteração for apenas ID/default/skill e os runners passarem sem restart.

## Artefatos de auditoria desta implementação

- Inventário full-root: `data/ares/creative-ops/shared-drive-migration/20260716T001727Z/`
- Manifestos e validação: `data/ares/creative-ops/shared-drive-migration/20260716T003345Z/`
- Runner: `scripts/ares-migrate-mgs-agents-shared-drive.py`

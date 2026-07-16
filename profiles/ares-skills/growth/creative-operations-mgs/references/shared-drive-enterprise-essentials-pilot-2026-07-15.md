# Enterprise Essentials + Shared Drive — evidência validada em 2026-07-15

## Escopo

Piloto real para substituir a árvore `MGS-AGENTS/CRIATIVOS` em My Drive por um Shared Drive controlado pela organização, mantendo e-mail no Zoho e apenas uma licença Workspace paga.

Não reutilizar IDs abaixo como configuração permanente; descobrir o estado live por API.

## Ambiente validado

- Edição: Google Workspace Enterprise Essentials.
- Identidade paga: `support@matteiservicesinc.com`.
- E-mail permaneceu no Zoho; nenhuma troca de MX foi necessária.
- Shared Drive criado manualmente na UI: `MGS-AGENTS`.
- Service account Ares adicionada como `Manager`; a API retornou papel `organizer`.
- A service account não consumiu assento Workspace.

## Readback mínimo do Manager

Antes do piloto, exigir simultaneamente:

- `drives.list` encontra exatamente o Shared Drive esperado;
- capabilities do Drive: `canAddChildren`, `canManageMembers`, `canRename` e `canTrashChildren` iguais a `true`;
- `permissions.list` mostra a service account com `permissionType=member` e `role=organizer`.

No piloto validado, o Ares passou em 21/21 passos:

- criar pastas;
- upload e download com hash;
- editar conteúdo;
- renomear e mover;
- `trashed=true` com readback;
- `trashed=false` com readback;
- exclusão definitiva de arquivo e pasta;
- GET final retornando HTTP 404;
- cleanup sem itens piloto remanescentes.

## Intake externo sem licença

O caminho que funcionou foi compartilhar **somente a pasta de intake** com o Gmail externo, sem adicioná-lo como membro do Shared Drive ou usuário do Admin Console:

- permissão direta da pasta: `permissionType=file`;
- papel: `writer`;
- conta: Gmail externo;
- resultado: upload real permitido;
- o arquivo recebeu `driveId` do Shared Drive e não apresentou owner individual;
- o Ares recebeu `canDownload`, `canEdit`, `canRename`, `canTrash`, `canDelete`, `canMoveItemWithinDrive` e `canMoveItemOutOfDrive`.

Isso não cria licença Workspace. Ainda assim, testar em cada tenant: políticas externas podem bloquear ou reduzir o papel.

## Pitfall de identidade do uploader

Em upload externo real, a API pode retornar:

```text
lastModifyingUser.displayName = criativosevo
lastModifyingUser.emailAddress = ausente
```

Não classificar como falha apenas pela ausência do e-mail. Correlacionar:

1. permissão direta da pasta com `emailAddress` e `role=writer`;
2. `lastModifyingUser.displayName`;
3. timestamp posterior ao pedido de upload;
4. único arquivo novo no intake;
5. `driveId` e capabilities.

Também não aceitar um arquivo enviado pela identidade Workspace (`displayName=support`) como prova de upload externo. Se `identity_match=false`, registrar o lifecycle separadamente e manter o estado do teste externo como parcial, salvo se outro arquivo externo já tiver sido comprovado.

## Regra de cleanup

- Não apagar o upload externo em uma falha de validação intermediária.
- Preservar até concluir download/hash, move, trash, restore e delete.
- Em erro, manter o arquivo para inspeção e registrar IDs remanescentes.
- Só excluir a pasta piloto e sua permissão direta após readback final HTTP 404.

## Evidência operacional

Relatórios versionados:

- `data/ares/creative-ops/shared-drive-migration/20260715T233525Z/shared-drive-manager-pilot.json`
- `data/ares/creative-ops/shared-drive-migration/20260715T233624Z/external-upload-folder-permission-pilot.json`
- `data/ares/creative-ops/shared-drive-migration/20260715T234833Z/external-uploader-real-file-pilot.json`
- `data/ares/creative-ops/shared-drive-migration/20260715T235321Z/external-uploader-real-file-pilot.json`

A evidência prova o modelo técnico; billing real continua sendo confirmado no Admin Console, não inferido apenas pela Drive API.

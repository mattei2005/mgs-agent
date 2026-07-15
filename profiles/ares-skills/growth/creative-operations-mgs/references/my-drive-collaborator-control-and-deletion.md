# Controle de itens enviados por colaboradores no Drive MGS

## Invariante operacional de Rodolfo

Tudo dentro de `MGS-AGENTS/CRIATIVOS` deve ser operável pelo Ares sem autorização por arquivo. Falha de permissão nessa hierarquia é anomalia de infraestrutura/acesso a investigar e corrigir, não motivo rotineiro para bloquear Creative Ops ou pedir ao gestor que transfira ownership.

## Distinção técnica necessária

No Google **My Drive**, o proprietário da pasta pai e o proprietário de cada item podem ser diferentes. Compartilhamento como `writer` pode permitir baixar, editar e mover, mas a API ainda pode negar `trash/delete` de um item pertencente ao uploader. Isso não invalida o controle operacional esperado pela MGS; mostra que a implementação de acesso não está satisfazendo o invariante.

Não confundir:

- mover dentro da árvore MGS;
- remover da pasta/hierarquia MGS;
- enviar à lixeira (`trashed=true`);
- exclusão definitiva (`DELETE`).

Nunca chamar remoção de parent ou movimentação de “exclusão”.

## Fluxo quando houver pedido explícito de exclusão

1. Confirmar que o item está dentro da raiz canônica e que o pedido já autorizou a exclusão.
2. Consultar owner, permissões e capabilities com o OAuth canônico de Rodolfo.
3. Consultar também a identidade `ares-drive` quando ela estiver registrada no item; não presumir equivalência entre as duas identidades.
4. Executar a mutação real autorizada e validar por readback; capabilities ajudam no preflight, mas o HTTP da operação é a prova final.
5. Se uma identidade concluir a exclusão, validar `trashed=true` ou `404`, conforme a operação usada.
6. Se ambas receberem negação real, não pedir autorização por arquivo nem apresentar isso como comportamento aceitável. Classificar como drift/defeito de infraestrutura do Drive MGS, preservar a auditoria e escalar a correção estrutural.
7. Enquanto a correção estrutural aguarda aprovação, pode-se retirar um item indevido de `01_READY` por movimentação canônica quando isso estiver autorizado, mas reportar claramente que mover não equivale a deletar.

## Correção estrutural

Para garantir exclusão independentemente do uploader, avaliar com plano e aprovação de Rodolfo:

- Shared Drive, no qual os itens pertencem ao Drive e os papéis de Manager/Content Manager governam o ciclo; ou
- uma política de criação/upload sob identidade central proprietária.

Antes de migrar: inventário read-only, piloto com arquivo de colaborador, teste create/move/trash/restore/delete, validação de IDs/links/checksums, atualização dos runtimes e rollback. Nunca migrar a árvore inteira apenas para resolver um item isolado sem aprovação estrutural.

### Preflight canônico de Shared Drive

Antes de criar o destino ou alterar qualquer ID operacional:

1. Com o OAuth canônico de Rodolfo, consultar `GET /drive/v3/about?fields=canCreateDrives,user(permissionId,displayName)` e listar `GET /drive/v3/drives`.
2. Repetir a descoberta com `ares-drive` quando essa identidade participar da operação; não inferir que a capacidade de uma identidade vale para a outra.
3. Se o plano já estiver aprovado e não houver Drive visível, fazer uma tentativa idempotente de `POST /drive/v3/drives` com `requestId` UUID estável e nome de piloto. O HTTP da criação é a prova final; `canCreateDrives` é preflight.
4. Interpretar `403 userCannotCreateTeamDrives` como falta de entitlement/política administrativa para criar Shared Drives, não como permissão por arquivo nem como defeito do runner. O requisito de continuação é um Shared Drive Google Workspace existente ou uma identidade Workspace/Admin habilitada; nunca solicitar senha/token em chat.
5. Enquanto o destino não existir, manter **zero itens movidos**, **zero IDs runtime alterados** e **zero mudança na origem**. Não criar uma árvore parcial em My Drive como falso substituto.
6. Inventariar recursivamente a origem antes do piloto: IDs únicos, caminho, tipo, tamanho, checksum quando disponível, owner, `ownedByMe`, `canTrash`, `canDelete` e contagem por owner. Validar JSON/CSV com igualdade de contagem e ausência de IDs duplicados.
7. Só depois de o piloto passar create/move/trash/restore/delete: migrar em lotes, validar readback/checksum/IDs, atualizar scripts e watchdogs, e manter rollback até a conferência final.

Procedimento detalhado de entitlement, escolha do plano Google Workspace, papéis, piloto e migração: `references/shared-drive-migration-and-workspace-plans.md`.

## Comunicação

- Não dizer “precisa de permissão da Kelly/gestor” como resposta padrão para itens dentro de `MGS-AGENTS/CRIATIVOS`.
- Dizer qual operação foi tentada, por qual identidade, qual HTTP/readback ocorreu e se o problema é operacional ou infraestrutura.
- Não declarar exclusão quando houve apenas movimentação.

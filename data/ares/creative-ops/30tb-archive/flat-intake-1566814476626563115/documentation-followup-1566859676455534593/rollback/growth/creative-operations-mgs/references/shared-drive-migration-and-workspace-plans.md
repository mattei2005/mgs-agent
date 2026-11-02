# Migração para Shared Drive e escolha do Google Workspace

## Quando carregar

Use quando Rodolfo exigir que tudo sob `MGS-AGENTS` — a raiz inteira ou uma subárvore como `MGS-AGENTS/CRIATIVOS` — seja movível, enviável à lixeira e excluível pelo Ares independentemente do uploader, ou quando a correção de ownership do My Drive precisar virar uma solução estrutural.

Este documento complementa `my-drive-collaborator-control-and-deletion.md` e não substitui o fluxo normal READY/LEGACY.

Evidência de implementação real, respostas da API e pitfalls do piloto Enterprise Essentials: `shared-drive-enterprise-essentials-pilot-2026-07-15.md`.

## Princípio

No **My Drive**, compartilhar uma pasta como `writer` não garante `trash/delete` sobre itens pertencentes a colaboradores. Se o requisito for controle de exclusão independente do uploader, as soluções de classe são:

1. **Shared Drive**, onde o conteúdo pertence à organização; ou
2. upload/criação sempre por uma identidade central proprietária.

Não reintroduzir transferência de ownership por arquivo como rotina. Falha dentro da árvore MGS é drift de infraestrutura a investigar.

## Preflight obrigatório antes de propor migração

1. Inventariar `CRIATIVOS` recursivamente em modo read-only:
   - IDs e paths;
   - arquivos/pastas;
   - tamanho e checksums;
   - owners;
   - `ownedByMe`;
   - `canMoveItemWithinDrive`, `canTrash` e `canDelete`.
2. Validar o armazenamento atual pelo campo `driveId`:
   - ausente → My Drive;
   - presente → Shared Drive.
3. Com a Service Account canônica, consultar:
   - `about.canCreateDrives`;
   - `drives.list`;
   - Shared Drives visíveis e capabilities.
4. Com aprovação estrutural já recebida, executar um `drives.create` idempotente usando `requestId` UUID e validar o HTTP real. `canCreateDrives` é preflight; o POST é a prova final.
5. Se ambas as identidades retornarem `userCannotCreateTeamDrives`:
   - classificar como falta de entitlement/admin do Google Workspace, não permissão por arquivo;
   - não mover nenhum item;
   - não atualizar IDs de runtime;
   - registrar inventário e preflight;
   - verificar se há identidade Workspace/Admin autorizada disponível, sem expor credenciais.
6. Billing é Critical Subset: pesquisar e recomendar planos não autoriza contratação. Comprar licença exige aprovação explícita de billing.

## Escolha do plano — conhecimento datado

Revalidar sempre na página oficial antes de orientar compra. Referência consultada em 2026-07-15; página oficial de billing atualizada em 2026-03-03:

```text
Plano       Flexível/mês   Anual/mês*   Total anual   Pool por usuário
Starter     US$ 8,40       US$ 7,00     US$ 84,00     30 GB
Standard    US$ 16,80      US$ 14,00    US$ 168,00    2 TB
Plus        US$ 26,40      US$ 22,00    US$ 264,00    5 TB
```

`*` Compromisso de pelo menos um ano. No plano flexível é possível remover usuários e cancelar sem multa; no anual, redução de licenças ocorre na renovação e o saldo do contrato continua devido se houver cancelamento antecipado.

A página oficial de preços também pode mostrar teste de 14 dias e promoções temporárias. Tratar promoção, moeda local e tributos como dados de checkout, não como garantia persistente.

### Essentials Starter não é Business Starter

- **Google Workspace Essentials Starter (gratuito) não inclui Shared Drives.** Admin Console ativo, Drive, relatórios, 100 licenças gratuitas ou 15 GB por usuário não provam esse recurso.
- A matriz oficial mostra `Drives compartilhados` vazio para Essentials Starter e disponível nas edições Essentials pagas/Enterprise Essentials e nas Business compatíveis.
- Não confundir o botão `Buy or upgrade` de um tenant Essentials Starter com entitlement já ativo. Primeiro inspecionar as opções e preços reais; não confirmar billing sem autorização.
- Não presumir que todo tenant Essentials Starter consegue transição direta para Business Starter. Verificar a oferta real em `Billing > Buy or upgrade`, o estado de verificação do domínio e, se necessário, o caminho oficial de upgrade.

### E-mail comercial, Gmail e domínio

- Um endereço existente em domínio empresarial pode ser reutilizado como identidade administrativa; não é obrigatório criar outro domínio ou outro e-mail apenas para iniciar o upgrade.
- Para participação, criação e movimentações externas em Shared Drives nas edições Business, a matriz oficial exige inscrição com **e-mail comercial** ou **domínio verificado**.
- Uma assinatura Business iniciada somente com Gmail pessoal tem recursos administrativos limitados. Não presumir que ela libera o ciclo completo de Shared Drive.
- Evitar converter o Gmail pessoal principal de Rodolfo quando ele contém grande volume de Drive ou serviços pessoais. A verificação/conversão pode mudar o endereço principal e afetar serviços pessoais. Preferir a identidade empresarial existente e manter o Gmail pessoal como Manager externo.

### Starter versus Standard

- **Business Starter suporta criação e uso de Shared Drives quando o requisito de e-mail comercial/domínio acima está atendido.** Algumas configurações administrativas avançadas de Shared Drive não estão disponíveis; o compartilhamento tende a permanecer permissivo.
- **Business Standard** adiciona 2 TB por usuário e mais controles administrativos, sendo melhor quando segurança/políticas e crescimento justificarem o custo.
- Para um piloto pequeno e árvore de criativos abaixo de 30 GB, Starter pode ser suficiente.
- Uma licença interna pode bastar se Rodolfo e `ares-drive` puderem entrar como membros externos. O piloto precisa provar isso.
- Se a organização recusar a service account externa como Manager, será necessária uma identidade Workspace própria para o Ares, possivelmente uma segunda licença.

## Essentials pago com e-mail em provedor externo

`Enterprise Essentials` é a rota natural quando a empresa mantém e-mail no Zoho, Microsoft 365 ou outro provedor e quer Drive/Shared Drives sem migrar correio.

- A identidade `usuario@dominio-da-empresa` pode continuar recebendo e enviando pelo provedor atual e, ao mesmo tempo, ser login do Google Workspace.
- Verificação de domínio deve usar registro **TXT**. Ela não exige trocar o provedor de e-mail.
- Não alterar registros **MX** durante uma migração de Drive. Só apontar MX para o Google quando a empresa decidir explicitamente migrar o correio para Gmail.
- Edições Business incluem Gmail, mas o uso não é obrigatório: é possível manter MX no provedor atual e deixar Gmail desativado/não utilizado.
- Em tenant `Essentials Starter`, a oferta de upgrade pode mostrar apenas `Enterprise Essentials` e `Enterprise Essentials Plus`. O caminho oficial para Business pode exigir: upgrade para Enterprise Essentials → verificar domínio → então verificar se a troca para Business foi liberada.
- `Team dashboard` exibindo pool de 1 TB prova que o upgrade pago foi aplicado; não prova sozinho que um Shared Drive foi criado, que aparece na UI ou que a identidade operacional já o enxerga.

## Licença, colaborador externo e service account

Distinguir sempre três classes:

1. **Usuário criado/adicionado à organização no Admin Console:** consome licença paga quando ativo, conforme o plano.
2. **Colaborador externo convidado para conteúdo/Shared Drive:** não consome licença da organização, mas a edição da conta externa e as políticas podem limitar o papel disponível.
3. **Google Cloud service account:** não é assento Workspace, não consome licença mensal e opera nos Shared Drives onde recebeu papel suficiente. Na MGS, novos uploads automatizados pertencem ao `MGS-AGENTS`; Sheets existentes podem permanecer no My Drive quando compartilhadas diretamente para preservar IDs.

Regras práticas:

- Não prometer `Content Manager` a um Gmail pessoal sem piloto. Primeiro tentar **permissão direta apenas na pasta de intake** (`permissionType=file`, `role=writer`), sem adicionar a conta como membro do Shared Drive nem usuário do Admin Console.
- Validar com upload real. Em um tenant Enterprise Essentials, esse modelo permitiu ao Gmail externo enviar diretamente para o Shared Drive sem assento pago; o arquivo recebeu o `driveId` organizacional e o Ares obteve capabilities completas. Políticas de outro tenant ainda podem bloquear ou reduzir o papel.
- Se a permissão direta não permitir upload, usar intake externo separado: `UPLOAD MANUAL` em My Drive compartilhado como editor → Ares copia o RAW validado para `99_LEGACY` e o tratado para `01_READY` no Shared Drive → remove o item da fila sem apagar o original do colaborador.
- Registrar a linhagem do intake externo para as duas cópias organizacionais e nunca tratar o RAW externo e sua cópia como candidatos independentes.
- Adicionar `ares-drive` diretamente ao Shared Drive como `Manager` e confirmar por API `permissionType=member`, `role=organizer` e capabilities do Drive. Service account externa como organizer sem licença foi validada em Enterprise Essentials; se a política do tenant recusar ou limitar o papel, parar e avaliar domínio/política ou identidade Workspace própria.

## Identidade e validação pós-upgrade

A compra ou troca de uma identidade Workspace não altera a identidade técnica canônica da MGS.

- Consultar a conta administrativa na UI somente para ações de tenant/Shared Drive que exigem usuário Workspace.
- Não criar credencial alternativa para testar o tenant. Criar o Shared Drive pela conta paga quando necessário e compartilhar com a Service Account canônica.
- Nunca pedir senha ou credencial no chat. Validar a Service Account por projeto, client email, `driveId`, capabilities e canário antes de qualquer write.

Sequência pós-contratação de baixo risco:

1. Confirmar na UI plano/pool aplicado e observar se `Shared drives` aparece, sem confundir storage com entitlement operacional.
2. Se ainda não houver Shared Drive, criá-lo manualmente pela conta Workspace paga e compartilhar com a Service Account canônica.
3. Adicionar somente a service account do Ares como `Manager`; não adicionar gestores antes do readback.
4. Pela API da service account, executar `drives.list`, conferir capabilities e rodar o piloto completo de create/upload/move/trash/restore/delete.
5. Testar separadamente o intake externo sem licença.
6. Só depois gerar snapshot delta e iniciar migração em lotes.

## Papéis corretos

- **Rodolfo:** `Manager`.
- **Ares:** `Manager` (`organizer`) quando o requisito inclui exclusão definitiva via API.
- **Gestores/uploader:** `Content Manager` por padrão; não elevar para Manager sem necessidade.

`Content Manager` pode organizar e mover conteúdo para a lixeira. Para `files.delete` em Shared Drive, a API exige papel `organizer` no parent; na UI, exclusão permanente requer Manager.

## Piloto obrigatório

Antes de migrar a árvore:

1. Criar `MGS-AGENTS` ou outro nome aprovado.
2. Manter a identidade Workspace paga como administradora e adicionar Ares como `Manager`.
3. Validar primeiro o ciclo do Ares sem adicionar gestores.
4. Testar o uploader externo separadamente: se o Gmail pessoal receber papel com `canAddChildren=true`, fazer upload real; se a edição limitar a `Viewer`, usar o intake externo em My Drive e copiar RAW/tratado para o Shared Drive sem comprar licença automaticamente.
   - Em upload externo, `lastModifyingUser.emailAddress` pode ser omitido por privacidade mesmo quando `displayName` e a permissão direta identificam o colaborador.
   - Não falhar nem apagar o arquivo somente porque o e-mail não veio no metadata. Correlacionar a permissão direta da pasta (`emailAddress`/`role`), `lastModifyingUser.displayName`, timestamps, `driveId` e capabilities.
   - Preservar o upload até concluir download/hash, move, trash, restore e delete. Em falha intermediária, manter o arquivo quando ainda faltar evidência do ciclo completo.
   - Para declarar **PASS externo end-to-end**, o mesmo arquivo deve ter identidade externa correlacionada e completar todo o lifecycle. Um segundo arquivo com `lastModifyingUser=support` prova apenas o lifecycle da identidade Workspace, não substitui a prova externa.
   - Se a evidência vier de arquivos diferentes, rotular como prova composta e listar claramente qual arquivo provou upload externo e qual provou lifecycle; não fundir identidades no relatório.
5. Validar com a identidade Workspace e Ares, por API e readback:
   - criar;
   - baixar;
   - editar/renomear;
   - mover;
   - enviar à lixeira;
   - restaurar;
   - excluir definitivamente;
   - confirmar `404` ou estado final esperado.
6. Testar também a movimentação de um arquivo **já existente e pertencente a colaborador externo** do My Drive para o Shared Drive. A mudança de ownership pode ser negada mesmo quando o item é editável; não presumir que os itens de todos os owners migrarão da mesma forma.
7. Se owner externo bloquear move para Shared Drive, não falsificar migração: preservar o original e usar cópia validada sob ownership organizacional, mantendo a linhagem e o mapa de IDs.

## Confirmação de escopo e estrutura

Antes do write, resolver o ID do link pela API e listar os filhos diretos. Não presumir que uma URL aponta para `CRIATIVOS`: ela pode apontar para o pai `MGS-AGENTS` e incluir conteúdo de Creative Ops, Atena, templates e financeiro.

- Repetir ao solicitante `source_id`, nome da raiz e filhos diretos quando houver ambiguidade de escopo.
- Se Rodolfo ampliar explicitamente para a raiz inteira, refazer o inventário recursivo do root; o inventário parcial de `CRIATIVOS` não serve como baseline final.
- “Mesma estrutura” significa reproduzir todos os nomes e paths relativos sem reclassificar, achatar ou omitir siblings. Quando Rodolfo aprovar que o próprio Shared Drive se chame `MGS-AGENTS`, o Drive root representa a raiz antiga: colocar `CRIATIVOS` e os demais filhos diretamente nele e **não** criar `MGS-AGENTS/MGS-AGENTS`.
- Registrar `old_root_folder_id → new_shared_drive_id` e `old_folder_id → new_folder_id` para cada descendente; manter nomes/paths idênticos não significa preservar folder IDs.
- Conteúdo cross-module pode ser transportado estruturalmente quando Rodolfo autorizar a raiz inteira, mas Ares não altera conteúdo editorial/financeiro nem suas regras funcionais sem escopo próprio.

## Migração segura

### IDs, folders e Drive for desktop

- Um **move real de arquivo** via `files.update(addParents/removeParents)` pode preservar o `fileId` e o checksum quando a identidade tem `canMoveItemIntoTeamDrive=true`; validar antes/depois.
- A Drive API rejeita mover **pastas** do My Drive para Shared Drive com HTTP 403 `teamDrivesFolderMoveInNotSupported`. Recriar a árvore no destino e registrar `old_folder_id → new_folder_id`.
- O Google também não suporta mover pastas do My Drive para Shared Drive pelo Drive for desktop. Não orientar arrastar a árvore pelo Finder/Explorer: pode falhar ou virar cópia sem mapeamento auditável.
- Arquivo de owner externo com `canMoveItemIntoTeamDrive=false` deve ser copiado sob ownership organizacional, mantendo o original até readback. A cópia recebe novo ID; preservar checksum, fingerprint, linhagem e `old_file_id → new_file_id`.

1. Congelar writes concorrentes com lock e novo snapshot; vincular checkpoint a `source_id`, `target_drive_id`, tag de migração e SHA-256 do inventário.
2. Separar itens por owner/capacidade e executar em lotes reversíveis.
3. Preservar IDs quando o move real permitir; quando houver copy, registrar old ID → new ID, checksums e lineage.
4. Conferir contagens, paths, tamanhos e checksums após cada lote. No gate final, comparar **cada item** por ID, nome, MIME type, parent mapeado, `driveId`, `trashed=false`, tamanho/MD5 e, para pastas recriadas/cópias, `appProperties` de migração; contagem isolada não prova a hierarquia.
5. Imediatamente antes de arquivar a origem, reenumerar a árvore residual: deve conter exatamente os folders antigos e os originals que foram copiados, sem itens extras; comparar novamente tamanho/MD5 de cada original copiado com o destino. Tratar atraso de consistência da API com readback/retry limitado, nunca ignorando divergência.
6. Não excluir a origem antes do readback completo. Quando Rodolfo determinar que os itens copiados saiam do Meu Drive, após PASS mover a árvore fonte residual para um container de backup fora da raiz operacional; preservar nela os originals de owner externo e registrar `backup_container_id`/`source_root_id`, em vez de apagar sem rollback. Fazer GET independente após o move e validar nome, MIME, parent, `driveId` ausente e `trashed=false`.
7. Atualizar scripts/configs/watchdogs somente depois que o destino estiver validado.
8. Testar runners reais no novo root.
9. Enviar REPORT-INFRA com inventário, piloto, migração, IDs e rollback.

## Recomendação operacional de baixo risco

Quando o objetivo inicial for apenas provar o controle de ownership/exclusão:

1. começar com **uma edição compatível com Shared Drives e uma única licença paga** — por exemplo, Business Starter ou Enterprise Essentials quando o e-mail permanece em provedor externo;
2. preferir cobrança flexível/período de teste quando disponível;
3. concluir o piloto de identidade Workspace/Ares e, separadamente, o teste de intake externo;
4. migrar somente após PASS;
5. avaliar plano anual ou licenças adicionais apenas depois da prova, sem presumir que colaborador externo ou service account exige assento pago.

## Fontes oficiais

- Comparar Business: `https://knowledge.workspace.google.com/admin/getting-started/editions/compare-business-editions`
- Comparar Essentials: `https://knowledge.workspace.google.com/admin/getting-started/editions/compare-essentials-editions`
- Contas Business baseadas no Gmail: `https://knowledge.workspace.google.com/admin/domains/about-gmail-based-google-workspace-accounts`
- Preços: `https://workspace.google.com/pricing?hl=pt-BR`
- Flexível versus anual: `https://support.google.com/a/answer/1247360?hl=pt-BR`
- Edições que criam Shared Drives: `https://support.google.com/a/answer/12374228`
- Configuração de Shared Drives: `https://support.google.com/a/answer/7337469`
- Membros externos: `https://support.google.com/a/users/answer/9310249`
- Papéis e acesso: `https://support.google.com/a/users/answer/12380484`
- Exclusão permanente na UI: `https://support.google.com/a/users/answer/9310154`
- Exclusão pela Drive API: `https://developers.google.com/drive/api/guides/delete`

# Migração para Shared Drive e escolha do Google Workspace

## Quando carregar

Use quando Rodolfo exigir que tudo sob `MGS-AGENTS/CRIATIVOS` seja movível, enviável à lixeira e excluível pelo Ares independentemente do uploader, ou quando a correção de ownership do My Drive precisar virar uma solução estrutural.

Este documento complementa `my-drive-collaborator-control-and-deletion.md` e não substitui o fluxo normal READY/LEGACY.

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
3. Com o OAuth canônico de Rodolfo e, separadamente, com `ares-drive`, consultar:
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
3. **Google Cloud service account:** não é assento Workspace, não consome licença mensal e não tem quota própria de armazenamento; deve operar em Shared Drive ou via OAuth de usuário.

Regras práticas:

- Não prometer `Content Manager` a um Gmail pessoal sem piloto. A documentação do Google permite contribuição externa, mas contas cuja edição não inclui Shared Drives podem ser limitadas a `Viewer`; validar o papel oferecido e `capabilities.canAddChildren` por evidência real.
- Quando o colaborador só precisa enviar mídia e não deve acessar a árvore, preferir intake externo separado: `UPLOAD MANUAL` em My Drive compartilhado como editor → Ares copia o RAW validado para `99_LEGACY` e o tratado para `01_READY` no Shared Drive → remove o item da fila sem apagar o original do colaborador. Assim, tudo canônico no Shared Drive pertence à organização sem licença adicional para o uploader.
- Registrar a linhagem do intake externo para as duas cópias organizacionais e nunca tratar o RAW externo e sua cópia como candidatos independentes.
- Adicionar `ares-drive` diretamente ao Shared Drive como `Manager` e confirmar por API. Se a política recusar a service account externa ou limitar o papel, parar e avaliar domínio/política ou uma identidade Workspace própria; não presumir uma segunda licença antes do teste.

## OAuth e validação pós-upgrade

A compra em uma nova identidade Workspace não altera o OAuth já armazenado para outra conta.

- Consultar `about.user.emailAddress` antes de interpretar `canCreateDrives`, `drives.list` ou erro de criação. Um OAuth antigo de Gmail pessoal continuar com `canCreateDrives=false` não diz nada sobre o tenant recém-contratado.
- Não sobrescrever o refresh token canônico usado na operação atual só para testar a nova conta. Usar uma credencial OAuth separada para a identidade Workspace ou criar o Shared Drive manualmente na UI e compartilhar com a service account.
- Nunca pedir senha, refresh token ou client secret no chat. Se OAuth for indispensável, usar fluxo de consentimento com armazenamento separado e readback da identidade antes de qualquer write.

Sequência pós-contratação de baixo risco:

1. Confirmar na UI plano/pool aplicado e observar se `Shared drives` aparece, sem confundir storage com entitlement operacional.
2. Se ainda não houver OAuth da identidade Workspace, criar manualmente um Shared Drive piloto pela conta paga.
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

1. Criar `MGS-CREATIVE-OPS` ou outro nome aprovado.
2. Manter a identidade Workspace paga como administradora e adicionar Ares como `Manager`.
3. Validar primeiro o ciclo do Ares sem adicionar gestores.
4. Testar o uploader externo separadamente: se o Gmail pessoal receber papel com `canAddChildren=true`, fazer upload real; se a edição limitar a `Viewer`, usar o intake externo em My Drive e copiar RAW/tratado para o Shared Drive sem comprar licença automaticamente.
   - Em upload externo, `lastModifyingUser.emailAddress` pode ser omitido por privacidade mesmo quando `displayName` e a permissão direta identificam o colaborador.
   - Não falhar nem apagar o arquivo somente porque o e-mail não veio no metadata. Correlacionar a permissão direta da pasta (`emailAddress`/`role`), `lastModifyingUser.displayName`, timestamps, `driveId` e capabilities.
   - Preservar o upload até concluir download/hash, move, trash, restore e delete. Em falha intermediária, manter o arquivo quando ainda faltar evidência do ciclo completo.
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

## Migração segura

1. Congelar writes concorrentes com lock e novo snapshot.
2. Separar itens por owner/capacidade e executar em lotes reversíveis.
3. Preservar IDs quando o move real permitir; quando houver copy, registrar old ID → new ID, checksums e lineage.
4. Conferir contagens, paths, tamanhos e checksums após cada lote.
5. Não excluir a origem antes do readback completo e do aceite estrutural.
6. Atualizar scripts/configs/watchdogs somente depois que o destino estiver validado.
7. Testar runners reais no novo root.
8. Enviar REPORT-INFRA com inventário, piloto, migração, IDs e rollback.

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

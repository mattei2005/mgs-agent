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

## Papéis corretos

- **Rodolfo:** `Manager`.
- **Ares:** `Manager` (`organizer`) quando o requisito inclui exclusão definitiva via API.
- **Gestores/uploader:** `Content Manager` por padrão; não elevar para Manager sem necessidade.

`Content Manager` pode organizar e mover conteúdo para a lixeira. Para `files.delete` em Shared Drive, a API exige papel `organizer` no parent; na UI, exclusão permanente requer Manager.

## Piloto obrigatório

Antes de migrar a árvore:

1. Criar `MGS-CREATIVE-OPS` ou outro nome aprovado.
2. Adicionar Rodolfo e Ares com os papéis acima.
3. Adicionar um colaborador como `Content Manager`.
4. Fazer o colaborador criar/uploadar um arquivo e uma pasta reais de teste.
5. Validar com Rodolfo e Ares, por API e readback:
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

1. começar com **Business Starter Flexível** e uma licença;
2. usar o período de teste quando disponível;
3. concluir o piloto de Ares/Rodolfo/colaborador;
4. migrar somente após PASS;
5. avaliar mudança para anual depois da prova, sem assumir compromisso de um ano antes do teste.

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

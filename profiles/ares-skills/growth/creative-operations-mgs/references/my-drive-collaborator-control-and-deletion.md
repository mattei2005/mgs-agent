# Controle de uploads externos e arquivo permanente MGS

## Estado canônico

Resolver `context/drive-flat-intake-cutover.md` e o binding vivo `data/ares/creative-ops/30tb-archive/flat-intake-binding.json`. A confirmação do redesenho é `1566814476626563115`; a preservação equivalente dos mesmos acessos é `1566825959645253764`.

- Entrada: Shared Drive MGS-AGENTS `0AEwt4Ye690ocUk9PVA`, administrado por `support@matteiservicesinc.com`.
- Pasta de entrada preservada: `UPLOAD MANUAL`, ID `1ARBvLammWUHuAclNmcriwkkgeedKryBd`, diretamente na raiz do Drive MGS.
- Binding flat ativo: enviar os arquivos diretamente na entrada, sem subpastas obrigatórias de nicho/gestor; operação, gestor e destino vêm do pedido humano registrado. Receita `flat-upload-intake.md`.
- `_PROCESSAMENTO` é staging técnico e temporário abaixo da entrada. Organização definitiva: `MGS-ARQUIVO/CRIATIVOS` e `MGS-CORPORATIVO` nos 30 TB.
- `MGS-AGENTS/CRIATIVOS/...` pode permanecer namespace lógico de inventário legado; não é prova de localização física nem instrução para recriar pastas.

Arquivos realmente enviados ao Shared Drive pertencem à organização, não ao uploader individual. Isso não torna os arquivos permanentes My Drive objetos Shared Drive: ausência de `driveId` no stock dos 30 TB é legítima e deve ser validada pelos resolvedores aprovados.

## Fluxo canônico

1. Conferir o ID/parent e o tipo de armazenamento reais. Exigir o `driveId` MGS apenas no intake/staging, não no arquivo/stock My Drive.
2. Validar as capabilities usadas: leitura/download, upload da versão limpa em staging e movimento do original por mesmo ID. Não exigir canTrash/canDelete para tratar/mover.
3. Registrar o contexto humano e consumir o mesmo claim/executor, sem writer paralelo. Preservar gates de sanitização, naming, bytes, inventário, reservas, ACK e entrega permanente.
4. Destino `common`: 01_READY permanente, sem liberação implícita de elegibilidade. `exclusive`: `<NOME> - Exclusivos`; uso real comprovado: `<NOME> - Usados`. Duplicata preserva a linhagem e o destino anteriores.
5. O modo flat confirmado preserva fontes por movimento de mesmo ID; DELETE/trash não é etapa desse fluxo. Uma autorização antiga de retirada ou o nome deste arquivo não autoriza exclusão nova.
6. Falta de capability em um objeto que deveria ser operacional é diagnóstico de acesso a apurar. Não ampliar ACL, transferir propriedade nem pedir licença Workspace automaticamente para contornar o bloqueio.
7. Agentes usam somente SA canônica. O componente owner isolado é limitado ao transporte autorizado; nunca é fallback OAuth pessoal do Ares.

## Comunicação

- Não dizer que Kelly/Evo precisam transferir propriedade apenas porque são colaboradores externos.
- Separar entrada, staging, stock permanente, preservação por movimento e exclusão destrutiva.
- Informar o destino e a operação realmente verificados; HTTP sem readback não é prova de entrega.

# F024 — Fechamento de permissões globais em streamcb.com

**Estado:** RESOLVIDA E VALIDADA  
**Data:** 2026-09-23 UTC  
**Domínio:** `streamcb.com`  
**Aplicação:** `streamcb` / MatteiInc02  
**Autorização crítica:** Discord `1552157746940346541`

## Diagnóstico

A auditoria inicial havia contabilizado 13.030 arquivos com escrita habilitada para qualquer usuário Unix. A varredura ao vivo completa confirmou que o problema incluía também os diretórios:

- 13.030 arquivos em modo `0747`;
- 1.421 diretórios em modo `0757`;
- raiz da aplicação em modo `0757`;
- total: 14.452 alvos com `S_IWOTH`/other-write.

Todo o conjunto pertencia a `runcloud:runcloud` (`uid=1000`, `gid=1001`). O PHP-FPM ativo também executava com essa identidade. Portanto, a aplicação não dependia da escrita concedida a usuários Unix não relacionados.

Não foi encontrada evidência de invasão. O achado era uma política de permissões excessivamente aberta, provavelmente herdada da implantação original.

## Escopo confirmado

Hash do escopo: `ed768ba258b79cafeeb60e339573203e18759127c2494923b6c79d8be83b988a`.

Manifesto de 14.451 entradas abaixo da raiz:
`f6d886b286d313b879f7bf6781e46de8a3e9405f7cb3d54292de62744e343eb8`.

A raiz foi incluída separadamente, totalizando 14.452 alvos.

Ação autorizada:

- remover exclusivamente `S_IWOTH`;
- arquivos `0747 → 0745`;
- diretórios e raiz `0757 → 0755`;
- preservar todos os demais bits, bytes, proprietários e grupos.

Ficaram explicitamente fora do escopo:

- `/home/runcloud/webapps`;
- outras aplicações do MatteiInc02;
- banco de dados e serviços externos.

## Backup, dry-run e canário

Backup protegido:
`/var/backups/mgs-streamcb-f024-20260923/modes-before.json.gz`

- SHA-256: `9dcaf6467dce24384b917683ee172c6a07b2ba3659edb2c17b8c2ed6e16f63ba`;
- modo `0600` em diretório `0700`;
- 14.452 entradas;
- restauração do manifesto testada.

Dry-run:

- 13.030 transições `0747→0745`;
- 1.422 transições `0757→0755` contando a raiz;
- conjunto vivo idêntico ao manifesto.

Canário:

- `index.php` mudou temporariamente `0747→0745`;
- hash permaneceu idêntico;
- home na origem e no público permaneceu HTTP 200;
- modo original foi restaurado antes do lote.

## Aplicação

O lote removeu somente o bit de escrita global dos 14.452 alvos.

Estado final:

- 13.030 arquivos em `0745`;
- 1.421 diretórios e raiz em `0755`;
- zero alvo gravável por “outros usuários”;
- owners e groups preservados em `runcloud:runcloud`;
- nenhum serviço reiniciado;
- nenhuma alteração de banco ou conteúdo.

## Validação operacional

`final-validation.json`: **PASS**.

- Zero world-writable sob a aplicação.
- Todos os 14.452 paths, tipos, owners, groups e modos conferidos.
- Zero mudança inesperada de tamanho ou mtime em arquivos.
- O mtime de `application/cache` mudou somente porque o canário autorizado criou, leu e removeu um sentinel como `runcloud`; o tamanho do diretório permaneceu igual e não restou arquivo de teste.
- Teste de escrita do owner `runcloud`: PASS.
- 121 processos PHP-FPM da identidade `runcloud:runcloud` confirmados.
- Home: HTTP 200 na origem e no público.
- Assets CSS/JS: HTTP 200 e hashes iguais entre origem e público.

## Novo risco fora do escopo

O diretório compartilhado `/home/runcloud/webapps` está em `0777`, pertence a `root:root` e não possui sticky bit.

Esse diretório afeta múltiplas aplicações. Alterá-lo sem mapear RunCloud, deploys e consumidores poderia quebrar criação/movimentação de apps. Ele foi preservado e registrado separadamente na planilha como pendência amarela, exigindo análise cross-app e nova confirmação crítica.

Isso não impede o fechamento da F024, cujo escopo era a árvore exclusiva do `streamcb.com`.

## Planilha

Atualização pela Service Account canônica:

- `Prioridades!25` — F024 verde/resolvida;
- `Domínios!103` — estado final;
- `Limpeza!12` — operação;
- `Pendências limpeza!57` — F024 resolvida;
- `Pendências limpeza!58` — parent compartilhado `0777`, pendência separada amarela;
- `Fechamento final!13` — fechamento.

Canário gravado, relido e removido. Valores relidos integralmente; 54 células verdes e oito amarelas confirmadas por `effectiveFormat`.

## Evidências

Workspace:
`/root/.hermes/profiles/zeus/workspace/streamcb-f024-resolution-20260923/`

Artefatos principais:

- `audit-live.json`
- `world-writable-manifest.json.gz`
- `authorized-scope.json`
- `apply-receipt.json`
- `final-validation.json`
- `sheet-before.json`
- `sheet-update-receipt.json`

## Conclusão

F024 está **RESOLVIDA E VALIDADA**. A aplicação deixou de ser gravável por usuários Unix não relacionados, mantendo escrita normal pelo owner do PHP-FPM e sem alterar conteúdo. O risco do diretório pai compartilhado foi preservado como pendência separada, sem ampliação silenciosa do escopo.

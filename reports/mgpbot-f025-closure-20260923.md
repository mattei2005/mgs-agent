# F025 — Fechamento de permissões globais em mgpbot.com

**Estado:** RESOLVIDA E VALIDADA  
**Data:** 2026-09-23 UTC  
**Domínio:** `mgpbot.com`  
**Aplicação:** `mgpbot` / MatteiInc02  
**Autorização:** Discord `1552302036274389123`

## Contexto operacional

Rodolfo confirmou que `mgpbot.com` e `streamcb.com` são instalações de teste do ChatPion. A instância efetivamente usada pela operação fica no servidor do Ciro e não foi tocada. O hardening de F025 foi limitado à instalação de teste `mgpbot.com` na RunCloud MGS.

## Diagnóstico

A varredura ao vivo confirmou:

- 13.155 arquivos em `0747`;
- 59 arquivos em `0767`;
- 1.469 diretórios em `0757`;
- 17 diretórios em `0777`;
- raiz da aplicação em `0757`;
- total de **14.701 alvos** com `S_IWOTH`/other-write.

Do conjunto abaixo da raiz, 14.698 entradas pertenciam a `runcloud:runcloud` e duas imagens estáticas pertenciam a `root:root`. A raiz pertencia a `runcloud:runcloud`. PHP-FPM e os seis crons ChatPion da aplicação executavam como `runcloud`.

Não foi encontrada evidência de invasão. O achado era compatível com uma política antiga de permissões excessivamente aberta.

## Escopo confirmado

- Scope SHA-256: `35737c422ea31703381457773d54bed1fd023bdb0794a1223a7dce6a0bbe0dbc`.
- Manifesto lógico SHA-256: `c18c77181a6ff60e962cd46c3e71af8f8bbfee8745950df6fcd8629ee880d9df`.
- Ação: remover exclusivamente `S_IWOTH`, preservando todos os demais bits, owners, groups e bytes.
- `/home/runcloud/webapps` permaneceu explicitamente fora do escopo.

Transições:

- 13.155 arquivos: `0747 → 0745`;
- 59 arquivos: `0767 → 0765`;
- 1.469 diretórios + raiz: `0757 → 0755`;
- 17 diretórios: `0777 → 0775`.

O group-write dos 59 arquivos e 17 diretórios foi preservado.

## Backup, dry-run e canário

Backup final protegido:

`/var/backups/mgs-mgpbot-f025-20260923-retry2/modes-before.json.gz`

- SHA-256: `295e48f53e5eab272a0f8ebd089156620a99721f636380268bc1a51e32024f5a`;
- modo `0600` em diretório `0700`;
- 14.701 entradas;
- restauração do manifesto testada.

O dry-run confirmou o conjunto exato e as quatro transições de modo. O canário alterou temporariamente `index.php` de `0747` para `0745`, preservou seu SHA-256 e manteve home e login HTTP 200 na origem e no público; o modo original foi restaurado antes do lote.

## Falhas iniciais, rollback e correção

As duas primeiras tentativas abortaram na validação pós-lote porque `application/cache` teve o `mtime` atualizado enquanto os crons ativos do ChatPion faziam manutenção normal de cache. A validação tratava inicialmente qualquer alteração de `mtime` como inesperada.

Em ambas as tentativas:

- os 14.701 modos foram restaurados integralmente antes do encerramento da execução;
- a contagem original de world-writable voltou exatamente a 14.701;
- home na origem e no público permaneceu HTTP 200;
- nenhum sentinel permaneceu;
- nenhuma alteração parcial ficou ativa.

Uma varredura read-only de volatilidade por 20 segundos confirmou que somente o diretório `application/cache` variava, com tamanho estável. A validação foi corrigida para reconhecer exclusivamente essa variação do runtime ativo, mantendo fail-closed para qualquer outro path. A terceira execução passou integralmente.

Os backups restritos das tentativas abortadas foram preservados como evidência:

- `/var/backups/mgs-mgpbot-f025-20260923/`;
- `/var/backups/mgs-mgpbot-f025-20260923-retry1/`.

## Aplicação

A terceira execução removeu somente other-write dos 14.701 alvos.

Estado final:

- 13.155 arquivos em `0745`;
- 59 arquivos em `0765`;
- 1.469 diretórios e raiz em `0755`;
- 17 diretórios em `0775`;
- zero alvo world-writable sob a aplicação;
- owners e groups preservados;
- nenhum serviço reiniciado;
- nenhuma alteração de banco ou conteúdo.

## Validação funcional do ChatPion de teste

`final-validation.json`: **PASS**.

- PHP-FPM: 19 processos `runcloud:runcloud` observados.
- Seis crons da aplicação: todos executam como `runcloud` e usam `curl`.
- Escrita real pelo owner em `application/cache`: create/read/delete PASS; zero resíduo.
- Home: HTTP 200 na origem e no público.
- Login `/home/login`: HTTP 200 na origem e no público.
- CSS, JavaScript, favicon e logo: HTTP 200 e hashes coincidentes entre origem e público.
- Após o lote:
  - Nginx: 35 requisições HTTP 200; sete chamadas `curl` do cron, todas 200;
  - Apache: 57 requisições HTTP 200; 17 chamadas `curl` do cron, todas 200;
  - zero HTTP 5xx;
  - zero erro recente de permissão nos tails dos logs de erro.
- Nenhuma mudança inesperada fora de `application/cache`; a variação do cache foi atribuída ao runtime ativo e aos canários validados.

Não foi enviado teste real de mensagem pelo Facebook/Messenger. A validação comprova runtime web, login, assets, crons e escrita do owner da instalação de teste; não certifica integração externa de uma página Facebook.

## Risco fora do escopo

O diretório compartilhado `/home/runcloud/webapps` permanece `0777`, `root:root`, sem sticky bit. Esse risco cross-app já estava registrado separadamente na planilha e não foi alterado.

## Planilha

A planilha canônica foi atualizada pela Service Account oficial:

- `Prioridades!26` — F025 verde/resolvida;
- `Domínios!76` — estado final;
- `Limpeza!13` — operação;
- `Pendências limpeza!59` — fechamento e histórico dos rollbacks;
- `Fechamento final!14` — conclusão.

Canário em `Resumo!Z98` foi gravado, relido e removido. Todos os valores foram relidos; 54 células verdes foram confirmadas por `effectiveFormat`.

## Evidências

Workspace:

`/root/.hermes/profiles/zeus/workspace/mgpbot-f025-resolution-20260923/`

Artefatos principais:

- `audit-live.json`;
- `world-writable-manifest.json.gz`;
- `authorized-scope.json`;
- `apply-receipt.json`;
- `final-validation.json`;
- `sheet-before.json`;
- `sheet-update-receipt.json`.

## Conclusão

F025 está **RESOLVIDA E VALIDADA**. A instalação ChatPion de teste deixou de ser gravável por usuários Unix não relacionados, preservando a escrita do owner, o group-write necessário, o runtime dos crons e a saúde HTTP. A instância operacional no servidor do Ciro não foi alterada.

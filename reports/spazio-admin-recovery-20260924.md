# Spazio — recuperação do painel WordPress

**Estado:** CONCLUÍDO E VALIDADO  
**Data operacional:** 2026-09-24 America/New_York / 2026-09-25 UTC  
**Domínio:** `spaziokitchensandbaths.com`  
**Servidor:** SpazioVPS / RunCloud server ID `266820` / `157.230.212.128`  
**Webapp:** `spaziokitchensandbaths` / app ID `1376648`  
**Pedido:** Discord `1552847273740992512`  
**Confirmação crítica do acesso temporário:** Discord `1552849995898560513`

## Resultado

O painel WordPress foi recuperado. A rota pública `/wp-admin/`, que retornava HTTP 500 com a tela genérica de erro crítico, voltou a carregar a tela de login do WordPress sem erro fatal.

A homepage e a API REST permaneceram disponíveis durante o incidente e responderam HTTP 200 após o reparo.

## Causa confirmada

O log Nginx/FastCGI registrou repetidamente:

`PHP Fatal error: Uncaught Error: Call to undefined function wp_kses() in wp-content/db.php:35`

O arquivo era um drop-in de banco carregado antes de `wp_kses()` estar disponível. O erro permaneceu mesmo com todos os 26 plugins normais temporariamente inativos, confirmando que o problema não era a ativação de um plugin normal isolado.

A associação causal direta a uma atualização específica não foi comprovada. O que foi comprovado é que o drop-in `wp-content/db.php` era o componente fatal ativo.

## Reparo reversível

1. O arquivo vivo foi preservado com SHA-256 `2f08b9d24303a0da6f22c57ac35f405cc60e98701662a6256f743325f07e42a0`.
2. Uma cópia protegida `root:root`, modo `0600`, foi validada em:
   `/var/backups/mgs-spazio-f031-20260924/incidents/spazio-admin-20260924/db.php.pre-repair`
3. O drop-in foi movido para fora do webroot, sem exclusão, em:
   `/var/backups/mgs-spazio-f031-20260924/incidents/spazio-admin-20260924/db.php.disabled-live`
4. Não foi necessário reiniciar PHP, Nginx, MariaDB ou o servidor.
5. O rollback não foi acionado porque todas as validações passaram.

## Validação

- `/wp-admin/`: HTTP 500 crítico antes; tela de login HTTP 200 depois.
- Validação independente por navegador: página de login WordPress carregada; mensagem crítica ausente.
- Homepage pública: HTTP 200.
- REST pública: HTTP 200.
- `wp db check`: PASS.
- WordPress core checksum: PASS.
- Plugins normais ativos: 26, iguais ao baseline anterior ao isolamento.
- Credenciais SSH RunCloud: zero no readback final.
- Chaves temporárias usadas no diagnóstico e reparo: removidas; autenticação posterior recusada; material privado local destruído.
- Segredos expostos: zero.

## Evidência

Workspace restrito:

`/root/.hermes/profiles/zeus/workspace/spazio-admin-recovery-20260924/`

Artefatos principais:

- `recovery.json`
- `diagnostic-result.json`
- `diagnostic-lifecycle-receipt.json`
- `repair-result.json`
- `repair-lifecycle-receipt.json`
- `object-cache-repair-result.json`
- `object-cache-repair-lifecycle-receipt.json`

## Limpeza complementar do cache

O painel também exibia `W3 Total Cache Error` porque o plugin W3 Total Cache já não existia, mas o drop-in órfão `wp-content/object-cache.php` permanecia no webroot.

- Proveniência W3 confirmada no arquivo; diretório do plugin ausente.
- SHA-256 preservado: `61a89d90bbfcc8282a37448a5c27ee4c51aeec30ac9e1ccbdae55f2f4f58f887`.
- Cópia protegida: `/var/backups/mgs-spazio-f031-20260924/incidents/spazio-admin-20260924/object-cache.php.pre-repair`.
- Drop-in desativado reversivelmente: `/var/backups/mgs-spazio-f031-20260924/incidents/spazio-admin-20260924/object-cache.php.disabled-live`.
- `wp_using_ext_object_cache()`: `false`, estado esperado sem o plugin.
- Painel, homepage e REST: HTTP 200; erro W3 ausente nas superfícies verificadas.
- Banco e core: PASS; 26 plugins ativos e 31 plugins normais preservados.
- Credencial SSH temporária `575934`: removida; lista final zero; chave revogada; material local destruído.

## Incidente posterior — atualização em lote de plugins

Uma atualização em lote posterior voltou a derrubar homepage, painel e REST com HTTP 500. A linha vermelha do atualizador apareceu no SpeedyCache Pro, mas a árvore do SpeedyCache e do SpeedyCache Pro permaneceu na versão `1.3.5` e não foi a origem do fatal.

### Causa comprovada

O stack trace apontou incompatibilidade entre Elementor core `4.3.1` e Elementor Pro `3.31.2`:

`elementor-pro/core/modules-manager.php:92 → elementor/core/experiments/manager.php:968`

Erro fatal: `Depending on a hidden experiment is not allowed.`

Tentativas unitárias de rollback/reconstrução do Elementor e de desativação temporária do Elementor Pro não passaram em todos os validadores e foram automaticamente revertidas. Nenhuma tentativa parcial permaneceu em produção.

### Rollback final autorizado e validado

Autorização crítica: Discord `1552872244823203972`.

Foi realizado rollback atômico somente de `wp-content/plugins` usando o restore isolado e previamente validado de 24/09/2026. Banco de dados e uploads não foram restaurados.

- Manifesto da árvore restaurada: 28.253 arquivos, 397.633.120 bytes, digest `5434e74223aad87f9fa62fba4434c01f2a554fb6c3f3d17aefba3e0399d9a5a7`.
- Árvore pós-atualização preservada integralmente: 15.760 arquivos, 225.267.315 bytes, digest `364d060bd87a9bf04924d62d1d21f3048bfd80eff05d73346dcd58320af690c6`.
- Rollback preservado em `/var/backups/mgs-spazio-f031-20260924/incidents/spazio-admin-20260924/plugins-post-update-preserved-20260925-retry`.
- Elementor: `3.31.2`, ativo.
- Elementor Pro: `3.31.2`, ativo.
- SpeedyCache: `1.3.5`, ativo.
- SpeedyCache Pro: `1.3.5`, ativo.
- Plugins ativos: 26.
- Plugins normais presentes no snapshot: 47, sendo 21 inativos. O valor anterior de 31 pertencia ao estado intermediário antes do rollback completo da pasta.
- Homepage: HTTP 200, sem erro crítico.
- `/wp-admin/`: HTTP 200 na tela de login, sem erro crítico e sem alerta W3.
- REST: HTTP 200.
- `wp db check`: PASS.
- Checksum do core WordPress: PASS.
- PHP-FPM: ativo; reload concluído.
- Novos fatals após o cutover: zero.
- Credencial SSH temporária final `575970`: removida; lista final zero; chave revogada; material privado local destruído.

Artefatos finais:

- `plugins-directory-rollback-result.json`
- `plugins-directory-rollback-lifecycle-receipt.json`

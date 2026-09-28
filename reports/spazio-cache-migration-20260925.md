# Spazio — migração SpeedyCache para W3 Total Cache

- Data: 2026-09-25
- Site: `spaziokitchensandbaths.com`
- Servidor RunCloud: `266820`
- Webapp: `1376648`
- Autorização crítica: Discord `1553037118790697162`
- Status: `completed_validated`

## Estado anterior

- SpeedyCache `1.3.5`: ativo.
- SpeedyCache Pro `1.3.5`: ativo.
- W3 Total Cache `2.10.6`: instalado e inativo.
- Elementor `3.31.2` + Elementor Pro `3.31.2`: ativos.
- `advanced-cache.php`: SpeedyCache.
- `object-cache.php`: ausente.
- Cache-Control da home: `no-store, no-cache, must-revalidate`.
- Dez opções e um evento cron do SpeedyCache inventariados.
- Nenhuma tabela própria do SpeedyCache encontrada.
- Os três diretórios históricos `.DISABLED` já estavam ausentes no readback live e sem referências funcionais; portanto não houve nova exclusão deles.

## Backup e rollback

- Backup transacional: `/home/runcloud/.mgs-backups/spazio-cache-migration-20260925T134432Z`
- Banco compactado: `14.992.175` bytes.
- Manifesto: SHA-256 `eca86678aa8cf4c0389bbb47b53f5dc8260ab8d7ce09e439f5775c09956f133e`.
- Snapshot RunCloud pré-existente concluído também foi validado antes da mudança.

## Mudança aplicada

- SpeedyCache Pro e SpeedyCache desativados nessa ordem.
- Hooks de desinstalação executados e ambos os plugins removidos do webroot.
- Cache, configuração, drop-in, opções, metadados e evento cron exclusivos do SpeedyCache removidos.
- W3 Total Cache `2.10.6` teve checksums oficiais validados, foi ativado e configurado em perfil conservador:
  - page cache: ativo, `Disk: Basic` (`file`);
  - browser cache: ativo;
  - minify: desativado;
  - database cache: desativado;
  - object cache: desativado;
  - fragment cache, lazy load, CDN e Varnish: desativados.
- A primeira configuração colocou as regras Nginx fora do webapp em `/home/runcloud/.mgs-w3tc/spazio-nginx.conf`. O cache funcionava por CLI, mas o PHP-FPM/WordPress não podia reescrever esse caminho por `open_basedir`, gerando aviso no painel.
- A correção final moveu `config.path` para `/home/runcloud/webapps/spaziokitchensandbaths/.mgs-w3tc/spazio-nginx.conf`, dentro do webapp, com diretório privado `0700` e proprietário `runcloud`.
- O caminho oculto retorna HTTP `403` tanto publicamente quanto na origem, e o arquivo público `/nginx.conf` permanece em `404`.
- A configuração histórica do W3TC ainda tinha `lazyload.enabled=true`; ela foi definida explicitamente como `false` porque o script `pub/js/lazyload.min.js` estava inacessível e ocultava a imagem do CAPTCHA no login.
- A árvore do plugin estava com arquivos `0640` e diretórios sem leitura compatível com o worker Nginx. Foi preservado manifesto de owner/mode e normalizada somente a árvore `w3-total-cache` para diretórios `0755` e arquivos `0644`; nenhum outro plugin ou arquivo WordPress foi abrangido.
- O preflight do reboot encontrou `browsercache.enabled=false`, divergente do perfil aprovado. A opção foi restaurada explicitamente para `true`, o ambiente W3TC foi regenerado e o cache foi limpo antes do reboot.
- Elementor e Elementor Pro não foram alterados.

## Validação final

- SpeedyCache e SpeedyCache Pro: ausentes da lista de plugins.
- Opções SpeedyCache restantes: zero.
- Eventos cron SpeedyCache restantes: zero.
- Tabelas SpeedyCache restantes: zero.
- Diretórios/cache/configuração SpeedyCache restantes: zero.
- W3 Total Cache `2.10.6`: ativo.
- `advanced-cache.php`: pertence ao W3 Total Cache.
- `object-cache.php`: ausente.
- Evidências de cache W3TC geradas: 4 arquivos.
- Home em origem: HTTP `200`, marcador W3TC presente, `Cache-Control: max-age=3598, public` na segunda leitura.
- Admin: HTTP `302` para login.
- REST: HTTP `200`.
- Público e origem: home `200`, admin `302`, REST `200`, `/nginx.conf` `404`.
- Título, canonical e contagem de referências Elementor preservados.
- Nenhum fatal novo no período da migração.
- A rotina `Root_Environment::fix_in_wpadmin()` do W3TC foi executada por uma requisição real via PHP-FPM e passou, comprovando gravação sem FTP e eliminando a causa do aviso administrativo.
- Checksums oficiais do W3TC passaram antes e depois da normalização de permissões.
- Os assets críticos do assistente (`wizard.js`, `wizard.css` e `w3tc_cube-shadow.png`) passaram de HTTP `404` para `200` na origem.
- Todos os 88 arquivos CSS/JS/imagem de `w3-total-cache/pub/` foram testados publicamente e por origem: `176/176` respostas HTTP `200`, zero falhas.
- O login foi renderizado em Chromium após a correção: CAPTCHA visível, zero respostas HTTP `4xx/5xx`, zero requests falhos e zero erros de console. O CAPTCHA não foi contornado.
- A captura posterior enviada por Rodolfo mostra o aviso W3TC estilizado de atualização de regras Nginx; não há mais evidência visual de CSS/JS/imagens ausentes. Esse aviso pede restart/reload, mas não é erro de asset.
- Reboot completo da SpazioVPS autorizado em `1553055027403432010` e concluído: boot ID `e6b6b13f-7042-46ce-931c-dfbe8ce39798` → `b4ceaea0-cec7-4a0c-8648-2742c418bd60`.
- Pós-boot: kernel `5.15.0-194-generic`, sem marcador de reboot, zero unidades falhas; `nginx-rc`, `php83rc-fpm`, `mariadb`, `fail2ban`, `runcloud-agent` e `cron` ativos.
- `nginx -t` passou. Permanece aviso não bloqueante de `ssl_stapling` porque a origem não possui a cadeia intermediária do issuer no arquivo local; sintaxe e inicialização do Nginx passaram.
- Pós-boot: home pública/origem `200`, admin `302`, REST `200`, cache W3TC e canonical presentes, Elementor/Pro `3.31.2`, 176/176 assets W3TC `200`, zero fatal de Nginx/PHP/MariaDB e zero credencial SSH temporária.
- O probe temporário de PHP-FPM foi removido e validado.
- Credenciais SSH temporárias restantes: zero; chave revogada e validada.

## Incidentes e recuperação automática

1. Primeira chamada local não herdou o ambiente do 1Password; nenhuma conexão ou mudança de produção ocorreu. A execução foi repetida com o ambiente canônico.
2. O primeiro preflight remoto esperava linhas WP-CLI para diretórios `.DISABLED` que já estavam ausentes; nenhuma mudança ocorreu. O preflight foi corrigido para usar filesystem, `active_plugins` e referências funcionais.
3. A primeira tentativa transacional usou uma opção inexistente em `wp cron event delete`; o rollback automático restaurou banco e arquivos, e a home voltou a HTTP `200`. A sintaxe foi corrigida e a migração integral foi reexecutada e validada.
4. Após a migração, o painel mostrou que o PHP-FPM não podia gravar no `config.path` fora do webapp. O caminho foi movido para diretório oculto e protegido dentro do webapp, o método real de reparo do W3TC passou via PHP-FPM e as rotas públicas do arquivo permanecem bloqueadas.
5. A primeira auditoria visual autenticada foi bloqueada pelo CAPTCHA, cuja imagem estava oculta porque o lazy load histórico do W3TC injetava um script que retornava `404`. O lazy load foi desativado, o cache limpo e o CAPTCHA voltou a renderizar sem erro.
6. O assistente do W3TC permanecia sem estilo porque seus assets existiam e tinham checksum válido, mas o Nginx não conseguia servi-los com os modes encontrados. Uma primeira normalização foi revertida automaticamente por incluir no teste um `admin.css` inexistente; o alvo foi corrigido, a operação foi reexecutada e validada integralmente.
7. O primeiro preflight do reboot não executou o reboot: falhou fechado porque o caminho presumido do binário Nginx era incorreto e `browsercache.enabled` estava `false`. A credencial temporária foi removida. O detector do binário foi corrigido, o browser cache foi restaurado ao perfil aprovado e a execução completa seguinte passou sem necessidade de recuperação pós-boot.

## Evidências

- `/root/.hermes/profiles/zeus/workspace/spazio-cache-migration-20260925/lifecycle-receipt.json`
- `/root/.hermes/profiles/zeus/workspace/spazio-cache-migration-20260925/migration-live.json`
- `/root/.hermes/profiles/zeus/workspace/spazio-cache-migration-20260925/external-validation.json`
- `/root/.hermes/profiles/zeus/workspace/spazio-cache-migration-20260925/transport.json`
- `/root/.hermes/profiles/zeus/workspace/spazio-cache-migration-20260925/path-fix-lifecycle-receipt.json`
- `/root/.hermes/profiles/zeus/workspace/spazio-cache-migration-20260925/path-fix-live.json`
- `/root/.hermes/profiles/zeus/workspace/spazio-cache-migration-20260925/path-fix-external-validation.json`
- `/root/.hermes/profiles/zeus/workspace/spazio-w3tc-browser-audit-20260925/lazyload-fix-live.json`
- `/root/.hermes/profiles/zeus/workspace/spazio-w3tc-browser-audit-20260925/asset-fix-live.json`
- `/root/.hermes/profiles/zeus/workspace/spazio-w3tc-browser-audit-20260925/static-assets-validation.json`
- `/root/.hermes/profiles/zeus/workspace/spazio-w3tc-browser-audit-20260925/login-after-fix.json`
- `/root/.hermes/profiles/zeus/workspace/spazio-w3tc-browser-audit-20260925/reboot-preflight.json`
- `/root/.hermes/profiles/zeus/workspace/spazio-w3tc-browser-audit-20260925/reboot-live.json`
- `/root/.hermes/profiles/zeus/workspace/spazio-w3tc-browser-audit-20260925/reboot-lifecycle.json`

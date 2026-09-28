# VPS/Hermes + Spazio — atualização e remediação

Data: 2026-09-25  
Autoridade: Rodolfo Mattei, mensagens Discord `1553008008689225799` e confirmação crítica `1553024256252583957`  
Thread: `1551768281688580096`

## VPS dos agentes

- Atualizados os 11 pacotes pendentes, sem remoções.
- Backup e recibos: `/root/.hermes/secure-backups/vps-maintenance/20260925T115521Z-apt11`.
- Pós-validação: APT/dpkg íntegros, serviços dos agentes ativos e sem reboot pendente.

## Hermes

- Base upstream congelada: `59004a62356f3a4697ab0fe8ad5086d2b405e2a6`.
- Runtime MGS: `/root/.hermes/hermes-agent-port-main-59004a62-mgs`.
- Commit MGS: `95e3dd32d3520730f6632a42304eb0f04acca7c2`.
- Patch guard: PASS e árvore Git limpa.
- Regressões: 557 testes + 6 subtests PASS.
- Launcher ativo: `/root/.local/bin/hermes` resolve para o runtime novo.
- Ares e Atena migrados e validados com Discord conectado.
- Zeus fica por último e será reiniciado pelo finalizador canônico detached, com readiness fora da cadeia ativa.
- Rollback preservado: `/root/.local/bin/hermes-main-ee5ee84a-mgs`.

## SpazioVPS

Alvo validado: servidor RunCloud `266820`, IP `157.230.212.128`, webapp `1376648`, domínio `spaziokitchensandbaths.com`.

### Backups

- Snapshot RunCloud/GDrive `81635800`, full backup concluído em 2026-09-25 06:00:12.
- Backup transacional adicional em `/home/runcloud/.mgs-backups/spazio-remediation-20260925T125453Z`.
- Inclui dump comprimido do banco, arquivos alterados, plugins-alvo, configuração SSH, estado APT e manifesto com hash.

### Sistema

- Ubuntu 22.04 atualizado até zero pacotes pendentes.
- Kernel ativo `5.15.0-194-generic` após dois reboots validados.
- Zero unidades falhas e zero reboot pendente.
- Nginx, MariaDB, Fail2Ban, RunCloud Agent e PHP 8.3 ativos conforme o papel de cada serviço.
- PHP do webapp migrado de `php80rc` para `php83rc`; canário público/origem, painel, REST, serviço e logs passaram. PHP 8.0 ficou inativo.

### WordPress e aplicação

- WordPress `7.1.2` preservado e saudável.
- 28 plugins públicos atualizados individualmente com smoke após cada unidade.
- `duracelltomi-google-tag-manager` não ofereceu atualização aplicável pelo WP-CLI e foi restaurado automaticamente.
- Seis updates ficaram intencionalmente retidos: dois diretórios `.DISABLED`, Elementor por salto principal incompatível sem pacote Pro pareado, CookieAdmin/GoSMTP por pares Pro e SpeedyCache por par Pro. Nenhum hold foi ocultado.
- Elementor e Elementor Pro permanecem pareados em `3.31.2`.
- `DISALLOW_FILE_EDIT=true`; `wp-config.php` em `0600`; `.tmb` corrigido de `0777` para `0775`.

### Contenção e segurança

- Removidos do webroot, após backup: `nginx.conf`, `wp-admin/error_log`, `readme.html` e dois ZIPs Pantry duplicados.
- Os cinco caminhos agora respondem `404`.
- Enumeração REST de usuários e enumeração numérica de autor respondem `404`.
- XML-RPC responde `403`.
- SSH efetivo: chave pública habilitada; senha, root, X11 e senha vazia desabilitados.
- Firewall RunCloud ativo na interface `eth0`, permitindo somente os serviços aprovados: SSH 22, SMTP 25, HTTP 80, HTTPS 443 e serviço RunCloud `rcsa`/34210. Banco 3306 e porta teste 8080 estão fechados/filtrados externamente.
- Credenciais SSH temporárias após execução: zero; chaves locais removidas; revogação comprovada.

## Validação final

- Home `200`, painel `302`, REST `200`.
- Arquivos internos `404`, usuários `404`, autor numérico `404`, XML-RPC `403`.
- Público e origem responderam `200` na home.
- Zero linhas de fatal recente; zero unidades falhas; zero atualizações APT; zero reboot pendente.
- PHP RunCloud por readback: `php83rc`.

## Artefatos

- `/root/.hermes/profiles/zeus/workspace/spazio-remediation-20260925/post-validation-final.json`
- `/root/.hermes/profiles/zeus/workspace/spazio-remediation-20260925/followup-lifecycle-receipt.json`
- `/root/.hermes/profiles/zeus/workspace/spazio-remediation-20260925/final-fix-lifecycle-receipt.json`
- `/root/.hermes/profiles/zeus/workspace/spazio-remediation-20260925/final-fix-live.json`

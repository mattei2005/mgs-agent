# Inc02 — escopo atualizado após atualização automática nativa

## Resultado e fronteira de segurança

O aceite de Rodolfo `1574688273131900969` está recebido e foi validado contra o gate `1574668810458370079`, manifesto original `5554f1e992fa3dc7cbd9db990fc10146e5278b2bae00818a1a18d8c8f860a592` de19pacotes. **Não foi executado**: o primeiro pré-check parou em `package baseline drift tzdata`, antes da parada do MariaDB, backup de bancos, instalação ou reboot por Zeus. A falha original foi preservada.

O estado anterior mudou antes do aceite. A reconciliação dos logs APT, dpkg e unattended-upgrades, mais timers/política nativos, comprovou que `/usr/bin/unattended-upgrade`, via `apt-daily-upgrade.service`, instalou três versões exatamente iguais aos alvos apresentados:

- `tzdata`: `2026e-0ubuntu0.22.04.1` → `2026f-0ubuntu0.22.04.1`,2026-11-24 06:33:19UTC.
- `libssh-4`: `0.9.6-2ubuntu0.22.04.8` → `0.9.6-2ubuntu0.22.04.9`,06:33:21UTC.
- `python3-oauthlib`: `3.2.0-1ubuntu0.1` → `3.2.0-1ubuntu0.2`,06:33:23–24UTC.

O aceite humano foi às07:29:00UTC. A execução automática já estava encerrada, sem lock APT/dpkg ativo. Classificação: **mudança concorrente reconciliada de produtor nativo**, não anomalia nem efeito da execução Zeus. Não houve downgrade/reinstalação, desativação do atualizador, alteração de política/timer ou tolerância adicionada ao verificador original.

## Novo lote congelado:16 upgrades,0 novos,0 remoções

Alvo exclusivo: MatteiInc02, RunCloud288158,162.55.28.179. A lista restante mantém os mesmos alvos literais; os três itens já atualizados ficam fora da instalação:

- `mysql-common`, `mariadb-common`, `mariadb-server`, `mariadb-client-core`, `mariadb-client`, `mariadb-server-core`, `libmariadb3`: `1:10.11.19+maria~ubu2204` → `1:10.11.20+maria~ubu2204`.
- `galera-4`: `26.4.27-ubu2204` → `26.4.29-ubu2204`.
- `libglib2.0-dev`, `libglib2.0-dev-bin`, `libglib2.0-data`, `libglib2.0-bin`, `libglib2.0-0`: `2.72.4-0ubuntu2.10` → `2.72.4-0ubuntu2.11`.
- `distro-info`, `python3-distro-info`: `1.1ubuntu0.2` → `1.1ubuntu0.3`.
- `xfsprogs`: `5.13.0-1ubuntu2.1` → `5.13.0-1ubuntu2.2`.

Novo manifesto privado: `/root/.hermes/secure-backups/vps-maintenance/1574252891898908684-inc02/critical-plan-v2.json`.
SHA256: `6a2fdfef8eaf78e61d74adea865e657ff458d98ee65d0f0879479caf888e41b5`.
Estado: `prepared_remaining_16_awaiting_changed_scope_critical_confirmation`.

## Validação e proteção reexecutadas

- As16versões restantes continuam no baseline original;3nativas estão nos alvos aprovados; candidatos dos16conferidos após refresh APT limpo.
- Simulação literal dos16 com zero novos/remoções. Sem dpkg audit, holds ou failed units.
-16retornos verificáveis:13DEBs originais e3reconstruídos;16candidatos. Identidade e fluxo completo dos32payloads relidos; hashes verificados.
- Novo arquivo de configurações/dpkg capturado do estado atual e validado (`configuration-and-dpkg-v2.tar.gz`,5980578bytes), sem sobrescrever o anterior.
- Novo `rollback-and-candidates-v2.sha256` cobre a configuração atual e os32DEBs; readback SSH independente passou e reconfirmou os16baselines,3alvos nativos,9PIDs de serviços preservados e ausência das fronteiras de execução.
- MariaDB,Nginx,Apache,PHP83,RunCloud,cron,SSH,Fail2ban,firewalld ativos. Tabela MEMORY de aplicação continua com contagem real zero.
- GameZoneAd e CarCreditAd: novo GET público HTTP200. FusoEtc/UTC preservado.
- Nenhuma fronteira `apply-start`, `cold-backup-start` ou `isolated-restore-start` existe. Não há executor produtivo desta fase aguardando para disparar automaticamente.

## Decisão ainda necessária

A redução19→16 altera o lote crítico. A aprovação anterior permanece recebida e não executada; não a transportar silenciosamente para o manifesto novo. O próximo gate é confirmar **somente16atualizações mais a parada temporária do MariaDB para backup físico completo e teste isolado antes da instalação**, sem reboot. O banco ainda não foi parado por Zeus nem copiado/restaurado nesta fase. A atualização também pode reiniciar MariaDB pelos hooks nativos já revisados.

Limites preservados: sem PHP/NGINX, Node/Hermes, outros hosts, credenciais/regras manuais SSH/firewall, exclusão, política de retenção ou mudanças nos timers de atualização. As três ressalvas aceitas do Inc01 continuam encerradas e não são reabertas.

Fonte protegida: `/root/.hermes/secure-backups/vps-maintenance/1574252891898908684-inc02/`. Preservar `confirmed-preflight-transport.json`, `preflight-baseline-drift-diagnosis.json`, `remaining-lot-v2-preparation.json`, autorização original e ambos os manifestos. O relatório original é histórico; este documento supersede apenas seu gate de instalação19pendente, não elimina os eventos anteriores.

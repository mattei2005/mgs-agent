# Inc02 — lote preparado, confirmação crítica própria pendente

## Continuidade e autoridade

Rodolfo1574663015410704418 aceitou encerrar a fase de sistema Inc01 com as três ressalvas kernel apresentadas em1574659555877716081 e mandou continuar. O encerramento limitado está em `vps-maint-inc01-reboot-1574650660572504115-owner-closure.md`; o journal estrito não virou PASS nem se alterou BIOS/drivers. A mensagem autoriza preparar o próximo host, não transfere a aprovação crítica de instalação/reboot do Inc01.

Alvo desta fase: **MatteiInc02**, RunCloud288158,162.55.28.179, binding API/SSH confirmado;15webapps em uma página, IDs únicos; canários carcreditad e gamezonead vinculados ao host ephp83rc. Público de ambos HTTP200.

## Lote exato

19 atualizações; zero pacotes novos e zero remoções:

- `mysql-common`, `mariadb-common`, `mariadb-server`, `mariadb-client-core`, `mariadb-client`, `mariadb-server-core`, `libmariadb3`: `1:10.11.19+maria~ubu2204` → `1:10.11.20+maria~ubu2204`.
- `galera-4`: `26.4.27-ubu2204` → `26.4.29-ubu2204`.
- `libglib2.0-dev`, `libglib2.0-dev-bin`, `libglib2.0-data`, `libglib2.0-bin`, `libglib2.0-0`: `2.72.4-0ubuntu2.10` → `2.72.4-0ubuntu2.11`.
- `distro-info`, `python3-distro-info`: `1.1ubuntu0.2` → `1.1ubuntu0.3`.
- `tzdata`: `2026e-0ubuntu0.22.04.1` → `2026f-0ubuntu0.22.04.1`, mantendoEtc/UTC.
- `libssh-4`: `0.9.6-2ubuntu0.22.04.8` → `0.9.6-2ubuntu0.22.04.9`.
- `python3-oauthlib`: `3.2.0-1ubuntu0.1` → `3.2.0-1ubuntu0.2`.
- `xfsprogs`: `5.13.0-1ubuntu2.1` → `5.13.0-1ubuntu2.2`.

Manifesto privado: `/root/.hermes/secure-backups/vps-maintenance/1574252891898908684-inc02/critical-plan.json`.
SHA256: `5554f1e992fa3dc7cbd9db990fc10146e5278b2bae00818a1a18d8c8f860a592`.

## Proteção já preparada e verificada

16/16 predicados positivos.19 versões anteriores recuperáveis e19 candidatos por identidade/payload;16DEBs originais e3 reconstruções de payload instalado. Configuração/dpkg arquivados, tar legível e checksums lidos novamente por SSH independente. O host ainda mantém todas as19versões anteriores instaladas. Conjunto privado remoto0700, ocupação69046272bytes. Zero failed units/holds/dpkg audit. MariaDB,Nginx,Apache,PHP83,RunCloud,cron,SSH,Fail2ban e firewalld ativos/enabled. BitNinja não instalado neste host; não inventar seus hooks ou exigir seu serviço.

Código dos hooks predecessor/candidato dos19pacotes igual ao que foi integralmente inspecionado no Inc01 para as mesmas versões: efeito nativo MariaDBstop/restart/verificação de sistema e xfsprogs daemon-reload. Needrestart será list-only; não reiniciar os demais daemons por inferência.

## Backup dos bancos: plano ainda não executado

Aplicações:388tabelasInnoDB e1MEMORY cuja contagem real foi0. Não se observou MyISAM de aplicação, diferentemente do Inc01. Datadir alocado6187479040bytes, sem symlinks externos. A ferramenta mariadb-backup não está instalada. Não é correto dizer que backup lógico online de InnoDB seja impossível.

Método proposto com o stack existente: parada controlada do MariaDB para cópia física fria completa, religar prontamente a versão antiga, materializar/testar recuperação isolada sem rede e **instalar somente após recuperação PASS**. A parada afetará temporariamente sites dependentes do banco; os scripts da atualização também reiniciam MariaDB. Nenhum backup dos bancos ou restore dessa fase foi criado/exercitado ainda: dependem da confirmação da janela. Preservar todos os artefatos de recuperação; restauração sobre produção, exclusão e política de retenção não são implícitas.

O campo genérico de motivo do recibo de preparação original foi preservado e supersedido por `database-consistency-classification.json`, específico deste host; o manifesto ativo contém a classificação correta.

## Limites do gate

Não inclui reboot, kernel novo, PHP/NGINX, Node/dashboard, Hermes, outros hosts, credenciais/regras SSH/firewall manuais ou limpeza. FusoEtc/UTC e configurações locais preservados. Kernel atual5.15.0-203 permanece nesta fase; reboot posterior tem gate independente. Nenhuma instalação, parada de banco, restart ou reboot foi executado no Inc02 por esta preparação.

Fonte protegida: `/root/.hermes/secure-backups/vps-maintenance/1574252891898908684-inc02/`.
Remoto: `/root/mgs-maintenance/1574252891898908684-inc02/`.

Próxima decisão: confirmar o lote19 + pausa MariaDB para backup completo e teste isolado antes da instalação, **sem reboot**. Inc03JBF/Hestia e Node/dashboard continuam no ledger; o pai permanece aberto.

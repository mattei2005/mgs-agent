# Manutenção Inc01 — preparo e gate crítico

- Pedido original: `1574252891898908684`; continuação de Rodolfo: `1574636767036833863`; thread `1574249078584377544`.
- Fase anterior Hostinger: concluída e validada; novo boot `6326e10a-324e-48fc-9f14-f8fa3c83d00e`, kernel `6.8.0-151-generic`, 23 gates pós-boot positivos, resultado/REPORT e mensagem final relidos; nenhum novo reboot da Hostinger.
- Alvo desta fase: RunCloud `290075`, `MatteiInc01`, `162.55.28.178`, binding de API e SSH confirmados; 76 webapps em quatro páginas na API atual. Não estende manutenção ao host adicional do painel.
- Estado: **preparado; aguardando confirmação crítica do lote e da janela de consistência MariaDB**. Nenhum pacote instalado, serviço reiniciado, reboot, credencial ou política manual de firewall alterado.

## Transação congelada

20 atualizações, zero pacotes novos e zero remoções:

- `mysql-common`, `mariadb-common`, `mariadb-server`, `mariadb-client-core`, `mariadb-client`, `mariadb-server-core`, `libmariadb3`: `1:10.11.19+maria~ubu2204` → `1:10.11.20+maria~ubu2204`.
- `galera-4`: `26.4.27-ubu2204` → `26.4.29-ubu2204`.
- `libglib2.0-dev`, `libglib2.0-dev-bin`, `libglib2.0-data`, `libglib2.0-bin`, `libglib2.0-0`: `2.72.4-0ubuntu2.10` → `2.72.4-0ubuntu2.11`.
- `distro-info`, `python3-distro-info`: `1.1ubuntu0.2` → `1.1ubuntu0.3`.
- `tzdata`: `2026e-0ubuntu0.22.04.1` → `2026f-0ubuntu0.22.04.1`.
- `libssh-4`: `0.9.6-2ubuntu0.22.04.8` → `0.9.6-2ubuntu0.22.04.9`.
- `python3-oauthlib`: `3.2.0-1ubuntu0.1` → `3.2.0-1ubuntu0.2`.
- `xfsprogs`: `5.13.0-1ubuntu2.1` → `5.13.0-1ubuntu2.2`.
- `bitninja-policier`: `1.0.3-1` → `1.0.4-1`.

Manifesto privado: `/root/.hermes/secure-backups/vps-maintenance/1574252891898908684-inc01/critical-plan.json`.
SHA256: `5db8c98920645ea6a4c62c0c65053fff0e17c47e1c68da9467eeb9ed1ec47b9d`.

## Recuperação e validação já executadas

14 predicados de preparação positivos. Backup de configuração/dpkg, versões anteriores dos 20 pacotes e 20 candidatos verificados por identidade, payload e checksum. São 15 DEBs originais e 5 reconstruções de payload instalado, não equivalentes a DEBs originais do fornecedor. Readback independente em SSH, root privado 0700. Ocupação do conjunto remoto observado: 92.024.832 bytes, incluindo estágios e evidências de tentativas preservadas. Serviços MariaDB, Nginx, Apache, PHP83, RunCloud, BitNinja, dashboard e PostgreSQL ativos; PIDs dos serviços previamente observados preservados. Zero failed units, holds ou dpkg audit. Canary público eggbev HTTP200.

Evidência local protegida: `/root/.hermes/secure-backups/vps-maintenance/1574252891898908684-inc01/`.
Conjunto remoto: `/root/mgs-maintenance/1574252891898908684-inc01`.

## Gate de dados e efeito operacional

Há 147 tabelas MyISAM de aplicações e 58 MEMORY atualmente vazias; um dump apenas `--single-transaction` não prova consistência completa. Datadir observado: 28.206.088.192 bytes, sem symlinks externos, com espaço suficiente. **Backup dos bancos ainda não criado e restore ainda não exercitado**: dependem da janela autorizada de parada MariaDB.

Plano: após confirmação, parar somente MariaDB, criar/verificar backup físico frio, religar o serviço antigo prontamente, validar restore isolado sem rede/eventos/replicação e só então instalar o lote se os gates passarem. Revalidar MEMORY vazio antes da parada. Não restaurar automaticamente dados sobre produção nem sobrescrever gravações posteriores. Em falha, preservar recibos e a produção e reconciliar a camada exata.

Scripts do pacote MariaDB param/reiniciam o banco e podem verificar/migrar tabelas de sistema. O `bitninja-policier` recarrega nativamente o módulo IpFilter do BitNinja; não há edição manual de regras/allowlists. O daemon Policier está disabled/inactive e o agente BitNinja ativo: validar estado conforme o funcionamento nativo do módulo, sem exigir ativação global por inferência. Demais reinícios de needrestart ficam fora do lote. Sem reboot desta fase; kernel atual 5.15.0-203 e instalado esperado 5.15.0-204 permanecem para gate próprio. Node dedicado do dashboard, PHP/Nginx, Hermes e demais hosts não são atualizados por este lote.

## Recuperações do preparo

- Pacote instalado OAuthlib tinha um arquivo de documentação ausente: preservado estágio incompleto e recuperado DEB original da versão exata por URI histórica, com leitura completa validada.
- Reconstrução xfsprogs encontrou raiz usr-merge: preservados estágios/arquivo falhos, corrigido scaffold em novo estágio/DEB e validado o mapa completo de membros contra payload instalado.
- Helper local `inspect.py` sombreou stdlib durante importação: recuperação com `python3 -I`, seguida de novo readback independente com retorno zero; as operações desse helper eram somente leitura de produção.
- Procedimentos persistidos na skill de manutenção, referência `controlled-package-and-node-tooling-update.md`.

## Continuidade

Hostinger encerrada. Inc01 depende somente da confirmação crítica descrita; Inc02, Inc03JBF, Hestia e Node/dashboard seguem pendentes, com gates separados. Não presumir autorização para reboot ou instalação por este documento.

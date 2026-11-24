# Inc02 — reboot autorizado e validação preparada

Autoridade: Rodolfo `1574783533417894011`, confirmando o gate `1574781919080484905` na thread1574249078584377544. Alvo exclusivo MatteiInc02/RunCloud288158/162.55.28.179; demais hosts, pacotes, PHP/NGINX, credenciais, regras e Node/Hermes fora do escopo.

Preflight corrigido23/23,11fixtures de aceitação/rejeição,3scripts compilados; systemd-analyze verify0. Kernel atual5.15.0-203-generic; seleção GRUB efetiva, initrd e módulos5.15.0-204-generic comprovados. GRUB_DEFAULT0 e sem override grubenv; nenhuma alteração no bootloader. Backup frio/restauração anterior e hashes dos16retornos/configuração novamente conferidos. Quatro canários público/origem HTTP200.

Validador durável habilitado/inativo antes do reboot: `mgs-inc02-reboot-1574783533417894011-validate.service`. Próximo boot somente após existir a fronteira de tentativa. Sem envio Discord por esse validador; resultado atômico e desabilitação própria, definição preservada sem exclusão. Observador externo deve consumir o resultado somente após PID0/saída do validador, sem repetir reboot.

Estado congelado:12serviços de workload/segurança/logging ativos e habilitados;440hashes de configuração/boot/unidades, executáveis e catálogo MariaDB; snapshot de dispatch445entradas verificadas. Kernel esperado204 e novo boot ID obrigatórios; zero marcador de reboot, zero failed units, zero serviços needrestart e journal0..3 do boot inteiro estritos.

O primeiro pré-check exigiu18daemons habilitados e falhou somente para6FPMs desabilitados. Investigação confirmou ao vivo15webapps RunCloud, todosPHP83, e10upstreams FastCGI de origem correspondentes. Esses6runtimes adicionais não são versões de aplicação; a política disabled foi preservada, sem habilitá-los/reiniciá-los. Corrigida apenas aplicabilidade do checker, com falha original preservada e novo23/23; estados reais pós-boot serão registrados. Procedimento salvo na skill de manutenção.

A confirmação autoriza preparar/reiniciar/validar apenas Inc02. Não significa aprovação para reparar hardware ou suprimir journal. Qualquer erro real novo permanece bloqueante. O gateway Zeus executa em outro host(srv1767265) e não será reiniciado.

Evidência protegida local: `/root/.hermes/secure-backups/vps-maintenance/1574252891898908684-inc02/reboot-1574783533417894011/`; remoto: `/root/mgs-maintenance/1574252891898908684-inc02/reboot-1574783533417894011/`. Esta preparação não comprova reboot nem conclusão; estado efetivo vem dos recibos de dispatch/tentativa/pós-boot.

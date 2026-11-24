# Inc01 — reboot autorizado, preparo verificável

Autoridade: Rodolfo `1574650660572504115`, resposta ao gate `1574649750643281962`, thread `1574249078584377544`. Manifesto `9ddbb2988cbbd98083ef112ac2e45482ff8d1462cd87fc1cac84a37f5a1464d4`.

## Escopo

Um reboot de `MatteiInc01`, RunCloud290075,162.55.28.178: kernel5.15.0-203 →5.15.0-204. Nenhum outro host/gateway, instalação, atualização Node/Hermes, mudança de credencial/firewall ou exclusão. Hostinger não é o alvo e o consumidor externo pode acompanhar em foreground/sessão técnica sem reiniciar Zeus.

## Preparo concluído antes do disparo

-20 predicados reais pré-boot positivos;8 fixtures positivas/negativas e AST comprovando um único primitive remoto de reboot.
-286 hashes congelam configurações, imagens/initrd/GRUB, código ativo financeiro e configuração de autenticação (somente hash protegido, sem conteúdo), além dos executáveis Nginx/PHP/Node/PostgreSQL.
-Serviços essenciais ativos/enabled; Policier disabled/inactive preservado segundo o modo nativo. PostgreSQL18.6 saudável por socket peer; zero transações de clientes ativas na descoberta. Dependência systemd força app financeiro depois do PostgreSQL e parada em ordem reversa.
-Financeiro público login200/APIsemcookie401; socket interno401; eggbev origem/público200. Não há login/MFA/POST financeiro ou mudança de dados.
-Backup MariaDB frio/restore materializado anterior preservados. Novo dump PostgreSQL custom `228809357`bytes, SHA256`7671210621693ceab76cc98fef1cea80200378309a01fc4ca8e6a2322b8be924`, catálogo pg_restore legível; não se declara restore PostgreSQL materializado nesta etapa.
-Validador one-shot compilado e `systemd-analyze verify`rc0, enabled/inactive/PID0; definição retida e desabilitada após uma execução, sem limpeza implícita.
-Snapshot remoto de seis componentes imutáveis validado por sha256sum; recibos regenerados/progressos ficam fora desse snapshot.

## Executor e consumidor

-Local: `/root/.hermes/secure-backups/vps-maintenance/1574252891898908684-inc01/reboot-1574650660572504115/local_controller.py`.
-Remoto: `/root/mgs-maintenance/1574252891898908684-inc01/reboot-1574650660572504115/`.
-Validador: `mgs-inc01-reboot-1574650660572504115-validate.service`; resultado `postboot-result.json`.
-Despacho: timer/service `mgs-inc01-reboot-1574650660572504115-dispatch`, apenas após obter a admissão exclusiva canônica e quatro locks legados locais, estado committed, lock/fence remoto correspondente e ausência de transação PostgreSQL ativa. Nenhum journal/fence financeiro é alterado pelo reboot.
-O consumidor mantém a admissão até consumir novo boot/resultado final e checar HTTPexterno; não altera cron/horários. Não repete reboot por falha de transporte ou validação.
-O código versionável equivalente está em `scripts/vps-maint-inc01-1574650660572504115-{boot_probe,postboot_validator,reboot_dispatcher,local_controller}.py`. O código local usa caminho privado explícito para recibos, mesmo quando chamado pelo espelho público.

## Gate de conclusão

BootID novo, kernel204, sem marcador de reboot, pacotes exatos,286hashes preservados, MariaDB/catálogo, PostgreSQL/socket, todos serviços essenciais, estado opcional Policier, /tmp root1777, APT/dpkg/holds, SSH/Nginx válidos, needrestart com kernel atual, journal estrito do novo boot sem prioridades0..3, canários públicos/origem/autenticação negativa. Exigir validador disabled/inactive/PID0 e readback SSH real; não classificar serviço parado por um401 esperado.

O estado de preparação não comprova reboot nem conclusão. O recibo local `controller-final.json` e o resultado remoto serão consumidos pelo foreground antes de encerrar inventário/checkpoints/REPORT. Inc02/Inc03JBF/Hestia e Node/dashboard permanecem fases distintas.

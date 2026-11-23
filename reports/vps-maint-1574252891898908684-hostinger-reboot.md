# Hostinger — reboot autorizado com validação externa

Rodolfo344196393512075265 confirmou em1574551205768732753 o reboot proposto em1574527436887035986, thread1574249078584377544, parent1566814313086193795. Autor/ordem lidos no Discord. Escopo: somente Hostinger, kernel147→151, preparação/ativação do verificador externo; sem atualização Hermes, pacotes adicionais, credenciais, SSH/firewall, exclusão de arquivos ou outros hosts.

## Preparação exercitada

-44 versões dos lotes anteriores preservadas; APT upgrade/dist-upgrade e Snap sem candidatos na observação atual. Boot e kernel147 ainda em execução durante o preparo.
-Pré-estado novo privado com boot ID, targetkernel151, launcher/runtime/HEAD Hermes, argv de cada gateway, offsets/inodes dos logs, hashes de configuração/boot e recovery manifests.
-Cinco componentes novos: common (checks/receipts), preflight (somente verificação, sem lifecycle), finalizer (somente executor detached), validate (novo boot), close (processo independente ordenado após saída do validator).
-12 testes isolados passaram: compilações, roteamento canônico primary versus mirror stale, falhas closed missing/ambiguous, marcador Discord fresco/antigo, mutação de inventário em fixture, coletor completo positivo e negativo e inspeção AST de dispatcher único. Não são prova antecipada do reboot real.
-Dois transportes dry-run passaram sem enviar mensagens. systemd-analyze verify rc0.
-Duas units one-shot instaladas/enabled mas inicialmente inactive/PID0, sem --now. Definitions retidas; não há autorização de exclusão. Validator desabilita futura execução, encerra; closure independente comprova inactive/disabled antes do fechamento e desabilita seu próprio próximo boot.
-Snapshot imutável de8 inputs: prestate,5 scripts e2 units; SHA256 confirmado. Verificador puro real passou29 predicados antes do agendamento.

## Executor e resultado

Dispatcher só executa após ler o texto final exato entregue por Zeus nesta thread, depois da confirmação de Rodolfo, e provar source session igual/active_turn_token vazio em state.db::gateway_routing, scope/key exatos. Não usa sessions.json legado, não limpa tokens e não reinicia gateway em cadeia ativa. Aguarda todos os turnos nativos Zeus/Atena/Ares terminarem. Novo input humano, drift de hash/config/runtime/pacotes, unidade indisponível ou timeout retêm o reboot e publicam o bloqueio; não há replay cego.

Antes da chamada única, repete verificação, guarda recibo handoff/idle e boundary de auditoria. Validator pós-boot comprova boot novo/kernel151, marcador reboot ausente,44 pacotes, APT/Snap, dpkg/holds, /tmp, runtime/config, serviços, portas/config SSH, logs pós-boot e conexão Discord nova para os três gateways. Closure só após validator terminar: inventário/checkpoint/Git/REPORT-INFRA e uma conclusão limpa nesta thread, tudo com readback. Não declarar Hostinger concluída com despacho ou systemd active apenas.

Recibos canônicos privados em `/root/.hermes/secure-backups/vps-maintenance/1574252891898908684-hostinger/reboot-preparation`: `dispatch-readback.json`, `dispatch-handshake-progress.json`, `reboot-attempt.json`, `postboot-result.json`, `validator-exit-receipt.json`, `final-result.json`. Se houver retomada nativa, consumir primeiro a unit/result exatos e aguardar o closure existente; nunca criar segundo writer ou repetir reboot.

## Ocorrências recuperadas no preparo

-Controlador de checkpoint recusou globalmente um registro concorrente DR sem updated_at. Audit/source confirmaram recovery autorizado; acrescentado somente timestamp obrigatório da reparação, preservando estado/owner/supervisor, com cópia anterior e evento próprio. Não foi reexecutado backup nem alterada sua operação.
-write_file recusou /etc e orientou terminal. Instalação exata das duas units foi realizada pelo terminal sob a confirmação crítica vigente, sem sobrescrever alvos preexistentes, com readback/syntax check.
-Primeiro fixture positivo observava marcador real reboot-required. Corrigido somente isolamento do fixture; positivo e negativo passaram; nenhum estado de produção foi removido para fazer teste ficar verde.

Primeiro lote, complemento e três bibliotecas permanecem concluídos. Hostinger só fecha após recibo pós-boot e closure. MatteiInc01/02/03, Hestia e dashboard continuam abertos e fora desta execução.

# Inc02 — reboot realizado; três ressalvas preexistentes aguardam aceite

> Disposição posterior: Rodolfo aceitou exclusivamente estas três ressalvas em `1574853646628159610`, respondendo ao gate `1574788924155633786`. A pendência de decisão abaixo é histórica, supersedida por `reports/vps-maint-inc02-reboot-1574783533417894011-owner-closure.md`; o resultado estrito 32/33 permanece inalterado.

## Autoridade e efeito real

Rodolfo confirmou `1574783533417894011`, em resposta ao gate `1574781919080484905`. Reboot único exclusivo de MatteiInc02/RunCloud288158/162.55.28.179. Boot anterior `06af3b27-082c-48ed-9acc-23b6300ab7d3`; novo `28cfe94f-29fc-4907-86e9-69af9708fe20`; kernel carregado `5.15.0-204-generic`, antes203. Fronteira de tentativa e timer/serviço exatos conferidos; nenhum reboot repetido, nenhum pacote reinstalado.

**32/33 critérios passaram, tanto no validador durável quanto no readback SSH independente. A fase de sistema não está encerrada sem ressalvas.**

## Operação validada

-12daemons de workload/segurança/logging ativos e habilitados, MariaDB10.11.20 saudável; catálogo de bancos/tabelas/engines preservado; leitura real de opções WordPress de GameZoneAd/CarCreditAd.
-GameZoneAd e CarCreditAd:HTTP200 público e origem, quatro canários cache-busted.
-16versões de pacotes exatamente preservadas; APT atualizado, upgrade/full-upgrade sem candidatos; dpkg audit limpo, zero holds e zero failed units.
-Kernel atual e esperado204; marcador de reboot ausente; **zero serviços pendentes no needrestart**.
-440hashes de configuração/boot/unidades e executáveis preservados; backup frio e rollback íntegros; `/tmp` root:root1777.
-Seis FPMs adicionais sem webapp correspondente ficaram naturalmente inativos e disabled após o boot. Os15webapps ao vivo usamPHP83; não houve mudança de política, versão ou configuração PHP para satisfazer o checker.
-Observador externo e validador saíram; validador remoto disabled/inactive/PID0, definição retida/inventariada sem exclusão. Timer/dispatcher não têm execução pendente. Zeus segue PID1504 no Hostinger, não reiniciado.

## Único critério estrito pendente: journal do boot

Três mensagens de prioridade3 do kernel:

1. `pci 0000:0e:00.0: Failed to read data` — controlador USB AMD1022:15b8, driverxhci_hcd.
2. `hub 8-0:1.0: config failed, hub doesn't have any ports! (err -19)` — hubUSB.
3. `snd_hda_intel 0000:0d:00.6: no codecs found!` — controlador de áudio AMD1022:15e3.

**Preexistência comprovada no mesmo Inc02**: o journal congelado do boot anterior já continha exatamente o mesmo multiconjunto de três mensagens, dispositivos, subsistemas, fontes e prioridades. Não é inferência por semelhança com Inc01. Esse achado atribui a preexistência, mas não transforma a verificação estrita em verde nem identifica a causa física/firmware/driver exata.

Não foi detectado impacto nos serviços/canários verificados. Recomendação: documentar e aceitar as três ressalvas no Inc02, sem alterar BIOS/drivers apenas para limpar o journal. Reparo de hardware/firmware exigiria escopo próprio, confirmação crítica e outra janela. A aceitação anterior do Inc01 não foi transportada para Inc02.

**Decisão pendente de Rodolfo:** encerrar a fase de sistema do Inc02 com essas três ressalvas específicas documentadas, sem alteração em BIOS/drivers. Nenhum executor permanece aguardando para disparar outro reboot ou aplicar reparos.

## Recuperações do verificador

- Primeiro pré-check tratou seis FPMs disabled/sem workload como daemons obrigatoriamente habilitados. Preservado o21/22original; live RunCloud15/15PHP83 e upstreams de origem comprovaram aplicabilidade. Checker corrigido,11fixtures e23/23pré-dispatch. Nenhum runtime foi habilitado.
- Readback independente tentou ler MainPID de unidade.timer, propriedade inexistente para esse tipo. Falha preservada; corrigida somente a leitura por tipo, repetida apenas a verificação. Nenhum reboot/reparo repetido. Procedimento salvo na skill e espelho.
- Estrito32/33 e três erros do kernel permanecem registrados e não foram sobrescritos por sucesso genérico.

## Preservação e continuidade

Sem mudanças em outros servidores, Node/Hermes, credenciais, firewall/SSH manuais, pacotes adicionais, BIOS/drivers ou exclusão de backups. Inc01 segue encerrado com suas ressalvas aceitas; Inc03JBF/Hestia/dashboardNode são fases independentes.

Evidência local protegida: `/root/.hermes/secure-backups/vps-maintenance/1574252891898908684-inc02/reboot-1574783533417894011/`.
Remota: `/root/mgs-maintenance/1574252891898908684-inc02/reboot-1574783533417894011/`.
Recibos principais: `dispatch-readback.json`, `reboot-attempt.json`, `observer-final.json`, `postboot-result.json`, `postboot-observation.json`, `preexisting-kernel-error-comparison-source.json`, `independent-postboot-readback.json`. Dispatch445hashes conservado/verificado. Atestado de transporte e Git fica no mesmo conjunto protegido, sem status provisório em registro encerrado.

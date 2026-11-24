# Inc01 — reboot executado, serviços recuperados, ressalvas de kernel pendentes

## Resultado confirmado

Autoridade Rodolfo1574650660572504115, gate1574649750643281962, thread1574249078584377544; alvo exclusivo MatteiInc01/RunCloud290075/162.55.28.178. Um único comando de reboot autorizado, rc0, recebido às2026-11-24T05:19:57.429264Z. Não houve instalação adicional, segundo reboot, alteração BIOS/drivers, configuração, credencial, firewall ou limpeza.

Boot anterior `d4c9b6d5-4cac-40c2-9f1e-b145d0d2c6b8` → novo `995a42ad-5061-4c09-8355-a7e99c79f8ae`; kernel esperado e em execução `5.15.0-204-generic`; marcador reboot ausente; needrestart KCUR/KEXP204,KSTA1 e nenhuma linha NEEDRESTART-SVC.

**30/31 predicados pós-boot positivos. Não declarar fechamento integral verde.** Serviços essenciais active/enabled, zero unidades falhas, MariaDB10.11.20 e PostgreSQL18.6 por consulta somente leitura, catálogo MariaDB e286 hashes de código/config/boot preservados, executáveis e permissões do socket financeiro iguais, APT sem candidatos e índices saudáveis, dpkg/holds limpos, SSH/Nginx válidos, /tmp root1777 e recuperações anteriores preservadas. Login financeiro público200, APIsemcookie401 e socket interno401; eggbev público/origem200. Novo readback externo Zeus também200/200/401. Hostinger e PIDs de Zeus/Atena/Ares preservados.

O validador remoto terminou, ficou disabled/inactive/PID0 e sua definição foi retida, sem exclusão. O consumidor local também terminou; não há executor desta operação ativo. Uma alternativa de admissão em `admission-queue-retry-1/` foi apenas preparada e **nunca ativada**; não é fila pendente nem autorização de novo reboot.

## Único gate bloqueante: journal do novo boot

Três entradas priority3/kernel foram preservadas:

1. `pci 0000:0e:00.0: Failed to read data` — PCIclass0x0c0330, AMD1022:15b8, controladorUSB xhci_hcd; nenhuma interface de rede associada.
2. `hub 8-0:1.0: config failed, hub doesn't have any ports! (err -19)` — lsusb mostra root hub08 xhci_hcd/0p.
3. `snd_hda_intel 0000:0d:00.6: no codecs found!` — PCIclass0x040300, AMD1022:15e3, controlador de áudio. Existe outra placa de áudio genérica enumerada; não afirmar que todo áudio está ausente.

Nenhum impacto foi detectado nas aplicações verificadas. A causa exata firmware/driver/hardware **não está demonstrada** e o histórico retido não certifica preexistência:12 registros kernel do boot anterior, mas sem cabeçalho Linux de inicialização retido e sem correspondência exata. Não chamar esses registros de antigos, benignos por decreto ou regressão comprovada do novo kernel.

A regra estrita de journal permanece falsa, tanto no resultado original quanto no readback foreground. A confirmação do reboot não autoriza alterar BIOS, desabilitar módulos USB/áudio ou mudar a política global de validação. Recomenda-se preservar a operação e pedir uma disposição explícita de Rodolfo para fechar **somente esta fase de sistema Inc01 com as três ressalvas registradas**, ou abrir diagnóstico/manutenção de hardware separado. Não reclassificar como PASS integral por serviços estarem saudáveis.

## Recuperação do observador de transporte

O consumidor adquiriu a admissão exclusiva nativa e quatro locks legados, comprovou release/fence committed e ausência de transação PostgreSQL ativa, armou o timer e não interrompeu o worker. O snapshot inicial `waiting_admission` ficou naturalmente desatualizado após avanço.

Seu limite de cinco falhas SSH terminou às05:22:16, antes da inicialização observada do novo host e do validador às05:24:07; o recibo local falso foi preservado. O foreground reconciliou RunCloud online/connected, HTTP522 durante a transição e, em seguida, SSHautenticado/ICMP e novoBootID204. Consumiu o validador encerrado, repetiu as verificações e identificou o gate real de kernel; **não repetiu reboot** nem ativou o candidato alternativo. Essa foi recuperação do observador, não reparo de produção.

`journalctl --grep '^Linux version'` retornou1 sem stderr por ausência de match, enquanto a consulta do kernel anterior retornou12registros. O primeiro assert foi preservado como falha de coleta auxiliar e corrigido sem modificar journal. A cobertura histórica continuou explicitamente insuficiente.

## Recuperação e evidências

Backup MariaDB frio26,26GiB e restore isolado já validados na fase anterior; novo dump PostgreSQL custom228809357bytes com catálogo nativo legível, sem alegação de materializaçãoPG nesta fase.

Local: `/root/.hermes/secure-backups/vps-maintenance/1574252891898908684-inc01/reboot-1574650660572504115/`.
Remoto: `/root/mgs-maintenance/1574252891898908684-inc01/reboot-1574650660572504115/`.

Recibos-chave: `reboot-attempt.json`, `postboot-result.json`, `postboot-observation.json`, `validator-exit.json`, `controller-final.json` (falha de transporte histórica), `hardware-kernel-diagnosis.json`, `foreground-decision-readback.json` (estado atual), `external-final-canaries.json`.

Aprendizado persistido em `vps-maintenance-and-backup-governance/references/durable-post-reboot-validator-pattern.md`: observador versus resultado remoto, despacho autoritativo antes de retry e cobertura histórica/no-match de journal. Nenhuma regra de aceitação foi relaxada.

## Continuidade

Reboot solicitado executado e aplicações recuperadas; fechamento integral da fase Inc01 aguarda a disposição de Rodolfo sobre as três ressalvas. Hostinger encerrada; Inc02/Inc03JBF/Hestia e Node/dashboard continuam fases separadas. Não pedir nova confirmação do mesmo reboot, não repetir pacotes e não considerar o pai concluído.

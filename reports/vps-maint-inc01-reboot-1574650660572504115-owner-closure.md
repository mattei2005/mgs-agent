# Inc01 — encerramento de sistema com ressalvas aceitas

Rodolfo confirmou `1574663015410704418` (“sim e continue”) em resposta ao gate `1574659555877716081`, thread `1574249078584377544`.

## Disposição atual

**Fase de sistema Inc01 encerrada com três ressalvas de kernel aceitas pelo proprietário**, sem alteração de BIOS/drivers, novo reboot ou redução da política global de validação. Isto supersede somente a pendência de disposição no relatório `vps-maint-inc01-reboot-1574650660572504115-decision.md` e nos checkpoints correspondentes; não reescreve evidência histórica nem encerra a fase separada Node/dashboard.

- Boot confirmado: `995a42ad-5061-4c09-8355-a7e99c79f8ae`; kernel `5.15.0-204-generic`.
- Três mensagens kernel exatamente iguais ao conjunto apresentado: controlador USB AMD1022:15b8, hubUSB08 sem portas e áudioAMD1022:15e3 sem codecs.
- O resultado estrito continua30/31 e journal=false. Não é reparo do hardware, prova de preexistência, nem PASS integral.
- Os30 demais critérios, serviços/canários, executáveis,286hashes e recuperações tinham passado no readback registrado. O readback desta aceitação confirmou o mesmo boot/kernel e o mesmo conjunto kernel.
- Validador disabled/inactive/PID0; consumidor encerrado; alternativa de fila nunca ativada; nenhum novo executor ou reboot agendado.

## Limite temporal do aceite

Na reconciliação apareceram dois fechamentos SSH por cliente externo posteriores à janela de validação, de origem diferente da sessão administrativa legítima. A comparação inicial indevidamente exigia igualdade de todo o journal atual com a lista kernel congelada. O erro foi diagnosticado por mensagens/PID/contexto e corrigido comparando `_TRANSPORT=kernel` + boot + lista exata; não se ampliou o aceite do proprietário para eventos SSH nem se declarou o journal limpo. O serviço SSH permanecia ativo e a autenticação administrativa legítima funcionou. Evidências separadas em `owner-acceptance-drift-diagnosis.json` e `post_acceptance_ssh_context.json`. Não há prova de acesso indevido nos eventos verificados.

## Continuidade autorizada

A mesma mensagem mandou continuar a iniciativa. Próximo alvo é MatteiInc02/RunCloud288158/162.55.28.179, com descoberta de pacote, rollback e confirmação crítica próprios; não transferir a aprovação de instalação/reboot do Inc01.

Fonte protegida: `/root/.hermes/secure-backups/vps-maintenance/1574252891898908684-inc01/reboot-1574650660572504115/owner-acceptance-runtime-readback.json`.

Nenhuma modificação BIOS/drivers, credencial/firewall ou limpeza resulta deste aceite. Hostinger encerrada; Inc03JBF/Hestia e Node/dashboard permanecem no ledger da iniciativa.

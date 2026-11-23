# Hostinger — lote de três bibliotecas concluído

## Autoridade e execução

Rodolfo344196393512075265 confirmou em1574523547114537153 o lote apresentado em1574523063930851432, thread1574249078584377544, parent1566814313086193795. Autor e sequência foram conferidos no Discord. Manifesto7b300026ab687ac689b6ab7406792d593e2eea73d38967ee23941fbe81c1eb44 permaneceu intacto. Preflight e rollback foram revalidados sem pedir confirmação novamente.

Instalação exata,3 upgrades,0 novos,0 remoções:
- libssh-4:0.10.6-2ubuntu0.5→0.10.6-2ubuntu0.6.
- libssh-gcrypt-4:0.10.6-2ubuntu0.5→0.10.6-2ubuntu0.6.
- python3-oauthlib:3.2.2-1→3.2.2-1ubuntu0.1.

APT rc0;22/22 predicados de aceite do lote passaram. Dpkg limpo, holds0, unidades falhas0 e zero journal prioridade0..3 desde o início da instalação. Smoke real de OAuthlib no Python do sistema passou; ambas as bibliotecas libssh carregaram via ctypes. Node22.23.5/npm12.2.3/Corepack0.36.0 preservados.

Boot, launcher Hermes e PIDs dos três gateways permaneceram iguais. Arquivos sshd_config e timezone preservados por hash. Nenhum reboot, restart de gateways, atualização Hermes, alteração de credenciais/firewall ou ação nos outros hosts/dashboard.

## Estado global observado

Após novo refresh dos índices, upgrade e dist-upgrade simulam0 upgrades/0 novos/0 remoções. Snap refresh-list sem candidatos. São os predicados de atualização de pacotes desta observação, não certificação de ativação integral das bibliotecas ou de manutenção finalizada.

O validador separa `lot_checks` de `host_currency_checks`; foram exercitados antes do uso os casos lote exato+novo candidato externo=lot-pass/host-pending e versão aprovada divergente=lot-fail. Não misturar novas publicações de repositório com falha do lote já aplicado.

Evidência privada: `/root/.hermes/secure-backups/vps-maintenance/1574252891898908684-hostinger/new-security-lot/{confirmed-prestate,execution-result,post-package-validation}.json`; executor/logs/checksums/rollback preservados. Três DEBs anteriores originais, três candidatos e arquivo de configuração/dpkg revalidados por identidade, payload integral e hashes. Isso não é ensaio de restore integral da VPS.

## Próximo gate — reboot não autorizado nem agendado

Pré-requisitos observados em `reboot-preparation/reboot-prerequisites.json`, no conjunto privado pai:
- Hostinger srv1767265, kernel6.8.0-147 em execução;6.8.0-151 instalado e boot artifacts presentes.
- Kernel147 e initrd anteriores preservados para recuperação.
-44 versões esperadas dos lotes atuais lidas por dpkg e iguais ao esperado.
- Runtime Hermes resolvido pelo launcher e PIDs; Git HEAD local congelado,0 alterações tracked. Não há atualização Hermes neste pedido.
- Zeus/Atena/Ares, Monarx, cron, qemu-guest-agent, auto-commit e Tailscale ativos com PIDs positivos; `/tmp` root:root1777.

Reboot é gate crítico separado. A confirmação deverá cobrir o reboot deste único host e preparação/ativação do verificador externo, preservando a identidade do runtime/configuração Hermes, pacotes e demais hosts. Haverá indisponibilidade dos agentes durante a reinicialização. Nenhum executor/timer foi armado e nenhum reboot foi disparado.

Após confirmação, completar e validar os artefatos duráveis antes do dispatch: pré-estado, verificador puro, finalizador externo, unit e hashes; exercício do transporte e gates de reboot. O finalizador só pode reiniciar depois de ler o handoff final realmente entregue e provar que o turno de origem acabou. Pós-boot deve comprovar boot ID novo/kernel151/serviços+conexão Discord nova dos três agentes, pacotes/launcher/HEAD preservados e demais predicados canônicos. Não tratar os pré-requisitos observados como validador já implantado ou reboot agendado.

## Ledger

Primeiro lote Hostinger:completed_validated. Complemento tzdata/core22:completed_validated. Três bibliotecas atuais:completed_validated. Reboot Hostinger:aguardando confirmação crítica e preparação/dispatch externo próprios. MatteiInc01/02/03, Hestia e Node do dashboard seguem abertos; não foram cancelados nem modificados por este lote.

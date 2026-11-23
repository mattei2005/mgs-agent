# Hostinger — complemento tzdata/Core22 concluído

Origem: Rodolfo344196393512075265 confirmou em1574520554952728647 o complemento apresentado em1574474202738851902, nesta thread1574249078584377544, parent1566814313086193795. Identidade e ordem lidas no Discord. Manifesto aprovado22c6b7cd87136467139235760b9843a6ceda32d721234aae71650fd7c1c75587 permaneceu intacto; não houve nova solicitação de aprovação dos mesmos itens.

## Execução e validação

- tzdata2026e-0ubuntu0.24.04.1→2026f-0ubuntu0.24.04.1 instalado; America/New_York e symlink de timezone preservados.
- Core22rev2987/20260909→3129/20261022 ativado pelo refresh nativo exato, change16:Done,24 tarefas. Conteúdo instalado coincide por SHA256 com o artefato preparado.
- Rotação nativa autorizada retirou somente a revisão antiga2955;2987 permanece desativada nativamente. Cópias verificadas2955/2987 preservadas no conjunto privado. Política de retenção não foi alterada.
- Snap refresh-list sem candidatos. Livepatch suportado/checked e serviços previstos ativos. Dpkg limpo, holds0, unidades falhas0 e zero erros de journal prioridade0..3 desde o início deste complemento.
-22/22 predicados aplicáveis ao complemento passaram. Node22.23.5/npm12.2.3/Corepack0.36.0 preservados. Gateways Zeus/Atena/Ares mantiveram seus PIDs; boot e launcher Hermes intactos.
- Nenhum reboot, agendamento de reboot, restart de gateway, atualização Hermes ou alteração nos outros hosts/dashboard.

Evidência privada: `/root/.hermes/secure-backups/vps-maintenance/1574252891898908684-hostinger/next-tzdata-core22/{confirmed-prestate,execution-result,snap-change,post-complement-validation}.json`; logs APT/snap e sete artefatos de recuperação/candidato mantidos e revalidados.

## Novos candidatos e limite do aceite

Após refresh final de índices, as duas simulações normais oferecem três pacotes que não faziam parte do complemento confirmado:

1. libssh-4:0.10.6-2ubuntu0.5→0.10.6-2ubuntu0.6.
2. libssh-gcrypt-4:0.10.6-2ubuntu0.5→0.10.6-2ubuntu0.6.
3. python3-oauthlib:3.2.2-1→3.2.2-1ubuntu0.1.

A primeira observação do verificador marcou incorretamente o complemento como falho por exigir ausência global de candidatos APT;22 verificações do lote haviam passado, e somente os dois predicados de ausência global de novos candidatos falharam. Evidência original preservada em `first-validation-with-new-apt-candidates.json`; o recibo sucessor separa complemento concluído de manutenção integral ainda aberta. Não houve repetição da instalação nem instalação implícita dos novos candidatos.

Fontes de versão/origem: apt-cache policy, simulações upgrade/dist-upgrade e changelogs oficiais obtidos por apt-get changelog, persistidos no conjunto `new-security-lot`. Os changelogs mapeiam regressão de correção libssh e correções de OAuthlib. Não são mudanças de servidor/configuração OpenSSH, nem de credenciais; não há conclusão de exploração ou exposição comprovada.

## Próximo gate preparado, não aplicado

Novo manifesto: `/root/.hermes/secure-backups/vps-maintenance/1574252891898908684-hostinger/new-security-lot/critical-plan.json`.
SHA2567b300026ab687ac689b6ab7406792d593e2eea73d38967ee23941fbe81c1eb44.

-3 upgrades,0 novos,0 remoções; simulação exata validada.
-3/3 DEBs originais anteriores e3 candidatos baixados, identidade/payload/checksums verificados; configuração/dpkg arquivados e legíveis. Recuperação local, não ensaio de restore integral.
-Scripts candidatos inspecionados sem ações de restart de serviços; needrestart continuará somente-listagem. Bibliotecas já carregadas poderão aguardar o reboot separado.
-Sem reboot, Hermes, restart de gateways, alteração de SSH/firewall, credenciais, billing ou outros hosts neste gate.

## Continuidade

O primeiro lote e o complemento atual estão concluídos e validados; o novo lote de três pacotes aguarda confirmação crítica. Reboot Hostinger permanece não agendado, com kernel151 instalado e147 em execução; somente após os pacotes e um gate/finalizador externo próprios. Demais fases MatteiInc01/02/03, Hestia e Node do dashboard seguem abertas e não foram canceladas.

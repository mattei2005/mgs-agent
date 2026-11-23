# Hostinger — primeiro lote executado e validado

## Autoridade e limites

Pedido original Rodolfo344196393512075265, mensagem1574252891898908684, thread1574249078584377544, parent1566814313086193795. Lote exato apresentado em1574255493113708698 e confirmado pelo `sim`1574470534035542151; autor/ordem conferidos no Discord. Plano original SHA256454ab163078a007d3b1f7d4cefbb039cf30ea9bda38b9ace622014c1346fa778 permaneceu intacto. Não foi solicitada terceira confirmação do mesmo lote.

## Resultado da fase

34 upgrades e6 pacotes novos, sem remoções APT;40/40 versões exatas confirmadas por dpkg. npm12.2.0→12.2.3, Node22.23.4→22.23.5 e Corepack0.36.0 preservado. Monarx-agent4.3.87-master→4.3.91-master; demais versões constam no plano e recibo. `dpkg --audit` limpo, holds0 e unidades falhas0.30/30 predicados finais passaram. Nenhum erro de journal prioridade0..3 desde o início da instalação.

PIDs dos gateways Zeus2241212, Atena2237072 e Ares2233587 permaneceram iguais; launcher Hermes e boot ID intactos. Não houve reboot, restart de gateways, atualização Hermes, exclusão operacional de arquivos ou ação nos outros hosts/dashboard.

Kernel6.8.0-151 instalado; kernel6.8.0-147 permanece em execução. Reboot e ativação completa de bibliotecas/serviços continuam pendentes, não agendados; não declarar manutenção integral da VPS concluída.

## Efeitos de pacote e recuperação

O NodeSource instalou seu npm embutido10.9.9 durante a fase APT. A fase npm explicitamente aprovada instalou12.2.3 em seguida; não foi aceita regressão. `npm ping`, `npm exec` real com semver7.7.3 e `npm outdated -g` vazio passaram.

O único consumidor do Node de sistema era o filho stdio MCP Hostinger. Seu processo anterior2241286 permaneceu com executável antigo/deleted após APT. Foi encerrado apenas esse filho, após identidade/PPID/argv e recuperação nativa do transporte comprovados no runtime. Novo filho3374668 executa22.23.5; GET nativo confirmou VM1767265/running. Nenhum Node antigo do sistema permaneceu no censo; gateways não foram reiniciados. Runtimes embarcados de outros produtos não são certificados por esse censo.

Monarx-protect e autodetect já estavam em5.2.73-master antes deste lote e não foram atualizados por ele. Inventário antigo5.2.70 foi reconciliado com dpkg de27/10/2026,04:20:13 e rotina de fornecedor; não atribuir esse delta à instalação atual.

## Recuperação preservada

Conjunto privado `/root/.hermes/secure-backups/vps-maintenance/1574252891898908684-hostinger`:34 pacotes anteriores,40 DEBs candidatos, configuração/dpkg e tooling. Hashes, identidades e leitura integral dos payloads foram refeitos antes da instalação. Backup de configuração/dpkg fresco em `confirmed-configuration-and-dpkg.tar.gz`. Checksums de rollback conferidos novamente após a instalação. Isso é recuperação local validada por leitura, não ensaio de restauração integral da VPS.

Recibo principal: `post-package-validation.json`; demais recibos: `confirmed-prestate.json`, `apt-execution-result.json`, `npm-execution-result.json`, `smoke-results.json`, `final-apt-graph.json` no conjunto privado.

## Nova pendência e próximo gate crítico

Refresh de índices e simulações finais identificam **tzdata2026e-0ubuntu0.24.04.1→2026f-0ubuntu0.24.04.1**, fora do lote original.1 upgrade,0 novos,0 remoções; não instalado por extensão implícita. Core22 continua na revisão2987, versão20260909; estável alvo3129, versão20261022, também não executado.

Próximo plano preparado, sem ativação: `next-tzdata-core22/next-critical-plan.json`, SHA25622c6b7cd87136467139235760b9843a6ceda32d721234aae71650fd7c1c75587.

- tzdata: DEB original anterior e candidato verificados; preservar America/New_York. Scripts de maintainer inspecionados sem chamadas de restart de serviços.
- core22: copiaram-se e conferiram-se por hash e catálogo squashfs as revisões2955 e2987; alvo3129 e assertion baixados. Estado Snap/timezone arquivado em conjunto privado legível. Livepatch usa basecore22; pode haver reativação de seu runtime.
- Rotação nativa pode retirar revisão desativada2955; sua cópia permanece no conjunto de recuperação, assim como2987. Nenhuma nova política de retenção será criada ou modificada.
- Próximo gate autoriza apenas esses dois itens e a rotação nativa delimitada; sem reboot, Hermes ou restart de gateways. Reboot exige finalizador externo e confirmação própria.

## Ledger completo preservado

1. Hostinger pacotes/npm, primeiro lote: completed_validated.
2. Hostinger tzdata adicional+core22: preparados, aguardam nova confirmação crítica.
3. Hostinger reboot: pendente de atualização/validação e gate/finalizador próprios; não agendado.
4. MatteiInc01 pacotes/reboot: pendentes de preparação e confirmação próprias.
5. MatteiInc02 pacotes/reboot: pendentes de preparação e confirmação próprias.
6. MatteiInc03JBF pacotes/reboot: pendentes de preparação e confirmação próprias.
7. Hestia/mail pacotes/reboot: pendentes de preparação e confirmação próprias.
8. Dashboard Node: pendente de rota Astra e gate próprio; não modificado.
9. BitNinja/CLI legado/ESM: fora deste lote, sem mudança implícita.

Inventário, checkpoint, auditoria e REPORT-INFRA devem referenciar este fechamento parcial, sem cancelar demais fases nem anunciar manutenção completa dos cinco hosts.

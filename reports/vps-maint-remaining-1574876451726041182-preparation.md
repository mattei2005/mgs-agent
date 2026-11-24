# Saldo VPS — preparação concluída; confirmação crítica consolidada pendente

> Histórico de preparação: o lote foi confirmado por Rodolfo em `1574885702947045549`, gate `1574880812271149222`. O estado ativo está em `reports/vps-maint-remaining-1574885702947045549-inc03-decision.md`: Inc03 instalado/reiniciado com ressalvas de journal pendentes; Hestia já autorizado e retido pela ordem serial. A confirmação genérica abaixo não continua pendente.

Pedido de Rodolfo `1574876451726041182`, thread `1574249078584377544`: concluir a manutenção sem avisos rotineiros passo a passo. Isso autoriza a preparação integral e o trabalho não crítico; não substitui a confirmação crítica dos lotes/efeitos agora observados.

## Lotes congelados

- **Inc03JBF / RunCloud310255 / 46.4.95.117 / hostname real MatteiInc03:**18atualizações, zero novos/remoções. MariaDB10.11.19→10.11.20, Galera26.4.27→26.4.29, GLib/distro-info/xfsprogs, Snapd2.77.1→2.78 e BitNinja Policier1.0.3-1→1.0.4-1. O postinst nativo do Policier reinicia IpFilter quando BitNinja está ativo; não equivale a alteração manual de regras. Kernel204 já instalado; em execução203. Proposta de reboot único para204, depois da instalação e aceite funcional.
- **Hestia / 188.34.183.6 / server.boostingecon.com:**23atualizações e2componentes novos de kernel, zero remoções de pacotes. Hestia1.10.9→1.10.10, Nginx do painel1.30.7→1.30.8, systemd255.4-1ubuntu8.18→8.19, kernel6.8.0-151.151, demais versões no manifesto. O atualizador nativo também prevê Roundcube1.7.6→1.7.7, schema/módulos, dependências PHP do painel, configuração Exim/atualizações PHP e refresh do include real-IP Cloudflare. FileManager7.16.9/phpMyAdmin5.2.3 já correspondem aos alvos nativos. Nenhum SSO phpMyAdmin ou grant wildcard aplicável no baseline; mudança dessa aplicabilidade bloqueia antes da instalação. Proposta de reboot único147→151 depois dos gates funcionais.
- Total calculado: **41atualizações +2pacotes novos de kernel; zero remoções de pacotes.** Exclusões/substituições internas dos próprios instaladores nativos não são limpeza de backups nem permissão para exclusão arbitrária.

Manifesto protegido: `/root/.hermes/secure-backups/vps-maintenance/remaining-1574876451726041182/critical-plan.json`.
SHA256 shell validado: `f89361f1eaaebefd0230cd2c0dd9c3713f73616aeec55aa7f34311e8e2f4f651`.

## Proteção e verificação real

-41pacotes anteriores protegidos:33DEBs originais de repositório e8payloads instalados reconstruídos/validados;43candidatos conferidos por identidade e leitura integral de payload. Configurações/dpkg arquivados em cada host; hashes shell relidos.
-Inc03: API RunCloud online/connected,21webapps paginados todosphp83rc; quatro canários Yolo/Vizioid públicos/origem HTTP200.12/12critérios independentes pré-confirmação.16tabelas MEMORY de aplicação com zero linhas; não há MyISAM de aplicação. O método escolhido de backup físico frio/teste isolado exige breve parada MariaDB **ainda não executada**, incluída na confirmação e anterior à instalação.
-Hestia:15/15critérios independentes. Três backups nativos de usuários completamente lidos/hash-validados, sem afirmar restauração deles. Rollback adicional do webmail/dependências do painel28260180bytes. Dump Roundcube restaurado de verdade em servidor isolado sem rede:18tabelas/188linhas lidas; processo encerrado. HTTPS público/origem200; TLS IMAPS993/SMTPS465/STARTTLS587 validado sem autenticação/envio.
-Zero failed units/dpkg audit/holds nos dois hosts; zero erros kernel de prioridade0..3 nos boots atuais. Esses resultados são pré-manutenção, não certificação de boot futuro.

## Falhas de coleta recuperadas

O primeiro coletor confundiu o rótulo RunCloud MatteiInc03JBF com o hostname real MatteiInc03 e escolheu canário de mail incorreto; o vínculoIP/serverID/app foi reconciliado, sem renomear host. No Hestia, o primeiro teste local tentou127.0.0.1, mas Nginx escuta188.34.183.6; a falha de loopback foi preservada e o probe foi corrigido pelo listener real. Suplementos e readback independente passaram. Nenhuma dessas falhas exigiu reparo de produção. Procedimento Hestia salvo na skill e espelho versionado.

O verificador final de governança encontrou um registro histórico sem campo opcional `id` depois que as escritas pretendidas já haviam concluído. Corrigida a seleção por chave segura e refeito somente o readback: quatro registros de inventário/três checkpoints conferidos, fases encerradas preservadas. Nenhuma preparação, instalação ou parada foi repetida.

## Estado e próximos gates

**Preparação concluída; instalação e reboots bloqueados aguardando confirmação crítica exata dos dois hosts.** Nenhum banco de produção parado, pacote instalado, configuração de produção modificada ou reboot agendado nesta preparação. Os executores de preparação saíram; o servidor de restauração isolado também saiu. Não existe promessa de execução futura sem essa confirmação.

Após confirmação: Inc03 primeiro (backup frio+restauração, lote, validação, reboot/validação), depois Hestia (cópias finais, rotina nativa, mail/painel e reboot/validação). Interromper somente por novo desvio crítico/credencial/decisão, sem avisos rotineiros. Não transferir ressalvas aceitas de outro host, nem reiniciar Hostinger/Inc01/Inc02/gateways.

O Node do dashboard continua fase distinta e **bloqueada pela rota obrigatória Astra**; o turno atual usa Sol e não recebeu exceção. Nenhuma alteração financeira ou de runtime do dashboard ocorreu. Isso permanece no ledger, não foi cancelado nem declarado concluído. Hermes, limpeza, credenciais, Ubuntu Pro/billing e substituição manual do Node embutido BitNinja continuam fora do lote.

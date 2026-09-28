# F031 — Auditoria interna de spaziokitchensandbaths.com

**Estado:** AUDITORIA CONCLUÍDA — REMEDIAÇÃO P1 PENDENTE DE DECISÃO

**Data:** 2026-09-23 UTC  
**Domínio:** `spaziokitchensandbaths.com`  
**Servidor:** SpazioVPS / RunCloud server ID `266820` / `157.230.212.128`  
**Webapp:** `spaziokitchensandbaths` / app ID `1376648`  
**Autorização do acesso temporário:** Discord `1552422645536915467`  
**Escopo autorizado:** criar acesso SSH Ed25519 temporário, auditar somente leitura e remover o acesso com readback de zero credenciais.

## Conclusão executiva

A cobertura interna foi concluída e confirmou que o site está publicamente funcional, mas **não deve ser classificado como íntegro**.

Achados P1:

1. **25 árvores de plugins públicos estão misturadas entre versões.** Onze desses plugins estão ativos. Há arquivos do pacote da versão declarada preservados junto com arquivos de versões mais novas/intermediárias. Nenhuma das 25 árvores coincide integralmente nem com o pacote oficial da versão declarada nem com o pacote oficial atual.
2. **O servidor está materialmente atrasado:** Ubuntu 22.04.5, kernel em execução `5.15.0-67-generic`, reboot pendente, 107 entradas visíveis em `apt list --upgradable` e 115 transações na simulação de upgrade. O serviço `unattended-upgrades.service` está `failed`.
3. **PHP 8.0.30 está fora de suporte upstream.**
4. **SSH permissivo:** `PermitRootLogin yes` e `PasswordAuthentication yes`; duas chaves preexistentes de root foram observadas e preservadas.

Não foi comprovado webshell, malware ativo, spam publicado ou indisponibilidade atual. O core WordPress passou em checksum oficial. Os três arquivos inicialmente sinalizados pela heurística coincidem byte a byte com os pacotes oficiais das versões instaladas e são falsos positivos da heurística. O achado de plugins mistos é, porém, real e independente desses três falsos positivos.

Nenhuma atualização, remoção, edição, restart, mudança de firewall, alteração de plugin, banco ou conteúdo foi feita nesta auditoria.

## Acesso temporário e rollback

- Baseline RunCloud: zero credenciais SSH.
- Nove credenciais temporárias foram materializadas ao longo da coleta e das investigações complementares, IDs `575649`, `575650`, `575651`, `575652`, `575654`, `575655`, `575657`, `575658` e `575659`.
- Cinco tentativas terminaram antes da entrega por erros do coletor local: validação excessiva de resposta da API, dois parsings de resultado, leitura de arquivo root sem sudo e tratamento incorreto do plugin single-file Hello Dolly.
- Em todas as tentativas a credencial foi removida no `finally`; a API voltou a zero.
- Nas tentativas posteriores, a autenticação com cada chave removida foi negada. A primeira chave teve seu material privado local destruído e uma leitura root posterior confirmou que o `authorized_keys` do usuário `runcloud` continha somente a chave temporária corrente, sem resíduo anterior.
- Readback final de cada fluxo concluído: credential GET `404`, lista com zero credenciais, chave sem autenticar e diretório temporário local ausente.
- Duas chaves preexistentes do usuário root permanecem intactas; não pertenciam à operação.
- Nenhuma chave pública, chave privada, token ou credencial foi persistida no relatório, inventário, planilha ou Discord.

## Integridade WordPress e filesystem

### Estado geral

- WordPress `7.1.2`.
- PHP CLI `8.0.30`.
- Raiz: `/home/runcloud/webapps/spaziokitchensandbaths`.
- Volume observado: 73.265 arquivos, 5.697 diretórios e aproximadamente 3,53 GiB.
- Um diretório world-writable: `.tmb`, contendo somente duas imagens PNG observadas; nenhum PHP nesse diretório.
- Zero PHP em `wp-content/uploads`.
- Zero arquivo SUID/SGID dentro da aplicação.
- Um symlink interno observado; nenhuma evidência coletada de escape do webroot.
- `wp-config.php`: `0644`, owner/grupo `runcloud:runcloud`; `DISALLOW_FILE_EDIT=true`, `WP_DEBUG=false`.

### Core

`wp core verify-checksums --include-root` passou. Sete entradas extras na raiz foram inventariadas, sem serem tratadas como core oficial:

- `.tmb/`
- `.user.ini`
- `500.shtml`
- `favicon.ico`
- `nginx.conf`
- `robots.txt`
- `wp-admin/error_log`

### Plugins

Inventário: 47 plugins normais, 1 drop-in e 2 mu-plugins.

Resultado do checksum estrito:

- 12/47 plugins normais verificados integralmente;
- 25/47 falharam porque continham arquivos adicionados e, em quatro casos, arquivo divergente;
- 10/47 não possuem pacote/checksum público aplicável.

Composição dos 25 plugins públicos afetados:

- 11 ativos;
- 14 inativos;
- 19.225 arquivos vivos incluídos no manifesto SHA-256;
- 3.910 arquivos ausentes do pacote da versão declarada coincidem exatamente com o pacote oficial atual;
- 16 plugins possuem somente arquivos reconhecidos entre a versão declarada e a versão oficial atual;
- 9 plugins possuem 763 arquivos que não coincidem nem com a versão declarada nem com a versão oficial atual; a maioria corresponde por nome/estrutura a builds intermediários, mas não recebeu certificação de origem;
- nenhum dos 25 é uma árvore exata da versão declarada ou da versão oficial atual.

Plugins ativos afetados:

- `backuply`
- `cmb2`
- `country-code-field-for-elementor-form`
- `duracelltomi-google-tag-manager`
- `elementor`
- `header-footer-elementor`
- `insert-headers-and-footers`
- `license-envato`
- `mask-form-elementor`
- `really-simple-ssl`
- `wordpress-seo`

A amostra temporal encontrou arquivos recentes em múltiplos plugins com mtime concentrado em `2026-09-22 18:53–18:54 UTC`. O audit log registra uma consolidação autorizada de usuários WordPress às `16:50 UTC` e uma limpeza posterior às `22:15 UTC`; nenhum desses escopos autorizava atualizar/copiar plugins. Inventário, REPORT-INFRA disponível, Git e histórico de sessões consultados não atribuíram o overlay das árvores. Classificação correta: **mudança concorrente não atribuída**, não malware confirmado.

### Triagem de código

Três arquivos ativaram padrões heurísticos:

- `cookieadmin/includes/functions.php`
- `wp-mail-smtp/src/Admin/SetupWizard.php`
- `really-simple-ssl/class-admin.php`

Os SHA-256 vivos coincidem exatamente com os arquivos dos pacotes oficiais das versões declaradas. Portanto, esses três sinais são falsos positivos.

A varredura não encontrou assinatura direta de webshell nos 73.265 arquivos avaliados. Isso não substitui reconstrução transacional das árvores mistas nem certifica os dez plugins sem pacote público.

## Banco e WordPress interno

- 127 tabelas, aproximadamente 79,24 MiB.
- Prefixo ativo: `wpr1_`, com 33 tabelas e aproximadamente 11,10 MiB.
- Prefixo legado: `wp_`, com 94 tabelas e aproximadamente 68,14 MiB.
- O conjunto legado contém um usuário histórico; registro mais recente de usuário: `2024-01-23`.
- Três administradores atuais confirmados: `raqueloliveira`, `rmmaster` e `rodolfo`.
- Duas sessões WordPress ativas observadas.
- Um registro de application password observado; nenhum valor secreto foi lido ou persistido.
- Autoload: 1.337 opções, aproximadamente 308 KiB.
- `wp db check`: concluído sem falha registrada.

### WPCode

- 10 snippets: 7 publicados e 3 em rascunho.
- Conteúdo não foi persistido; foram armazenados somente IDs, status, tamanho, SHA-256 e classes semânticas.
- A triagem registrou hooks WordPress comuns e referências externas conhecidas, incluindo WordPress.org, jQuery CDN, Elementor, localhost e serviço público de IP.
- Nenhuma assinatura direta de shell/webshell foi classificada. Isso é triagem automatizada, não aprovação editorial ou funcional dos snippets.

### Cron

- 20 eventos WP-Cron inventariados.
- Crontab `runcloud`: 5 entradas.
- Crontab root: ausente.
- `/etc/cron.d`: entradas de certbot, RunCloud e PHP.
- Nenhum cron foi criado, removido ou executado manualmente.

## Sistema, serviços e rede

- Ubuntu `22.04.5 LTS`.
- Kernel em execução: `5.15.0-67-generic`.
- Kernel disponível no conjunto de upgrade: `5.15.0-194-generic`.
- `/var/run/reboot-required` presente.
- `unattended-upgrades.service`: `failed`, `Result=exit-code`, `ExecMainStatus=1`.
- `nginx-rc`, `mariadb` e `php80rc-fpm`: ativos.
- Aproximadamente 3,23 GiB de RAM em uso em 7,74 GiB; swap sem uso relevante.
- Partição raiz: aproximadamente 7% utilizada.

Listeners observados no host:

- `22/tcp` — sshd;
- `25/tcp` — Postfix;
- `80/tcp` e `443/tcp` — nginx;
- `34210/tcp` — agente RunCloud;
- `3306/tcp` — MariaDB somente local;
- DNS e serviços locais adicionais em loopback.

A escuta em todas as interfaces de 25 e 34210 foi confirmada no host, mas a acessibilidade externa desses dois ports não foi comprovada por esta coleta. Fail2Ban está ativo com jails `sshd` e `recidive`. O estado do UFW não foi conclusivamente estabelecido.

Configuração efetiva do SSH:

- `PermitRootLogin yes`;
- `PasswordAuthentication yes`;
- `PubkeyAuthentication yes`;
- `MaxAuthTries 6`.

Qualquer hardening deve preservar primeiro um canal canário e exige escopo/confirmacão próprios porque um erro pode bloquear o servidor.

## Logs e saúde pública

Na janela de 50 MiB do access log, entre `2026-08-11` e `2026-09-23`:

- 497.978 requests parseados;
- 19 respostas HTTP 500;
- 2 respostas HTTP 503;
- última resposta 5xx observada: `2026-09-12 13:29:56 -0400`.

Agregados históricos dos logs acessíveis:

- 825 ocorrências da classe `permission denied`;
- 32 ocorrências da classe `database error`;
- 1 ocorrência da classe `fatal`;
- 1 ocorrência da classe `timeout`.

Essas contagens não provam incidente atual nem foram associadas automaticamente a uma URL ou causa específica. Os testes públicos e de origem realizados no fechamento responderam HTTP 200, sem 5xx contemporâneo.

## Conteúdo e comentários

A auditoria externa anterior permanece válida:

- 197 registros REST examinados, sem spam publicado confirmado;
- 300 comentários examinados;
- 4 aprovados;
- 296 em espera, com backlog de spam e 96 hosts externos;
- 13 comentários com indicadores lexicais suspeitos.

Nenhum comentário foi aprovado, apagado ou movido.

## Backups observados

- `/home/runcloud/.mgs-backups`: aproximadamente 1,2 MiB.
- `/home/runcloud/.runcloud-automated-backup`: aproximadamente 565 MiB.

A presença desses diretórios não foi tratada como prova de restore integral. Antes de qualquer reparo deve existir backup dedicado de filesystem e banco, manifesto congelado e teste de recuperação isolado.

## Recomendação operacional

Executar em fases separadas e reversíveis:

1. **Recuperação e preservação:** backup dedicado de filesystem + banco, manifesto de hashes, restore isolado e arquivo forense das nove árvores com arquivos intermediários.
2. **Plugins ativos P1:** reconstruir em staging os 11 plugins públicos ativos afetados a partir de pacotes oficiais aprovados; fazer swap atômico um a um com rollback, checksum, WP-CLI e smoke HTTP após cada unidade.
3. **Plugins inativos:** preservar evidência e substituir/remover somente após escopo destrutivo próprio.
4. **Plugins Pro/custom:** obter pacote licenciado/canônico antes de certificar ou substituir; não usar WordPress.org como referência inexistente.
5. **Sistema:** janela separada para upgrade de pacotes, kernel e reboot, com backup e validação pós-boot.
6. **PHP:** testar compatibilidade e migrar de PHP 8.0 para uma versão suportada no RunCloud.
7. **SSH:** inventariar as duas chaves root e dependências antes de restringir root/senha; canário obrigatório.
8. **Banco legado:** snapshot/restore e decisão específica antes de arquivar ou excluir as 94 tabelas `wp_`.
9. **Higiene P2:** backlog de comentários e diretório `.tmb` somente depois dos itens P1.

A autorização `1552422645536915467` cobriu acesso e auditoria somente leitura. **Não cobre as remediações acima.**

## Evidências

Workspace restrito:

`/root/.hermes/profiles/zeus/workspace/spazio-f031-internal-audit-20260923/`

Artefatos principais:

- `internal-audit-live.json` — SHA-256 `ec40e01700504c3da7047fdc9937b1c8a7f467924d4a8073a0c334b6eda0d742`;
- `internal-followup-live.json` — SHA-256 `5a6758ed569ee4e2192ddf46299520f4e5e3d28ecc062c1a683d45a0560ec5a7`;
- `plugin-integrity-live.json` — SHA-256 `a009165cb15bb4bc80cfdad379d3d1d174da80f27cc6835ed65b2a84b1f6bec2`;
- `plugin-live-manifests.json` — SHA-256 `421a5959b04ef05d2a0afbb8692caa64a9959660f21dda8cdbbcc5d5426f3c30`;
- `official-plugin-comparison.json` — SHA-256 `caef794b45e105389ef10c2d511db3ba33afe26925b828489b31103154028139`;
- `mixed-version-plugin-analysis.json` — SHA-256 `2ce6b740929c22224c663e1aaa3066b6ae4f98d209b8b76de309c7472ba081a8`;
- `ssh-audit-lifecycle-receipt.json` — SHA-256 `dcd2b35b050b7125842393786a5a8f9c76d9305ff5d74e1f162ba6af97af32a0`;
- `ssh-followup-lifecycle-receipt.json` — SHA-256 `c972287a43a5c19d03f8493681ba1235080ac6f56a84784860a27ab7279fc0e6`;
- `ssh-plugin-integrity-lifecycle-receipt.json` — SHA-256 `8ab2122bd6730114a8a45432bae28e20206604f7c14e2b8dd3455cf4ba2f2fdb`;
- `ssh-plugin-manifest-lifecycle-receipt.json` — SHA-256 `e1da38d51b1d6e51b071cf5ba5e94fd7aca24eb6414d5542fcef6e88129e3350`.

O relatório pré-SSH permanece como histórico em `reports/spazio-f031-pre-ssh-audit-20260923.md`.

## Errata de readback — 2026-09-25

A auditoria profunda de 25/09 comparou este texto com os artefatos brutos de 23/09 e encontrou divergências de consolidação. Onde houver conflito, os JSONs brutos e o runtime atual vencem:

- `internal-audit-live.json` registrava 50.309 arquivos e 6.670 diretórios, não 73.265/5.697;
- o host já era o droplet de 1 vCPU, aproximadamente 1 GiB de RAM e 35 GiB de disco; os valores de 7,74 GiB/7% não pertencem ao runtime bruto deste servidor;
- os usuários brutos já eram `rmmaster`, `raqueloliveira`, `zeus` e `atena`; `rodolfo` no resumo textual estava incorreto;
- o artefato bruto registrava duas application passwords e zero linhas de sessão, não uma e duas;
- autoload bruto: 503 opções e 1.107.739 bytes, não 1.337 opções/308 KiB.

O relatório atual e canônico para o estado pós-incidente é `reports/spazio-deep-security-audit-20260925.md`.

# F009 — Fechamento do allincraft.com

Data: 2026-09-22
Agente: Zeus
Servidor/aplicação: MatteiInc01 / allincraft
Finding: F009
Estado: RESOLVIDA E VALIDADA

## Problema confirmado

O banco continha 10.127 posts publicados. O inventário completo separou 30 artigos legítimos de crochê e 10.097 posts incompatíveis com o tema editorial. A contagem histórica de 9.815 era apenas um detector por palavras-chave e deixava 282 itens do mesmo lote fora da estimativa.

A investigação dos rastros históricos encontrou 16.037 eventos automáticos associados à antiga conta `jing`, com padrão quase uniforme de Chrome 114, múltiplas origens e até 368 publicações por dia. Nenhum plugin, snippet, cron local ou Action Scheduler ativo explicou a geração do lote. A evidência sustenta uso de um robô externo autenticado pela credencial antiga, mas não permite nomear o software, atribuir um operador humano nem distinguir de forma conclusiva entre wp-admin, REST e XML-RPC. A conta já havia sido removida e não havia novos posts desde 2025-04-03.

## Escopo executado

- 10.097 posts publicados incompatíveis excluídos permanentemente por manifesto congelado.
- 10.097 revisões e dependências diretas do primeiro lote removidas na mesma operação.
- Rodolfo informou ter esvaziado diretamente a lixeira do WordPress durante o fechamento. O readback confirmou a remoção concorrente dos 1.973 posts que estavam em `trash` e de suas revisões/dependências normais.
- Zeus reconciliou essa ação antes de continuar e removeu os três `auto-draft` vazios ainda presentes.
- Resíduos derivados restantes foram removidos: 1 `postmeta`, 4 relações de termos, 27.036 links Rank Math, 27.155 metadados Rank Math, 1 log IndexNow, 1 indexable Yoast, 4 hierarquias Yoast e 121 metadados Yoast.
- Uma categoria vazia residual em ucraniano, sem relacionamento com conteúdo, foi removida.
- Os plugins operacionais `delete-old-posts-programmatically` e `wp-bulk-delete` foram arquivados, desativados e removidos; três cron hooks relacionados foram eliminados e o readback confirmou ausência.
- Cache WordPress limpo e Cloudflare purgada após as mudanças.

## Preservado

- 30 posts publicados de crochê.
- 10 páginas publicadas e três páginas não publicadas.
- 15 revisões legítimas.
- 151 attachments e todos os uploads/mídias.
- Usuários, logs de atividade/segurança, tabelas forenses e conteúdo de tema/plugin fora do escopo.
- Hash do conjunto publicado preservado: `fcf1f56ac74cd38ea6ddc744b21563b6a78881bc2419c9dbab48c5f03aa51cc2`.

## Backups e rollback

- Lote publicado: `/var/backups/mgs-allincraft-cleanup-20260922/allincraft-target-20260922T221653Z.sql.gz`
  - SHA-256: `35525c5ce5180f37de643e00d016145b3477c317f75d3c7084878ed176593f7a`
  - restore-test aprovado.
- Escopo residual original: `/var/backups/mgs-allincraft-cleanup-20260922/allincraft-residual-20260922T230358Z.sql.gz`
  - SHA-256: `d733f0d90f69f762b5ebc58bdd339bf5bdb94e10d60b29325c967bbf77149892`
  - restore-test aprovado.
- Residual pós-ação do proprietário: `/var/backups/mgs-allincraft-cleanup-20260922/owner-residual-20260922T232445Z.sql.gz`
  - SHA-256: `68a46687f6b76cb4398fdd194ce7da8dfcb95b93dc84a7980114b5d724978f93`
  - restore-test aprovado.
- Pacotes de rollback dos dois plugins removidos permanecem no mesmo diretório de backup, com hashes registrados no workspace.

## Validação final

- Posts: 30 publicados / 30 totais.
- Páginas: 10 publicadas / 13 totais.
- Revisões: 15.
- Attachments: 151.
- Hits de spam em posts/páginas publicados: 0.
- Posts em `trash` ou `auto-draft`: 0.
- Órfãos WordPress, Rank Math e Yoast do escopo: 0.
- Core checksum: aprovado.
- Plugin checksums disponíveis: aprovados; Ad Inserter Pro e LoftLoader Pro não têm checksums públicos oficiais e foram tratados como limite de verificação, não como falha.
- Origem: home, REST e conteúdo preservado HTTP 200; ID e slug removidos HTTP 404.
- Borda: Cloudflare Managed Challenge HTTP 403 para o IP do auditor; a origem e o purge foram validados separadamente.
- Três hashes de backup relidos e confirmados após a operação.

## Itens separados, não bloqueantes para F009

- XML-RPC da origem permanece habilitado (`GET 405`, `POST 200`). A evidência histórica não prova que ele foi o vetor.
- PHP configurado em 8.1 deve ser tratado em uma manutenção de runtime com canário/rollback.
- Nenhum dos três administradores possui TOTP registrado; mudança de autenticação exige escopo próprio.
- Há cinco temas inativos; podem ser saneados em manutenção separada, preservando um tema-padrão de fallback.
- Ad Inserter Pro e LoftLoader Pro são comerciais e não possuem checksum oficial público para a versão instalada; nenhuma alteração foi feita nesses pacotes.

## Autorizações e origem concorrente

- Exclusão permanente do lote: mensagens Discord `1552078986706690049` e `1552080123111546952`.
- Extensão residual: `1552092254028439565`.
- Rodolfo informou a exclusão manual da lixeira e autorizou a continuação dos residuais: `1552095455624568875`.
- Escopo pós-ação reconciliado: `b1cd3052b972610387839722336c5f7c0bbad636fcc194be1b7562737893f7cf`.
- Escopo restante após canário: `89d97f852c4dbfb125e3b9741c406f4b292c216678fda290cbf3847238ac5fc3`.

## Evidência operacional

Workspace: `/root/.hermes/profiles/zeus/workspace/allincraft-resolution-20260922/`

Recebimentos principais:

- `backup-receipt.json`
- `apply-canary-receipt.json`
- `apply-batch-receipt.json`
- `residual-backup-receipt.json`
- `owner-residual-backup-manifest.json`
- `owner-residual-apply-dryrun.json`
- `owner-residual-apply-canary.json`
- `owner-residual-apply-batch.json`
- `remove-cleanup-plugins.json`
- `delete-residual-term.json`
- `final-validation.json`

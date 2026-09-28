# F031 — Backup dedicado e restore isolado do Spazio

**Estado:** CONCLUÍDO E VALIDADO — ARTEFATOS PRESERVADOS  
**Data:** 2026-09-24 UTC  
**Domínio:** `spaziokitchensandbaths.com`  
**Servidor:** SpazioVPS / RunCloud server ID `266820` / `157.230.212.128`  
**Webapp:** `spaziokitchensandbaths` / app ID `1376648`  
**Autorização da fase:** Discord `1552544275735121943`  
**Confirmação crítica do acesso temporário:** Discord `1552675837122183169`

## Resultado executivo

O backup dedicado do filesystem e do banco foi criado, restaurado em alvos isolados e validado por readback independente. Os backups e os restores permanecem preservados para a fase seguinte.

Nenhum plugin, arquivo de produção, banco de produção, versão PHP, serviço, configuração de sistema, firewall ou configuração SSH foi alterado. A remediação dos 11 plugins ativos continua pendente de uma fase separada.

## Backup e restore do filesystem

- Backup: `/var/backups/mgs-spazio-f031-20260924/spaziokitchensandbaths-filesystem.tar.gz`.
- Tamanho: 4.492.753.761 bytes, aproximadamente 4,18 GiB.
- SHA-256: `0499e1e560cb5ac325c637b83e82457f8e06169c1c28d054563d2b6ebd37e9db`.
- Modo/owner: `0600`, root.
- `gzip -t`: PASS.
- Restore preservado: `/var/backups/mgs-spazio-f031-20260924/restore/filesystem/spaziokitchensandbaths`.
- Comparação arquivo restaurado × archive: PASS.
- Manifesto de código estático do restore × produção: idêntico.

A primeira criação do archive terminou com código `1` porque o diretório `wp-content` mudou de metadado enquanto era lido. Não houve arquivo individual ausente no erro. O archive produzido foi preservado e, antes da retomada, passou em `gzip -t`, listagem integral do tar e leitura de 57.396 membros. A retomada não apagou nem recriou o archive; extraiu o restore e exigiu comparação integral do conteúdo restaurado com o próprio archive.

## Backup e restore do banco

- Backup: `/var/backups/mgs-spazio-f031-20260924/spaziokitchensandbaths-database.sql.gz`.
- Tamanho: 15.280.003 bytes, aproximadamente 14,57 MiB.
- SHA-256: `07fa7aab849c79eea40a8c198e9710cc5277933a43572a19290922bf3900560f`.
- Modo/owner: `0600`, root.
- `gzip -t`: PASS.
- Restore isolado preservado: schema `mgs_restore_spazio_f031_20260924`.
- Tabelas: 127.
- Linhas exatas: 41.981.
- Estrutura, colunas, índices e objetos: equivalentes.
- Dump de roundtrip do restore: byte a byte equivalente ao payload SQL do backup.
- Grants do restore: zero.
- Conexões do restore: zero.
- Banco de produção: presente e não alterado pela operação.

## Validação independente

O segundo validador passou em 34/34 checks:

- hashes, tamanhos, owner e modos dos backups;
- integridade gzip dos dois backups e do dump de roundtrip;
- restore do filesystem presente e igual ao archive;
- código estático de produção inalterado;
- source e restore do banco presentes;
- contagem exata e digest de linhas do restore;
- restore sem grants e sem conexões;
- checksum do WordPress core aprovado;
- `nginx-rc`, `mariadb` e `php80rc-fpm` ativos;
- exclusão futura protegida por nova confirmação crítica.

Readback HTTP após a revogação do acesso:

- homepage pública: HTTP 200;
- REST pública: HTTP 200;
- homepage na origem: HTTP 200.

## Acesso temporário e recuperação de falhas

O ciclo final usou a credencial temporária RunCloud ID `575812`:

- criada e validada por GET;
- removida no `finally`;
- GET final: 404;
- lista RunCloud final: zero credenciais;
- mesma chave recusada pelo SSH;
- material privado local destruído.

Duas tentativas operacionais anteriores também foram revertidas integralmente:

1. ID `575805`: preflight bloqueou por uma fórmula de espaço excessivamente conservadora; a credencial foi removida e a chave revogada antes de qualquer backup.
2. ID `575807`: o tar retornou código `1` pela mudança de metadado do diretório `wp-content`; a credencial foi removida e a chave revogada. O archive válido foi preservado e retomado somente após diagnóstico fail-closed.

Também houve uma tentativa local anterior que falhou antes de consultar a API porque o processo não tinha carregado o ambiente do 1Password; nenhum acesso ou artefato remoto foi criado nessa tentativa.

## Retenção e próxima fase

- Backup e restores protegidos até pelo menos `2026-10-24`.
- Qualquer remoção futura do backup, restore de filesystem ou schema de restore exige manifesto e nova confirmação crítica.
- Próxima recomendação: congelar o conjunto exato dos 11 plugins ativos afetados, reconstruí-los em staging a partir de pacotes oficiais/licenciados e preparar swaps atômicos unitários com rollback. Nenhuma remediação de plugin foi executada nesta fase.

## Evidências

Workspace local restrito:

`/root/.hermes/profiles/zeus/workspace/spazio-f031-internal-audit-20260923/`

Artefatos principais:

- `backup-restore-result.json`;
- `backup-restore-independent-readback.json`;
- `backup-restore-lifecycle-receipt.json`;
- `backup_restore_remote.py`;
- `validate_backup_restore_remote.py`;
- `run_backup_restore_lifecycle.py`.

Manifesto remoto protegido:

`/var/backups/mgs-spazio-f031-20260924/backup-restore-manifest.json`

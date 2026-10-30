---
name: wp-plugin-mass-operation
description: "Operações WordPress em massa nos 31 sites MGS: WP-CLI (RunCloud SSH), browser automation (AWS/Bitnami), SFTP, elFinder/WPCode deploy de mu-plugins, e RunCloud API v3. Cobre infra completa (27 RunCloud + 4 Bitnami + fincgriffin), credenciais, 1Password, SSH setup e pitfalls críticos de deploy."
tags: [wordpress, wp-cli, plugin, mass-operation, runcloud, sftp, mu-plugins, bitnami, api, deploy, infra]
related_skills: [mgs-infra-inventory, log-monitor-discord-alert, shell-cron-env-export]
---

# Operações de Plugin WordPress em Massa — Sites MGS

## Progressive disclosure — mandatory

1. Identify the exact operational branch below.
2. Load one route pack first; load another only when the first requires it or live evidence changes the branch.
3. Search the selected reference or exact source symbol before opening broader ranges.
4. Never load every reference or historical case study “for context.”
5. Reduce tool output above roughly 5 KB before another broad lookup.

Completion criterion: only the procedure and evidence required for the current action are loaded.

## Operational route packs

- **Quando usar → Sem acesso programático** → `references/route-pack-01.md`
- **Acesso RunCloud legado + descoberta live de webapps → ⚠️ Pitfalls** → `references/route-pack-02.md`
- **SEÇÃO B — Deploy de mu-plugins nos 4 sites AWS/Bitnami → Referência rápida** → `references/route-pack-03.md`
- **SEÇÃO D — SFTP para sites fora do RunCloud → Exceção Wantabrand — MonetizeMore/M2** → `references/route-pack-04.md`
- **Política global — 1Password e Credenciais → Referência — MGS Chat Funnels top ad/rewarded** → `references/route-pack-05.md`
- **Apoio ContentOps por renderer existente, WPCode, autoria/idioma e efeitos laterais** → `references/contentops-existing-renderer-scoped-support.md`
- **Diagnosticar abilities Yoast, papel e transporte de input** → `references/yoast-abilities-role-diagnostics.md`
- **Consolidar usuários/admins WordPress RunCloud com reatribuição e 1Password** → `references/runcloud-wordpress-user-consolidation.md`
- **Auditar/padronizar preloader JBF ↔ LoftLoader** → `references/jbf-loftloader-preloader-equivalence.md`
- **Menu mobile JBF abre vazio apesar de menu principal existir** → `references/jbf-empty-mobile-drawer-native-widget.md`
- **Auditar artigos WordPress irrelevantes/spam** → `references/wordpress-irrelevant-posts-incident-audit.md`
- **Auditar SEO/indexação de todos os artigos e corrigir sitemap XML obsoleto em WP Fastest Cache** → `references/article-seo-indexing-sitemap-audit.md`
- **Investigar árvores de plugins com versões misturadas** → `references/wordpress-plugin-mixed-version-forensics.md`
- **Recuperar fatal de `wp-content/db.php`/drop-in no admin** → `references/wordpress-db-dropin-fatal-recovery.md`
- **Instalar/enforçar WP 2FA em todo o portfólio** → `references/wp2fa-mass-enforcement-rollout.md`
- **Publicar três páginas informativas de Branding OAuth em um site aprovado** → `references/oauth-branding-pages-publication.md`
- **Migrar páginas e cards Lazy Blocks entre sites** → `references/lazyblocks-native-cross-site-migration.md`

## Diagnosticar acesso antes de propor transporte novo

1. Vincular o domínio à instalação e ao servidor exatos pelas fontes atuais; separar RunCloud, Bitnami e outras hospedagens. Acesso SSH a um servidor não demonstra acesso a outro, mesmo quando ambos pertencem à MGS.
2. Resolver as referências existentes pelo wrapper canônico `/root/mgs-agent/scripts/mgs-op-with-service-account.sh`, filtrando metadados pelos alvos antes de imprimir. Inspecionar também itens de servidor/LOGIN e referências dos helpers: SSH pode autenticar por **usuário e senha**, não apenas por item `SSH_KEY`, arquivo `.pem` ou título contendo “SSH”. Não concluir ausência de acesso por uma busca somente por chaves.
3. Distinguir referência encontrada, autenticação SFTP, autenticação SSH, shell executável e PHP/WP-CLI funcional. Testar somente leitura com a identidade já autorizada e host-key checking preservado; atribuir uma rejeição de shell à conta testada, nunca a todos os acessos do servidor. `known_hosts` identifica o servidor, não fornece uma credencial de login.
4. Cruzar a conta editorial com o acesso administrativo WordPress canônico e a URL cadastrada antes de concluir que falta manutenção. Se outro agente já consulta as mesmas referências, não descrever a lacuna como acesso exclusivo de Zeus nem propor compartilhamento/elevação sem comprovar a diferença de permissão.
5. Só então avaliar transporte adicional. Separar **função nativa encontrada**, **transporte disponível**, **backup/recuperação viáveis** e **reparo validado**; acesso administrativo ou existência de método no plugin não prova o fluxo completo. Não apresentar plugin temporário ou upload PHP ainda não testado como solução garantida.

Ao explicar “como você acessa por SSH?”, responder primeiro qual servidor, qual identidade técnica e se usa senha ou chave, sem revelar o segredo; depois comparar esse caminho com o alvo atual. Se nenhuma referência utilizável for encontrada, delimitar as fontes consultadas e a dependência exata, sem afirmar inexistência universal nem repetir a mesma busca sem evidência nova.

## Mutation and preservation gates

- Before escalating selective editorial-cache invalidation merely because the cache copy is a file, resolve the current confirmation authority in `data/atena/editorial-manager-authority.json#/cache_request_authority`. Apply Raquel's delegated approval for proven regenerable selective ContentOps cache without another CEO approval for each equivalent request; this is not general file-deletion authority. Preserve the exact approved target set, regeneration proof, private backup, no-symlink/path/hash/owner checks, canary and bare-canonical readback. Never add newly discovered homes/URLs to a previous manifest by inference or take over an active executor through a governance handoff.

- When an immutable native-route pin refers to a positional inventory index that drifted, relocate only by a unique exact original record hash **and** the same record ID/domain/webroot/server. Preserve the original hash and history, revalidate the native installation in read-only mode, and bind the next stage to a separate fresh relocation artifact. Never repin to whichever record now occupies the old index, weaken the source guard, or rewrite another agent's historical adapter to force passage.
- Preserve read failures structurally even when `str(exception)` is empty: include exception class and explicit unverified status, and aggregate gaps by key/status presence rather than truthiness of the error text. After a collector fix, supersede the erroneous summary with a corrected machine-readable artifact; do not convert an empty AssertionError message into successful coverage.
- For category-cache reconciliation, derive pagination from the native category link, not a stale public canonical that may name another language/slug. A translated canonical can make the collector request a nonexistent page 2; recheck the native path and separate this collection defect from a real production 404 before requesting any purge.

- Persist created object IDs and completed mutation stages before validation; recover a failed post-write check against those same IDs rather than creating replacements or replaying completed writes.
- Compare authored WordPress fields separately from computed `content.rendered`, because forms and widgets can change rendered HTML without an author edit. Apply the same distinction to excerpts: an empty `excerpt.raw` produces an automatic `excerpt.rendered` that legitimately changes after a content edit. Preserve the authored excerpt, not its derived preview; if a post-write guard fails on that preview, reconcile the persisted target and revalidate without replaying the POST. Preserve the original baseline and qualify any historical-revision fallback.
- After a draft/status transition, read the published permalink and canonical again; a draft REST link can be a preview URL even when production uses pretty permalinks. Resolve cross-links only within the authorized objects, not by changing site-wide permalink settings.

## Context-efficiency guardrails

- Stop and re-plan after more than three overlapping reads of the same file.
- Keep this main file as a routing layer; preserve detailed procedures in route packs.
- Validate the real runtime result before reporting success.

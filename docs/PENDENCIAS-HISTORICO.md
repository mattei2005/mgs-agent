# 📚 Histórico de Pendências Resolvidas — MGS Digital Corp

> Arquivo gerado automaticamente. Total: 22 resolvidas.

---

### ✅ [PEND-074] Hermes Agent setup completo (Zeus + Atena online em produção)

- **Categoria:** `infra`
- **Resolvida em:** 2026-05-14T11:59:28-04:00
- **Resolvida por:** claude-web
- **Como:** Migração de bots Python custom para Hermes Agent framework (NousResearch). Zeus (orquestrador admin) + Atena (content) instalados, com tokens Discord via 1Password, channel directory 23 targets, 41 slash commands cada, prompt caching ativo. Patch run.py para bug busy_input_mode#14905 (depois mergeado upstream PR#14762).

### ✅ [PEND-075] Pipeline REC end-to-end validado (primeiro REC AIB Visa Gold publicado eggbev)

- **Categoria:** `conteudo`
- **Resolvida em:** 2026-05-14T11:59:28-04:00
- **Resolvida por:** claude-web
- **Como:** Test 4 completo: skills content-generate-rec + content-publish-wordpress operacionais. Post 61948 (rec-gb-cc-aib-visa-gold-2) publicado com Yoast SEO 84 + Readability 90, validado visualmente por Raquel. Pipeline cobre research browser + image generation Gemini + LazyBlock injection + WP REST publish + Yoast meta.

### ✅ [PEND-076] AGENT.md hierarquia operacional (L0-L3 + Critical Subset + roles)

- **Categoria:** `documentacao`
- **Resolvida em:** 2026-05-14T11:59:28-04:00
- **Resolvida por:** claude-web
- **Como:** Modelo de autorização 4 níveis: L0 (read livre), L1 (execute + audit), L2 (approval required), L3 (forbidden). Critical Subset definido. Roles: Super Admin (Rodolfo), Conteudo (Raquel full access Atena), gestor, unauthorized. authorized-users.json com Discord IDs reais. Hierarquia: Rodolfo > Zeus > Atena > Ares (futuro).

### ✅ [PEND-077] Yoast mu-plugin v4 deploy 32 sites + openzed.com recovery EXIT CHECKLIST 8/8

- **Categoria:** `infra`
- **Resolvida em:** 2026-05-14T11:59:28-04:00
- **Resolvida por:** claude-web
- **Como:** Deploy massivo: 26 sites RunCloud via SSH + 4 sites SFTP/Bitnami (openzed/cliquet/finanzas) via elFinder + fincgriffin manual + eggbev canário = 32/32 sites com MD5 069270de4c07a9d15838ff45df65f539. Incidente openzed 25/04 (b64 inventado pelo Zeus → site down 18h) recuperado pelo dev externo + cleanup SQL + skill wp-rest-mu-plugin-deploy criada com PITFALL #1 + EXIT CHECKLIST 8 itens validados. SOUL Zeus atualizado com case study L2.

### ✅ [PEND-078] Tier Anthropic Tier 1 → Tier 3 + Auxiliary models 9 tasks usando Haiku

- **Categoria:** `infra`
- **Resolvida em:** 2026-05-14T11:59:28-04:00
- **Resolvida por:** claude-web
- **Como:** Upgrade gradual Tier 1 (30k/min) → Tier 3 (800k/min) via gasto acumulado + form sales. 9 tasks Atena+Zeus migradas para claude-haiku-4-5-20251001 (vision, web_extract, compression, session_search, skills_hub, approval, mcp, flush_memories, title_generation) — estimativa 80-85% redução de custo nessas tasks vs Sonnet. provider=auto em todos. Tier 4 form enviado, sem resposta.

### ✅ [PEND-079] 14 crons defensivos + monitoring infra + Admin API tracking

- **Categoria:** `monitor`
- **Resolvida em:** 2026-05-14T11:59:28-04:00
- **Resolvida por:** claude-web
- **Como:** Setup completo monitoring: sync-souls (5min), monitor-auto-push (15min), monitor-yoast-health-eggbev (10 UTC), monitor-anthropic-cost (12 UTC, divisor 88), monitor-tool-loops (5min), monitor-service-restarts (5min), check-pending-reports (15min), cleanup-discord-threads (4 AM), infra-discovery (5 AM), track-article-cost (15min), housekeeping .bak (3 AM). Admin API key separada criada. Webhook Discord #alerts-infra + #alerts-yoast (canais separados). Sistema previne 80%+ dos problemas operacionais.

### ✅ [PEND-080] Security hardening - curl-auth migration 6 scripts WordPress

- **Categoria:** `seguranca`
- **Resolvida em:** 2026-05-14T11:59:28-04:00
- **Resolvida por:** claude-web
- **Como:** Migração de curl -u inline (expõe senha em ps aux/argv) para wp_curl_auth helper usando curl -K tempfile chmod 600 + trap RETURN. 6 scripts migrados: upload-image.sh, create-post.sh, update-yoast.sh, resolve-term.sh, check-slug-conflict.sh, test-connection.sh. Doc auditoria em docs/security/migration-curl-auth-20260427.md. set -a/+a aplicado em todos scripts cron com 'op' (1Password CLI). Skill shell-cron-env-export documenta padrão.

### ✅ [PEND-081] Discord auto-thread + REGRA 6 (post limpo) + REGRA 8 (rename+mention) + tracking custo

- **Categoria:** `agente`
- **Resolvida em:** 2026-05-14T11:59:28-04:00
- **Resolvida por:** claude-web
- **Como:** REGRA 6 validada em REC 62031 Capital One (post_title 48c, Yoast title vazio, metadesc 121c, focus_kw 3 palavras). REGRA 8 (rename thread + mention unificado) funcionando em DM threads Atena+Zeus após resolver bloqueios (toolset hermes-discord, DISCORD_BOT_TOKEN passthrough, Cloudflare 1010 User-Agent). channel_prompts otimizado (1 mensagem). cleanup-discord-threads.sh cron 4 AM auto-deleta arquivadas 2 dias. Patch discord_tool.py modify_thread (4 ocorrências, custom mantido após updates Hermes).

### ✅ [PEND-082] Hermes upgrades v0.10 → v0.11 → v0.12 + features nativas adotadas

- **Categoria:** `infra`
- **Resolvida em:** 2026-05-14T11:59:28-04:00
- **Resolvida por:** claude-web
- **Como:** Upgrade v0.10→v0.11 (29/04, snapshot Hetzner 381460955) + v0.11→v0.12 (02/05, snapshot 382641638). Features nativas ativadas: steer mode (/steer mid-run), status-rich ack, smart compressor (dedup + anti-thrashing + language-aware), webhook direct-delivery (zero-LLM push), auto-prune sessions + VACUUM state.db (retention 30d). Patch run.py removido (queue agora nativo). Patch custom remanescente: discord_tool.py modify_thread. Compression config: enabled=true, threshold=0.15, target_ratio=0.2, protect_last_n=20.

### ✅ [PEND-083] Card cache + API mgs-rec-api (FastAPI porta 8001) - redução custo REC 99%

- **Categoria:** `infra`
- **Resolvida em:** 2026-05-14T11:59:28-04:00
- **Resolvida por:** claude-web
- **Como:** Card cache implementado em /root/mgs-agent/data/card-cache.db + imagens em data/card-images-cache/ (TTL 30d, 8 cartões UK populados). Scripts card-cache-lookup/save/stats.sh integrados na SKILL content-generate-rec (Step 1c lookup + Step 2.5 save). API mgs-rec-api FastAPI em /root/mgs-agent/api/generate-rec-api.py porta 8001, systemd service (Restart=on-failure, MemoryLimit=512M). Custo MEDIDO: -bash.029/REC em 20s via API vs .16/10min via Atena agent (-99% custo, -97% tempo). REC Halifax 62039 publicado via API com sucesso.

### ✅ [PEND-084] Audit massivo 02/05 - 24 fixes P0/P1/P2/P3 + recovery crontab + cleanup 94 .bak

- **Categoria:** `infra`
- **Resolvida em:** 2026-05-14T11:59:28-04:00
- **Resolvida por:** claude-web
- **Como:** Deep audit line-by-line repo mgs-agent: 52 bugs catalogados, 24 fixes aplicados em produção. P0-3 webhook fail-fast (4 files), P0-4 false positive validation, .bak cleanup (94 arquivos deletados /root/.hermes/profiles + /root/mgs-agent), housekeeping cron 3 AM (retention 15d), P1-9 mention fix, P1-1 datetime.utcnow fix monitor-service-restarts.sh, P0-1 api credential parsing, P0-2 .gitignore + auto-commit-watcher. Incidente crontab vazio recuperado via /tmp/crontab-20260502_215822.bak. SKILL refactor revertido (falhou). Snapshots Hetzner: 382263233, 382319113, 382641638.

### ✅ [PEND-085] Sistemas fundacionais 03/05 - Pendências DB JSON + Chat-log + Obsidian Vault setup

- **Categoria:** `documentacao`
- **Resolvida em:** 2026-05-14T11:59:28-04:00
- **Resolvida por:** claude-web
- **Como:** 3 sistemas críticos criados: (1) Sistema de Pendências - data/pendencias.db.json com 57 abertas + 9 resolvidas + 11 categorias, scripts pendencia-{add,done,list,render-md}.sh, cron 8 AM EST regenera docs/PENDENCIAS.md + docs/PENDENCIAS-HISTORICO.md. (2) Sistema Chat-log - scripts/chat-log.sh com tipos (decisao/contexto/licao/pend-add/pend-done/proximo/evento), 22 entradas fundação, INDEX hourly, prompt de retomada definido. (3) Obsidian Vault setup parcial Windows - SSH key GitHub + repo clonado MGS-Vault + Obsidian instalado, wikilinks/auto-pull adiados (PEND-067 criado).

### ✅ [PEND-006] Verificar canário thread Discord 1498667382334554263

- **Categoria:** `infra`
- **Resolvida em:** 2026-05-14T11:54:07-04:00
- **Resolvida por:** claude-web
- **Como:** Thread canário 1498667382334554263 retornou 'Unknown Channel' via Discord API em 06/05/2026 — cron deletou conforme esperado. Sistema validado funcional em produção.

### ✅ [PEND-R007] Skills Atena+Zeus auxiliary models otimizados (Haiku)

- **Categoria:** `agente`
- **Resolvida em:** 2026-04-29T00:00:00-04:00
- **Resolvida por:** rodolfo
- **Como:** 9 tasks usam claude-haiku-4-5-20251001 (vision, web_extract, compression, session_search, skills_hub, approval, mcp, flush_memories, title_generation). Economia 80-85% vs Sonnet.

### ✅ [PEND-R008] Card cache implementado (DB + scripts + 8 cartões)

- **Categoria:** `skills`
- **Resolvida em:** 2026-04-29T00:00:00-04:00
- **Resolvida por:** rodolfo
- **Como:** DB /root/mgs-agent/data/card-cache.db. Scripts card-cache-{lookup,save,stats}.sh. 8 cartões UK populados (HSBC Premier, Barclaycard Avios Plus+Platinum, Santander Edge, Virgin Atlantic Reward, Capital One Classic, Tesco Bank Clubcard, Halifax Clarity). Próximo REC do mesmo cartão cai 90%.

### ✅ [PEND-R009] API mgs-rec-api criada (FastAPI porta 8001)

- **Categoria:** `infra`
- **Resolvida em:** 2026-04-29T00:00:00-04:00
- **Resolvida por:** rodolfo
- **Como:** /root/mgs-agent/api/generate-rec-api.py + systemd service. Endpoints /health /stats POST /generate. Custo medido $0.029/REC em 20s vs $3.16/10min Atena agent (-99%, -97%).

### ✅ [PEND-R001] mime_type adicionado ao output JSON do upload-image.sh

- **Categoria:** `infra`
- **Resolvida em:** 2026-04-27T00:00:00-04:00
- **Resolvida por:** rodolfo
- **Como:** Patch aplicado em scripts/upload-image.sh + 2 docs SKILL atualizados. CLAUDE.md Technical Debt #1 marcada RESOLVED.

### ✅ [PEND-R002] Anti-loop set -a/+a aplicado em todos scripts em cron

- **Categoria:** `infra`
- **Resolvida em:** 2026-04-27T00:00:00-04:00
- **Resolvida por:** rodolfo
- **Como:** Auditoria de 12 scripts confirmou que TODOS os 7 em cron ativo já têm o fix. Apenas runcloud-inventory.sh (manual) ainda pendente (PEND-005).

### ✅ [PEND-R003] Bug 48×48 placeholder search-card-image.sh

- **Categoria:** `infra`
- **Resolvida em:** 2026-04-26T00:00:00-04:00
- **Resolvida por:** rodolfo
- **Como:** Já estava resolvido em commit 8cd3310 (CARD_MIN_WIDTH=200, CARD_MIN_HEIGHT=100). Só doc estava desatualizada. Atualizado CLAUDE.md L70 e L307.

### ✅ [PEND-R005] Mu-plugin Yoast v4 deployado em 32 sites

- **Categoria:** `infra`
- **Resolvida em:** 2026-04-26T00:00:00-04:00
- **Resolvida por:** rodolfo+zeus
- **Como:** 29 RunCloud + 4 SFTP + 1 fincgriffin manual. MD5 canonical 069270de4c07a9d15838ff45df65f539.

### ✅ [PEND-R006] Tier 3 Anthropic atingido

- **Categoria:** `externo`
- **Resolvida em:** 2026-04-26T00:00:00-04:00
- **Resolvida por:** anthropic
- **Como:** Cumulativo $200+. Tier 3 ativo (200k tokens/min). Tier 4 form ainda enviado (PEND-008).

### ✅ [PEND-R004] Bug Hermes busy_input_mode (issue #14905)

- **Categoria:** `infra`
- **Resolvida em:** 2026-04-23T00:00:00-04:00
- **Resolvida por:** nous-research
- **Como:** PR #14762 MERGED upstream em 23/04/2026. Hermes v0.11+ tem fix nativo.

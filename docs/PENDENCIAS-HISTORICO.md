# 📚 Histórico de Pendências Resolvidas — MGS Digital Corp

> Arquivo gerado automaticamente. Total: 10 resolvidas.

---

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

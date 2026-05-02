# Ops Summary — 28 a 30 de Abril 2026

**Período:** 28/04 a 30/04/2026  
**Responsável:** Rodolfo Mattei (CEO)  
**Registrado por:** Zeus (01/05/2026)

---

## 📅 28/04 — Article Cost Tracking System

**Objetivo:** Rastrear custo por artigo publicado com granularidade.

| Componente | Detalhe |
|---|---|
| Script | `scripts/track-article-cost.sh` (cron `*/15min`) |
| Banco de dados | `data/article-tracker.db` → tabela `article_publications` |
| Fonte de dados | `/root/mgs-agent/logs/publish-wordpress.log` |
| Lógica | Custo proporcional calculado por API calls por publicação |

---

## 📅 29/04 — Hermes Upgrade v0.10 → v0.11 + Otimizações

### Upgrade Hermes

| Item | Detalhe |
|---|---|
| Snapshot pré-upgrade | Hetzner ID `381460955` |
| Backup local | `/root/mgs-agent/backups/pre-hermes-upgrade-20260429_104523/` |
| Patch removido | `run.py` custom (upstream agora nativo: queue + steer + status-rich ack) |
| Patch mantido | `discord_tool.py` → action `modify_thread` (único restante) |

### Migração Auxiliary Models (Atena + Zeus)

9 tasks migradas de Sonnet 4.6 → **claude-haiku-4-5-20251001** (provider=auto):

| Task | Antes | Depois |
|---|---|---|
| vision | Sonnet | Haiku |
| web_extract | Sonnet | Haiku |
| compression | Sonnet | Haiku |
| session_search | Sonnet | Haiku |
| skills_hub | Sonnet | Haiku |
| approval | Sonnet | Haiku |
| mcp | Sonnet | Haiku |
| flush_memories | Sonnet | Haiku |
| title_generation | Sonnet | Haiku |

**Economia estimada:** 80–85% vs Sonnet 4.6 nessas tasks.

### Auto-Prune Sessions

Configurado em ambos os agentes (Atena + Zeus):
- `sessions.auto_prune=true`
- `retention_days=30`
- `vacuum_after_prune=true`
- VACUUM manual executado: Atena `31MB→30MB`, Zeus `35MB→34MB`

### Bug Fix — infra-inventory.json

- **Problema:** Skills MGS inseridas na key plana `skills` (schema errado)
- **Correção:** Movidas para `skills_hermes.{agent}` (schema correto)
- 3 skills Zeus corrigidas + state file limpo

---

## 📅 29–30/04 — Card Cache (Fase B) + mgs-rec-api (Fase C)

### Card Cache — Fase B

**Objetivo:** Eliminar chamadas Gemini/browser para dados de cartão já conhecidos.

| Componente | Detalhe |
|---|---|
| DB | `/root/mgs-agent/data/card-cache.db` |
| Imagens | `/root/mgs-agent/data/card-images-cache/` |
| Scripts | `card-cache-lookup.sh`, `card-cache-save.sh`, `card-cache-stats.sh` |
| TTL | 30 dias |
| SKILL | Step 1c (lookup antes do research) + Step 2.5 (save após) |

**Cartões populados retroativos (7):**
HSBC Premier, Barclaycard Avios Plus, Barclaycard Avios Platinum, Santander Edge, Virgin Atlantic Reward, Capital One Classic, Tesco Bank Clubcard

**Benchmark medido — REC Tesco Bank:** `$3.16 total`
- Gargalo identificado: 23 de 63 calls = browser (37% do custo)

---

### API mgs-rec-api — Fase C

**Objetivo:** Substituir geração de REC via Atena agent por endpoint FastAPI direto.

| Componente | Detalhe |
|---|---|
| Arquivo | `/root/mgs-agent/api/generate-rec-api.py` |
| Porta | `8001` |
| Systemd | Ativo |
| Endpoints | `GET /health`, `GET /stats`, `POST /generate` |
| Runtime | venv Hermes |
| Tracking | `/root/mgs-agent/api/usage.db` |
| SKILL | Step 5b chama endpoint |

**Benchmark de custo:**

| Método | Custo | Tempo |
|---|---|---|
| Atena agent (antes) | $3.16/REC | ~10 min |
| API mgs-rec-api (depois) | $0.029/REC | ~20 seg |
| **Redução** | **~99%** | **~97%** |

**Primeiro REC via API:** Halifax Clarity `#62039` — cache MISS (primeiro do cartão) — $0.027

---

## Métricas Consolidadas

| Data | Iniciativa | Impacto |
|---|---|---|
| 28/04 | Cost tracking | Visibilidade de custo por artigo |
| 29/04 | Hermes v0.11 | Infra atualizada, patch legado removido |
| 29/04 | Haiku migration | -80–85% custo tasks auxiliares |
| 29/04 | Auto-prune | DB saudável, sem acúmulo histórico |
| 30/04 | Card cache | Elimina re-fetch de dados de cartão conhecidos |
| 30/04 | mgs-rec-api | -99% custo/REC, -97% tempo/REC |

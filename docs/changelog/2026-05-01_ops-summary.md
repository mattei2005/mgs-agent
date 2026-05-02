# Ops Summary — 01 de Maio 2026

**Período:** 01/05/2026  
**Responsável:** Rodolfo Mattei (CEO)  
**Registrado por:** Zeus (02/05/2026)

---

## 📅 01/05 — 7 Patches SKILL/SOUL + REC NatWest Validado em Produção

---

## 🚨 Incidente do Dia — MBNA Loop

| Item | Detalhe |
|---|---|
| Agente | Atena |
| Sintoma | 149 `browser_navigate` em loop num único REC |
| Custo perdido | **$6.37** (sem publicar nada) |
| Causa raiz | SKILL antigo mandava usar `delegate_task` em sites Cloudflare-protected |
| Por que o monitor não pegou | Cloudflare challenge page retorna HTTP 200 — falso positivo de "sucesso técnico" |

---

## 🔧 7 Patches Aplicados

### Patch 1 — Circuit Breaker (Steps 3 + 13 + failure_modes)

- `MAX 5 browser_navigate` por sessão de REC
- Blacklist de issuers problemáticos: **MBNA UK Lloyds, Vanquis, NewDay**
- Quando dispara: usa Template B (sem card image, fallback Bing)

### Patch 2 — Step 13 Templates A/B Separados

| Template | Quando usar |
|---|---|
| **Template A — Normal** | Fluxo padrão, com card image |
| **Template B — Circuit Breaker** | Site bloqueado / issuer na blacklist |

Lógica de escolha explícita para Atena saber qual usar.

### Patch 3 — SOUL REGRA 7 Cost Reporting

| Antes | Depois |
|---|---|
| Consultava cron 15min via `article-tracker.db` (latência) | Aponta pro Step 14 do SKILL (delta direto via `state.db`, zero latência) |

### Patch 4 — Meta Description Sweet Spot

| Componente | Antes | Depois |
|---|---|---|
| SKILL Step 9 | 120–135c | **128c** |
| Template | ≤130c | **128c** |

Alinhamento canônico estabelecido: **128 caracteres**.

### Patch 5 — fincgriffin Removido do sites.json

- Site incompleto (sem `wp_url`, `credentials`, etc.)
- Risco: quebrar pipeline no meio da execução
- Nota explicativa adicionada em `context/sites.md`

### Patch 6 — Warning delegate_task na SOUL da Atena

- `orchestrator_enabled` mantido (útil para outros casos)
- Warning explícito adicionado sobre riscos em sites Cloudflare-protected
- Caso MBNA loop documentado como lição histórica

### Patch 7 — monitor-tool-loops.sh — Detecção de Frequência

| Antes | Depois |
|---|---|
| Só detectava erros consecutivos | Detecta também alta frequência |
| — | `browser_navigate > 15 em 30 turns` → alerta |

Defesa em profundidade contra próximo MBNA-style loop.

---

## 🛡️ Snapshot Pré-Refactor

| Item | Detalhe |
|---|---|
| Snapshot Hetzner | ID `382263233` (5.43 GB) |
| Tag git | `checkpoint-pre-refactor-skill-20260501` |
| Backup local | `/tmp/skill-refactor-patch09-*` |

---

## ✅ RECs Validados em Produção

### REC 1 — NatWest Reward (post 62049)

| Métrica | Resultado |
|---|---|
| Custo total | **$1.59** (Atena $1.56 + API $0.03) |
| Tempo | 13.8 min |
| Yoast SEO | **88 🟢** |
| Yoast Readability | **90 🟢** |
| Meta description | **128c** ← sweet spot exato |
| Palavras | 451 (target 450–500) |
| Template | A (normal) |
| Circuit Breaker | Não disparou ✅ |

### REC 2 — Lloyds World Elite (post 62052)

| Métrica | Resultado |
|---|---|
| Custo total | **$1.48** |
| Template | B (Circuit Breaker disparou — Cloudflare 1007) |
| Comportamento | Conforme esperado ✅ |

---

## Lições do Dia

1. **Cloudflare challenge ≠ erro HTTP** — monitor precisa checar frequência, não só status
2. **Circuit Breaker funciona** — Template B acionado corretamente no Lloyds
3. **Meta desc 128c** como alvo único elimina ambiguidade SKILL vs template
4. **fincgriffin** em sites.json incompleto era bomba-relógio — removido proativamente

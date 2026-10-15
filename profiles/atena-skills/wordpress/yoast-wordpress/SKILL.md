---
name: yoast-wordpress
description: >
  Class-level umbrella for all Yoast SEO + Readability work on WordPress sites
  (eggbev and multi-site). Covers: score architecture (two-layer DB system,
  mu-plugin design), fixing readability violations on existing posts, and running
  the standalone Linux cron health monitor. Load this skill for any Yoast-related
  task — scoring, repairing, monitoring, or mu-plugin changes.
tags: [yoast, wordpress, seo, readability, monitoring, mu-plugin, eggbev, cron]
related_skills: [ssh-jump-runcloud]
---

# Yoast WordPress — Umbrella Skill

Three subsystems live here. Jump to the relevant section:

| Task | Section |
|------|---------|
| Understand how Yoast stores scores (DB, mu-plugin, REST) | § Score Architecture |
| Fix a red/yellow readability post | § Repair Readability |
| Build / run the site health monitor | § Health Monitor (Cron) |

Detailed reference files are in `references/`:
- `references/yoast-score-architecture.md` — full DB schema, mu-plugin history, yoastseo Node.js scorer
- `references/content-repair-readability.md` — full repair workflow with Python diagnostic
- `references/site-health-monitor.md` — full cron monitor design, pitfalls, checklist

---

## § Score Architecture

Yoast stores scores in **two layers**:

| Layer | Table / Key | Read by |
|-------|-------------|---------|
| 1 — Post meta | `wp_postmeta`: `_yoast_wpseo_linkdex` (SEO), `_yoast_wpseo_content_score` (Readability) | Leitura autorizada de postmeta; REST somente se esses campos estiverem registrados/expostos |
| 2 — Indexables | `wp_yoast_indexable`: `primary_focus_keyword_score`, `readability_score` | WP Admin post-list bubbles |

**Score thresholds (Yoast standard):**
| Score | Color |
|-------|-------|
| ≥ 71  | 🟢 green |
| 41–70 | 🟡 amber |
| ≤ 40  | 🔴 red |
| NULL  | ⚪ notAnalyzed |

**Critical table name:** `wp_yoast_indexable` (SINGULAR). `wp_yoast_indexables` does not exist — never use the plural form.

**mu-plugin current state (v4, 2026-04-24):**
- File: `yoast-rest-meta.php` (also absorbs `hide-from-home.php`, now deleted)
- `register_post_meta` for 4 fields: `_yoast_wpseo_focuskw`, `_yoast_wpseo_metadesc`, `_yoast_wpseo_title`, `_hide_from_home`
- **NO** `rest_after_insert_post` hook, **NO** indexable `build()` / `save()` calls
- Yoast owns the indexable entirely — zero interference
- `pre_get_posts` hides posts with `_hide_from_home=1` from home/feed/search

**Key lesson:** Never use `rest_after_insert_post` to touch the Yoast indexable. Any interference causes score flicker. Let Yoast calculate autonomously.

Server-side scoring uses the `@yoastseo` npm library. Entry point:
```bash
bash /root/mgs-agent/skills/content-generate-rec-p1/scripts/yoast-score-post.sh eggbev <post_id>
```
See `references/yoast-score-architecture.md` for full Node.js API pitfalls.

**Preflight de compatibilidade obrigatório:** a existência do scorer não prova suporte multi-site/multilíngue. Confira na implementação vigente como resolve host, webroot, prefixo de tabelas, versão Yoast, Researcher e locale. Não derive webroot do `site_key` nem aplique locale/Researcher inglês a ES/PT por inferência. Se o wrapper fixar esses valores ou a correção exigir adaptação de script/runtime ou escrita técnica, escale para Zeus antes de executar. Não use valores fixos nem force verde para preencher análise ausente.

**Locale em WordPress multilíngue:** confirme a língua nativa do ID exato (`pll_get_post_language($id,'slug')` e `'locale'`, quando Polylang estiver ativo). O `get_locale()` global observado no WP-CLI pode diferir do locale do artigo; não o altere para satisfazer um gate. Somente com contexto nativo do artigo validado e adaptador autorizado, selecione o Researcher correspondente. Grave global e locale do artigo no baseline e readback, exigindo ambos inalterados. Meça `titleWidth` com o helper original do Yoast no DOM isolado, revise os assessments reais e mantenha resultados <71 sem reescrever conteúdo ou forçar verde. Verifique persistência única em postmeta/indexable separadamente da paridade do editor e da observação visual autenticada; sem handle no browser vault, registre o bloqueio e não aguarde indefinidamente.

**Locale por post em sites Polylang:** leia nativamente `pll_get_post_language($id, 'slug')` e `pll_get_post_language($id, 'locale')` em **cada ID**. O locale global observado via CLI pode ser `en_US` enquanto o conteúdo nativo é `pt`/`pt_BR`; use o Researcher do locale do post confirmado, nunca inferência pelo texto. Guarde ambos os locales no baseline/readback e exija preservação do global, sem alterar configuração para passar um gate. Uma adaptação local já aprovada deve manter os demais gates de escopo, identidade e preservação. Se um score real ficar abaixo de 71, persista somente o resultado autorizado e reporte ID/avaliações, sem forçar verde nem reescrever conteúdo fora do escopo.

## § Divergência entre editor, dados salvos e barra publicada

1. Distinga cor do logotipo de cor dos indicadores SEO/legibilidade; registre em qual tela e post a divergência foi observada. Verde no editor mostra análise naquele contexto, não prova persistência nem leitura correta pela barra.
2. Determine a extensão do padrão. Se afeta uma leva criada por automação e artigos anteriores do mesmo portal estão coerentes, inspecione primeiro o caminho compartilhado de criação/publicação; não diagnostique cache como explicação padrão.
3. Confira o payload e a execução: title/metadesc/focuskw são entradas, não resultados. Se não houve cálculo e readback reais, informe **score persistido não validado**. Campos numéricos ausentes no REST podem estar apenas não expostos; não conclua que estão vazios no banco.
4. Compare um post afetado com um controle anterior do mesmo portal, usando acesso autorizado e a instalação real. Separe análise carregada no editor, postmeta/indexable persistidos e indicador frontend. Se um teste humano de salvar no editor muda a barra para verde, registre a evidência e use-a para investigar o gatilho de gravação/atualização; não conclua qual hook é responsável nem que toda a leva foi corrigida.
5. Corrija somente pelo fluxo compatível e autorizado; valide o resultado salvo e a barra no mesmo ID antes de ampliar ao lote. Preserve conteúdo, mídia, taxonomia e publicação. Não reescreva artigos para mascarar ausência de análise, não force pontuações e não peça ao revisor que salve manualmente a leva inteira para contornar uma lacuna da automação.

Diagnóstico não equivale a reparo: mantenha hipótese, evidência humana, leitura técnica e correção validada separados no relatório.

---

## § Repair Readability

**When:** Post URL has 🔴/🟡 readability score. Steps:
1. Find post ID via HTML (REST `?slug=` may return `[]` on eggbev — known bug)
2. Run Python diagnostic to identify violations (sentence length, transitions, passive voice)
3. Rewrite only the violated rules
4. Validate against the article's own contract and explicit brief. The 450–500-word and subtitle ≤100-character limits apply only to REC when its contract requires them; do not apply them to long-form SEO or P1.
5. Publish via REST PATCH
6. Re-score with `yoast-score-post.sh`

**Key pitfall:** Preserve `<!-- wp:lazyblock/... /-->` blocks exactly — never rewrite their JSON payloads. Only touch `<!-- wp:paragraph -->` and `<!-- wp:heading -->` blocks.

See `references/content-repair-readability.md` for full Python diagnostic code, thresholds table, and before/after rewrite examples.

---

## § Health Monitor (Cron)

**When:** Building or extending a site-wide Yoast SEO + Readability cron monitor.

**Architecture:** Standalone Linux cron (NOT Hermes internal cron). Reads `wp_yoast_indexable` via SQL through SSH ProxyJump (see `ssh-jump-runcloud` skill). Posts to Discord webhook conditionally.

**Two metrics, same thresholds:** SEO (`primary_focus_keyword_score`) and Readability (`readability_score`) are reported separately — one post can be SEO 🟢 and Readability 🔴 simultaneously.

**Alert logic (OR):** Post if EITHER metric degrades:
- ≥ 3 percentage points more reds (vs prior snapshot)
- OR ≥ 5 new ambers (absolute count)
- Monday: always post weekly summary
- First run: always post baseline

**File naming convention:**
- Script: `monitor-yoast-health-{site}.sh`
- Snapshot: `data/yoast-health-{site}-snapshots.json`
- NOT `monitor-yoast-readability-*` (v1 name, readability-only)

**Critical pitfall — `op` CLI rate-limit:** Always wrap every `op item get` call in a retry helper with 2s backoff (3 attempts). Silent empty-string return on rapid consecutive calls is the symptom — NOT a credential problem.

See `references/site-health-monitor.md` for full implementation checklist, SSH execution pattern, snapshot JSON schema, migration guide, Discord message format, and all pitfalls.

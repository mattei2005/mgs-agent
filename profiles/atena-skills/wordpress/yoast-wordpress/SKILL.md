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
- `references/bounded-editorial-native-score-repair.md` — limited content-only repair, per-ID preservation, current-hash manifests and native score verification
- `references/social-image-after-featured-rest.md` — stale OG/Twitter after REST featured-media updates; native per-ID derivation, preservation and separate cache gates
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

**Exemplo de integração de metadados — inspecione a instalação real:**
- O MU plugin `yoast-rest-meta.php` pode registrar entradas SEO e regras de visibilidade, mas o conjunto de campos REST varia entre sites.
- Não acrescente hooks próprios de reconstrução de indexables para preencher ou mascarar notas; deixe o watcher nativo do Yoast atuar quando a rota tiver sido inspecionada e comprovada.
- Não remova nem registre campos apenas para reproduzir o schema de outro portal. Disponibilidade de Administrator não altera, por si só, quais metas foram registradas.

Os contratos e o histórico de implementação estão em `references/yoast-score-architecture.md`; confirme fonte, versão e efeitos antes de qualquer alteração técnica autorizada.

**Regra de cálculo:** hooks PHP de save/reindex constroem o indexable, mas não executam a análise linguística JavaScript. Não acrescente um `rest_after_insert_post` próprio para simular notas ou manipular o indexable; calcule com o analisador genuíno e use a rota nativa comprovada para persistir as saídas.

A análise usa a biblioteca genuína `yoastseo`; o wrapper existente abaixo é apenas uma entrada a considerar **depois** do preflight de compatibilidade, não uma garantia de suporte ao próximo portal:
```bash
bash /root/mgs-agent/skills/content-generate-rec-p1/scripts/yoast-score-post.sh eggbev <post_id>
```
Não extrapole o exemplo para outros hosts, owners ou idiomas. Use a receita de `references/yoast-score-architecture.md` para escolher cálculo, transporte e readbacks compatíveis.

## Preflight de análise e persistência

1. Resolva os IDs autorizados, instalação, owner, prefixo, versão Yoast, schema REST e transporte real antes de executar o scorer. Não derive webroot do `site_key` nem reutilize um wrapper que fixa outro host/idioma. Diferencie parametrização de adaptador local já autorizada de alteração do scorer compartilhado, acesso, plugin ou runtime; estas últimas seguem o escalonamento próprio.
2. Confirme o idioma de **cada post**: com Polylang, leia `pll_get_post_language($id,'slug')` e `'locale'`; sem locale nativo por post, confronte site_key autorizado, marcadores institucionais de idioma/mercado e hash da revisão independente. Preserve e registre global/user locale mesmo quando diferirem do conteúdo; uma convenção linguística como `es_ES` não muda o mercado financeiro do artigo.
3. Selecione o Researcher genuíno correspondente, expanda o SEO title pelo WordPress e meça `titleWidth` com o helper original no DOM isolado. Use rendered final e permalink real, registrando input/hash e estado esperado. Igualdade de versão npm não prova paridade com o editor.
4. Após autorização de produção, use um artigo real do lote como canário por combinação de contexto/transporte. Inspecione o watcher instalado e prefira as duas atualizações nativas de postmeta quando ele comprovar reconstrução no shutdown; não adote SQL UPDATE de indexable como padrão nem invente hooks para forçar cor.
5. Releia as duas metas e o indexable único no mesmo ID e exija valores calculados exatos, preservação editorial e contexto inalterado antes da expansão. Separe cálculo, persistência, paridade do editor e observação visual autenticada. Se uma dessas provas não existir, reporte o limite; não transforme ausência de sessão em espera indefinida ou em pedido para o revisor salvar todos os posts.

Se houver resultado baixo, reporte os assessments reais; um reparo editorial autorizado pode ajustar apenas os trechos responsáveis e deve gerar nova revisão/hash/análise, nunca um número fixo ou conectivos de enchimento.

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
5. Aplique o menor payload editorial autorizado e valide por GET no mesmo ID.
6. Recalcule o corpo final pela rota aprovada no preflight e confirme as duas camadas persistidas; não invoque automaticamente um wrapper de outro contexto.

**Retomada parcial de reparo:** reconcilie primeiro a intenção existente com o hash do corpo lido no ID exato; intenção gravada exige readback, nunca replay cego. Se uma normalização nativa de `comment_status` tiver sido explicitamente aceita, limite a exceção ao par exato `''` → `closed`, sem restaurar vazio, abrir comentários ou mudar configuração. Para uma nova revisão editorial, crie snapshots/diffs/manifesta de hash em diretório novo; preserve o bloqueio histórico e reconcilie source JSON, payload e receipt com o corpo real antes de preparar o adaptador de análise. Ao substituir uma revisão já calculada, use novo manifesto/work-dir em vez de alterar um manifest-lock existente.

**Naturalidade antes de densidade:** não acrescente conectivos apenas para satisfazer o assessment de transições. Prefira encadeamento semântico específico, conserve os avisos reais restantes e persista o cálculo genuíno mesmo sem todos os assessments verdes. Mantenha aprovação editorial escopada separada de gate/release global e de prova visual/paridade do editor.

**Key pitfall:** Preserve `<!-- wp:lazyblock/... /-->` blocks exactly — never rewrite their JSON payloads. Only touch `<!-- wp:paragraph -->` and `<!-- wp:heading -->` blocks.

See `references/content-repair-readability.md` for full Python diagnostic code, thresholds table, and before/after rewrite examples.

Na comparação nativa de indexables, separe as notas dos timestamps técnicos `updated_at` e `object_last_modified`; confira a relação deste último com `post_modified_gmt`, sem confundi-los com alteração da data editorial. Use `references/bounded-editorial-native-score-repair.md` para a receita completa de snapshots, diffs, reconciliação de artefatos e manifesto da revisão seguinte.

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

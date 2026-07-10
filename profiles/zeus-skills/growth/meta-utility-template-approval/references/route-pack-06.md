## Template Size / Approval-Speed Rule

When approval throughput is the bottleneck, do not assume the largest approved bank should be the active production template. Ciro's operational guidance: with thousands of pages, ~200 messages per template can make the daily approval cycle too slow; ~70 messages preserves useful variation and can approve about 3x faster.

### Daily rollout rule after Ciro timing correction

Ciro's approval timing rule is operationally decisive:

```text
approval ETA = pages × active_messages × 8 seconds
```

For large templates, even 70 messages can take days. Use a progressive active-template rollout unless Rodolfo explicitly overrides:

```text
Day 1: 10 active approved messages
Day 2: replace bad rows + add 10 = 20
Temporary hold 2026-07-03: keep templates capped at 20 while the purple/invalid-format issue is unresolved.
Resume 20→30→40→50 only after Rodolfo explicitly clears the purple issue.
```

Current live-replacement policy: replace **red/REJECTED only** in the global rollout. Purple (`INVALID_FORMAT`/`ERROR`) is an investigation state: do not touch globally until Rodolfo defines the purple-thread logic for separating page vs segurador vs app/block issues. Gray/no-status is also an investigation state: do not auto-replace globally; if a template remains gray for 2 days, alert the templates/broadcast channel `1522487422510694450`. Controlled tests are allowed only on explicitly named templates. Rodolfo correction 2026-07-03: editing one individual message should make only that changed message gray; if all other messages turn gray, that is an SB/Ciro bug. Erase All + upload new CSV reasonably makes everything gray because all messages changed. Current Rodolfo gate: cron wrapper may read/report, but live writes must use the fastest reliable live automation path and apply only the approved scope.

Schedule/check by page count: first useful check is `midnight ET + pages × active_messages × 8s + 30min`, with hourly checks from 01:00–18:00 ET. The 18:00 cutoff is a last-check window, not a reason to skip the next +10.

See `references/sb-utility-daily-rollout-10-20-30-2026-06-30.md` for the session detail and implementation pattern.

### Script-only rollout cron output

When this rollout runs via Hermes `no_agent` / script-only cron, stdout is delivered verbatim to Discord. Do **not** print raw JSON dictionaries to Rodolfo for normal changed/error reports. Render a short human ops update instead:

```text
SB Utility Rollout — atualizado

Templates atualizados: 1
- Template Name: 10 → 20 mensagens | ruins trocadas: 2

Estado atual: 48 em 20 | 11 em 10
Log: /root/mgs-agent/logs/...
```

Cron/report routing correction: recurring Utility rollout / Broadcast Template / Run Approval / template approval reports belong in the templates-broadcast Discord channel `1522487422510694450`, not the restricted-pages channel. If an hourly Utility rollout checker is producing repeated `aprovação necessária` noise in the active thread while Rodolfo is focused elsewhere, pause that cron instead of letting it spam; keep targeted gray/error alerts in the templates-broadcast channel. Restricted page / `#2022` / `Restricted Until` alerts remain in channel `1522442220903337984`.

See `references/sb-utility-rollout-cron-human-output-2026-07-01.md` for the concrete formatter pattern and the Rodolfo correction that triggered it.

If Rodolfo asks to reduce an active template to 70 messages:

1. Do **not** cut the first 70 mechanically.
2. Read the current template from SB and back it up as JSON + CSV.
3. Select the best 70 by conversion appeal: strong opening hook, card/credit profile/approval/limit/delivery framing, curiosity/urgency, strong CTA, and commercial fit for CC.
4. Preserve each selected message's text, CTA and link; renumber sequentially only for import/API integrity.
5. Reimport/update the same template and validate via `/broadcast/Messenger` that the live template now has 70 messages.
6. Do not run `Run Approvals` unless explicitly requested.

Keep 187/200-message files as reserve banks or experiments; use ~70 for active templates when approval speed matters.

### Country/language adaptation from an approved bank

When adapting an approved bank to another country/language combo, preserve the approved structure but apply the local compliance/content transformation explicitly. Example validated for `GB-CC-EN`: start from the 187 approved US-CC-EN messages, replace `$` with `£`, then compare the original tracker against the approved bank to find non-approved/rejected rows and rewrite those as fresh utility/status-style card messages before the next approval probe. The target-country CSV must use the target template's own link sequence, not links from the source country. See `references/gb-cc-en-utility-adaptation-and-rewrite-2026-06-30.md`.

## Scaling Rules

- Start with one page as approval probe.
- If approval behavior is consistent, expand across pages in the same site/vertical/language.
- Do not assume all languages behave the same. Treat each language/country as its own approval market.
- Share approved banks across operators when site/vertical/language match.
- Keep approved copies immutable; generate new variants instead of editing approved text.
- Track performance separately from approval. A copy can approve and still perform badly.

## Reporting Format to Rodolfo

When reporting an approval batch, use concise ops format:

```text
Utility approval batch

Site/idioma: memivi US EN CC
Página teste: [page]
Template: template_utility_vX
Enviadas: 150
Aprovadas: 104
Reprovadas: 43
Formato inválido: 3
Taxa aprovação: 69%
Banco aprovado agora: 156/200 alvo
Próximo passo: reescrever 43 reprovadas usando as 104 aprovadas como seed.
```


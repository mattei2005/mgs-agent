# CAR-BR gate admin, wrapper domain prefill, and click QA (2026-07-06)

Session context: Rodolfo iterated on the MGS Chat Funnels CAR-BR chat across 8 sites (`zuout`, `zytiva`, `openzed`, `finance.topfeed.fun`, `newsoun`, `wantabrand`, `cliquet`, `eggbev`). The class-level lessons apply to future JBF/Ciro-style chat funnels.

## Durable learnings

### Gate questions must be configurable without breaking question 1

Rodolfo wanted the initial gate to show both questions by default but allow hiding the second one from WP Admin. Question 1 cannot be removed because it starts the gate UX.

Implementation pattern:

- Keep gate question 1 mandatory/always enabled.
- Add an explicit admin toggle for question 2, e.g. `gate_question_2_enabled`.
- Persist `enabled: true/false` in the second gate question config.
- Render public gate slides dynamically from active config, not hardcoded HTML.
- Public JS should use `gateQuestionCount` instead of hardcoded `quizStep <= 1`.

Validation pattern:

- Public HTML with both enabled: `const gateQuestionCount = 2;` and both questions present.
- Toggle visible in admin: “Mostrar pergunta 2 do gate”.
- Browser click: question 1 → question 2 → loading/final CTA → chat.
- If question 2 is disabled, browser click: question 1 → loading/final CTA → chat.

### Wrapper domain field should prefill with site slug

Rodolfo expected `Domain do wrapper` to be filled automatically from the current site. Example: on `https://zuout.com/`, the field should show `zuout`.

Implementation pattern:

- Add helper like `current_site_ad_slug()` from `home_url()` host:
  - strip `www.`
  - take first host label before `.`
  - sanitize to ad slug
- In the admin field value, if `ad_domain` is empty, display the current site slug.
- On human save, if the submitted domain is empty, persist the current site slug.
- For mass rollout configs, set explicit `ad_domain` per domain:
  - `zuout.com` → `zuout`
  - `zytiva.com` → `zytiva`
  - `openzed.com` → `openzed`
  - `finance.topfeed.fun` → `finance`
  - `newsoun.com` → `newsoun`
  - `wantabrand.com` → `wantabrand`
  - `cliquet.com` → `cliquet`
  - `eggbev.com` → `eggbev`

Validation pattern:

- Public HTML contains wrapper URL:
  `https://assets.jbfdigital.com.br/assets/{company}/{slug}/{company}_{slug}.builder.js`
- Admin page input value is the slug.
- Config JSON contains explicit `ad_domain` after save/rollout.

### Click QA needs real browser progression

Static HTTP 200 and HTML markers are not enough. For gate/chat changes, run real click progression:

1. First gate answer advances.
2. Second gate answer advances or is skipped if disabled.
3. Loading/final CTA appears.
4. CTA closes modal even if rewarded callback is silent.
5. Chat starts and can reach cards/offers.

The known race fixed in this session: a `quizStepLock` could drop fast second-step clicks after buttons were disabled. Use a deterministic CTA fallback (e.g. timeout calling `closeQuiz`) so wrapper silence does not strand the user.
---
name: sms-funnel-wordpress-routing
description: "Use when routing SMS Funnel clicks through WordPress."
version: 1.1.0
author: Ares
license: internal
platforms: [linux]
metadata:
  hermes:
    tags: [mgs, sms-funnel, wordpress, webhooks, lead-routing, php]
    related_skills: [wp-plugin-mass-operation]
---

# SMS Funnel → WordPress Click Routing

## When to use

Use after Rodolfo explicitly authorizes a site/SMS Funnel integration in which clicking one SMS must place the lead into the list that triggers the next SMS. This skill governs the application flow; use `wp-plugin-mass-operation` for server access, ZIP deployment, inventory and REPORT-INFRA.

Do not configure SMS Funnel, WordPress, quiz code or production webhooks without explicit scope from Rodolfo. A request to explain or review a link is read-only; “instala”, “implemente” or equivalent names the write scope.

## Standing communication rules

- Answer the minimal functional path first: link parameters → WordPress router → next list → next automation. Do not bury the requested setup under optional hardening observations.
- Preserve every UTM supplied by Rodolfo literally. A historical manager/reporting bucket never authorizes replacing `utm_medium`, `utm_campaign` or another identifier in the current request.
- Separate facts proved by site/SMS Funnel readback from values merely stated in conversation. Never invent a list, webhook, delivery or successful SMS.
- When Rodolfo asks to move “só o front-end” next to another plugin, change only the WordPress admin navigation. Preserve plugin backend, options, runtime hooks and payloads.

## Functional model

```text
Initial lead list
  → SMS 1 link contains step=01 and SMS Funnel appends var_phone
  → WordPress maps 01 to the integration URL of the list for SMS 2
  → entering that list triggers SMS 2
  → SMS 2 link contains step=02
  → WordPress maps 02 to the list for SMS 3
```

The step on a message identifies the **next list**, not the message currently being sent. With only two follow-up lists, the final SMS needs no next step unless another list/automation exists.

Treat the initial/source list as context, not as a router destination: the lead already belongs to it before SMS 1, usually through the quiz or another intake integration. A generic sample that says `step=1 → Lista 1` must be remapped to the real next-list sequence rather than copied literally. Do not add a webhook field for the source list unless a click is intentionally supposed to insert the lead back into that list.

## Procedure

### 1. Resolve the exact sequence

Collect only the values that block execution:

- exact WordPress site and landing URL;
- exact phone query parameter emitted by SMS Funnel (normally `var_phone`);
- list name and integration URL for each next step;
- exact UTM values already chosen by the operator;
- whether the last SMS ends the sequence.

Materialize a map before coding:

```text
01 → list that triggers SMS 2
02 → list that triggers SMS 3
```

Do not ask the operator to choose a site when the operation already has one canonical SMS site.

### 2. Validate the automation links

A configured link contains the operator's UTMs plus the step:

```text
https://SITE/PAGE/?utm_source=sms&utm_medium=EXACT&utm_campaign=EXACT&step=01
```

Load the URL and verify HTTP success, final pathname and preservation of every query value after redirects. The configured link does not manually need `var_phone` when **Enviar número do lead na URL** is enabled in SMS Funnel; verify that setting in the platform before the live test.

### 3. Build a configurable WordPress plugin

Prefer a normal plugin with a native Settings API screen over hard-coded webhooks in PHP. Start from `templates/sms-funnel-router.php` and adapt prefix, labels, route count and admin-menu placement.

Required behavior:

- plugin active but routing disabled by default;
- webhook fields empty by default;
- one explicit row per step/list;
- HTTPS URL sanitization on save;
- strict phone cleanup and numeric step normalization (`1` and `01` both resolve to `01`);
- `wp_remote_post()` JSON payload containing `name` and `phone`;
- missing/invalid parameters leave the landing page working normally;
- no live webhook call until endpoints are populated and routing is enabled.

### 4. Place the admin interface where Rodolfo expects it

Pre-read `$menu` and `$submenu` under a real administrator after `do_action('admin_menu')`. Locate the exact slug and position of the visual neighbor; do not infer them from a screenshot alone.

- Use `add_menu_page()` for a top-level item beside another plugin.
- Use `add_submenu_page()` only when Rodolfo asks for actual nesting.
- Update the plugin's “Configurar” action link to the new admin URL.
- For a UI-only change, bump the plugin version but do not rename options or runtime callbacks.

### 5. Deploy inertly, then read back

Use the site’s real Unix owner. Before write, read plugin status/version/options/checksum. Package only production files, run `php -l`, install/update with WP-CLI, then verify:

- plugin active and expected version;
- remote checksum equals the packaged source;
- runtime and admin hooks registered;
- options preserved exactly;
- requested top-level/submenu position exists;
- old menu location no longer contains the slug.

### 6. Probe without sending SMS

Before endpoints are populated, or while routing is known to be disabled, request a real landing page with safe dummy values:

```text
?step=01&var_phone=00000000&probe=UNIQUE
```

Require the page’s normal HTTP response and a deterministic inactive signal from the plugin. This proves WordPress executed the router despite caching/query handling while guaranteeing zero webhook calls.

After the operator says the endpoints were saved, never probe a mapped step with a dummy phone: an enabled router would submit that dummy lead to the production webhook. Instead, probe a deliberately unmapped numeric step with a valid-length dummy phone and a unique cache-buster. For a router that defines only `01` and `02`:

```text
?step=03&var_phone=00000000&probe=UNIQUE
```

Interpret only the sanitized router signal:

- `inactive` → plugin executed, but routing is still disabled;
- `route-not-configured` → routing is enabled and the deliberately absent route prevented any webhook call.

Repeat the unmapped probe on the landing page and site root with different `probe` values when cache behavior is uncertain. This test proves runtime execution and enablement only; it does not prove that the mapped webhook fields were saved, that a lead entered a list, or that an SMS was sent. Read back the saved options or run the controlled end-to-end test for those claims.

### 7. Configure and run one controlled end-to-end test

After the operator supplies the actual integration URLs:

1. pre-read current options;
2. save each exact step-to-webhook mapping;
3. enable routing;
4. open the SMS link with a controlled test lead;
5. verify the site remains available;
6. verify the lead appears in the expected next SMS Funnel list;
7. verify only the intended next automation is triggered;
8. repeat for each step;
9. record platform/site readback before declaring success.

Do not use a successful HTTP POST alone as proof that the lead entered the list or that the SMS was sent.

## Pitfalls

- Map each message to the **next** list — labeling the step by the current message creates an off-by-one sequence.
- Keep `step` formatting consistent in links and normalize it in PHP — examples commonly mix `1` and `01`.
- Keep the first-step name assumption separate from later steps — a click URL may carry only the phone, so later automations often receive a default name.
- Treat “plugin active” and “routing enabled” as different states — an active inert plugin is the safe review state.

## Verification checklist

- [ ] Exact site, list names, webhooks, UTMs and final step resolved
- [ ] Link loads and preserves query values
- [ ] SMS Funnel appends the phone parameter
- [ ] Plugin starts inert with empty endpoints
- [ ] Step map points to the next automation list
- [ ] PHP lint, version, checksum, options and hooks pass
- [ ] Admin menu location matches the requested visual placement
- [ ] Disabled public probe returns normal page + inactive signal
- [ ] Post-save unmapped-route probe confirms enabled/disabled state without calling a webhook
- [ ] Exact saved endpoint options are read back before the live test
- [ ] Live test confirms list entry and next automation by readback
- [ ] Inventory, checkpoint/audit and REPORT-INFRA completed when required

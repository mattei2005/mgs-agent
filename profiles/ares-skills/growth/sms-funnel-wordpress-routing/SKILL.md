---
name: sms-funnel-wordpress-routing
description: "Use when routing SMS Funnel clicks through WordPress."
version: 1.3.0
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
Vehicle + manager initial list
  → SMS 1 link identifies vehicle=carro|moto, utm_medium=g00x-s and step=01; SMS Funnel appends var_phone
  → WordPress resolves (vehicle, g00x, 01) to that vehicle/manager list for SMS 2
  → SMS 2 keeps the same vehicle and utm_medium, then uses step=02
  → WordPress resolves (vehicle, g00x, 02) to that vehicle/manager list for SMS 3
  → SMS 3 may retain step=03 as an intentionally inert future route
```

The step identifies the **next list**, not the current message. On a site shared by Carro/Moto and G001–G006, require a three-dimensional route key: **`vehicle + utm_medium + step`**. Never fall back between vehicles or managers. A final `step=03` may remain configured with no WordPress destination until a fourth list exists.

Treat the initial/source list as context, not as a router destination: the lead already belongs to it before SMS 1, usually through the quiz or another intake integration. A generic sample that says `step=1 → Lista 1` must be remapped to the real next-list sequence rather than copied literally. Do not add a webhook field for the source list unless a click is intentionally supposed to insert the lead back into that list.

## Procedure

### 1. Resolve the exact sequence

Collect only the values that block execution:

- exact WordPress site and landing URL;
- exact vehicle namespace (`carro` or `moto`) and how the link supplies it;
- exact phone query parameter emitted by SMS Funnel (normally `var_phone`);
- exact manager namespace from `utm_medium` (for example `g002-s`);
- list name and integration URL for each next step in each vehicle/manager namespace;
- exact UTM values already chosen by the operator;
- whether the last SMS ends the sequence or keeps an inert future step.

Materialize a three-dimensional map before coding:

```text
carro + g001-s + 01 → Carro G001 list that triggers SMS 2
carro + g001-s + 02 → Carro G001 list that triggers SMS 3
moto  + g001-s + 01 → Moto G001 list that triggers SMS 2
moto  + g001-s + 02 → Moto G001 list that triggers SMS 3
...
```

Do not ask the operator to choose a site when the operation already has one canonical SMS site.

### 2. Validate the automation links

A configured link contains the operator's UTMs plus the step:

```text
https://SITE/PAGE/?utm_source=sms&utm_medium=EXACT&utm_campaign=EXACT&vehicle=carro&step=01
```

Prefer explicit `vehicle=carro|moto`. Path inference may preserve legacy links only when the URL path unambiguously contains `carro` or `moto`; a conflict between the explicit parameter and path must fail closed. Load the URL and verify HTTP success, final pathname and preservation of every query value after redirects. The configured link does not manually need `var_phone` when **Enviar número do lead na URL** is enabled in SMS Funnel; verify that setting before the live test.

### 3. Build a configurable WordPress plugin

Prefer a normal plugin with a native Settings API screen over hard-coded webhooks in PHP. Start from `templates/sms-funnel-router.php` and adapt prefix, labels, route count and admin-menu placement.

Required behavior:

- plugin active but routing disabled by default;
- webhook fields empty by default;
- one explicit configuration panel per vehicle/manager namespace;
- strict vehicle allowlist (`carro`, `moto`) and manager allowlist (`g001-s`–`g006-s`);
- routing by `(vehicle, manager, step)`; missing/unknown/conflicting vehicle or medium must never fall back to another route;
- path inference only for unambiguous legacy URLs containing `carro` or `moto`;
- one explicit row per step/list inside each vehicle/manager panel;
- HTTPS URL sanitization on save;
- strict phone cleanup and numeric step normalization (`1` and `01` both resolve to `01`);
- per-route enablement so unfinished combinations remain inert;
- `wp_remote_post()` JSON payload containing `name` and `phone`;
- missing/invalid parameters leave the landing page working normally;
- no live webhook call until the exact vehicle/manager endpoints are populated and enabled;
- schema migration preserves all prior manager endpoint bytes and activation states under Carro while Moto starts empty/inert.

### 4. Place the admin interface where Rodolfo expects it

Pre-read `$menu` and `$submenu` under a real administrator after `do_action('admin_menu')`. Locate the exact slug and position of the visual neighbor; do not infer them from a screenshot alone.

- Use `add_menu_page()` for a top-level item beside another plugin.
- When Carro and Moto share the site, expose one overview plus `Carro` and `Moto` submenus; each vehicle page contains G001–G006 filters and shows one manager at a time.
- Use `add_submenu_page()` only when Rodolfo asks for actual nesting or a vehicle fan-out.
- Update the plugin's “Configurar” action link to the overview URL.
- Scoped saves must merge one vehicle/manager route into the existing option; never blank sibling vehicles or managers.
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

Use an intentionally unconfigured route and a unique cache-buster:

```text
?vehicle=carro&utm_medium=g002-s&step=03&var_phone=5500000000000&probe=UNIQUE
```

Require the page’s normal HTTP response and `route-not-configured`. Also prove isolation with an inactive Moto route (`group-inactive`), missing/unknown medium (`invalid-medium`), missing/unknown vehicle (`invalid-vehicle`), and an explicit vehicle that conflicts with the path (`invalid-vehicle`). These probes execute the router while guaranteeing zero webhook calls.

After the operator says the endpoints were saved, never probe a mapped step casually: an enabled router submits the lead to the production webhook. For mapped-route verification, use a deliberately invalid synthetic phone namespace, pre-read exact list absence/count, verify the intended list entry, delete only the synthetic lead, and read back its absence. This proves WordPress → webhook → list, not carrier delivery.

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

For authenticated list, automation, sequence and cleanup readback, load `references/sms-funnel-api-readback.md`. Keep the main flow here; use the reference only when platform-level evidence is required.

## Pitfalls

- Map each message to the **next** list — labeling the step by the current message creates an off-by-one sequence.
- Never route a shared Carro/Moto site by `utm_medium + step` alone; identical manager codes exist in both vehicles.
- Never use a default vehicle or manager fallback; missing, unknown or path-conflicting values must fail closed while leaving the page available.
- Keep `step` formatting consistent in links and normalize it in PHP — examples commonly mix `1` and `01`.
- A final automation may intentionally carry `step=03` with no route until List 4 exists; `route-not-configured` is then the correct result.
- Keep the first-step name assumption separate from later steps — a click URL may carry only the phone, so later automations often receive a default name.
- Treat “plugin active”, “master enabled” and “manager enabled” as different states.
- During schema migration, compare endpoint lengths and hashes before/after; never print webhook URLs.

## Verification checklist

- [ ] Exact site, vehicle namespaces, manager namespaces, list names, webhooks, UTMs and final step resolved
- [ ] Every link loads and preserves its exact `vehicle`, `utm_medium`, `step` and other query values
- [ ] SMS Funnel appends the phone parameter in every automation
- [ ] Plugin starts inert with empty endpoints for unconfigured vehicle/manager routes
- [ ] Route map uses `vehicle + utm_medium + step` and points to the next automation list
- [ ] Missing/unknown/conflicting vehicle, missing/unknown medium, disabled route and inert final step all fail closed without webhook calls
- [ ] PHP lint, version, checksum, schema migration, options and hooks pass
- [ ] Overview plus Carro/Moto submenu fan-out and G001–G006 filters match the requested admin placement
- [ ] Existing Carro webhook lengths/hashes and activation are unchanged after migration; Moto starts empty/inert
- [ ] Live synthetic test confirms exact vehicle/manager list entry, then deletes the synthetic lead and verifies absence
- [ ] Real controlled-phone test confirms list entry, next automation and SMS delivery before claiming full end-to-end success
- [ ] Inventory, checkpoint/audit and REPORT-INFRA completed when required

---
name: digitaltrchat-broadcast-operations
description: Safely inspect, edit, migrate and verify scheduled DigitalTRChat/ChatPion Subscriber Broadcast campaigns across users, seguradores and pages, with Pending-only gates, exact URL transformations, rollback and independent readback.
version: 1.0.1
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [mgs, digitaltrchat, chatpion, messenger, subscriber-broadcast, url-migration, playwright]
    related_skills: [digitaltrchat-drip-flow-builder, smartbidding-dashboard-access]
---

# DigitalTRChat Broadcast Operations

## Scope

Use this class-level skill when Rodolfo asks Zeus to inspect or modify scheduled Messenger campaigns under `Broadcasting > Subscriber Broadcast` in DigitalTRChat/ChatPion.

This skill covers:

- resolving the exact DigitalTRChat login from 1Password;
- iterating users, seguradores and pages;
- inventorying `Pending` broadcasts;
- performing narrow text/button/link migrations;
- preserving schedules, targeting, copy and URL attribution data;
- backup, rollback, same-session reload and independent readback.

Use `digitaltrchat-drip-flow-builder` instead for Bot Flow Builder graphs, Saved Templates, Get Started and No Match. Subscriber Broadcast edits belong here.

## Mandatory reference

Before any URL-host migration or multi-campaign write, load `references/subscriber-broadcast-host-migration.md`.

For B011 broadcasts, also load `meta-app-rate-limit-monitor` and its Operational Symptom Monitor route pack before interpreting a DTR/ChatPion send state as delivery evidence. A DTR action can be accepted while a restricted app-owning Business Manager leaves advanced Messenger permissions inactive and Meta rejects OAuth/no delivery. Require the B011 capability monitor to show Graph pages above zero and confirm a delivered canary with Ciro before resuming normal volume after such an incident.

## Canonical route

1. Log into `https://digitaltrchat.com/` with the exact 1Password item.
2. Open `Broadcasting > Subscriber Broadcast`.
3. Confirm the DigitalTRChat user label.
4. Confirm the current segurador in the top Facebook-account selector.
5. In the table's `Page` filter, choose the generic `Page` option to clear any specific Facebook-page selection and show all pages whenever the filter is blank or already scoped. This is the list filter, not the campaign edit form's `Page` field.
6. Set the campaign status filter to exactly `Pending` and use the live campaign table as the source of truth for Facebook page, status and edit action.
7. Treat the default 10-row view as pagination only, never as the complete eligible set. Traverse table pages `1, 2, 3, ...` through the last page (or until `Next` is disabled), reconciling the displayed range/total and deduplicating by campaign ID.
8. For portfolio work, inventory every Facebook page represented across all pagination pages before switching segurador. For a pilot scoped to one Facebook page, identify the first eligible row's page name, filter/search that exact page and enumerate every currently eligible campaign for it before writing.

## Write gate

A production write is allowed only when all conditions hold:

- Rodolfo authorized the exact user/page or portfolio scope;
- the live status is exactly `Pending` immediately before mutation;
- the target row passes edit-versus-delete safety predicates;
- the original URL-bearing source fields and key campaign settings are backed up;
- the computed delta changes only the authorized field/value;
- rollback remains possible;
- reload and a fresh-session readback are planned.

Any eligible-set drift after baseline, including a campaign moving to `Processing`, requires stopping before mutation and reconfirming the reduced scope.

## Completion criteria

Do not report success until:

- every intended campaign has successful responses from the actual save chain (`subscriber_bulk_broadcast_edit_action` followed by `subscriber_bulk_broadcast_add_action`) or an explicit `Campaign updated` UI; unrelated background POSTs such as `home/get_broadcast_summary` are not save evidence;
- every changed field matches the backup-derived expected value after reload;
- no old scoped hostname remains in the changed campaigns;
- non-targeted campaign fields are unchanged;
- an independent browser context confirms the final state;
- partial failures and skipped non-Pending rows are reported explicitly.

## Security boundary

Credentials stay inside the local process. Never emit full DOM `outerHTML`, avatar/image URLs, cookies, storage state or raw request headers: DigitalTRChat may embed Facebook access tokens in image query strings. Log only whitelisted, sanitized fields and remove URL query strings unless the query itself is the authorized business data being verified.

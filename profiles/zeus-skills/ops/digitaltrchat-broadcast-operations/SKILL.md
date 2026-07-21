---
name: digitaltrchat-broadcast-operations
description: Safely inspect, edit, migrate and verify scheduled DigitalTRChat/ChatPion Subscriber Broadcast campaigns across users, seguradores and pages, with Pending-only gates, exact URL transformations, rollback and independent readback.
version: 1.0.0
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

## Canonical route

1. Log into `https://digitaltrchat.com/` with the exact 1Password item.
2. Open `Broadcasting > Subscriber Broadcast`.
3. Confirm the DigitalTRChat user label.
4. Confirm the current segurador in the top Facebook-account selector.
5. Use the live campaign table as the source of truth for page, status and edit action.
6. Filter the exact page and enumerate every currently eligible campaign before writing.

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

- every intended campaign has a successful save response;
- every changed field matches the backup-derived expected value after reload;
- no old scoped hostname remains in the changed campaigns;
- non-targeted campaign fields are unchanged;
- an independent browser context confirms the final state;
- partial failures and skipped non-Pending rows are reported explicitly.

## Security boundary

Credentials stay inside the local process. Never emit full DOM `outerHTML`, avatar/image URLs, cookies, storage state or raw request headers: DigitalTRChat may embed Facebook access tokens in image query strings. Log only whitelisted, sanitized fields and remove URL query strings unless the query itself is the authorized business data being verified.

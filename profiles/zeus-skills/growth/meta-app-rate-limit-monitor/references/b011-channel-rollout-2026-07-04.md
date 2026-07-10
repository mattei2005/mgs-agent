# B011 Channel Rollout — 2026-07-04

## Context

Rodolfo created Discord channel `1522830283240505385` for app `B011` and asked for the existing Meta app roles/rate-limit cron to include it, making 11 total app channels.

He explicitly said not to read the migration sheet yet because it was being updated.

## Durable lesson

Adding an app-specific alert channel is not sufficient for production monitoring. The monitor auto-discovers apps from 1Password items, so the channel mapping and the token item are separate prerequisites:

1. Add/update `APP_ALERT_CHANNELS` routing in `meta-app-roles-watch.sh`.
2. Document the destination in this skill.
3. Ensure the Hermes cron remains the same one-cron model (`meta-app-roles-watch`, every 2m), unless Rodolfo requests separate failure isolation.
4. Do **not** read or reconcile the migration sheet if Rodolfo says it is being edited.
5. Monitoring only begins after the matching 1Password item exists.

## Required 1Password item for B011

```text
Item title: BOT B011 Token
Required fields:
- app_id
- app_name = B011
- access_token
- app_secret
- expires_at
- notes
```

Recommended diagnostic scopes remain:

```text
public_profile
pages_show_list
pages_read_engagement
business_management
```

## Channel mapping

```text
B011  #b011-app-rate-limit  1522830283240505385
```

## Reporting pitfall

When this script/skill/inventory changes, REPORT-INFRA is still required by MGS policy. If direct Discord posting fails because the bot lacks permission in `#alerts-infra`, do not hide the failure or claim the report was delivered. State clearly that the technical change is applied but REPORT-INFRA delivery is blocked by Discord permissions.

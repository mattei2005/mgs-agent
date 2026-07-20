# Post-reload personalization audit

Use this reference when a successful cron completion causes concern that an update or migration overwrote Hermes profile customizations.

## Evidence layers

Treat these as separate claims:

1. **Intentional migration:** what changed between the pre-change backup and the validated candidate.
2. **Preservation:** whether the current live config is byte-identical to the validated candidate and, where applicable, its versioned mirror.
3. **Resolved behavior:** what Hermes currently resolves for selected safe keys.
4. **Runtime health:** whether the gateways are live and the MGS runtime patch remains applied.
5. **Delivery explanation:** why the cron result appeared in that conversation.

Do not substitute one layer for another. A service can be healthy with a wrong config; a mirror can match while runtime resolution uses another home; a green patch guard does not prove profile files were preserved.

## Comparison matrix

For each profile, identify:

- live: `/root/.hermes/config.yaml` or `/root/.hermes/profiles/<profile>/config.yaml`;
- validated candidate from the maintenance report directory;
- versioned mirror under `/root/mgs-agent/profiles/` when one exists;
- archived pre-change member inside the verified backup tarball.

Require both byte equality and parsed-YAML equality for live ↔ candidate and live ↔ mirror. Report hashes only as abbreviated evidence; never expose file contents wholesale.

## Safe pre/post diff

Read the backup member directly with Python `tarfile`; do not extract it over live paths. Parse YAML, flatten leaf paths, and compare the key union. Redact any path containing terms such as:

- `token`
- `secret`
- `password`
- `cookie`
- `credential`
- `api_key` / `apikey`
- `oauth`
- `authorization`

For lists and long strings, report type/length rather than values. The output should answer which settings changed without becoming a credential dump.

Typical intentional migration classes include:

- `_config_version` migration;
- model alignment;
- compression threshold alignment;
- explicit `agent.verify_on_stop=false`;
- removal of deprecated or null-only keys.

Preserved custom keys should be named only when useful, but preservation should be grounded in full-file equality rather than a hand-picked allowlist.

## Correct profile resolution

`HERMES_PROFILE=<name>` is not a reliable substitute for selecting the profile configuration home. For resolved reads, use:

```text
HERMES_HOME=/root/.hermes/profiles/<profile> hermes config get <safe.key> --json
```

Use `HERMES_HOME=/root/.hermes` for root. Validate only safe keys such as schema version, model, compression, progress mode, approval mode, session grouping, and background-notification policy.

Pitfall: if every profile unexpectedly returns the same values, the resolver is probably reading the same home. Stop and correct profile selection before drawing conclusions.

## Patch and service verification

- Require `git apply --reverse --check <canonical-patch>` to prove the customization patch is currently present and reversible.
- Run the canonical MGS guard when appropriate; record the real return code and concise final marker.
- Verify each gateway with systemd fields: `ActiveState`, `SubState`, `ExecMainStatus`, `NRestarts`, and `MainPID`.
- A previously successful cron result is historical evidence; live checks determine current state.

## Cron delivery classification

A generic `Cronjob Response` message may be the expected output of a one-shot post-reload validator delivered to its origin thread. Check whether the shown job still exists or is active. A `PASS` completion with no active recurring job is not a drift alert.

## Verification residue

Some guards create deterministic pytest cache markers whose filenames vary by run, leaving one tracked marker missing and one equivalent untracked marker present. Recheck the repository after testing. If both marker contents are identical and a rename restores the tracked path, restore the original path and require a clean status. Do not delete arbitrary files or use destructive Git cleanup; MGS Critical Subset rules still apply.

## Executive report shape

Lead with one sentence:

- whether changes occurred;
- whether they were intentional/authorized;
- whether any later drift or personalization loss exists.

Then give concise evidence:

- intentional key changes by profile;
- live/candidate/mirror equality count;
- resolved key status;
- patch guard and service health;
- why the cron message appeared;
- residual risk or unrun gate.

State explicitly that the audit itself did not modify configuration when true.

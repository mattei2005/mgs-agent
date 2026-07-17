# VPS OS package maintenance after Hermes update — 2026-07-05

Use when Hermes has already been updated/validated separately and Rodolfo asks to finish the remaining VPS/Ubuntu package maintenance.

## Validated workflow

1. Treat Hermes and OS packages as separate scopes. If Rodolfo says Hermes was already handled in another thread, do **not** re-run Hermes update; only verify `hermes --version` as part of final health.
2. Snapshot before mutating:
   - package versions for the specific upgradable packages;
   - `apt list --upgradable`;
   - gateway service status for Zeus/Atena/Ares/agente legado;
   - `node -v`, `npm -v`, `hermes --version`;
   - reboot flag.
3. Apply low-risk packages first with explicit package names rather than broad unattended `dist-upgrade`.
4. Distinguish **listed** updates from **currently eligible** updates before acting:
   - `apt list --upgradable` may list phased packages that normal APT will not install yet;
   - `apt-get -s upgrade` is the decisive check for what APT will apply now and may report `0 upgraded ... N not upgraded` even while `apt list` shows N entries;
   - filter the `WARNING: apt does not have a stable CLI interface` line before counting package rows;
   - if the approved scope says not to force phased updates, install only the explicitly eligible package names and leave the phased set documented as pending, not failed.
5. For packages initially kept back/deferred, run a simulation first:
   - `apt-get -s install --only-upgrade cloud-init fwupd`
   - verify it does not remove critical packages and only installs expected dependencies.
6. If Rodolfo explicitly says to finish everything, it is acceptable to clear a held-package change with:
   - `apt-get install -y --allow-change-held-packages --only-upgrade <packages>`
7. Cloud-init conffile pitfall: noninteractive upgrade can still fail at `/etc/cloud/cloud.cfg` prompt if the local file was modified. Preserve the current VPS config by repairing with:
   - `apt-get -y -o Dpkg::Options::='--force-confold' -f install`
   This keeps the local config and completes `dpkg` cleanly.
8. Validate after package work:
   - `apt list --upgradable` should be empty or only documented exceptions;
   - `apt-get -s upgrade` must distinguish installable updates from phased/deferred ones;
   - `dpkg --audit` should be empty;
   - exact package versions with `dpkg-query`;
   - gateways active;
   - no new gateway warnings after the maintenance window;
   - `needrestart -b` for kernel/services; if only a non-gateway service such as `unattended-upgrades.service` is stale, restart that service and revalidate rather than restarting Hermes gateways;
   - reboot flag.
9. Record audit event with package list, logs, remaining reboot state and validation result. If Monarx packages changed, update the existing `monarx-security-agent` versions in `data/infra-inventory.json`; do not create a duplicate inventory entry. Register the infra report in the dedicated channel when available, otherwise use the canonical audit-log fallback before declaring completion.

## Hermes/hardline pitfall

Hermes may hard-block `systemctl restart ...` or reboot/shutdown-like commands from the agent terminal. Do not fight this with loops. If package work is done and only kernel/service restart remains, report that the remaining action must be performed outside the agent, normally:

```bash
sudo reboot
```

Then validate after the VPS returns: current kernel matches expected, `apt list --upgradable` empty, `dpkg --audit` clean, Zeus/Atena/Ares/agente legado active, Hermes up to date, and recent gateway logs clean.

## Forced phased updates in controlled batches

When Rodolfo explicitly wants the VPS fully current instead of waiting for Ubuntu phased rollout:

1. Simulate each package group with explicit names and `apt-get -s install --only-upgrade ...`.
2. Require zero removals and zero unexpected new dependencies before mutation.
3. Snapshot exact package versions, gateway states, `dpkg --audit`, reboot flag, Node/npm/Corepack, and create rollback backup before the first batch.
4. Apply explicit batches instead of one broad command. Recommended risk isolation:
   - `apport` + Python helpers;
   - `libheif` + plugins;
   - `fwupd` + library;
   - `plymouth` + library/theme last.
5. After every batch, require empty `dpkg --audit` and Zeus/Atena/Ares/agente legado + cron/autocommit active. Stop on the first failed batch.
6. A phased package is not necessarily broken or held; explicit `--only-upgrade` opts into the candidate early. Keep this distinction in the report.

## Corepack/npm major update isolation

Treat global Node package-manager updates separately from APT even when the user says “update everything”:

1. Check target `engines.node` and registry shasum metadata before mutation.
2. Back up `/usr/lib/node_modules/npm` and `/usr/lib/node_modules/corepack` outside Git; verify archive and checksum; record current versions.
3. Upgrade Corepack first. Validate its exact version, Node/npm unchanged, and gateways active.
4. Upgrade npm major second. Validate exact version, `npm ping`, one real `npm exec` smoke, global prefix, `npm outdated -g`, and gateways.
5. Final acceptance requires APT pending `0`, npm global pending `{}`, no held packages, clean `dpkg`, zero failed units, and no reboot requirement unless documented.
6. Retain the rollback archive until post-maintenance validation is complete; never mix npm rollback troubleshooting with APT rollback.

Validated 2026-07-10: 12 phased Ubuntu packages were applied in four explicit batches after simulation; Corepack `0.34.6 → 0.35.0` and npm `10.9.8 → 12.0.0` were then updated independently with rollback backup and real smokes. Final state: APT `0`, npm outdated `{}`, gateways `4/4`, clean `dpkg`, no reboot.

## Reporting shape

Keep the final report executive:

- packages pending: count;
- `dpkg`: clean/dirty;
- agents: active/not active;
- Hermes/Node/npm versions;
- reboot required: yes/no;
- exact blocker if the agent cannot perform reboot/restart due hardline.

Do not present the remaining reboot as a package-update failure; classify it as the expected final activation step for kernel/service replacement.
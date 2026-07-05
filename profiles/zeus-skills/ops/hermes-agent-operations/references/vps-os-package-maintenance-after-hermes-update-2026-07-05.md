# VPS OS package maintenance after Hermes update — 2026-07-05

Use when Hermes has already been updated/validated separately and Rodolfo asks to finish the remaining VPS/Ubuntu package maintenance.

## Validated workflow

1. Treat Hermes and OS packages as separate scopes. If Rodolfo says Hermes was already handled in another thread, do **not** re-run Hermes update; only verify `hermes --version` as part of final health.
2. Snapshot before mutating:
   - package versions for the specific upgradable packages;
   - `apt list --upgradable`;
   - gateway service status for Zeus/Atena/Ares/Hera;
   - `node -v`, `npm -v`, `hermes --version`;
   - reboot flag.
3. Apply low-risk packages first with explicit package names rather than broad unattended `dist-upgrade`.
4. For packages initially kept back/deferred, run a simulation first:
   - `apt-get -s install --only-upgrade cloud-init fwupd`
   - verify it does not remove critical packages and only installs expected dependencies.
5. If Rodolfo explicitly says to finish everything, it is acceptable to clear a held-package change with:
   - `apt-get install -y --allow-change-held-packages --only-upgrade <packages>`
6. Cloud-init conffile pitfall: noninteractive upgrade can still fail at `/etc/cloud/cloud.cfg` prompt if the local file was modified. Preserve the current VPS config by repairing with:
   - `apt-get -y -o Dpkg::Options::='--force-confold' -f install`
   This keeps the local config and completes `dpkg` cleanly.
7. Validate after package work:
   - `apt list --upgradable` should be empty or only documented exceptions;
   - `dpkg --audit` should be empty;
   - exact package versions with `dpkg-query`;
   - gateways active;
   - no new gateway warnings after the maintenance window;
   - `needrestart -b` for kernel/services;
   - reboot flag.
8. Record audit event with package list, logs, remaining reboot state and validation result.

## Hermes/hardline pitfall

Hermes may hard-block `systemctl restart ...` or reboot/shutdown-like commands from the agent terminal. Do not fight this with loops. If package work is done and only kernel/service restart remains, report that the remaining action must be performed outside the agent, normally:

```bash
sudo reboot
```

Then validate after the VPS returns: current kernel matches expected, `apt list --upgradable` empty, `dpkg --audit` clean, Zeus/Atena/Ares/Hera active, Hermes up to date, and recent gateway logs clean.

## Reporting shape

Keep the final report executive:

- packages pending: count;
- `dpkg`: clean/dirty;
- agents: active/not active;
- Hermes/Node/npm versions;
- reboot required: yes/no;
- exact blocker if the agent cannot perform reboot/restart due hardline.

Do not present the remaining reboot as a package-update failure; classify it as the expected final activation step for kernel/service replacement.
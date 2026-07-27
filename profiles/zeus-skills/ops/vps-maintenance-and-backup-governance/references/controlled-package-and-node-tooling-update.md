# Controlled Package and Node Tooling Update

## Purpose

Execute a narrowly authorized VPS package/tooling update without turning a small patch into a broad `dist-upgrade`, an unplanned service restart, or an unverified npm self-update.

Use this after the audit has identified exact APT and global Node targets and Rodolfo has authorized the maintenance scope.

## 1. Freeze exact package identities

1. Refresh APT indexes.
2. Read `Installed` and `Candidate` from `apt-cache policy <package>`.
3. Use the **literal candidate string**, including vendor suffixes such as `-master`, in simulations and installs. Do not shorten `4.3.51-master` to `4.3.51`; APT treats them as different versions.
4. Simulate the exact command:

```bash
apt-get -s install --only-upgrade package=exact-candidate
```

Require the expected package count, zero removals, and no unexpected dependencies. Any candidate or transaction drift changes scope and stops execution.

For npm, capture current Node/npm/Corepack and query the exact target metadata:

```bash
npm view npm@TARGET version engines dist.shasum dist.integrity dist.tarball --json
```

Verify the live Node version satisfies `engines.node` before mutation.

## 2. Critical confirmation boundary

Before touching `/usr`, present:

- exact current and target versions;
- simulated APT transaction;
- npm/Node compatibility;
- rollback location and contents;
- whether services may restart;
- explicit statement that Hermes and reboot are outside scope unless separately authorized.

Do not treat a general “continue maintenance” as permission to add unrelated packages, restart a deferred system service, update Hermes, or reboot.

## 3. Build rollback before mutation

Create a mode-`0700` set under:

```text
/root/.hermes/secure-backups/vps-maintenance/<timestamp>/
```

Include:

- a tar.gz of `/usr/lib/node_modules/npm` and Corepack when present;
- a non-secret pre-state JSON with Node/npm/Corepack, exact package versions, service states/PIDs, reboot marker, and authorization message ID;
- the exact previous vendor `.deb` downloaded while it is still available.

Generate hashes in shell, then validate:

```bash
sha256sum archive > archive.sha256
sha256sum -c archive.sha256
tar -tzf archive >/dev/null
dpkg-deb -f previous.deb Version
```

Do not print configuration or credential contents.

## 4. Apply APT and npm as separate gates

### APT gate

Install only the simulated package/version with `--only-upgrade`, `--no-install-recommends`, noninteractive mode, and `--force-confold` when local conffiles must be preserved.

Immediately validate:

- exact `dpkg-query` version;
- target service active;
- empty `dpkg --audit`;
- zero unexpected APT candidates;
- Zeus/Atena/Ares active;
- gateway PIDs unchanged unless their restart was explicitly authorized;
- no priority 0..3 journal errors since the maintenance boundary.

Record the APT gate before proceeding to npm.

### npm gate

Before install, download the registry tarball to a temporary directory and verify it against the published shasum. Prefer the standard self-update first:

```bash
npm install -g npm@TARGET --no-audit --no-fund --no-progress
```

Use the manual verified-tarball replacement path only if the standard self-update fails; report both attempts. After success require:

- `npm -v` and npm `package.json` both equal the target;
- Node/Corepack unchanged unless included in scope;
- `npm ping` succeeds;
- a real `npm exec` smoke succeeds;
- `npm outdated -g --depth=0 --json` returns `{}`;
- gateways and the security service remain active.

## 5. Interpret needrestart without scope expansion

Run `needrestart -b` after the package work.

- Kernel current and no `/var/run/reboot-required` means no reboot is required.
- A deferred unrelated service such as `systemd-logind.service` is a **documented residual**, not permission to restart it.
- If that service was not named in the confirmed scope, report it and obtain separate authorization before restart—especially when SSH/user sessions may be affected.
- Do not call a clean package transaction failed solely because a separate deferred service remains.

## 6. Reconcile canonical services and inventory

Do not guess unit names. Resolve operational services from `data/infra-inventory.json` and live systemd readback; for example, the active MGS auto-commit unit may differ from an assumed name.

When Monarx changes:

- update the existing `monarx-security-agent` inventory entry rather than adding a duplicate;
- reconcile all Monarx package versions against `dpkg-query`;
- use APT history to attribute versions changed earlier by the weekly vendor cron.

Update the existing VPS runtime baseline with npm/Corepack, rollback path, validation gates, residuals, and authorization IDs. Finish with audit readback and canonical REPORT-INFRA.

## Acceptance summary

A successful narrow maintenance reports:

- exact before/after versions;
- APT pending `0`, npm outdated `{}`, clean dpkg, no holds;
- gateway PIDs and security service state;
- rollback integrity;
- kernel/reboot status;
- deferred services separately;
- Hermes explicitly unchanged when outside scope.

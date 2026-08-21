# Provider plan resize and phased package maintenance

Use when a VPS plan upgrade changes vCPU, RAM, or disk and the same window includes “update everything” plus an owner-requested reboot.

## Validate the provider resize from the guest

1. Capture a fresh boot boundary and live resources: `hostnamectl`, `nproc`/`lscpu`, `free`, `lsblk`, `df`, boot ID and uptime. Provider labels are secondary; guest runtime is authoritative for what the OS can use.
2. Compare with the last grounded pre-upgrade observation, naming raw before/after values rather than assuming the marketed plan specification.
3. Prove the root filesystem expanded, not only the virtual block device. Check disk, partition and mounted filesystem sizes separately.
4. Reconcile GPT warnings against current state. A boot-time “correct GPT errors” warning after a disk resize can be stale if cloud tooling repaired it later. Use read-only `sgdisk -v`, `parted ... print free`, and `fdisk -l`; report a current defect only when those live checks still fail. Alignment cautions with `No problems found` are not a broken GPT.
5. Verify all required services after the provider-triggered boot, zero failed units, kernel/OOM state, disk latency and resource pressure.

## Turn “update everything” into a frozen APT transaction

1. Refresh indexes, enumerate every `apt list --upgradable` row, and resolve literal installed/candidate versions with `apt-cache policy`.
2. Separate standard security, regular Ubuntu, third-party/vendor and phased candidates in the report.
3. When the owner explicitly authorizes **all** APT candidates, include phased packages only through a frozen exact-version transaction and:
   - `APT::Get::Always-Include-Phased-Updates=true`;
   - `--only-upgrade`;
   - `--no-install-recommends`;
   - `--force-confold` for local conffiles.
4. Simulate the exact package/version vector and require the authorized count, zero new packages, zero removals and zero held-back packages. Candidate drift stops execution.
5. Keep application lifecycle separate: “everything on the VPS” in an OS-maintenance thread does not silently authorize a large Hermes port that was explicitly reported as a separate controlled application update.

## Rollback and validation

- Create a mode-0700 secure maintenance set with package targets, simulation, pre-state, service PIDs, boot ID, kernel, Hermes launcher/HEAD, gateway log offsets and authorization message ID.
- Download the exact previous vendor packages while still available, validate their `Package`/`Version` metadata, then hash and verify the complete set with shell `sha256sum`.
- After installation require exact version readback for every target, APT pending zero, no holds, clean `dpkg --audit`, current/expected kernel agreement, services active, zero failed units and no new priority 0..3 errors.
- Do not run `apt autoremove` merely because simulation lists old automatic dependencies.
- An owner may request a reboot even when the package graph does not require one. Treat that as a separately authorized host cycle and still use the durable post-boot validator; do not manufacture a reboot marker.

## MGS evidence — 2026-08-20

A Hostinger plan resize was confirmed live as 4 vCPU, 15.6 GiB RAM and a 200 GiB disk with the root partition/filesystem expanded. Current GPT verification returned `No problems found` despite a boot-time warning. A frozen 23-package transaction (16 standard security, two Monarx, one regular Ubuntu and four phased candidates) simulated as `23 upgraded / 0 new / 0 removed / 0 held`, installed successfully, and passed exact-version/APT/service pre-boot checks. Preserve only this validated pre-boot evidence here; post-boot closure belongs in its result artifact.

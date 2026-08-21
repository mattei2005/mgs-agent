# KVM resize, full package closure, and audit JSONL repair

Use this reference when a provider plan upgrade changes vCPU/RAM/disk, the owner requests every eligible VPS package including phased candidates, or post-maintenance governance is blocked by binary/structural corruption in an append-only JSONL audit.

## 1. Verify a provider resize from the guest

Treat live guest state as authoritative; a provider plan label is supporting context only.

1. Capture a new observation timestamp and boot ID.
2. Read `nproc`/`lscpu`, `free`, `lsblk`, `df -hT`, and inode usage.
3. Prove the root partition and filesystem both grew; a larger virtual disk alone is not sufficient.
4. Check `journalctl -b` for resize/GPT warnings, then validate current state with `sgdisk -v`, `parted ... print free`, and `fdisk -l` before calling it a disk problem. A warning emitted early in boot may already have been closed by cloud-init/growpart.
5. Require current GPT validation, expected capacity, low pressure, no OOM, zero failed units, and all MGS services active.

## 2. Interpret “update everything” with phased APT candidates

Normal `apt-get full-upgrade` can defer phased packages. If Rodolfo explicitly asks for every eligible VPS package:

1. Freeze every `apt list --upgradable` package with literal installed/candidate versions.
2. Simulate one exact transaction using `--only-upgrade --no-install-recommends`, explicit `package=version` targets, and `-o APT::Get::Always-Include-Phased-Updates=true`.
3. Require the exact authorized count and `0 newly installed / 0 removed / 0 not upgraded`.
4. Keep application lifecycle separate: “everything on the VPS” does not make a large locally patched Hermes port a routine APT transaction. State the boundary before mutation and preserve the active launcher/HEAD.
5. Preserve previous vendor `.deb` files while still published. Validate package metadata plus SHA-256; do not downgrade merely because rollback artifacts exist.
6. After installation require exact version readback for every target, APT pending zero, no holds, clean `dpkg --audit`, current/expected kernel agreement, gateway PID preservation unless separately authorized, and no new priority 0..3 journal errors.

## 3. Durable host cycle after packages

Even when no kernel marker requires a cycle, an explicitly authorized host cycle still uses the durable validator pattern.

- Freeze boot ID, package targets, launcher/HEAD, service states, gateway log offsets, `/tmp` mode, and hashes.
- The dispatch finalizer revalidates hashes, package state, APT zero, validator enabled, protected services active, and the unchanged boot ID before issuing the host cycle.
- The post-boot validator must separate **technical checks** from **governance checks** in its result.
- A self-removing one-shot that exits nonzero for a governance-only residual leaves a `not-found/failed` unit in systemd even after its file is gone. Do not report zero failed units from a check taken before the validator exits. Acceptance requires a second read after exit; an external cleanup step may run `systemctl reset-failed <unit>` only when the unit file is absent, the intended validator result is already durable, and no technical service failed.
- Report technical package/boot success plainly while keeping governance residuals separate; never imply the packages failed because an audit/report artifact needs repair.

## 4. Exact repair of NUL bytes in append-only JSONL

Removing bytes from the canonical audit is destructive and requires Critical Subset confirmation bound to an exact byte range/count.

### Freeze and back up

1. Read the file as bytes; locate every contiguous NUL run and count total NUL bytes.
2. Confirm the authorized run is unchanged immediately before mutation.
3. Create a mode-`0700` secure backup set with a mode-`0600` byte-identical copy and manifest.
4. Generate and verify SHA-256 with shell.

### Atomic rewrite without losing concurrent appends

1. Re-read the live file after backup.
2. Accept only either byte identity with the backup or an append-only suffix; abort on any earlier-byte drift.
3. Reconfirm the exact NUL range/count.
4. Build `clean = current[:start] + current[end:]` in a same-directory temporary file.
5. Flush/fsync the temp file, preserve mode, then perform a last live-byte equality check immediately before `os.replace`.
6. Fsync the directory after promotion.
7. Verify exact size delta, zero NULs, and `clean == current.replace(b"\x00", b"")`; this proves every non-NUL byte was preserved.
8. Hash the repaired live file and the repair result; revalidate the original backup hashes.

Any concurrent append detected after the working read aborts the promotion and restarts from a new freeze. Never truncate to the last valid line or drop malformed historical records as an incidental NUL repair.

## 5. Full JSONL validation is a new scope boundary

After the byte repair, parse every non-empty line independently and report all historical invalid lines. Do not silently normalize them under the NUL authorization.

Safe classification patterns:

- A plain legacy text line can be wrapped in a JSON record that preserves the raw text.
- A multi-line legacy REPORT block can become one structured JSON record preserving every field/text value.
- A line containing multiple JSON objects separated by literal `\\n` may be split only after every segment independently passes `json.loads`.
- Any ambiguous or semantically lossy transformation requires a new confirmation and a fresh backup.

Closure requires: repaired bytes/hash readback, whole-file parse result, checkpoint/inventory update, canonical REPORT-INFRA, Git sync where applicable, and an explicit residual if other invalid historical lines remain.
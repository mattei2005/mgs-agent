# Hostinger VPS agent migration bootstrap — MGS

Use when Rodolfo has provisioned a fresh Hostinger VPS for moving one or more MGS Hermes agents.

## Recommendation pattern

Default migration order is canary-first, not all-at-once:

1. Move **Ares first** as the canary when the driver is Growth/browser/AdsPower/Meta tooling.
2. Keep **Zeus last** because Zeus is the control plane/orchestrator and should not be the first system moved.
3. Keep **Atena stable** until the new VPS is proven, because Atena owns editorial/WordPress production and crons.
4. Consider agente legado after Ares if the VPS will also host browser/creative tooling.

## First response shape

Give a numbered plan and a direct recommendation. Keep it short:

1. Prepare Hostinger VPS.
2. Install base MGS/Hermes dependencies.
3. Migrate only Ares.
4. Validate Ares in Discord.
5. Add AdsPower/MCP after Ares is alive.
6. Run parallel for 24–48h.
7. Migrate agente legado/Atena later if warranted.
8. Migrate Zeus last.

## Access handling

- Never ask Rodolfo to paste passwords/tokens in Discord.
- Ask him to store the credential in 1Password and provide the item name.
- Confirm credential presence by item/title/field length only; never print the secret.
- If the screenshot shows only masked password bullets, treat it as proof of item existence, not usable credential.

## Safe initial inventory

Before mutating the VPS, do a read-only SSH inventory:

- hostname
- user
- date/timezone
- `/etc/os-release`
- `uname -a`
- CPU cores
- RAM
- root disk and inode usage
- IPs/default route
- SSH service state
- APT locks
- uptime
- listening TCP ports

Use password automation only internally and redact the password in any captured output. A durable pattern is Python `pexpect` that obtains the password from `op item get ... --fields '<password field>' --reveal`, uses it for SSH, and replaces the secret with `[REDACTED]` before printing.

## Critical confirmation boundary

Installing packages, setting timezone, changing system config, modifying `/etc`, firewall, Fail2Ban or `sshd_config` crosses into system state. For MGS, pause after inventory and ask for explicit confirmation before bootstrap.

For the first bootstrap, prefer **no firewall/SSH hardening yet** unless Rodolfo explicitly asks. State that you will not change:

- SSH port
- password login
- firewall
- `sshd_config`
- root password

## Bootstrap base scope

Safe base bootstrap for a fresh Hostinger VPS:

1. `apt-get update`
2. `apt-get -y upgrade`
3. install base packages: `ca-certificates curl gnupg lsb-release git jq unzip zip rsync htop tmux nano build-essential python3 python3-venv python3-pip openssh-client nodejs npm`
4. install 1Password CLI if missing
5. install `uv` if missing
6. set timezone to `America/New_York`
7. create base directories: `/root/mgs-agent`, `/root/mgs-agent/logs`, `/root/mgs-agent/backups`, `/root/mgs-agent/tmp`, `/root/.hermes/profiles`
8. validate versions and disk
9. report whether reboot is required

## Validation/report fields

Final report should include:

- IP/hostname
- OS
- CPU/RAM
- disk before/after
- timezone
- SSH state
- installed component versions: git, node, npm, python3, uv, op
- reboot required: yes/no
- remote bootstrap log path
- what was deliberately not changed

## Next step after bootstrap

After base bootstrap, move to Ares canary:

1. Install Hermes Agent.
2. Copy/clone `/root/mgs-agent`.
3. Copy only `/root/.hermes/profiles/ares/` plus needed config/SOUL/skills.
4. Transfer Codex GPT-5.5 auth securely without printing tokens.
5. Create `ares-gateway.service` only after config is present.
6. Validate live Discord response.
7. Decide whether old Ares is paused or kept standby.

Do not start with AdsPower/MCP before Ares is alive; AdsPower is phase two after the agent runtime works.
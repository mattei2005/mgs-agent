---
name: ssh-jump-runcloud
description: >
  RunCloud server access umbrella: deploy files and run commands on RunCloud servers.
  Primary path: SSH ProxyJump S03→S01 via expect scripts (for machines where direct SSH
  from mgs-agent works through S03). Fallback path: WP Plugin Editor form POST when
  SSH is fully blocked by Cloudflare (e.g. eggbev). Also covers persisting rules to
  Atena's SOUL.md (edit, sync to mgs-agent repo, commit, push with 1Password token).
  See references/ for full workflows.
tags: [ssh, runcloud, eggbev, deploy, jump-host, expect, wp-admin, plugin-editor]
related_skills: [yoast-wordpress]
---

# SSH Jump — RunCloud S03 → S01

## Context

RunCloud Server 01 (162.55.28.178) hosts eggbev and has direct SSH blocked from
the mgs-agent machine. Server 03 (46.4.95.117) can reach S01, so it acts as jump host.

- S01 (target): 162.55.28.178 — hosts eggbev, wantabrand, receitasdescomplicada, etc.
- S02 (irrelevant): 162.55.28.179 — different sites
- S03 (jump host): 46.4.95.117 — can reach S01 on port 22

All credentials in 1Password vault `MGS Conteúdo`:
- S01: item `Runcloud Server 01 - 162.55.28.178- zeus Acesso`, field `password`
- S03: item `Runcloud Server 03 - 46.4.95.117- zeus Acesso`, field `password`
- All use user `zeus`

**IMPORTANT:** `sshpass` is NOT available on S03. Use SSH ProxyJump (`-J`) natively
from the mgs-agent machine with expect scripts to handle both password prompts.

## Pitfalls

- S01 shows ALL ports blocked from mgs-agent (22, 2222, 8022, 443, 34210 all CLOSED)
- S03 port 22 is open from mgs-agent ✓
- `sshpass` not on S03 → can't chain sshpass inside an SSH session
- `expect` single-quotes inside heredoc cause parsing errors — use `[lindex $argv N]` for passwords
- The S01 MOTD ends with "Made with ♥ by RunCloud Team" — use `expect "Made with"` then `sleep 3` to wait for shell prompt
- Shell prompt on S01 is `zeus@MatteiInc01:~$ ` — not a simple `$` pattern; use `sleep N` after commands instead of pattern-matching the prompt
- `sudo cat /path/to/wp-config.php` returns "Permission denied" for zeus — use `sudo -u runcloud` for WP CLI commands
- `wp db tables '*yoast*'` may return empty even if Yoast is installed (see yoast-score-architecture skill)

## Step-by-step: Copy a file to S01

```bash
# 1. Load credentials
set -a && . /root/mgs-agent/.env && set +a
S03_PASS=$(op item get 'Runcloud Server 03 - 46.4.95.117- zeus Acesso' \
  --vault 'MGS Conteúdo' --fields password --reveal)
S01_PASS=$(op item get 'Runcloud Server 01 - 162.55.28.178- zeus Acesso' \
  --vault 'MGS Conteúdo' --fields password --reveal)

# 2. Write expect script for SCP
cat > /tmp/scp_jump.exp << 'EOFEXP'
#!/usr/bin/expect -f
set s03 [lindex $argv 0]
set s01 [lindex $argv 1]
set timeout 30
spawn scp -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=/root/.ssh/known_hosts_mgs \
  -J zeus@46.4.95.117 \
  /local/path/to/file.php \
  zeus@162.55.28.178:/tmp/file.php
expect "46.4.95.117's password:"
send "$s03\r"
expect "162.55.28.178's password:"
send "$s01\r"
expect {
    "100%" { puts "SCP SUCCESS"; exp_continue }
    eof {}
}
EOFEXP
chmod +x /tmp/scp_jump.exp

# 3. Run SCP
/tmp/scp_jump.exp "$S03_PASS" "$S01_PASS"
```

## Step-by-step: Run a command on S01

```bash
# Write a shell script to /tmp first, SCP it, then execute via expect SSH

# 1. Write the remote script locally
cat > /tmp/remote_cmd.sh << 'EOF'
#!/bin/bash
# your command here, e.g.:
sudo cp /tmp/file.php /home/runcloud/webapps/eggbev/wp-content/mu-plugins/file.php && echo OK
EOF
chmod +x /tmp/remote_cmd.sh

# 2. SCP the script (use scp_jump.exp pattern above, change paths)

# 3. Execute via SSH expect
cat > /tmp/run_remote.exp << 'EOFEXP'
#!/usr/bin/expect -f
set s03 [lindex $argv 0]
set s01 [lindex $argv 1]
set timeout 60

spawn ssh -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=/root/.ssh/known_hosts_mgs -J zeus@46.4.95.117 zeus@162.55.28.178
expect "46.4.95.117's password:"
send "$s03\r"
expect "162.55.28.178's password:"
send "$s01\r"
expect "Made with"
sleep 3
send "bash /tmp/remote_cmd.sh\n"
sleep 10        # adjust based on command duration
send "exit\r"
expect eof
EOFEXP
chmod +x /tmp/run_remote.exp
/tmp/run_remote.exp "$S03_PASS" "$S01_PASS"
```

## Full deploy workflow (deploy file + verify)

```bash
cat > /tmp/deploy_full.sh << 'EOFEXP'
#!/bin/bash
set -a && . /root/mgs-agent/.env && set +a
S03_PASS=$(op item get 'Runcloud Server 03 - 46.4.95.117- zeus Acesso' --vault 'MGS Conteúdo' --fields password --reveal)
S01_PASS=$(op item get 'Runcloud Server 01 - 162.55.28.178- zeus Acesso' --vault 'MGS Conteúdo' --fields password --reveal)

# Step 1: SCP file
KNOWN_HOSTS_FILE="/root/.ssh/known_hosts_mgs"
mkdir -p /root/.ssh && chmod 700 /root/.ssh
: > "$KNOWN_HOSTS_FILE" && chmod 600 "$KNOWN_HOSTS_FILE"
TMP_DIR="$(mktemp -d /tmp/runcloud-deploy.XXXXXX)"
trap 'rm -rf "$TMP_DIR"' EXIT
cat > "$TMP_DIR/scp.exp" << 'EOF'
#!/usr/bin/expect -f
set s03 [lindex $argv 0]; set s01 [lindex $argv 1]; set known_hosts [lindex $argv 2]; set timeout 30
spawn scp -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=$known_hosts -J zeus@46.4.95.117 /tmp/myfile.php zeus@162.55.28.178:/tmp/myfile.php
expect "46.4.95.117's password:"; send "$s03\r"
expect "162.55.28.178's password:"; send "$s01\r"
expect { "100%" { exp_continue } eof {} }
EOF
chmod +x "$TMP_DIR/scp.exp" && "$TMP_DIR/scp.exp" "$S03_PASS" "$S01_PASS" "$KNOWN_HOSTS_FILE"

# Step 2: Deploy + verify
cat > /tmp/verify.sh << 'EOF'
#!/bin/bash
TARGET="/home/runcloud/webapps/eggbev/wp-content/mu-plugins/myfile.php"
sudo cp /tmp/myfile.php "$TARGET" && echo COPY_OK
sudo md5sum "$TARGET" /tmp/myfile.php
sudo grep -c 'update_post_meta' "$TARGET" && echo HAS_META || echo NO_META
EOF
scp + exec as above...
EOFEXP
```

## Verification commands (run on S01 via expect SSH)

```bash
# Find webapps on S01
sudo ls /home/runcloud/webapps/ 2>&1

# Find specific file
sudo find /home -maxdepth 6 -name 'myfile.php' 2>/dev/null

# Check WP plugins (as runcloud user)
sudo -u runcloud wp --path=/home/runcloud/webapps/eggbev plugin list 2>&1

# Check WP DB tables
sudo -u runcloud wp --path=/home/runcloud/webapps/eggbev db tables --all-tables 2>&1
```

---

## § Fallback: Deploy Without SSH (WP Plugin Editor)

When S01's SSH is fully blocked via Cloudflare (all ports 22/2222/8022/443 closed
from mgs-agent), files can be deployed via the **WP admin Plugin Editor form POST**,
which writes to the filesystem using the WP Filesystem API.

**Prerequisites:** Admin credentials (regular password, NOT Application Password),
custom login URL (WPS Hide Login), Plugin Editor not disabled (`DISALLOW_FILE_EDIT`).

**Critical pitfalls:**
- Application Passwords rejected for form login — use real password from 1Password
- `admin-ajax edit-theme-plugin-file` nonces expire too fast — use the form POST (step 3)
- WPS Hide Login: standard `wp-login.php` returns 404 — find slug in 1Password or `whl_page` option
- `REST POST /wp/v2/plugins` only accepts wordpress.org slugs — cannot upload arbitrary ZIPs
- `die()` in injected PHP returns HTTP 500 — execution still happened, read result via WP option

See `references/wp-deploy-file-without-ssh.md` for full Python workflow (steps 1–5),
bootstrap technique (execute PHP + store result via WP option), eggbev-specific
credentials, and a table of approaches already tried-and-failed (saves rework).

---

## § Manage Agent Identity (SOUL.md)

When a rule must survive model resets and upgrades. `memory.jsonl` is volatile —
SOUL.md is the permanent identity file for Atena.

### File locations

| Role | Path |
|---|---|
| Live SOUL.md (Atena) | `/root/.hermes/profiles/atena/SOUL.md` |
| Repo mirror (Atena) | `/root/mgs-agent/profiles/atena-soul.md` |
| Sync script | `/root/mgs-agent/scripts/sync-souls.sh` |

### Steps

**1. Capture MD5 before editing**
```bash
md5sum /root/.hermes/profiles/atena/SOUL.md
```

**2. Find insertion point**
```bash
read_file("/root/.hermes/profiles/atena/SOUL.md", offset=270, limit=15)
```

**3. Edit via patch** — use `mcp_patch` to append the new rule after the last meaningful line.

**4. Validate with grep**
```bash
grep -n -iE "keyword" /root/.hermes/profiles/atena/SOUL.md
```

**5. Sync to repo**
```bash
bash /root/mgs-agent/scripts/sync-souls.sh
# Verify MD5s match:
md5sum /root/.hermes/profiles/atena/SOUL.md
md5sum /root/mgs-agent/profiles/atena-soul.md
```

**6. Commit + push with 1Password token**
```bash
cd /root/mgs-agent
git add profiles/atena-soul.md
git commit -m "docs(soul/atena): <description>"
set -a && . /root/mgs-agent/.env && set +a
TOKEN=$(op item get 'GitHub PAT - mgs-agent' --vault 'MGS Conteúdo' --fields github_token --reveal 2>/dev/null)
git push "https://$TOKEN@github.com/mattei2005/mgs-agent.git" main
```

**Pitfalls:**
- `~/.hermes/` is NOT a git repo — commits go to `/root/mgs-agent/`
- `profiles/atena-soul.md` in repo ≠ `~/.hermes/profiles/atena/SOUL.md` — always sync via script first
- `sync-souls.sh` only copies if source is newer — force with `cp` directly if timestamps are wrong
- 1Password field is `github_token` (not `credential` or `password`) — wrong name returns empty string silently
- `git push` may say "Everything up-to-date" if auto-process already pushed — verify with `git log --oneline -3`

**Reporting format:** MD5 before/after · grep match counts · commit hash · push status

---

## Server → webapp mapping (verified 2026-04-24)

| Server | IP | Webapps include |
|--------|-----|-----------------|
| S01 | 162.55.28.178 | eggbev, wantabrand, receitasdescomplicada, newsfolha, topfeed, vagaaqui, lyzmo, ... |
| S02 | 162.55.28.179 | autocreditadxx, autolendpro, carcreditad, creditoparaveiculo, gamingadx, ... |
| S03 | 46.4.95.117 | xyvlov, escalatepower, marevelx, ducapes-finance, FinanceADX, cephyric, ... |

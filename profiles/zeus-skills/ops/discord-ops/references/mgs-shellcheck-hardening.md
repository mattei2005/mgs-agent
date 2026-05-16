# MGS ShellCheck hardening pattern

Use when continuing a repo hardening pass and Rodolfo asks for lint/deeper Bash review after functional fixes are already stable.

## Scope

- Install ShellCheck only after the user has approved the non-critical linting step.
- Audit tracked Bash/sh scripts, excluding runtime/history areas such as `data/` and `backups/` unless the task is explicitly about archived scripts.
- Treat ShellCheck as a safety net, not as permission to refactor broadly.

## Commands

```bash
cd /root/mgs-agent

# Discovery
command -v shellcheck >/dev/null && shellcheck --version || echo missing

# Install on Ubuntu when approved
apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y shellcheck

# Build audited file list: tracked shell scripts, excluding data/backups
python3 - <<'PY'
import pathlib, subprocess
tracked = subprocess.check_output(['git','ls-files'], text=True).splitlines()
files = []
for f in tracked:
    p = pathlib.Path(f)
    if not p.is_file() or f.startswith(('data/','backups/')):
        continue
    first = p.open('r', encoding='utf-8', errors='ignore').readline()
    if (first.startswith('#!') and ('bash' in first or 'sh' in first)) or f.endswith('.sh'):
        files.append(f)
print('\n'.join(files))
PY
```

## Validation pattern

Use JSON output to classify findings. Prioritize `error` and `warning`; leave `note/info/style` alone unless they indicate a real operational issue.

```bash
python3 - <<'PY'
import subprocess, pathlib, collections, json
tracked = subprocess.check_output(['git','ls-files'], text=True).splitlines()
files = []
for f in tracked:
    p = pathlib.Path(f)
    if not p.is_file() or f.startswith(('data/','backups/')):
        continue
    first = p.open('r', encoding='utf-8', errors='ignore').readline()
    if (first.startswith('#!') and ('bash' in first or 'sh' in first)) or f.endswith('.sh'):
        files.append(f)
subprocess.check_call(['bash','-n',*files])
summary=[]; counts=collections.Counter(); notes=0
for f in files:
    proc=subprocess.run(['shellcheck','--format=json',f], text=True, capture_output=True)
    comments=[]
    if proc.stdout.strip():
        data=json.loads(proc.stdout); comments=data if isinstance(data,list) else data.get('comments',[])
    actionable=[c for c in comments if c.get('level') in ('error','warning')]
    notes += sum(1 for c in comments if c.get('level') not in ('error','warning'))
    if actionable:
        for c in actionable: counts[str(c.get('code'))]+=1
        summary.append((f,len(actionable),[(c.get('line'),c.get('code'),c.get('level'),c.get('message')) for c in actionable[:8]]))
print('bash_scripts=%s' % len(files))
print('shellcheck_error_warning=%s' % sum(n for _,n,_ in summary))
print('shellcheck_notes_info_style=%s' % notes)
for f,n,samples in summary:
    print(f'FILE {f} findings={n}')
    for line,code,level,msg in samples:
        print(f'  L{line} SC{code} {level}: {msg}')
PY
```

## Fix patterns proven useful

- `SC2259` with `cmd | python3 <<'PY'`: heredoc overrides piped stdin. Fix by passing the file path as an argument and reading it inside Python, or pass data via an environment variable/temporary file. Do not leave a pipe that Python never reads.
- `SC2086` on numeric `find -mtime +$N`: quote as `-mtime +"$N"`.
- `SC2064` in cleanup traps: use a single-quoted trap that expands variables at signal/return time, e.g. `trap 'rm -f "$temp_cred"' RETURN` when the variable is local and still in scope.
- `SC2034` unused loop variables: rename to `_attempt` or remove unused assignments when harmless.
- `SC2034` in legacy/deprecated scripts: prefer a scoped `# shellcheck disable=SC2034` with a comment explaining compatibility, rather than refactoring old runtime blindly.
- Quote file arguments passed to `jq`, `du`, `rm`, and similar tools when ShellCheck flags word splitting.

## Guardrails

- Do not chase every `SC1091` for sourced `.env`/helper files; add `# shellcheck source=/dev/null` only when it improves signal.
- Do not alter credentials, payloads, or webhook routing just to satisfy lint.
- Do not run destructive scripts as validation. Prefer `--dry-run`, `bash -n`, fake fixtures, or service status checks.
- Report notes/info/style separately from error/warning; Rodolfo wants the risk split, not a noisy undifferentiated lint dump.

## Minimal final report fields

```text
ShellCheck version
Tracked Bash scripts checked
error/warning count
notes/info/style count
bash -n result
any dry-runs used
services status
Git status / commits
Próximo passo pendente
```

# Atena/OpenHands provider diagnostic — 2026-05-26

Use when Atena claims OpenHands is fixed/working, or when Rodolfo asks whether Atena still has operational failures.

## Durable lesson

OpenHands can be technically working while violating MGS cost policy if it is wired to Anthropic/Sonnet via a 1Password API key. Treat “OPENHANDS_OK” as only a functionality smoke; also verify provider/model and persistence/audit state.

## Read-only checks

```bash
# Atena gateway and Codex auth
systemctl is-active atena-gateway.service
python3 - <<'PY'
import json, os, time
for path in ['/root/.hermes/profiles/atena/auth.json','/root/.hermes/profiles/zeus/auth.json']:
    d=json.load(open(path)); p=d.get('providers',{}).get('openai-codex',{}); t=p.get('tokens',{}) if isinstance(p,dict) else {}
    print(path)
    print(' active_provider=', d.get('active_provider'))
    print(' codex_access_token_len=', len(t.get('access_token') or ''))
    print(' codex_refresh_present=', bool(t.get('refresh_token')))
    print(' mtime=', time.strftime('%Y-%m-%d %H:%M:%S %Z', time.localtime(os.path.getmtime(path))))
PY

# OpenHands binary and wrapper static state
OPENHANDS_SUPPRESS_BANNER=1 openhands --version 2>/dev/null || true
bash -n /root/mgs-agent/scripts/run-openhands-atena.sh
stat -c 'mode=%a owner=%U group=%G size=%s mtime=%y' /root/mgs-agent/scripts/run-openhands-atena.sh

# Wrapper model/provider without printing credentials
grep -nE 'LLM_MODEL|Anthropic API Key|LLM_API_KEY|LLM_BASE_URL|openrouter|openai|anthropic' \
  /root/mgs-agent/scripts/run-openhands-atena.sh

# Saved OpenHands trajectories under Atena profile; do not print api_key values
python3 - <<'PY'
import os, glob, json, time, re
base='/root/.hermes/profiles/atena/home/.openhands/conversations'
for d in sorted(glob.glob(base+'/*'), key=os.path.getmtime, reverse=True)[:8]:
    bs=os.path.join(d,'base_state.json')
    model=key_len=final=None
    if os.path.exists(bs):
        txt=open(bs,errors='ignore').read()
        try:
            j=json.loads(txt); llm=j.get('agent',{}).get('llm',{})
            model=llm.get('model')
            key=llm.get('api_key') or ''
            key_len='masked' if key=='***' else len(key)
        except Exception:
            m=re.search(r'"model"\s*:\s*"([^"]+)"',txt); model=m.group(1) if m else None
    evs=sorted(glob.glob(os.path.join(d,'events','*.json')))
    for ev in evs[-6:]:
        try:
            e=json.load(open(ev))
            if e.get('kind')=='ActionEvent' and e.get('action',{}).get('kind')=='FinishAction':
                final=(e.get('action',{}).get('message') or '')[:180].replace('\n',' ')
        except Exception: pass
    print(time.strftime('%Y-%m-%d %H:%M:%S %Z', time.localtime(os.path.getmtime(d))), os.path.basename(d), 'model=',model,'api_key_len=',key_len,'events=',len(evs),'final=',final)
PY

# Versioning/audit state
git -C /root/mgs-agent status --short -- scripts/run-openhands-atena.sh profiles/atena-skills profiles/atena-soul.md
```

## Findings to flag

- `LLM_MODEL=anthropic/claude-*` or saved trajectories with `model=anthropic/claude-*` are a cost/governance finding unless Rodolfo explicitly authorized Anthropic API usage for this task.
- A new wrapper under `/root/mgs-agent/scripts/` that is untracked or not reported via REPORT-INFRA is an auditability finding.
- A skill changed only under `/root/.hermes/profiles/atena/skills/...` without sync/versioning is a traceability finding.
- `OPENHANDS_OK` proves the CLI can call a model; it does **not** prove the model/provider is policy-compliant.

## Recommended correction shape

1. Stop using native Anthropic/Sonnet API as Atena’s default OpenHands backend unless Rodolfo explicitly approves cost.
2. Prefer an approved no/low incremental cost backend for OpenHands, or leave OpenHands disabled with a clear preflight failure instead of silently falling back to Anthropic.
3. Keep wrapper scripts in `/root/mgs-agent/scripts/`, run `bash -n`, and ensure they are versioned/reported.
4. Update the Atena OpenHands skill only with provider-neutral instructions plus the MGS policy caveat.
5. Validate with both a smoke (`OPENHANDS_OK`) and provider audit (saved trajectory model/base URL, no credential leakage).

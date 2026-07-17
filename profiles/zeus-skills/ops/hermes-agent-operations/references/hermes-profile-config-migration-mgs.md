# Controlled profile config migration after Hermes update

Use this when Hermes reports profiles with an older `_config_version` after an update, especially for MGS profiles Zeus/Atena/Ares/agente legado.

## Decision rule

Config migration is usually safe when:

- A current backup exists or is created first.
- Critical MGS fields are checked before/after: provider, model, Discord routing, Codex OAuth presence, Anthropic absence, patch guard, gateways.
- Migration is run profile-by-profile and outputs are sanitized.

Do not assume config migration is equivalent to a provider/model change. It primarily writes new defaults and bumps `_config_version`, but still treat it as an operational config write.

## Recommended workflow

1. Create a small rollback backup of critical profile files:

```bash
stamp=$(date +%Y%m%d-%H%M%S)
backup="/root/hermes-config-soul-auth-pre-migrate-${stamp}.tar.gz"
tar -czf "$backup" \
  /root/.hermes/profiles/zeus/config.yaml /root/.hermes/profiles/zeus/SOUL.md /root/.hermes/profiles/zeus/auth.json \
  /root/.hermes/profiles/atena/config.yaml /root/.hermes/profiles/atena/SOUL.md /root/.hermes/profiles/atena/auth.json \
  /root/.hermes/profiles/ares/config.yaml /root/.hermes/profiles/ares/SOUL.md /root/.hermes/profiles/ares/auth.json \
  /root/.hermes/profiles/legacy-agent/config.yaml /root/.hermes/profiles/legacy-agent/SOUL.md /root/.hermes/profiles/legacy-agent/auth.json

tar -tzf "$backup" >/dev/null
```

Prefer this targeted backup over a live full-profile tar when agents are active; full-profile backups can warn `file changed as we read it` and may be slow/noisy.

2. Snapshot configs for diff:

```bash
for p in zeus atena ares legacy-agent; do
  cp "/root/.hermes/profiles/$p/config.yaml" "/tmp/${p}-config-before-${stamp}.yaml"
done
```

3. Run migration for only outdated profiles:

```bash
for p in atena ares legacy-agent; do
  hermes -p "$p" config migrate 2>&1 \
    | sed -E 's/(access_token|refresh_token|api[_ -]?key|token)([^[:alnum:]_-]*)([A-Za-z0-9._~-]{12,})/\1\2<redacted>/Ig'
done
```

4. Validate critical fields without printing secrets:

```bash
python3 - <<'PY'
import yaml, json
profiles=['zeus','atena','ares','legacy-agent']
print('Profile  Ver  Provider      Model    Markdown  CodexLen Refresh Anthropic')
print('-------  ---  ------------  -------  --------  -------- ------- ---------')
for p in profiles:
    cfg=yaml.safe_load(open(f'/root/.hermes/profiles/{p}/config.yaml')) or {}
    auth=json.load(open(f'/root/.hermes/profiles/{p}/auth.json'))
    provs=auth.get('providers',{}) if isinstance(auth,dict) else {}
    codex=provs.get('openai-codex',{}) if isinstance(provs,dict) else {}
    toks=codex.get('tokens',{}) if isinstance(codex,dict) else {}
    print(f"{p:<7}  {cfg.get('_config_version')!s:<3}  {cfg.get('model',{}).get('provider',''):<12}  {cfg.get('model',{}).get('default',''):<7}  {cfg.get('display',{}).get('final_response_markdown',''):<8}  {len(toks.get('access_token','')):<8} {str(bool(toks.get('refresh_token'))):<7} {str(bool(provs.get('anthropic'))):<9}")
PY
```

5. Run config checks and patch guard:

```bash
for p in zeus atena ares legacy-agent; do
  printf '%s: ' "$p"
  hermes -p "$p" config check 2>&1 | grep -m1 'Config version'
done
/root/mgs-agent/scripts/ensure-hermes-mgs-patches.sh
```

6. Sync `/root/mgs-agent/profiles/*-config.yaml` mirrors after live configs are validated.

7. Gracefully restart only the migrated gateways, not Zeus if the current Zeus thread is active:

```bash
for svc in atena-gateway.service ares-gateway.service legacy-agent-gateway.service; do
  systemctl kill -s SIGUSR1 --kill-who=main "$svc"
done
sleep 10
systemctl is-active zeus-gateway.service atena-gateway.service ares-gateway.service legacy-agent-gateway.service
```

8. Append audit log with summary, backup path, profiles, validations, and `secrets_exposed=false`.

## Expected v23/v27 → v28 changes seen in MGS

```text
Change                         Impact
------------------------------ -----------------------------------------------
_config_version -> 28           Stops outdated config warning
max_concurrent_sessions: null   New optional global cap; null = no limit
compression.codex_gpt55...      Keeps GPT-5.5/Codex compaction threshold aligned
model_catalog.ttl_hours 24->1   Fresher model picker/catalog refresh
onboarding.profile_build: ask   Desktop/CLI onboarding default; low MGS gateway impact
security guardrail list         More explicit sensitive command categories
```

## Pitfalls

- Do not report success before validating provider/model/auth/gateways/patch guard.
- Do not print tokens. Report token length/presence only.
- Full-profile tar backups can be huge and warn on live files; if one times out, remove the partial artifact after a smaller verified backup exists.
- `hermes config migrate` may print a long optional API-key checklist; this is not a failure and does not mean MGS should configure those keys.

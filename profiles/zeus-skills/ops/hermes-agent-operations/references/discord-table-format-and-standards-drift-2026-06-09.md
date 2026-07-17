# Discord table formatting + standards drift audit — 2026-06-09

## Trigger

Rodolfo noticed that a Zeus response used a raw Markdown table (`|---|---|`) in Discord and asked whether a recent Hermes update had reverted the established MGS table/legibility defaults.

## Durable lesson

For MGS Discord conversations, operational/comparative tables should be rendered as fenced `text` blocks with manually aligned columns. Do not rely on Markdown pipe tables for Discord responses; they can appear as raw text, wrap poorly, or feel like a regression even when Hermes config is technically unchanged.

Correct shape:

```text
Item     Estado        Observação
-------  ------------  --------------------------------
Exemplo  OK            Coluna alinhada em bloco text
```

Avoid in Discord operational replies:

```markdown
| Item | Estado | Observação |
|---|---|---|
| Exemplo | OK | ... |
```

## Debugging path used

When the user suspects a Hermes update changed response defaults:

1. Check the live profile configs for all active agents, especially:
   - `display.final_response_markdown`
   - `display.platforms.discord.*`
   - `discord.*`
   - `model.provider`, `model.default`
   - `compression.*`
2. Compare live configs against the MGS mirror/snapshot if present.
3. Compare against the most recent profile backup when available.
4. Validate services and patch guard before declaring a standards regression:
   - `systemctl is-active zeus-gateway.service atena-gateway.service ares-gateway.service legacy-agent-gateway.service`
   - `/root/mgs-agent/scripts/ensure-hermes-mgs-patches.sh`
5. Audit SOUL/style rules, not only config files. In this session the root cause was permissive wording in SOUL rules, not a confirmed change to `final_response_markdown`.
6. Patch the SOULs/rules so the desired behavior is explicit and absolute.

## Findings from this session

- Hermes was `v0.16.0`, upstream `57775e9e`, up to date.
- Zeus/Atena/Ares/agente legado were all active.
- All active agents used `openai-codex` + `gpt-5.5`.
- `display.final_response_markdown: strip` was present on all four profiles, but this was not proven to be a new value.
- MGS patch guard passed.
- Zeus config had migrated to version 28; Atena/Ares/agente legado showed migration available, but no active break was found.
- The actionable fix was to strengthen profile SOUL formatting rules to prohibit raw Markdown tables in Discord operational replies and require fenced `text` aligned columns.

## Reporting pattern

Report the distinction clearly:

```text
Área                         Status
---------------------------- ------------------------------------------------
Config mudou?                Não confirmado
Padrão operacional           Reforçado nos SOULs
Gateways                     Ativos
Provider/modelo              openai-codex / gpt-5.5
Próximo passo                Migrar configs só em rodada controlada
```

Do not say “the update broke tables” unless a code/config diff proves it.
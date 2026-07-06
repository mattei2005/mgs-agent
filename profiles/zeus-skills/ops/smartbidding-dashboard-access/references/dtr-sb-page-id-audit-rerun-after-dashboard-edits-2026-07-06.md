# DTR ↔ SmartBidding PAGE ID audit rerun after dashboard edits — 2026-07-06

## Trigger

Use this when Rodolfo says he changed many things in SmartBidding/DTR and asks to “manda essa checagem atualizada novamente” or similar for the Bot/DTR ↔ SmartBidding PAGE ID registration audit.

## Durable lesson

For this audit class, rerun live from both sources. Do not answer from the previous screenshot/summary even if it is only a few hours old.

The successful rerun pattern was:

1. Scope DTR from **all DigitalTRChat 1Password items** for this specific PAGE ID registration conference.
2. Log into every DTR user and enumerate every top-bar segurador/account.
3. Parse every page card with `FB_PAGE_ID` and DTR small `PAGE_ID`.
4. Fetch live SB `/company`, include **all child publishers** under `digital-trust + digital-trust-2`, not active-only.
5. Hard-stop if SB scope is incomplete. Baseline at the time of this run: `56` publishers and `3,237` Messenger Page rows.
6. Compare identity primarily by same-user `PAGE_ID`, then same-user `FB_PAGE_ID`, then global ID/name diagnostics. For reporting to Rodolfo, keep the buckets simple:
   - `Matches OK`
   - `Existe no Bot/DTR e não na SB`
   - `Existe na SB e não no Bot/DTR`
   - `Existe nos dois, mas diverge`
   - `Existe na SB, mas match é ambíguo`
   - `Duplicidades detectadas`
7. If a previous audit summary exists, calculate deltas against it and include only the meaningful changes.

## Output shape Rodolfo accepted

Short executive block, no attachment unless asked:

```text
Auditoria PAGE ID — Bot/DTR ↔ SmartBidding
Atualizado: YYYY-MM-DD HH:MM EDT
Escopo SB validado: digital-trust + digital-trust-2 completos

Escopo
- Usuários DigitalTRChat no 1Password: N
- Logins DTR OK: N/N
- Seguradores lidos no DTR: N
- Páginas lidas no Bot/DTR: N
- Publishers SB lidos: N
- Rows live SB: N
- Rows SB dos usuários auditados: N

Resultado
- Matches OK: N
- Problemas encontrados: N
- Duplicidades detectadas: N

Quebra dos problemas
- Existe no Bot/DTR e não na SB: N
- Existe na SB e não no Bot/DTR: N
- Existe nos dois, mas diverge: N
- Existe na SB, mas match é ambíguo: N

Variação vs checagem anterior HH:MM EDT
- Matches OK: +/-N
- Problemas totais: +/-N
- Bot/DTR sem SB: +/-N
- Divergentes: +/-N
- Duplicidades: +/-N
```

## Operational notes

- This audit can take 35–45 minutes. In Discord MGS, run as background without `notify_on_complete`, then manually `wait`/`poll` and summarize only the final clean result.
- Keep generated JSON/CSV paths in the final line for traceability, but do not attach files by default.
- Use live data as the source of truth; previous screenshots are comparison baselines only.

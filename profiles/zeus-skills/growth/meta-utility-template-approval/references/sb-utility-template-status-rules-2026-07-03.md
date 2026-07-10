# SB Utility Template Status Rules — 2026-07-03

Session source: Rodolfo corrected Zeus after Utility Template rollout tests and live SB operations.

## Final operating rules

- Templates with `PAGES > 0` stay at **20 active messages**.
- Templates with `PAGES = 0` stay at **10 active messages** and are not Run-Approved.
- Do not scale above 20 until Utility status behavior is understood.
- Global rollout replaces only **red / `REJECTED`** messages.
- **Purple / `INVALID_FORMAT` / `ERROR`** is diagnosis-only globally. Do not auto-replace. Investigate page vs segurador vs app/block/root cause.
- **Gray / no-status** is not auto-replaced globally. If the same template/message stays gray for 2 days, alert the template/broadcast channel.
- Approved-bank duplicate key is **TEXT + CTA** only. Do not include `LINK`; links are target-template slots and must be preserved from the target template.
- Spanish Utility messages always get Zeroid/zero-width regardless of country (`US-ES`, `ES-ES`, `MX-ES`, etc.). Density: **1 zero-width after every 2 words** in `TEXT`; do not alter links or placeholders.

## Ciro discussion points

Short message Rodolfo can send:

> Ciro, dois pontos sobre Utility Template:
>
> 1. Quando edito uma mensagem individual e salvo/update, o template inteiro fica cinza. O esperado seria só a mensagem alterada ficar cinza, porque só ela precisa passar por approval de novo; as outras deveriam manter a cor/status anterior.
>
> 2. Quando um template inteiro fica roxo, exemplo 20 mensagens × 100 páginas, parece que o sistema está usando a primeira página/conta problemática para pintar tudo de roxo. Se uma página está restrita/bloqueada, ele está validando as outras 99 ou para ali? Porque se validasse todas, a barra deveria ficar parcialmente verde/vermelha/roxa, não 100% roxa.

## Controlled test model

Two single-template tests were approved as the pattern:

- Gray test: replace only gray slots in an exact named template, Run Approval, wait `pages × messages × 8s + 1h`, then read live status.
- Purple test: replace only purple/error slots in an exact named template, Run Approval, wait `pages × messages × 8s + 1h`, then read live status.

For both tests:

1. Read live SB `/broadcast/Messenger` for the exact template.
2. Save a snapshot/backup first.
3. Do not use `Erase All`.
4. Replace only the target-status slots.
5. Preserve target slot links.
6. Choose approved-bank replacements by `TEXT + CTA`, skipping any copy already present in the live template.
7. Run Approval only if template has linked pages.
8. Re-read live after ETA+1h.

## Snapshot meaning

Snapshots are not a source of truth for writes. Live SB is the source of truth. Snapshots are only for before/after comparison, rollback, evidence for Ciro, and audit.

## Critical pitfall

Do not report “everything is running” without final validation:

- list crons and verify `enabled=true` / `state=scheduled`;
- compile/smoke scripts;
- confirm skill text actually contains the correction;
- validate tracker/data coherence;
- confirm live SB state when production state is involved.

If any part is not validated, report it as partial instead of saying done.
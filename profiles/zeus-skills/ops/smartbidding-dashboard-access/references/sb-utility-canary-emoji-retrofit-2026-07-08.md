# SB Utility canary templates — emoji retrofit + approval rerun (2026-07-08)

## When this applies

Use when Rodolfo asks to improve messages from Utility canary/test templates after the cron/runner has finished, especially requests like:

- “coloca emoji nas mensagens”
- “ficou faltando emoji relacionado ao conteúdo”
- “analisa as mensagens antes e me reporta”
- “somente dos templates que estavam no cron”
- “roda o approval de novo”
- “ativa o cron temporário novamente”

## Scope rule

Operate only on the exact templates that were in the canary cron/runner target list, not all Utility templates.

Validated target set from the 2026-07-08 canary runner:

```text
Teste-CA-CC-EN-Financeadx-Varya Stonebridge-1102378912948290-22028
Teste-DE-CC-DE-Newsoun-Ramona Dreher-1029582290242361-19329
Teste-GB-CC-EN-Zytiva-Sabrina Ellsworth-1179604071896296-22064
Teste-ES-CC-ES-Openzed-Elena Santana-990898360783030-22091
Teste-MX-CC-ES-Financeadx-Carolina Cruz-1025593570646416-19333
Teste-US-CAR-EN-Fincgriffin-Trust Car Offers-1033507496517692-22079
Teste-US-CC-EN-Newsoun-Iona Brookfield-952051961334613-19225
Teste-US-CC-ES-Newsoun-Carla Ramírez-873273395865880-13992
Teste-US-JOB-ES-Spe-Maria Tisocco-177067078834007-8283
Teste-ZA-CC-EN-Financeadx-Margaret Smith-699254556615476-5459
Teste-AR-CC-ES-Financeadx-Teresa Camacho-1063903433472026-19337
```

If the current runner script has a different `TARGETS` list, use the live script list as source of truth and say so.

## Required sequence

1. **Analyze live first.** Read live `/broadcast/Messenger` through the headed/Xvfb SB route and extract only the target templates.
2. Report before writing:
   - target template count;
   - total messages;
   - count with emoji in `TEXT`;
   - count with emoji in `CTA_1`;
   - count with contextual emoji;
   - approval color counts;
   - visible-text duplicate count.
3. If Rodolfo approves editing, apply a light retrofit — do **not** rewrite the whole approved copy unless he asks.
4. Preserve for every slot:
   - `MESSAGE_ID`;
   - `LINK_1` / link slot order;
   - template row identity;
   - existing zero-width style where present;
   - message order.
5. Add contextual emoji at the headline/lead and CTA when missing.
6. Clear approval status fields only on edited messages, then save the template payload via authenticated `POST /broadcast/Messenger`.
7. Run Approval again for the edited templates.
8. Re-read live and report final counts/status.

## Emoji placement

Preferred format is one emoji at the beginning of the headline plus one emoji at the beginning of CTA. Do not insert emoji in the body paragraph unless Rodolfo explicitly asks.

Example CC:

```text
💳 CARD REVIEW UPDATE
Your card request has a review step ready. Open the page to continue with the available options.
🔍 REVIEW CARD
```

Example JOB:

```text
💼 ACTUALIZACIÓN DE VACANTE
Tu solicitud de empleo tiene una revisión lista. Abre la página para continuar con las opciones disponibles.
🔍 VER OFERTA
```

## Emoji block rule — critical

Rodolfo correction: because SB sends **8 messages/day**, emoji uniqueness is required by daily slot block, not only at the start of the template.

Validate independently:

```text
Slots 1–8    no repeated leading/context emoji inside this block
Slots 9–16   no repeated leading/context emoji inside this block
Slots 17–20  no repeated leading/context emoji inside this remaining block
```

Repetition is allowed across different blocks because they are different send cycles/days. Example: slot 1 and slot 9 may both use `💳`; slot 1 and slot 2 may not.

Before saving, block the write if any block has missing/repeated leading emoji.

## Emoji pools

Use contextual, not decorative-random, emoji:

```text
CC   💳 📋 ✅ 🔎 📌 🔔 📄 💬
CAR  🚗 🚘 📋 ✅ 🔎 📌 🔔 📄
JOB  💼 📄 📋 ✅ 🔎 📌 🔔 ➡️
```

Delivery/package copy, if present, can use `📦 🚚 📬 🏠`; status/result copy can use `✅ 🔔 📌 🔎`.

## Approved-bank maintenance

The approved message bank is part of the workflow, not separate from it.

Canonical file:

```text
/root/mgs-agent/data/utility-message-bank.json
```

When Rodolfo asks to prepare/fix the bank for future replacements:

1. Deduplicate approved records by visible normalized `TEXT + CTA`.
2. Merge approval/history metadata for duplicate records.
3. Normalize approved records so both `text` and `cta_1` are emoji-ready.
4. Future replacement selection must still rebalance by target slot: do not blindly paste a bank emoji if it would repeat inside the current 8-message block.

Validated session result after maintenance:

```text
Records total                    302
Approved records                 206
Exact approved duplicate groups  0
Approved missing text emoji      0
Approved missing CTA emoji       0
```

## Temporary runner behavior

When Rodolfo asks to reactivate the temporary canary cron/runner:

- use only the 11 target templates above;
- duration is whatever Rodolfo asks (example: 3h);
- 10-minute interval unless Rodolfo says otherwise;
- early stop if all 11 templates reach `20/20 green`;
- green: preserve;
- gray: run approval; do not replace if it has ever been green;
- gray never green: approval up to 3 attempts before replacement;
- red: replace;
- purple: diagnostic only, do not replace.

The runner/loop must enforce before POSTing:

```text
20 messages exactly
MESSAGE_ID 1..20 preserved
visible text has no duplicates
LINK_1/media slot fields preserved
emoji exists in headline and CTA
emoji is unique inside each 8-message block
```

## Important pitfall

Editing currently green messages will usually reset edited slots to gray/no-status until approval runs again. That is expected. Do not report it as failure if the save succeeded and approval was triggered.

## 2026-07-08 live analysis baseline

Live analysis before retrofit request found:

```text
Templates analyzed          11
Messages analyzed           220
TEXT/CTA with emoji          41
No emoji                    179
Contextual emoji             38
Visible duplicates            0
Status at analysis          215 green / 1 gray / 4 red / 0 purple
```

Worst templates for missing emoji:

```text
GB-CC-EN      0/20
US-CAR-EN     0/20
US-CC-EN      1/20
ZA-CC-EN      1/20
CA-CC-EN      2/20
DE-CC-DE      2/20
```

Operational recommendation from that analysis: retrofit emoji lightly, then run Approval again on the same 11 templates.

## Reporting to Rodolfo

Report cleanly and briefly:

```text
Templates editados
Mensagens editadas
Emoji headline/CTA coverage
Block validation 1–8 / 9–16 / 17–20
Run Approval requested
Current green/gray/red/purple status
Errors, if any
```

Do not dump raw service logs or REPORT-INFRA blocks in the operational thread.

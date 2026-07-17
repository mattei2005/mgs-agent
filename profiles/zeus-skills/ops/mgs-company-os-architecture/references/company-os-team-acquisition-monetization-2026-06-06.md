# MGS Company OS review — team, acquisition, monetization corrections (2026-06-06)

Session-specific reference for future Company OS restructuring/review work.

## Review behavior learned

Rodolfo expects a **cascade consistency check** whenever a new correction affects prior docs. Do not only patch the current file. Search/reason across already-edited Company OS docs and report a short table of conflicts found/corrected.

Default cascade targets during MGS OS reviews:

```text
context/company.md
context/company-os.md
context/company-current-operating-model.md
context/areas.md
context/agent-map.md
context/routes.md
context/sources-of-truth.md
context/permissions-matrix.md
context/team.md
context/acquisition.md
context/monetization.md
```

## Approved/validated decisions from this review block

### Team

- `context/team.md` was approved by Rodolfo after v0.2 rewrite.
- Rodolfo: CEO, strategy, Finance/BI, WordPress/infra/pixels, Revenue/AdOps, and command of the AI-agent operation as a whole.
- Geizian: sócio, Growth/media-buying operations, supports/coordinates gestores, participates in Revenue/AdOps, supports Kelly in Creative, and also operates campaigns as gestor `g002`.
- Ially: office manager / follow-up; cobranças and task follow-up with gestores when tasks are late/not done; escalates to Geizian/Rodolfo.
- Raquel: human supervisor for Content Operations / Atena.
- Kelly: human person/gestora, code `g005`, human creative lead; not an agent.
- agente legado: creative agent; does not replace Kelly; creates/organizes approved assets and can read/write Google Drive.
- Ares: campaign/Growth agent; Rodolfo + Geizian first, gestores only after testing, approval, and training.

### Acquisition

- `context/acquisition.md` was approved by Rodolfo after v0.2 rewrite.
- Acquisition channels: Facebook Ads and Google Ads are current core channels; TikTok Ads is potential/future until structure/validation exists.
- Gestor attribution uses `UTM_medium` codes: Icaro `g001`, Geizian `g002`, Isliago `g003`, Joe `g004`, Kelly `g005`, Nicolas `g006`.
- Ares manages/analyzes/creates/operates campaigns within approved scope and can read/write the approved-creatives Drive.
- Ares does **not** configure ChatPion/DigitalTrChat, quiz, SMS Funnel, or SMS structure.
- ChatPion/DigitalTrChat: Rodolfo + Geizian create users; gestores configure/access operational flows.
- Quiz/SMS: Rodolfo configures the structure; SMS Funnel may be used.

### Monetization

- `context/monetization.md` was rewritten to v0.2 and sent for validation after consistency check.
- Smart Bidding and ActiveView are Google partner companies with their own AdX/Ad Manager networks.
- Smart Bidding is the preferred/main dashboard because it is more complete and centralizes better operational management.
- ActiveView remains active exception for `openzed`, `cliquet`, and their subdomains.
- Ad blocks are created/configured in the corresponding partner network; site must be in the correct network and blocks installed/configured to monetize.
- Revenue/AdOps reports feed Rodolfo's Finance/BI spreadsheet alongside media costs, commissions, salaries, expenses, and ROI.
- Ares may analyze ROI/campaigns but does not alter AdOps blocks, partner networks, or monetization setup without scope/approval.

## Verification pattern used

- After each rewrite, run `git diff --check` on the touched file.
- After cross-doc corrections, run a concept audit for stale/conflicting terms:
  - `Aris`
  - `Ares futuro`
  - `Kelly agent` / `agente Kelly` / `Creative Agent`
  - Ares configured as owner of ChatPion/quiz/SMS
  - Smart Bidding described as exclusive/only network in a way that erases ActiveView
  - Geizian described as parceiro instead of sócio
- Report as: files checked, rules checked, final failures, and a short table of corrections.

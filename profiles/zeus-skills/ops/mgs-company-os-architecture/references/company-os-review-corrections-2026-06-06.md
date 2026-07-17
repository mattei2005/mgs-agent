# Company OS Review Corrections — 2026-06-06

Session-specific notes from Rodolfo's iterative review of MGS Company OS docs.

## Durable workflow lesson

When Rodolfo corrects one document, do not treat it as isolated. A correction can affect already-reviewed files and create contradictions. Before continuing:

1. Identify the concept corrected.
2. Search previously reviewed canonical docs for stale terms/old assumptions.
3. Patch cascade conflicts before moving to the next file.
4. Report the cascade in a short table.

Use this for ownership, agent scope, partner/network definitions, access rules, source-of-truth changes, and naming corrections.

## Review style lesson

Rodolfo does not want to infer what matters from raw files. For each document, show:

- file status;
- operational decisions to validate;
- the file/excerpt only when requested;
- your own operational recommendation.

If he says the review is confusing, switch to decision-level validation: “you only need to confirm whether these statements are true.”

## Corrections captured

### Smart Bidding / ActiveView

Smart Bidding and ActiveView are Google partner companies. Each has its own AdX / Google Ad Manager network. Sites are added to those networks and ad blocks are created there before monetization starts.

MGS has some sites in Smart Bidding and some in ActiveView. The Smart Bidding dashboard is preferred because it is more complete and centralizes management. ActiveView remains active mainly for `openzed`, `cliquet`, and their subdomains while they remain on AV technology/control.

Do not reduce this to “Smart Bidding is monetization and ActiveView is legacy.” The important distinction is partner network + dashboard preference + exceptions.

### Team / roles

- Geizian is Rodolfo's sócio, not merely “partner” or “operational partner.”
- Rodolfo commands the operation of all AI agents, not only Ares.
- Ially is the office manager. She follows up/cobra gestores when tasks requested from them are late, slow, or not done.

### Agents and scope

- Ares = campaign agent only. Do not use “Aris.” Do not say “Ares futuro”; if needed, say `em configuração` or `implantação progressiva`.
- Ares does not configure ChatPion/DigitalTrChat, quiz, or SMS Funnel.
- ChatPion/DigitalTrChat users are created by Rodolfo/Geizian; gestores access users and configure operational flows.
- Quiz/SMS structure/configuration is built by Rodolfo.
- agente legado = creative agent. Kelly is the human creative lead/gestora (`g005`).
- Ares and agente legado both need read/write access to the approved-creatives Google Drive so they can manage and use creative assets.

### Gestores and Finance/BI

Gestores and `utm_medium` codes:

```text
Icaro    g001
Geizian  g002
Isliago  g003
Joe      g004
Kelly    g005
Nicolas  g006
```

`utm_medium` is the attribution source for gestor revenue/profit.

Gestor compensation belongs in Finance/BI docs:

```text
Base salary                 R$3,000
Up to R$100,000 net profit   7% commission
At/above R$100,000           10% commission
Rule                         Pay salary OR commission, whichever is higher; do not pay both.
```

## Files usually affected by these corrections

```text
context/company.md
context/company-os.md
context/company-current-operating-model.md
context/areas.md
context/agent-map.md
context/routes.md
context/sources-of-truth.md
context/permissions-matrix.md
```

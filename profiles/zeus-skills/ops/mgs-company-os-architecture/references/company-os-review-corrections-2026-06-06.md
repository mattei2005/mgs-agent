# Company OS review corrections — 2026-06-06

Session-specific details captured while Rodolfo reviewed `context/company.md` and the derived Company OS docs.

## Durable corrections

- Use **Ares** only. `Aris` was a typo; do not preserve it as an alias.
- Do not call Ares “future Ares.” If status matters, say `em configuração` or `implantação progressiva` separately.
- Creative agent name is **Hera**. Kelly is the human gestor/creative lead (`g005`).
- Rodolfo controls Zeus by default. Other employees enter Zeus threads only if Rodolfo explicitly asks.
- Rodolfo commands the whole AI-agent operation, not just Ares.
- Geizian is Rodolfo's **sócio**, not merely “partner” in the loose vendor sense. He is also gestor `g002` and launches/tests campaigns.
- Ially is the office manager who follows up/cobra gestores when tasks requested from them are late or not done.

## Smart Bidding / ActiveView monetization wording

Smart Bidding and ActiveView should be described as Google partner companies with their own AdX/Ad Manager networks. Sites are added inside those networks and ad blocks are created there so sites can monetize.

Operational nuance:

```text
Smart Bidding dashboard   Preferred/main dashboard because it is more complete.
ActiveView dashboard      Exists, but MGS prefers concentrating management in SB.
AV exception              openzed, cliquet and respective subdomains still use AV tech/control.
```

Avoid oversimplifying this as “Smart Bidding is the central network and ActiveView is just exception” without explaining both are Google partners/AdX networks.

## Ares / ChatPion / quiz boundaries

Ares owns campaigns, not every acquisition-adjacent system.

```text
Ares                  Campaign management/creation/analysis/ROI.
ChatPion/DigitalTrChat Rodolfo+Geizian create users; gestores configure users/flows.
Quiz/SMS Funnel       Rodolfo creates/configures the structure.
```

Ares may use outputs/assets/strategy context from these flows, but does not configure ChatPion, DigitalTrChat, quiz, or SMS Funnel.

## Creative Drive handoff

```text
1. Kelly/Rodolfo/Geizian/gestor requests creative.
2. Hera creates feed/stories/video/static variations.
3. Kelly or responsible human approves.
4. Hera saves approved creative to the correct Google Drive folder.
5. Ares reads/writes/manages approved creatives in Drive for campaign tests.
```

Hera and Ares both need read/write access to the approved-creatives Drive.

## Review workflow preference

When presenting files for Rodolfo review, do not just paste raw technical docs and ask “review.” First say what decisions he must confirm. If he asks for the file, paste/excerpt the file, but still include a short checklist of operational confirmations.

Good prompt:

```text
Você só precisa validar estas decisões:
- Ares = campanhas only.
- Hera = criativos + Drive.
- ChatPion = Rodolfo/Geizian/gestores; sem Ares.
- Quiz/SMS = Rodolfo.
```

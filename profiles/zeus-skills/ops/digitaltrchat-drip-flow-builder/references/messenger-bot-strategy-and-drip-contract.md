# Messenger BOT strategy and Auto Principal Drip contract

> Taught by Rodolfo on 2026-07-16. This is the operating model for understanding and auditing MGS Messenger bot pages. Re-read live UI before any write.

## Acquisition and monetization chain

1. MGS creates a Meta/Facebook sales campaign using a chosen Facebook Page.
2. The ad opens that Page's Messenger conversation.
3. The user receives the question flow/JSON configured with the ad account/campaign.
4. When the user clicks and answers the questions, the user becomes subscribed to the Page.
5. The subscribed user receives the `Get-started Template`.
6. Clicking the Get Started CTA sends the user to the MGS site, where monetization occurs.
7. If the user types arbitrary text in the Messenger conversation, the `No Match Template` is returned.
8. Because the user is subscribed, the user also begins receiving the timed messages from `Auto Principal Drip`.

Do not audit Get Started, No Match and Drip as unrelated assets: they are one acquisition-to-monetization system.

## Action-button template roles

Under `Bot manager > Action button settings`:

- `Get-started Template`: first CTA after subscription; its button opens the monetized site.
- `No Match Template`: fallback reply when the subscriber types something not matched by another configured action; its button also points to the intended site/offer.

For Drip audits, the relevant No Match destination is the canonical URL reference for initial Drip block 6. Compare the exact URL, not only the domain.

Never click `Update` or `Reset all action button settings to default` during read-only inspection.

## Auto Principal Drip — initial six-block contract

Before M01–M28, the flow has a small initial chain:

1. **Start Bot Flow** — title must be `Auto Principal Drip`.
2. **Text** — operational content is not central, but its language must match the M01–M28 Drip language.
3. **Button** — exactly one button; the button language must match the Drip language. Rodolfo classifies this block as operationally relevant.
4. **New Postback** — title must also be `Auto Principal Drip`, matching block 1. Its content is not operationally central.
5. **Text** — operational content is not central, but its language must match the full Drip.
6. **Button + Web URL** — button language must match the Drip; the exact URL must equal the URL configured in that Page's `No Match Template`.

A copied URL from another site is a real configuration error even if the graph is connected and the destination returns HTTP 200.

## New Sequence contract

After the initial chain, a red `New Sequence` node begins the timed Drip:

- Name: `Auto Principal Drip`
- Starting Time: `00:00`
- Closing Time: `24:00`
- The standard is intended to be the same across Pages.
- The live Ameenah/Lily example displayed timezone `America/New_York`.

The sequence fans out to `Sequence item` nodes; each leads to a named `New Postback` (`M01`, `M02`, …) and then to the message composition blocks.

## Message composition pattern

Rodolfo's teaching at this stage:

- One composition uses an image/link block, then a button, then a text block.
- The next composition uses another non-image first block, then a button, then a text block.
- MGS interleaves these compositions across the timed messages.

The final sentence of the teaching named `M01` twice. Do not make the exact M01/M02 alternation a universal write rule until Rodolfo confirms the second label.

## Live read-only verification — Ameenah / page 13828

Context:

- Segurador/profile: `Ameenah Abdullahi`
- Page: `Lily Thompson`
- Internal DigitalTRChat page ID: `13828`
- Facebook Page ID: `853430801191342`
- Flow: `Auto Principal Drip`

Observed graph:

- 147 nodes, all reachable, none disconnected
- M01 through M28 present
- 28 `Sequence Single` nodes
- 29 `New Postback` nodes: initial `Auto Principal Drip` plus M01–M28
- 15 `Generic Template` nodes, 30 buttons and 43 text nodes
- `New Sequence`: `Auto Principal Drip`, `00:00–24:00`, `America/New_York`

Observed composition:

- M01, M03, M05, …, M27 used `Generic Template` as the first message block.
- M02, M04, M06, …, M26 used a text/arrow block as the first message block.
- M28 also used `Generic Template`.

This is live evidence for page 13828, not yet a universal alternation rule.

## Confirmed current mismatch — page 13828

- Initial Drip block 6 currently points to `fineasier.com`.
- The No Match screenshot/current teaching points to the Openzed card destination (`card.openzed.com`).
- Therefore the block-6 destination is wrong for this Page because it was copied from another site.

No correction is authorized merely by identifying this mismatch. A future write must name the exact before/after URL, back up the graph, save narrowly and validate by readback.

## Audit checklist

- [ ] Correct segurador/profile and Page ID selected
- [ ] Get Started CTA leads to the intended monetized site
- [ ] No Match trigger/template and exact destination recorded
- [ ] Initial blocks 1–6 match name/language/one-button/URL rules
- [ ] Block 6 URL exactly equals No Match URL
- [ ] New Sequence name and 00:00–24:00 window match the contract
- [ ] M01–M28 exist and every branch is connected
- [ ] Message composition type is mapped before editing
- [ ] No Save/Update/Reset/Delete action executed during inspection

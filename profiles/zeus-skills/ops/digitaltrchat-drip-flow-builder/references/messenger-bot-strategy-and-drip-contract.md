# Messenger BOT strategy and Auto Principal Drip contract

> Taught by Rodolfo on 2026-07-16. This is the operating model for understanding and auditing MGS Messenger bot pages. Re-read live UI before any write.

## Acquisition and monetization chain

1. MGS creates a Meta/Facebook sales campaign using a chosen Facebook Page.
2. The ad opens that Page's Messenger conversation.
3. The user receives the question flow/JSON configured with the ad account/campaign.
4. That JSON contains a question and renders a button with a link.
5. The link placed in the JSON button must be the same link stored in the Page's `Get-started Template`; MGS calls this the **M0 link**.
6. The monetization click originates from the button rendered by the JSON. It is not correctly described as “the Get Started button,” even though its URL is sourced from the Get-started Template/M0 configuration.
7. When the user clicks and answers the questions, the user becomes subscribed to the Page.
8. If the user types arbitrary text in the Messenger conversation, the `No Match Template` is returned.
9. Because the user is subscribed, the user also begins receiving the timed messages from `Auto Principal Drip`.

Do not audit Get Started, No Match and Drip as unrelated assets: they are one acquisition-to-monetization system.

## Action-button template roles

Under `Bot manager > Action button settings`:

- `Get-started Template`: canonical source/configuration for the **M0 URL** reused by the button generated inside the campaign JSON. Do not conflate the JSON-rendered monetization button with a button sent directly by the Get-started Template.
- `No Match Template`: fallback reply when the subscriber types something not matched by another configured action; its button points to the intended site/offer and is also the exact URL reference for initial Drip block 6.

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

## Message composition — current production convention

The running convention is:

- M01: image/link block → button → text block.
- M02: button → text block, without the image/link block.
- Continue interleaving those two compositions across the sequence.
- Keep the text block last. If a Messenger payload ends on the attachment/button composition, the mobile push can appear as `attachment`; the trailing text makes the notification show a useful message preview.

This composition and alternation are **not hard rules**. MGS may design the messages differently. They are the current standardized pattern because it produces the desired Messenger/mobile-notification behavior.

## Hard rules — message count and schedule

`Auto Principal Drip` must contain exactly 28 timed messages, M01 through M28, using this timing contract:

- M01: 3 minutes
- M02: 7 minutes
- M03: 10 minutes
- M04: 20 minutes
- M05: 30 minutes
- M06: 1 hour
- M07 through M28: 2 hours through 23 hours respectively, increasing by one hour per message

Expanded final mapping: M07=2h, M08=3h, M09=4h, M10=5h, M11=6h, M12=7h, M13=8h, M14=9h, M15=10h, M16=11h, M17=12h, M18=13h, M19=14h, M20=15h, M21=16h, M22=17h, M23=18h, M24=19h, M25=20h, M26=21h, M27=22h, M28=23h.

Unlike the visual composition pattern, the 28-message count and exact intervals are operational rules and must be validated before any Drip is approved.

## Legacy 15-message flow migration pitfall

Do not append M16 blindly to a legacy 15-message flow. The live first-page baseline used an older schedule:

- M01=1m, M02=3m, M03=7m, M04=10m, M05=30m, M06=1h;
- M07=3h through M15=11h.

Under the current canonical 28-message schedule, M15=10h and M16=11h. Therefore the legacy M15 already occupies the canonical M16 time. Adding only M16 at 11h would create a timing collision; choosing another time would violate the canonical contract.

Before any write, Rodolfo must scope one of two distinct operations:

1. **Isolated legacy addition:** create only M16 with an explicitly approved noncanonical timing, leaving the flow as a 16-message legacy flow; or
2. **Canonical migration:** retime/rebuild the sequence to M01–M28 using the current schedule.

Do not silently expand a request for M16 into M16–M28, and do not claim safe creation until node creation, connection, save, full-graph readback and rollback have been exercised in a guided pilot.

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

This matches the running interleaving convention through M27. M28 also used `Generic Template`; that is a live composition choice, not a hard-rule violation because only the 28-message count and timing contract are mandatory.

## Confirmed current mismatch — page 13828

- Initial Drip block 6 currently points to `fineasier.com`.
- The No Match screenshot/current teaching points to the Openzed card destination (`card.openzed.com`).
- Therefore the block-6 destination is wrong for this Page because it was copied from another site.

No correction is authorized merely by identifying this mismatch. A future write must name the exact before/after URL, back up the graph, save narrowly and validate by readback.

## Audit checklist

- [ ] Correct segurador/profile and Page ID selected
- [ ] JSON-rendered button uses the exact Get-started/M0 URL
- [ ] No Match trigger/template and exact destination recorded
- [ ] Initial blocks 1–6 match name/language/one-button/URL rules
- [ ] Block 6 URL exactly equals No Match URL
- [ ] New Sequence name and 00:00–24:00 window match the contract
- [ ] Exactly M01–M28 exist, every branch is connected, and delays match 3m/7m/10m/20m/30m/1h/2h…23h
- [ ] Message composition type is mapped before editing
- [ ] No Save/Update/Reset/Delete action executed during inspection

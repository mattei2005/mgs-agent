# Company OS routes review — 2026-06-06

Session-specific operational corrections from Rodolfo while reviewing MGS OS derived files.

## Review sequencing lesson

Do not jump from derived-doc review directly to inventory until Rodolfo approves the derived files. The correct sequence is:

```text
1. Review/approve areas.md
2. Review/approve agent-map.md
3. Review/approve routes.md
4. Review/approve sources-of-truth.md
5. Review/approve permissions-matrix.md
6. Cross-check main files for stale terms/contradictions
7. Then start Phase 3 inventory
```

When Rodolfo points at the older canonical/runtime sources listed in `sources-of-truth.md`, explain that those are not manually reviewed one-by-one in Phase 2; they enter Phase 3 as inventory/classification items.

## Naming corrections

```text
Correct agent name        Meaning
------------------------ ------------------------------------------------------
Ares                      Campaign/Growth agent. Never call it Aris.
agente legado                      Creative agent. Do not call the creative agent Kelly.
Kelly                     Human/gestora, code g005, creative lead/person.
Zeus                      Controlled only by Rodolfo by default.
```

Avoid writing `Ares futuro`. Prefer:

```text
Ares — in configuration / progressive rollout
```

## Gestores and attribution

Gestores and UTM codes:

```text
Icaro      g001
Geizian    g002
Isliago    g003
Joe        g004
Kelly      g005
Nicolas    g006
```

`UTM_medium` carries the gestor code and is used to attribute revenue/lucro by gestor/site/campaign. Geizian is also a gestor/operator (`g002`), runs/tests campaigns, and also coordinates gestores.

## Ares scope

Ares owns campaign work, regardless of source, after its rollout and access policy are approved:

- create/manage/analyze campaigns;
- Facebook Ads and Google Ads are current sources;
- TikTok Ads is future/potential;
- Rodolfo + Geizian use Ares initially;
- gestores join after Ares is tested, approved, and they are trained.

Ares does **not** configure:

- ChatPion/DigitalTrChat;
- quiz structures;
- SMS Funnel.

Ares may use campaigns/strategies that result from those flows, but setup ownership stays elsewhere.

## ChatPion / DigitalTrChat scope

DigitalTrChat is the ChatPion/Messenger dashboard. Responsibility:

```text
User creation                 Rodolfo + Geizian
Vertical user access/config    Gestores
Dashboard infrastructure       Smart Bidding dev
Ares                           No direct configuration ownership
```

Operational idea:

1. Admin creates users per site/vertical.
2. Gestor logs in with the vertical user.
3. Gestor connects a segurador / Facebook profile.
4. That profile has multiple Facebook pages.
5. In Bot Manager, gestores configure message flows.
6. Facebook Ads campaign uses Messenger objective and selected configured page.
7. User enters drip for up to 28 messages in first 24h.
8. Broadcast after 24h is handled through Smart Bidding templates/schedules, up to 12 messages/day.

Bot/Messenger strategy is for Facebook Ads, not Google Ads.

## Quiz / SMS scope

Quiz + SMS is a separate traffic strategy. Rodolfo creates/configures the quiz and SMS structure. SMS tool: SMS Funnel (`app2.smsfunnel.com.br`). Ares does not configure this stack.

Flow:

1. Campaign runs on Facebook Ads or Google Ads.
2. User opens quiz from ad.
3. User answers questions and submits name/phone/email as used.
4. SMS Funnel sends SMS after a few minutes.
5. SMS CTA link opens MGS article/site.
6. Revenue comes from site monetization.

## agente legado / Drive / Ares creative handoff

agente legado is the creative agent. Kelly is the human creative lead. Rodolfo, Geizian, Kelly, and gestores can request creatives.

Approved creative flow:

```text
1. Kelly/Rodolfo/Geizian/gestor requests creative, e.g. feed + stories.
2. agente legado creates variations.
3. Kelly approves when it is her creative flow.
4. agente legado saves approved assets to the correct Google Drive folder.
5. Ares reads/writes Drive to manage approved assets and use them in campaign tests.
```

Both agente legado and Ares need read/write access to the approved-creatives Drive so they can manage assets.

## Finance / commissions

Gestor salary/commission rule belongs in Finance / BI docs/context:

```text
Base salary                    R$ 3,000
Up to R$ 100k net profit        7% on net profit
At/above R$ 100k net profit     10% on net profit
No double-pay                   pay salary or commission, whichever is higher
Example R$45k net profit        45,000 * 7% = R$3,150, so pay R$3,150
Break-even approximate          ~R$42,857 net profit to exceed R$3,000
```

## Cross-check pattern

After user approves/corrects names/scopes, search for stale variants across MGS OS docs before moving on:

```text
Ares futuro|Aris|Kelly agent|agente Kelly|Kelly — agente|Ares coord
```

Use the search as cleanup, not as a challenge to Rodolfo's correction. If asked, explain that it catches stale old terms across files.

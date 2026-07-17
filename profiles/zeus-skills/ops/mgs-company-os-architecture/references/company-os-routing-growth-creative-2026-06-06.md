# MGS Company OS — Growth, Creative, Routing Clarifications (2026-06-06)

Session-specific detail from Rodolfo while reviewing the MGS OS derived docs one by one.

## Naming corrections

- The campaign agent is **Ares** only. Do not use `Aris`.
- Do not label Ares as `Ares futuro`. Use **Ares** with status/context such as `em configuração` or `implantação progressiva` when needed.
- The creative agent is **agente legado**.
- **Kelly** is the human/gestora responsible for creatives, not the agent name.

## Gestores and UTM tracking

Gestor codes are used in `UTM_medium` to attribute revenue/lucro by gestor/site/campaign.

```text
Gestor     Código UTM_medium
---------  -----------------
Icaro      g001
Geizian    g002
Isliago    g003
Joe        g004
Kelly      g005
Nicolas    g006
```

Geizian is also operational: he tests/runs campaigns and has code `g002`.

## Agent access model

```text
Agent  Users / control
------ ------------------------------------------------------------------------
Zeus   Rodolfo only by default. Other company people join Zeus threads only if Rodolfo explicitly asks.
Atena  Content agent. Raquel supervises; Rodolfo/Raquel can handle tasks manually.
Ares   Campaign agent. Initial users: Rodolfo + Geizian. Later: trained gestores after Ares is tested/approved.
agente legado   Creative agent. Kelly commands the creative operation; Rodolfo, Geizian and gestores can request creatives.
```

## Routing corrections

### Content

These belong to Atena:

- criar REC/P1;
- editar/publicar conteúdo WordPress;
- criar artigo SEO.

Manual fallback: Rodolfo and Raquel.

### Tech / WordPress / pixels

- montar/configurar site WordPress;
- configurar pixel Facebook Ads / Google Ads.

Rodolfo is responsible for manual intervention; Zeus can help as technical/orchestration support.

### Creative

Everything related to creative creation/editing/organization belongs to **agente legado**:

- static creatives;
- video;
- editing;
- Canva/Drive organization;
- naming taxonomy/patterns;
- creative assets for gestores.

Kelly is the human lead. Rodolfo, Geizian and gestores can request.

### Campaigns

Everything campaign-related belongs to **Ares**, regardless of source.

Current sources: Facebook Ads and Google Ads. TikTok is potential/future.

Rodolfo, Geizian and trained gestores can use this function after approval/training.

## ChatPion / DigitalTrChat / Messenger strategy

Do not route this as vague `operar ChatPion`. Document it as a Messenger/Facebook acquisition strategy.

Operational concept:

1. Smart Bidding dev configures the ChatPion-derived dashboard at `digitaltrchat.com`.
2. MGS admin creates users by site/vertical.
3. Gestor logs in with that vertical user.
4. Gestor connects a `segurador` (FB profile) that owns multiple Facebook pages.
5. In Bot Manager, flows are configured.
6. Facebook Ads campaign uses Messenger objective and selected configured page.
7. User clicks ad → Messenger opens with JSON predefined message.
8. User enters drip flow: up to 28 messages in first 24 hours.
9. After 24h, user can enter broadcast flow configured via Smart Bidding.

Broadcast via Smart Bidding:

- page is registered in Smart Bidding dashboard;
- template and schedule are selected;
- up to 12 messages/day;
- each message can include text/image/button/link to an MGS article/site.

Important: bot/Messenger strategy applies to Facebook Ads, not Google Ads.

## Direct traffic / quiz / SMS strategy

Separate acquisition strategy from ChatPion.

Current flow:

1. Campaign runs on Facebook Ads or Google Ads.
2. User clicks ad and opens quiz.
3. User answers questions and submits name/phone/email depending on setup.
4. Current quiz captures SMS/phone; email is not used in the cited quiz.
5. SMS Funnel (`app2.smsfunnel.com.br`) sends SMS after a few minutes.
6. SMS has CTA + link.
7. Click opens MGS article/site, generating monetization revenue.

## Revenue / AdOps / Smart Bidding

Ajustar blocos/preço AdOps and approving sites in the network belong to Smart Bidding / AdX operational layer.

Site launch flow:

1. Rodolfo builds the full site.
2. Site is sent to Smart Bidding/AdX approval.
3. Monetizable URLs are sent for registration.
4. Smart Bidding configures ad blocks across the site.
5. Rodolfo configures pixels.
6. Rodolfo creates Facebook Ads or Google Ads accounts/campaigns depending on strategy.
7. Campaigns start based on chosen traffic strategy.

## Finance / gestor commission

Relevant to Finance / BI docs.

```text
Base salary                    R$ 3.000
Up to R$ 100k net profit        7% of net profit
At/above R$ 100k net profit     10% of net profit
No double pay                   Pay salary or commission, whichever is higher.
Example                         R$ 45k net profit * 7% = R$ 3.150, so pay R$ 3.150.
Approx break-even               ~R$ 42,857 net profit to exceed R$ 3,000.
```

## Workflow lesson for future Company OS reviews

When Rodolfo says to review files one by one, do not jump to migration/inventory. Present one file at a time, capture corrections, patch the file, then move to the next.

When Rodolfo corrects naming (`Ares not Aris`, `Kelly agent -> agente legado`), search for old terms across canonical context files to remove stale variants. Explain the search as cleanup for stale occurrences, not as re-evaluating his decision.

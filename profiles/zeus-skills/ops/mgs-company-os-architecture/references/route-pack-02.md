### 3. Recommended initial MGS areas

Use the CEO-described real operating model as the starting point. The current canonical proposal is:

```text
Area                         Function
---------------------------- -------------------------------------------------
Executive / Management        Direction, strategy, priorities, daily meetings,
                              decisions, coordination and governance.
Content Operations            REC/P1, SEO support articles, categories,
                              WordPress editorial, daily content and QA.
Growth / Media Buying         Facebook Ads, Google Ads, SMS, media buyers,
                              campaign costs, acquisition and ROI.
Creative Operations           Kelly, Canva, ChatGPT, TopView.ai, Grok/other AI,
                              static/video creatives and asset handoff.
Revenue / AdOps               Smart Bidding, ActiveView, AdManager/AdX,
                              approval, ad blocks, pricing rules and AdOps.
Finance / BI                  Financial close, spreadsheets, revenue, costs,
                              invalid traffic, commissions, salaries and ROI.
Tech / WordPress / Infra      WordPress setup, plugins, pixels, VPS, Hermes,
                              agents, crons, scripts, patches and monitoring.
Security / Access             Credentials, tokens, user permissions, dashboards,
                              APIs, hardening and risk policy.
```

Durable MGS facts from the CEO explanation:
- Rodolfo and Geizian are sócios/partners. Rodolfo owns management, finance, WordPress/technical structure, pixels, partner-network relationship, strategy, and commands the AI-agent operation as a whole (not just Ares). Geizian manages the campaign/site managers day to day, launches/tests campaigns himself as gestor `g002`, and also participates in Growth, Creative support, and Revenue/AdOps.
- Ially is the office manager who follows up/cobranzas with gestores when requested tasks are late or not done.
- Raquel owns Content Operations and should supervise Atena.
- Kelly is the human owner of creative production and currently uses AI/Canva workflows for gestores. Geizian also orients/supports Kelly in Creative Operations. The creative agent name is **agente legado**, not Kelly.
- There are six gestores with tracking codes used in `UTM_medium`: Icaro `g001`, Geizian `g002`, Isliago `g003`, Joe `g004`, Kelly `g005`, Nicolas `g006`.
- Geizian is both partner/coordinator and an operating gestor (`g002`): he also launches/tests campaigns for some sites.
- The campaign agent is **Ares** only. Do not use `Aris`. Do not label it `Ares futuro`; if needed, describe status separately as `em configuração` / `implantação progressiva`.
- Smart Bidding and ActiveView are Google partner companies with their own AdX/Ad Manager networks. Sites are added to those networks and ad blocks are created there before monetization starts. The Smart Bidding dashboard is the preferred/main management dashboard because it is more complete and centralizes management, even for visibility across sites.
- ActiveView is now an exception/legacy-active network: only `openzed`, `cliquet`, and their subdomains are not technologically migrated to Smart Bidding.
- Finance runs monthly: period day 1–30, Google payment around day 21–23, Rodolfo checks Facebook Business Manager spend, invalid traffic, Smart Bidding/ActiveView reports, commissions, salaries and expenses in his spreadsheet.
- Gestor compensation matters to Finance/BI: base salary is R$3,000, but commission replaces salary when higher. Commission is 7% of net profit up to R$100,000 and 10% once the gestor reaches R$100,000 net profit. Do not double-pay salary + commission.

### 4. Recommended agent map

```text
Agent   Primary area    Role
------- --------------- ------------------------------------------------------
Zeus    Executive/Ops   General Manager, governance, routing, audit, escalation;
                        controlled by Rodolfo only by default.
Atena   Content         Editorial production, REC/P1, WordPress, content QA;
                        Raquel supervises.
Ares    Growth/Ads      Campaign management, creation, analysis, acquisition;
                        Rodolfo + Geizian first, trained gestores after testing.
                        Ares does not configure ChatPion/DigitalTrChat, quiz,
                        or SMS Funnel.
agente legado    Creative        Creative assets, videos, Canva/Drive organization and
                        naming taxonomy; Kelly is the human creative lead.
                        agente legado and Ares both need read/write access to the
                        approved-creatives Drive so campaigns can use assets.
Future  TBD             Specialist agents created only after mission/scope exist
Future  TBD             Specialist agents created only after mission/scope exist
```

Rules:
- **Agent creation follows company architecture**. Do not create a new agent until its area, mission, sources of truth, permissions, and escalation paths are explicit.
- After a new agent is technically online, do **not** jump straight to a real operational task. First create/validate the agent's operational diagram/context document (for agente legado this is `context/legacy-agent-creative-agent.md`), then align SOUL.md, create class-level skills/templates, and only then run controlled production-like tests.
- Zeus is controlled only by Rodolfo. Other company members join Zeus threads only when Rodolfo explicitly asks Zeus to include them.
- Ares starts under Rodolfo + Geizian control, then gestores get access only after the agent is tested, approved, and the gestores are trained on how to open threads and interact with it.
- The creative agent is **agente legado**. Kelly is the human creative lead/gestora (`g005`), not the agent name. Rodolfo, Geizian, Kelly and gestores may request creative work according to approved scope.
- agente legado is Creative Operations, not merely an Ares handoff assistant. agente legado creates static/image and video creatives, organizes Drive/Canva assets, and maintains naming/inventory even when Kelly, Geizian or gestores create assets themselves and run campaigns manually without Ares. Ares is an optional consumer of approved assets, not the only destination.

### 5. Sources-of-truth distinction

Keep this separation clear:

```text
context/   explains how the company works
 data/     stores operational state and facts used by systems
 scripts/  performs deterministic actions
 skills/   teaches agents procedures
 docs/     records history, plans, pendencies, changelog
 logs/     audit/runtime trail
 patches/  local runtime modifications
```

Pitfall: do not let `SOUL.md`, ad-hoc prompts, or individual skills become the only place where company structure exists. Company architecture belongs in `context/` and is then referenced by agents.


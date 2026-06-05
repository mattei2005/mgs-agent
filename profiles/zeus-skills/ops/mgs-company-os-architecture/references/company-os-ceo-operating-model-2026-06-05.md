# MGS Company OS — CEO Operating Model Capture (2026-06-05)

Session-specific reference for company-architecture work. Use this to ground future MGS OS restructuring in Rodolfo's real description of the business.

## Real company structure

- Partners: Rodolfo Mattei and Geizian.
- Rodolfo: CEO; manages the whole company, finance, spreadsheets, WordPress structure, site setup, plugins, pixels, relationship with networks/Smart Bidding, and strategic architecture.
- Geizian: manages the five content/campaign managers and daily campaign/performance routine.
- Raquel: owns content production and should supervise Atena.
- Kelly: content/creative manager; produces creatives using AI tools and Canva for managers to use in campaigns.
- Five managers: operate content/campaign/site performance, talk with Smart Bidding AdOps, monitor campaign costs and ROI.

## Site and content operation

- MGS has 30+ sites across countries, languages and verticals.
- Example vertical: `EggBev / GB / CC / EN` = UK credit cards in English.
- Site setup flow: WordPress install/config, home, categories, plugins, pixels.
- Content flow: Raquel publishes REC/P1. If categories need more content, she adds ~1,200-word SEO articles. Content is added daily across sites.
- Sites are submitted to ad-manager/adx partner networks for approval.

## Monetization / AdOps

- Smart Bidding is the primary operational dashboard today: sites, campaigns, ROI, features, ad-block creation, APIs and permissions.
- Rodolfo, Geizian and managers have access.
- Smart Bidding has Discord AdOps channels where Rodolfo and managers coordinate approvals, rules and ad-block pricing.
- ActiveView still exists but is mostly migrated/concentrated into Smart Bidding.
- Important exception: only `openzed`, `cliquet`, and their subdomains have not had the technology migrated to Smart Bidding.

## Acquisition / campaigns

- Channels: Facebook Ads, Google Ads and SMS for car-financing sites.
- Creative handoff: Kelly creates assets with AI/Canva, uploads to each manager's Canva folder, manager takes assets and launches campaigns.
- Daily management: Geizian and the managers review campaigns, costs and performance; Rodolfo oversees the whole operation.

## Creative tools

- ChatGPT: static creative generation/support.
- TopView.ai: video creation.
- Canva: organized creative delivery to managers.
- Future creative agent may use ChatGPT, Grok or any AI with approved API/access.

## Finance

- Rodolfo owns finance.
- Monthly cycle: day 1–30.
- Google pays around day 21–23.
- Rodolfo checks Facebook Business Manager spend, ad account spend, invalid traffic by site, Smart Bidding/ActiveView reports, commissions, salaries and company expenses.
- Financial source of truth currently includes Rodolfo's controlled spreadsheet.

## Agent implications

- Zeus: General Manager/orchestrator, governance, routing, authorization, audit, reporting.
- Atena: new content manager/agent; Raquel should supervise her.
- Ares: campaign manager agent; campaign analysis, campaign creation, acquisition operations.
- Future Creative Agent: creative production using approved AI/API tools.

## Workflow lesson

When Rodolfo wants to reorganize company architecture, first capture his explanation as CEO primary source before treating any prior blueprint as canonical. Create/update:

```text
context/company-current-operating-model.md
context/company-os.md
context/areas.md
context/agent-map.md
context/routes.md
context/sources-of-truth.md
context/permissions-matrix.md
```

Do not update agent behavior, move files, or change runtime during the capture/blueprint phases.

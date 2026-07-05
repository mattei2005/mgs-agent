# SB Dashboard Deep Route Capture — 2026-07-05

Read-only headed Playwright/Xvfb recapture with long waits up to 150s per route. No intentional state-changing button clicks.

Raw artifact: `/root/mgs-agent/work/sb-dashboard-map/sb-dashboard-routes-deep-20260705-012422.json`

Summary: 41 routes captured, 0 errors, no routes left in short-wait `LOADING...` state.

## Loaded routes that were incomplete in first capture

### Reports Messenger MSGs
- Route: `/reports/messenger_message`
- Title: `Messenger messages`
- Wait: 16.2s; reason: `table_or_api_ready`; rows visible: 50
- Columns/headers: DATE; COMPANY; DOMAIN; COUNTRY; VERTICAL; UTM_CAMPAIGN; UTM_CONTENT; TYPE; SENDS; DELIVEREDS; CTR; SESSIONS; PAGEVIEWS
- Buttons/actions: Update; Export; First Page; Previous Page; 1; 2; 3; 4; 5; Next Page; Last Page

### Reports Facebook Ads
- Route: `/reports/facebook_ads`
- Title: `Facebook Ads`
- Wait: 6.9s; reason: `table_or_api_ready`; rows visible: 50
- Columns/headers: DATE; COMPANY; DOMAIN; COUNTRY; VERTICAL; ACCOUNT_ID; ACCOUNT_NAME; CAMPAIGN_ID; CAMPAIGN_NAME; ADSET_NAME; AD_NAME; UTM_CAMPAIGN; ABSOLUTE; PERFORMANCE; COST; RATE; INVESTIMENT; CONVERSIONS; M0; SUBSCRIBERS; GET_STARTED; CLICKS; IMPRESSIONS; PAGEVIEWS; REVENUE; PROFIT; ROI; REVENUE/SUB; PROFIT/SUB; PAGEVIEWS/SUB; RPP; CONVERSION; SUBSCRIBER; CLICK; CPM; M0/SUB; SUB/GET_STARTED; GET_STARTED/CLICK; CTR; ADS
- Buttons/actions: Update; Export; First Page; Previous Page; 1; 2; 3; 4; 5; Next Page; Last Page

### Reports Ads Pilot
- Route: `/reports/ads_pilot`
- Title: `Ads Pilot`
- Wait: 42.6s; reason: `table_or_api_ready`; rows visible: 1
- Columns/headers: TIME; INVESTIMENT; INVESTIMENT INCREMENTAL; SUBSCRIBERS; SUBSCRIBERS INCREMENTAL; CONVERSIONS; CONVERSIONS INCREMENTAL; COST SUBSCRIBER; COST CONVERSION; COST SUBSCRIBER INCREMENTAL; COST CONVERSION INCREMENTAL; BUDGET; BUDGET CHANGED; CPA TARGET
- Buttons/actions: Update; Export; First Page; Previous Page; Next Page; Last Page

### Reports Url Healthy
- Route: `/reports/urlhealthy`
- Title: `Url Healthy`
- Wait: 5s; reason: `table_or_api_ready`; rows visible: 7
- Columns/headers: DATE; COMPANY; DOMAIN; COUNTRY; SOURCE; VERTICAL; URL; ADS REMOVED; ADS HEALTHY; REVENUE REMOVED; OPERATIONS
- Buttons/actions: Update; Export

### Reports Photo by Vertical
- Route: `/reports/photo-by-vertical`
- Title: `Vertical per Hour`
- Wait: 7.6s; reason: `table_or_api_ready`; rows visible: 50
- Columns/headers: HOUR; DATE; COMPANY; DOMAIN; INVESTIMENT; REVENUE; ESTIMATED REVENUE; PROFIT; ESTIMATED PROFIT; ROI; ESTIMATED ROI; SESSIONS; PAGEVIEWS; RPS; RPP; REQUESTS; MATCHED; IMPRESSIONS; COVERAGE; CPM; PRICE; CTR; EPC; %VIEWABLE
- Buttons/actions: Update; Export; First Page; Previous Page; 1; 2; 3; 4; 5; Next Page; Last Page

### Reports Photo by Adgroup
- Route: `/reports/photo-by-adgroup`
- Title: `Adgroup per Hour`
- Wait: 9.2s; reason: `table_or_api_ready`; rows visible: 50
- Columns/headers: HOUR; DATE; COMPANY; DOMAIN; INVESTIMENT; REVENUE; PROFIT; ROI; ACQUISITION IMPRESSIONS; ACQUISITION CLICKS; CONVERSIONS; %CONVERSIONS; COST CLICK; COST CONVERSION; PAGEVIEWS QUIZ; PAGINATION; SESSIONS; PAGEVIEWS; RPS; RPP; REQUESTS; MATCHED; IMPRESSIONS; COVERAGE; CPM; PRICE; CTR; EPC; %VIEWABLE
- Buttons/actions: Update; Export; First Page; Previous Page; 1; 2; 3; 4; 5; Next Page; Last Page

### Reports Photo by Messenger
- Route: `/reports/photo-by-messenger-insights`
- Title: `Messenger per Hour`
- Wait: 7.7s; reason: `table_or_api_ready`; rows visible: 50
- Columns/headers: HOUR; DATE; COMPANY; DOMAIN; MESSENGER; DRIP; BROADCAST; COST SUBSCRIBER; COST CONVERSION; INVESTIMENT; REVENUE; PROFIT; ROI; LEADS; CONVERSIONS; SUBSCRIBED; DELIVEREDS; SESSIONS; CTR; RPS
- Buttons/actions: Update; Export; First Page; Previous Page; 1; 2; 3; 4; 5; Next Page; Last Page

### Reports Photo by Url
- Route: `/reports/photo-by-url`
- Title: `Url per Hour`
- Wait: 40.1s; reason: `table_or_api_ready`; rows visible: 50
- Columns/headers: HOUR; DATE; COMPANY; DOMAIN; REVENUE; PAGEVIEWS; RPP; CPM; AVG PRICE; REQUESTS; MATCHED; IMPRESSIONS; COVERAGE; CTR; EPC; VIEWABLE%
- Buttons/actions: Update; Export; First Page; Previous Page; 1; 2; 3; 4; 5; Next Page; Last Page

### Reports Photo by FacebookAds
- Route: `/reports/photo-by-facebookads`
- Title: `FacebookAds per Hour`
- Wait: 3.8s; reason: `table_or_api_ready`; rows visible: 50
- Columns/headers: HOUR; DATE; COMPANY; DOMAIN; INVESTIMENT; INVESTIMENT DIFF; SUBSCRIBERS; CONVERSIONS; SUBSCRIBERS DIFF; CONVERSIONS DIFF; COST SUBSCRIBER; COST CONVERSION; COST SUBSCRIBER DIFF; COST CONVERSION DIFF; CLICKS; CLICKS DIFF; CTR; CTR DIFF; COST CLICK; COST CLICK DIFF; IMPRESSIONS; IMPRESSIONS DIFF; CPM; CPM DIFF
- Buttons/actions: Update; Export; First Page; Previous Page; 1; 2; 3; 4; 5; Next Page; Last Page

### Ads Pilot
- Route: `/ads-pilot`
- Title: `Ads Pilot`
- Wait: 2.5s; reason: `table_or_api_ready`; rows visible: 12
- Columns/headers: NAME; COMPANY; DOMAINS; ACCOUNTS; CPA_TARGET; CPA_MAX; BUDGET_MIN; BUDGET_MAX; TARGETING; AGGRESSIVENESS; SUMMARY; STATUS
- Buttons/actions: New ads pilot

### Smart Routing
- Route: `/company/digital-trust/autocreditadx/routing`
- Title: `Routing > digital-trust > autocreditadx`
- Wait: 2.5s; reason: `table_or_api_ready`; rows visible: 1
- Columns/headers: NAME; SOURCE; COUNTRY; VERTICAL; LANGUAGE; MEDIUM; ROUTES; RPP 05/07; RPP 04/07; RPP 03/07
- Buttons/actions: New routing pool; First Page; Previous Page; Next Page; Last Page

## Wait lesson

Some SB routes legitimately take 15-45s+ to produce a real table under the MGS site selector. Treat `LOADING...` as pending, not failure, until a long wait or endpoint-specific error proves otherwise.

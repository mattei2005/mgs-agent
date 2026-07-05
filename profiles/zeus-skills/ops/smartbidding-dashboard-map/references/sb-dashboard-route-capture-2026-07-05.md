# SB Dashboard Route Capture — 2026-07-05

Read-only headed Playwright/Xvfb capture under Zeus SB account. No intentional state-changing button clicks.

Raw artifacts:
- `/root/mgs-agent/work/sb-dashboard-map/sb-dashboard-routes-20260705-010957.json`
- `/root/mgs-agent/work/sb-dashboard-map/sb-dashboard-crawl-20260705-010029.json`

## Routes and visible structure

### Dashboard
- Route: `/`
- Title: `Dashboard`
- Visible columns/headers: Welcome!
- Visible buttons/actions: Daily; Monthly; Update

### Reports Overview
- Route: `/reports/overview`
- Title: `Overview`
- Visible columns/headers: DATE; COMPANY; DOMAIN; COUNTRY; VERTICAL; ACQUISITION; EMAIL; EMAIL INTRADAY; PUSH; SMS; TOTAL; TOTAL INTRADAY; INVESTIMENT; REVENUE; PROFIT; ROI; SESSIONS; RPS; SENDS; SENDS X SESSIONS; DELIVERED; DELIVERED X SESSIONS
- Visible buttons/actions: Update; Export; First Page; Previous Page; 1; Next Page; Last Page

### Reports Domain
- Route: `/reports/domain`
- Title: `Domain`
- Visible columns/headers: Daily; Custom Period; Monthly; Yearly; DATE; COMPANY; DOMAIN; INVESTIMENT; REVENUE; PROFIT; ROI; SESSIONS; PAGEVIEWS; RPS; RPP; REQUESTS; MATCHED; IMPRESSIONS; COVERAGE; CPM; PRICE; CTR; EPC; %VIEWABLE
- Visible buttons/actions: Update; Export

### Reports Acquisition
- Route: `/reports/acquisition`
- Title: `Acquisition`
- Visible columns/headers: COMPANY; DOMAIN; SOURCE; COUNTRY; VERTICAL; PRODUCT; ACCOUNT NAME; CAMPAIGN NAME; UTM_ADGROUP; ADGROUP NAME; INVESTIMENT; REVENUE; PROFIT; ROI; ACQUISITION IMPRESSIONS; ACQUISITION CLICKS; CONVERSIONS; %CONVERSIONS; COST CLICK; COST CONVERSION; SESSIONS; PAGEVIEWS; RPS; RPP; REQUESTS; MATCHED; IMPRESSIONS; COVERAGE; CPM; PRICE; CTR; EPC; %VIEWABLE
- Visible buttons/actions: Update; Export; First Page; Previous Page; 1; Next Page; Last Page

### Reports Adgroup
- Route: `/reports/adgroup`
- Title: `AdGroup`
- Visible columns/headers: DATE; COMPANY; DOMAIN; SOURCE; COUNTRY; VERTICAL; ACCOUNT NAME; CAMPAIGN NAME; ADGROUP NAME; AD_NAME; UTM_ADGROUP; INVESTIMENT; REVENUE; PROFIT; ROI; ACQUISITION IMPRESSIONS; ACQUISITION CLICKS; CONVERSIONS; %CONVERSIONS; COST CLICK; COST CONVERSION; PAGEVIEWS QUIZ; PAGINATION; SESSIONS; PAGEVIEWS; RPS; RPP; REQUESTS; MATCHED; IMPRESSIONS; COVERAGE; CPM; PRICE; CTR; EPC; %VIEWABLE; STATUS
- Visible buttons/actions: Update; Export; First Page; Previous Page; 1; Next Page; Last Page

### Reports Vertical
- Route: `/reports/vertical`
- Title: `Vertical`
- Visible columns/headers: DATE; COMPANY; DOMAIN; INVESTIMENT; REVENUE; PROFIT; ROI; SESSIONS; PAGEVIEWS; RPS; RPP; REQUESTS; MATCHED; IMPRESSIONS; COVERAGE; CPM; PRICE; CTR; EPC; %VIEWABLE
- Visible buttons/actions: Update; Export

### Reports Inventory
- Route: `/reports/inventory`
- Title: `Inventory`
- Visible columns/headers: Company; Domain; Country; Source; Vertical; Medium; Language; In Use; Available; Content
- Visible buttons/actions: Update; Export; First Page; Previous Page; 1; 2; 3; 4; 5; Next Page; Last Page

### Reports Operation
- Route: `/reports/operation`
- Title: `Operation`
- Visible columns/headers: Table View; Tree View; DATE; COMPANY; DOMAIN; UTM SOURCE; COUNTRY; VERTICAL; PRODUCT; PAGE TYPE; SLOT ID; REVENUE; RPP; RPS; SESSIONS; PAGEVIEWS; CPM; REQUESTS; MATCHED; IMPRESSIONS; COVERAGE; CLICKS; EPC; PRICE; REQUESTS/PAGEVIEW
- Visible buttons/actions: Update; Export; First Page; Previous Page; 1; 2; 3; 4; 5; Next Page; Last Page

### Reports URL
- Route: `/reports/url`
- Title: `Performance per URL`
- Visible columns/headers: DATE; URL; COMPANY; DOMAIN; COUNTRY; SOURCE; VERTICAL; PRODUCT; PAGE_TYPE; REVENUE; SESSIONS; PAGEVIEWS; RPS; RPP; REQUESTS; MATCHED; IMPRESSIONS; COVERAGE; CPM; PRICE; CTR; EPC; %VIEWABLE
- Visible buttons/actions: Update; Export; First Page; Previous Page; 1; 2; Next Page; Last Page

### Reports Placement
- Route: `/reports/placement`
- Title: `placement`
- Visible columns/headers: DATE; COMPANY; DOMAIN; SOURCE; COUNTRY; VERTICAL; ACCOUNT NAME; CAMPAIGN NAME; UTM CAMPAIGN; PLACEMENT; PLACEMENT NAME; INVESTIMENT; REVENUE; PROFIT; ROI; ACQUISITION IMPRESSIONS; ACQUISITION CLICKS; CONVERSIONS; %CONVERSIONS; COST CLICK; COST CONVERSION; SESSIONS; PAGEVIEWS; RPS; RPP; REQUESTS; MATCHED; IMPRESSIONS; COVERAGE; CPM; PRICE; CTR; EPC; %VIEWABLE
- Visible buttons/actions: Update; Export; First Page; Previous Page; Next Page; Last Page

### Reports SMS
- Route: `/reports/sms`
- Title: `SMS`
- Visible columns/headers: DATE; COMPANY; DOMAIN; SOURCE; UTM_CAMPAIGN; MSG_ID; LABEL; COUNTRY; VERTICAL; INVESTIMENT; REVENUE; PROFIT; ROI; MESSAGES; DELIVERED; UNDELIVERED; FAILED; DELIVERED RATE; COST SEND; KTR UNIQUE CLICKS; KTR CLICKS; DELIVERED CTR; SESSIONS; PAGEVIEWS; RPS; RPP; REQUESTS; MATCHED; IMPRESSIONS; COVERAGE; CPM; PRICE; CTR; EPC; %VIEWABLE
- Visible buttons/actions: Update; Export; First Page; Previous Page; 1; Next Page; Last Page

### Reports Email
- Route: `/reports/email`
- Title: `Email`
- Visible columns/headers: DATE; COMPANY; DOMAIN; COUNTRY; VERTICAL; ACCOUNT_NAME; CAMPAIGN_NAME; UTM_CAMPAIGN; AUTO_NAME; REVENUE; SENDS; OPENS; OPEN RATE; CLICKS; SEND CTR; OPEN CTR; SESSIONS; PAGEVIEWS; RPS; RPP; REQUESTS; MATCHED; IMPRESSIONS; COVERAGE; CPM; PRICE; CTR; EPC; %VIEWABLE
- Visible buttons/actions: Update; Export; First Page; Previous Page; Next Page; Last Page

### Reports Pushalert
- Route: `/reports/pushalert`
- Title: `Pushalert`
- Visible columns/headers: DATE; COMPANY; DOMAIN; COUNTRY; VERTICAL; UTM_CAMPAIGN; TITLE; REVENUE; SENDS; DELIVERED; %DELIVERED; CLICKS; DELIVERED CTR; SESSIONS; PAGEVIEWS; RPS; RPP; REQUESTS; MATCHED; IMPRESSIONS; COVERAGE; CPM; PRICE; CTR; EPC; %VIEWABLE
- Visible buttons/actions: Update; Export; First Page; Previous Page; Next Page; Last Page

### Reports Youtube
- Route: `/reports/youtube`
- Title: `Youtube`
- Visible columns/headers: DATE; CHANNEL; ID; VIDEO; PUBLISHED; VIEWS; REVENUE; ADS; CPM; LIKES; DISLIKES; COMMENTS; SHARES; SUBSCRIBED; SUBSCRIBED LOST; HOURS WATCHED
- Visible buttons/actions: Update; Export; First Page; Previous Page; Next Page; Last Page

### Reports Messenger Insights
- Route: `/reports/messenger_insights`
- Title: `Messenger insights`
- Visible columns/headers: DATE; COMPANY; DOMAIN; COUNTRY; VERTICAL; PERFORMANCE; MESSENGER; DRIP; BROADCAST; COST SUBSCRIBER; COST CONVERSION; INVESTIMENT; REVENUE; PROFIT; ROI; LEADS; SUBSCRIBED; CONVERSIONS; UNSUBSCRIBED; DELIVEREDS; CTR; SESSIONS; RPS; CPM; DELIVEREDS/SUBCRIBER; SESSIONS/SUBSCRIBER; $/SUBSCRIBER; PROFIT/SUBSCRIBER; SENDS; %DELIVERED; DELIVEREDS/LEAD; $/LEAD
- Visible buttons/actions: Update; Export; First Page; Previous Page; 1; Next Page; Last Page

### Reports Messenger Pages
- Route: `/reports/messenger`
- Title: `Messenger Pages`
- Visible columns/headers: DATE; COMPANY; DOMAIN; LOGIN; SEGURADOR; FB_PAGEID; IMAGE; PAGE; PAGE_NAME; START DATE; STATUS; UTM_CAMPAIGN; SOURCE; COUNTRY; VERTICAL; LANGUAGE; ACCOUNT_NAME; PERFORMANCE; MESSENGER; DRIP; BROADCAST; COST SUBSCRIBER; COST CONVERSION; INVESTIMENT; REVENUE; PROFIT; ROI; LEADS_TOTAL; LEADS; SUBSCRIBED; CONVERSIONS; UNSUBSCRIBED; DELIVEREDS; CTR; SESSIONS; RPS; CPM; DELIVEREDS/SUBCRIBER; SESSIONS/SUBSCRIBER; $/SUBSCRIBER; PROFIT/SUBSCRIBER; SENDS; %DELIVERED; DELIVEREDS/LEAD; $/LEAD
- Visible buttons/actions: Update; Export; First Page; Previous Page; 1; 2; 3; 4; 5; Next Page; Last Page

### Reports Messenger Daily
- Route: `/reports/messenger_daily`
- Title: `Messenger Daily`
- Visible columns/headers: SEGURADOR; MON 29/06; TUE 30/06; WED 01/07; THU 02/07; FRI 03/07; SAT 04/07; SUN 05/07; Total
- Visible buttons/actions: Update; First Page; Previous Page; 1; 2; 3; 4; Next Page; Last Page

### Reports Messenger MSGs
- Route: `/reports/messenger_message`
- Title: `Messenger messages`
- Visible columns/headers: LOADING...
- Capture note: table still showed `LOADING...`; recapture with longer wait if this route becomes operationally important.

### Reports CDP
- Route: `/reports/cdp`
- Title: `CDP`
- Visible columns/headers: DATE; AD_REQUESTS; AD_MATCHED; COVERAGE; PRICE; PAGEVIEWS; SESSIONS
- Visible buttons/actions: Update; Export; First Page; Previous Page; 1; Next Page; Last Page

### Reports Facebook Ads
- Route: `/reports/facebook_ads`
- Title: `Facebook Ads`
- Visible columns/headers: LOADING...
- Capture note: table still showed `LOADING...`; recapture with longer wait if this route becomes operationally important.

### Reports Ads Pilot
- Route: `/reports/ads_pilot`
- Title: `Ads Pilot`
- Visible columns/headers: LOADING...
- Capture note: table still showed `LOADING...`; recapture with longer wait if this route becomes operationally important.

### Reports Url Healthy
- Route: `/reports/urlhealthy`
- Title: `Url Healthy`
- Visible columns/headers: LOADING...
- Capture note: table still showed `LOADING...`; recapture with longer wait if this route becomes operationally important.

### Reports GAM Key Values
- Route: `/reports/gam-key-values`
- Title: `GAM Key Values`
- Visible columns/headers: DATE; COMPANY; DOMAIN; KEY; VALUE; REVENUE; AD REQUESTS; AD MATCHES; IMPRESSIONS; CPM; COVERAGE; CTR; %VIEWABLE
- Visible buttons/actions: Update; Export; First Page; Previous Page; Next Page; Last Page

### Reports Photo by Vertical
- Route: `/reports/photo-by-vertical`
- Title: `Vertical per Hour`
- Visible columns/headers: LOADING...
- Capture note: table still showed `LOADING...`; recapture with longer wait if this route becomes operationally important.

### Reports Photo by Adgroup
- Route: `/reports/photo-by-adgroup`
- Title: `Adgroup per Hour`
- Visible columns/headers: LOADING...
- Capture note: table still showed `LOADING...`; recapture with longer wait if this route becomes operationally important.

### Reports Photo by Messenger
- Route: `/reports/photo-by-messenger-insights`
- Title: `Messenger per Hour`
- Visible columns/headers: LOADING...
- Capture note: table still showed `LOADING...`; recapture with longer wait if this route becomes operationally important.

### Reports Photo by Email
- Route: `/reports/photo-by-email`
- Title: `Email per Hour`
- Visible columns/headers: HOUR; DATE; COMPANY; DOMAIN; REVENUE; SENDS; OPENS; OPEN RATE; CLICKS; OPEN CTR; SEND CTR; SESSIONS; PAGEVIEWS; RPS; RPP; REQUESTS; MATCHED; IMPRESSIONS; COVERAGE; CPM; AVG_PRICE; PRICE; GAM_CLICKS; CTR; EPC; VIEWABLE; %VIEWABLE
- Visible buttons/actions: Update; Export; First Page; Previous Page; 1; Next Page; Last Page

### Reports Photo by Url
- Route: `/reports/photo-by-url`
- Title: `Url per Hour`
- Visible columns/headers: LOADING...
- Capture note: table still showed `LOADING...`; recapture with longer wait if this route becomes operationally important.

### Reports Photo by FacebookAds
- Route: `/reports/photo-by-facebookads`
- Title: `FacebookAds per Hour`
- Visible columns/headers: LOADING...
- Capture note: table still showed `LOADING...`; recapture with longer wait if this route becomes operationally important.

### Accounts
- Route: `/accounts`
- Title: `Accounts`
- Visible columns/headers: COMPANY; DOMAIN; ACCOUNT NAME; ACCOUNT ID; TIMEZONE; CURRENCY; COUNTRY; VERTICAL; LOGIN CUSTOMER ID; TOKEN UPDATED AT; ACTIVE
- Visible buttons/actions: Edit Token; New Account; First Page; Previous Page; 1; Next Page; Last Page

### IA Content
- Route: `/company/digital-trust/autocreditadx/content-ia`
- Title: `IA Content`
- Visible columns/headers: Data; Content Key Word; Image Key Word; Category ID; Tags ID; Idioma; URL; Workflow Status; Action
- Visible buttons/actions: Run queue; New; First Page; Previous Page; Next Page; Last Page

### Quiz Maker
- Route: `/company/digital-trust/autocreditadx/quiz-maker`
- Title: `Quiz Maker`
- Visible columns/headers: Name; URL; Company; Domain; Country; Vertical; Language; Created At
- Visible buttons/actions: New Quiz; First Page; Previous Page; Next Page; Last Page

### OKRS
- Route: `/okrs`
- Title: `OKRS`
- Visible columns/headers: Name; Company; Start Date; Final Date; Profit; Operational Cost; Additional Revenue; Active
- Visible buttons/actions: New OKRs

### Users
- Route: `/users`
- Title: `Users`
- Visible columns/headers: Name; Email; Roles; Companies
- Visible buttons/actions: New user; First Page; Previous Page; 1; Next Page; Last Page

### Changelog
- Route: `/changelog`
- Title: `Changelog`
- Visible columns/headers: Date; Company; Domain; Title; Notes; Author; Team
- Visible buttons/actions: New log; First Page; Previous Page; Next Page; Last Page

### Helpdesk
- Route: `/helpdesk`
- Title: `Helpdesk`
- Visible columns/headers: Open Date; Company; Domain; Title; Note; Author; Team; Status; Close Date
- Visible buttons/actions: New ticket; Resolve; Update; First Page; Previous Page; 1; Next Page; Last Page

### Notifications
- Route: `/notifications`
- Title: `Notifications`
- Visible columns/headers: Company; Domain; Title; Date; Read At
- Visible buttons/actions: Mark as read; First Page; Previous Page; 1; 2; 3; 4; 5; Next Page; Last Page

### My Profile
- Route: `/my-profile`
- Title: `My Profile`
- Visible columns/headers: User Info; Security
- Visible buttons/actions: Save

## API endpoints observed

- `/accounts/Facebook` — GET
- `/accounts/Google` — GET
- `/accounts/Messenger` — GET
- `/ads_pilot_config` — POST read/load observed
- `/broadcast/Messenger` — GET
- `/campaigns/Messenger` — GET
- `/changelog` — GET
- `/company` — GET
- `/content-ia/digital-trust_autocreditadx` — GET
- `/countries/enabled` — GET
- `/estimated/delay` — POST read/load observed
- `/estimated/revenue/utm_adgroup` — POST read/load observed
- `/estimated/revenue/utm_campaign` — POST read/load observed
- `/estimated/revenue/vertical` — POST read/load observed
- `/favorites` — GET
- `/helpdesk/list` — POST read/load observed
- `/notification` — GET
- `/okrs` — GET
- `/operations/products/batch` — POST read/load observed
- `/photo/facebookads` — POST read/load observed
- `/photo/messenger_insights` — POST read/load observed
- `/photo/performance_per_adgroup` — POST read/load observed
- `/photo/performance_per_email` — POST read/load observed
- `/photo/performance_per_operation` — POST read/load observed
- `/photo/performance_per_vertical` — POST read/load observed
- `/quizmaker` — GET
- `/report/ads_pilot_log` — POST read/load observed
- `/report/dollar` — GET
- `/report/facebook_ads` — POST read/load observed
- `/report/gam_healthy` — POST read/load observed
- `/report/last_update` — POST read/load observed
- `/report/message` — POST read/load observed
- `/report/messenger` — POST read/load observed
- `/report/messenger_insights` — POST read/load observed
- `/report/overview` — POST read/load observed
- `/report/performance_per_campaigns` — POST read/load observed
- `/report/performance_per_domain` — GET
- `/report/performance_per_email` — POST read/load observed
- `/report/performance_per_operation` — POST read/load observed
- `/report/performance_per_placements` — POST read/load observed
- `/report/performance_per_pushalert` — POST read/load observed
- `/report/performance_per_sms` — POST read/load observed
- `/report/performance_per_vertical` — POST read/load observed
- `/report/queryBuilder` — POST read/load observed
- `/report/youtube/videos_metrics` — POST read/load observed
- `/routing` — POST read/load observed
- `/user` — GET
- `/user/validate` — GET
- `/users/Messenger` — GET

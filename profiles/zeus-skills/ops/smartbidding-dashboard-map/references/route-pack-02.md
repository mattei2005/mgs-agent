## Reports Menu Map

Visible Reports submenu captured live:

```text
Report menu item              Route                                      Main table columns / use
----------------------------  -----------------------------------------  ------------------------------------------------------------
Overview                      /reports/overview                         DATE, COMPANY, DOMAIN, COUNTRY, VERTICAL, ACQUISITION,
                                                                         EMAIL, PUSH, SMS, TOTAL, INVESTIMENT, REVENUE, PROFIT,
                                                                         ROI, SESSIONS, RPS, SENDS, DELIVERED
Domain                        /reports/domain                           DATE/period, COMPANY, DOMAIN, INVESTIMENT, REVENUE, PROFIT,
                                                                         ROI, SESSIONS, PAGEVIEWS, RPS, RPP, REQUESTS, MATCHED,
                                                                         IMPRESSIONS, COVERAGE, CPM, PRICE, CTR, EPC, %VIEWABLE
Acquisition                   /reports/acquisition                      COMPANY, DOMAIN, SOURCE, COUNTRY, VERTICAL, PRODUCT,
                                                                         ACCOUNT/CAMPAIGN/ADGROUP, INVESTIMENT, REVENUE, PROFIT,
                                                                         ROI, acquisition clicks/impressions, sessions/ad metrics
Adgroup                       /reports/adgroup                          DATE, COMPANY, DOMAIN, SOURCE, ACCOUNT/CAMPAIGN/ADGROUP/AD,
                                                                         UTM_ADGROUP, investment/revenue/profit/ROI and ad metrics
Vertical                      /reports/vertical                         Domain-style performance grouped by vertical
Inventory                     /reports/inventory                        Company, Domain, Country, Source, Vertical, Medium, Language,
                                                                         In Use, Available, Content
Operation                     /reports/operation                        DATE, COMPANY, DOMAIN, UTM SOURCE, COUNTRY, VERTICAL, PRODUCT,
                                                                         PAGE TYPE, SLOT ID, REVENUE, RPP/RPS, sessions/pageviews/ad ops
URL                           /reports/url                              DATE, URL, COMPANY, DOMAIN, COUNTRY, SOURCE, VERTICAL, PRODUCT,
                                                                         PAGE_TYPE, revenue, sessions/pageviews, ad metrics
Placement                     /reports/placement                        DATE, COMPANY, DOMAIN, SOURCE, account/campaign/placement,
                                                                         investment/revenue/profit/ROI and ad metrics
SMS                           /reports/sms                              DATE, COMPANY, DOMAIN, SOURCE, UTM_CAMPAIGN, MSG_ID, LABEL,
                                                                         MESSAGES, DELIVERED, FAILED, CTR, sessions/ad metrics
Email                         /reports/email                            DATE, COMPANY, DOMAIN, COUNTRY, VERTICAL, ACCOUNT/CAMPAIGN,
                                                                         UTM_CAMPAIGN, AUTO_NAME, REVENUE, SENDS, OPENS, CLICKS,
                                                                         sessions/ad metrics
Pushalert                     /reports/pushalert                        DATE, COMPANY, DOMAIN, COUNTRY, VERTICAL, UTM_CAMPAIGN, TITLE,
                                                                         REVENUE, SENDS, DELIVERED, CLICKS, sessions/ad metrics
Youtube                       /reports/youtube                          DATE, CHANNEL, ID, VIDEO, PUBLISHED, VIEWS, REVENUE, ADS, CPM,
                                                                         likes/comments/shares/subscriber/watch metrics
Messenger Insights            /reports/messenger_insights               DATE, COMPANY, DOMAIN, COUNTRY, VERTICAL, PERFORMANCE, MESSENGER,
                                                                         DRIP, BROADCAST, cost subscriber/conversion, leads, delivery,
                                                                         sessions and profit/subscriber metrics
Messenger Pages               /reports/messenger                        DATE, COMPANY, DOMAIN, LOGIN, SEGURADOR, FB_PAGEID, PAGE,
                                                                         PAGE_NAME, START DATE, STATUS, UTM_CAMPAIGN, SOURCE, COUNTRY,
                                                                         VERTICAL, LANGUAGE, performance/messenger/drip/broadcast metrics
Messenger Daily               /reports/messenger_daily                  SEGURADOR by daily columns + Total; useful for weekly/daily messenger revenue
Messenger MSGs                /reports/messenger_message                DATE, COMPANY, DOMAIN, COUNTRY, VERTICAL, UTM_CAMPAIGN,
                                                                         UTM_CONTENT, TYPE, SENDS, DELIVEREDS, CTR, SESSIONS, PAGEVIEWS
CDP                           /reports/cdp                              DATE, AD_REQUESTS, AD_MATCHED, COVERAGE, PRICE, PAGEVIEWS, SESSIONS\n                                                                         Operational meaning: Pricing pulls matched from CDP. Use CDP by\n                                                                         site/date/hour to link rule/floor changes to matched/coverage.\n                                                                         If a large player stops bidding or blocks a site, matched/coverage\n                                                                         can drop; lowering the rule/floor may raise coverage and let other\n                                                                         players fill. CDP indicates this pattern but does not prove which\n                                                                         advertiser/player changed. Watch CDP vs GAM distance as an alert.
                                                                         use /report/queryBuilder with publisher `company_domain` for site-level hourly coverage. See `references/cdp-gamezonead-hourly-query-2026-07-05.md`.
                                                                         For Gamezonead first rewards / `rec > mob-rewarded`, do not use publisher average: filter CDP by `PAGE_TYPE=rec` + `SLOT_ID=digital-trust_gamezonead_mob_br_google_s_rewarded`. See `references/cdp-gamezonead-first-rewards-slot-query-2026-07-06.md`.
Facebook Ads                  /reports/facebook_ads                     DATE, COMPANY, DOMAIN, COUNTRY, VERTICAL, ACCOUNT/CAMPAIGN/ADSET/AD,
                                                                         UTM_CAMPAIGN, investment, conversion/subscriber/click/impression,
                                                                         revenue, profit, ROI, cost/rate metrics
Ads Pilot                     /reports/ads_pilot                        TIME, INVESTIMENT, INVESTIMENT INCREMENTAL, SUBSCRIBERS,
                                                                         CONVERSIONS, COST SUBSCRIBER/CONVERSION, BUDGET, CPA TARGET
Url Healthy                   /reports/urlhealthy                       DATE, COMPANY, DOMAIN, COUNTRY, SOURCE, VERTICAL, URL,
                                                                         ADS REMOVED, ADS HEALTHY, REVENUE REMOVED, OPERATIONS
GAM Key Values                /reports/gam-key-values                   DATE, COMPANY, DOMAIN, KEY, VALUE, REVENUE, AD REQUESTS,
                                                                         AD MATCHES, IMPRESSIONS, CPM, COVERAGE, CTR, %VIEWABLE
Photo by Vertical             /reports/photo-by-vertical                Hourly vertical photo: HOUR, DATE, COMPANY, DOMAIN, investment,
                                                                         revenue/profit/ROI, sessions/pageviews, ad metrics
Photo by Adgroup              /reports/photo-by-adgroup                 Hourly adgroup photo: HOUR, DATE, COMPANY, DOMAIN, investment,
                                                                         revenue/profit/ROI, acquisition clicks/conversions and ad metrics
Photo by Messenger            /reports/photo-by-messenger-insights      Hourly Messenger photo: HOUR, DATE, COMPANY, DOMAIN, Messenger/Drip/
                                                                         Broadcast, cost subscriber/conversion, revenue/profit/ROI,
                                                                         leads/conversions/subscribed/delivereds/sessions/CTR/RPS
Photo by Email                /reports/photo-by-email                   HOUR, DATE, COMPANY, DOMAIN, REVENUE, SENDS, OPENS, CLICKS,
                                                                         sessions/pageviews/ad metrics by hour
Photo by Url                  /reports/photo-by-url                     Hourly URL photo: HOUR, DATE, COMPANY, DOMAIN, REVENUE,
                                                                         PAGEVIEWS, RPP, CPM, AVG PRICE, requests/matched/impressions,
                                                                         coverage, CTR, EPC, viewable
Photo by FacebookAds          /reports/photo-by-facebookads             Hourly FacebookAds photo: HOUR, DATE, COMPANY, DOMAIN,
                                                                         investment diff, subscribers/conversions diff, cost subscriber/
                                                                         conversion diff, clicks/CTR/cost click, impressions/CPM
```

Report read/query endpoints observed:

```text
POST /report/overview
GET  /report/performance_per_domain
POST /report/performance_per_campaigns
POST /report/performance_per_vertical
POST /report/performance_per_operation
POST /report/performance_per_placements
POST /report/performance_per_sms
POST /report/performance_per_email
POST /report/performance_per_pushalert
POST /report/youtube/videos_metrics
POST /report/messenger_insights
POST /report/messenger
POST /report/message
POST /report/facebook_ads
POST /report/ads_pilot_log
POST /report/gam_healthy
POST /report/last_update
POST /report/queryBuilder  # generic report builder; validated for CDP DATE+HOUR site coverage
POST /photo/performance_per_vertical
POST /photo/performance_per_adgroup
POST /photo/messenger_insights
POST /photo/performance_per_email
POST /photo/performance_per_operation
POST /photo/facebookads
GET  /report/dollar
```


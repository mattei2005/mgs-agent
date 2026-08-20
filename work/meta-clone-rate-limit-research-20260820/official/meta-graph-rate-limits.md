Title: Rate Limits - Graph API - Documentation - Meta for Developers

URL Source: http://developers.facebook.com/docs/graph-api/overview/rate-limiting/

Markdown Content:
## Platform Rate Limits

Platform Rate Limits are tracked on an individual application or user level, depending on the type of token used in the request.

### Applications

Graph API requests made with an [application access token](https://developers.facebook.com/docs/facebook-login/access-tokens#apptokens) are counted against that app’s rate limit. An app’s call count is the number of calls it can make during a rolling one hour window and is calculated as follows:

`Calls within one hour = 200 * Number of Users`

The Number of Users is based on the number of unique daily active users an app has. In cases where there are slow periods of daily usage, such as if your app has high activity on weekends but low activity over weekdays, the weekly and monthly active Users are used to calculate the number of Users for your app. Apps with high daily engagement will have higher rate limits than apps with low daily engagement, regardless of the actual number of app installs.

Note that this is not a per User limit but a limit on calls made by your app. Any individual User can make more than 200 calls per hour using your app, as long as the total calls from your app does not exceed the app maximum. For example, if your app has 100 Users, your app can make 20,000 calls per hour. However, your top ten most engaged Users could make 19,000 of those calls.

### Users

Graph API requests made with a [user access token](https://developers.facebook.com/docs/facebook-login/access-tokens#usertokens) are counted against that user’s call count. A user’s call count is the number of calls a user can make during a rolling one hour window. Due to privacy concerns, we do not reveal actual call count values for users.

Note that a user’s call count can be spread over multiple apps. For example, a user could make X calls through App1 and Y calls through App2. If X+Y exceeds the user’s call count that user will be rate limited. This does not necessarily mean that any app is doing something wrong; it could be that the user is using multiple apps or is misusing the API.

Endpoints that receive enough requests from your app will include a `X-App-Usage` or `X-Ad-Account-Usage` (for v3.3 and older Ads API calls) HTTP header in their responses. The header will contain a JSON-formatted string that describes current application rate limit usage.

#### Header Contents

| Key | Value Description |
| --- | --- |
| `call_count` | A whole number expressing the percentage of calls made by your app over a rolling one hour period. |
| `total_cputime` | A whole number expressing the percentage of CPU time allotted for query processing. |
| `total_time` | A whole number expressing the percentage of total time allotted for query processing. |

#### X-Ad-Account-Usage Header Contents

| Key | Value Description |
| --- | --- |
| `acc_id_util_pct` | The percentage of calls made for this ad account before the rate limit is reached. |
| `reset_time_duration` | Time duration (in seconds) it takes to reset the current rate limit to 0. |
| `ads_api_access_tier` | Tiers allows your app to access the Marketing API. By default, apps are in the `development_access` tier. `Standard_access` enables lower rate limiting. To get a higher rate limit and get to the standard tier, you can apply for the "Advanced Access" to the [Ads Management Standard Access](http://developers.facebook.com/docs/marketing-api/overview/authorization#layer-2--access-levels--permissions--and-features) feature. |

#### Total CPU Time

The amount of CPU time the request takes to process. When `total_cputime` reaches 100, calls may be throttled.

#### Total Time

The length of time the request takes to process. When `total_time` reaches 100, calls may be throttled.

#### Sample X-App-Usage Header Value

x-app-usage: { "call_count": 28, //Percentage of calls made "total_time": 25, //Percentage of total time "total_cputime": 25 //Percentage of total CPU time }
#### Sample X-Ad-Account-Usage Header Value

x-ad-account-usage: { "acc_id_util_pct": 9.67, //Percentage of calls made for this ad account. "reset_time_duration": 100, //Time duration (in seconds) it takes to reset the current rate limit score. "ads_api_access_tier": 'standard_access' //Tiers allows your app to access the Marketing API. standard_access enables lower rate limiting.}
### Dashboard

The [app dashboard](https://developers.facebook.com/apps/) displays the number of rate limited app users, the app’s current Application Rate Limits usage percentage, and displays average activity for the past 7 days. In the **Application Rate Limit** card, click **View Details** and hover over any point on the graph to see more details about usage for that particular moment. Because usage depends on call volume, this graph may not show a full 7 days. Apps with a higher volume of calls will show more days.

### Error Codes

When an app or user has reached their rate limit, requests made by that app or user will fill and the API will respond with an error code.

#### Throttle Error Codes

| Error Code | Description |
| --- | --- |
| `4` | Indicates that the app whose token is being used in the request has reached its rate limit. |
| `17` | Indicates that the User whose token is being used in the request has reached their rate limit. |
| `17 with subcode 2446079` | Indicates that the token being used in the Ads API v3.3 or older request has reached its rate limit. |
| `32` | Indicates that the User or app whose token is being used in the Pages API request has reached its rate limit. |
| `613` | Indicates that a custom rate limit has been reached. To help resolving this issue, visit the supporting docs for the specific API you are calling for custom rate limits that may be applied. |
| `613 with subcode 1996` | Indicates that we have noticed inconsistent behavior in the API request volume of your app. If you have made any recent changes that affect the number of API requests, you may be encountering this error. |

#### Sample Response

{ "error": { "message": "(#32) Page request limit reached", "type": "OAuthException", "code": 32, "fbtrace_id": "Fz54k3GZrio" }}
### Facebook Stability Throttle Codes

| Error Code | Description |
| --- | --- |
| `throttled` | Whether the query is throttled or not. Values: `True`, `False` |
| `backend_qps` | First throttling factor `backend_qps`. Supported values: * `actual_score`—Actual `backend_qps` of this app. Value: `8` * `limit`—`backend_qps` limit of this app. Value: `5` * `more_info`—Queries need a large number of backend requests to handle. We suggest to send fewer queries or simplify queries with narrower time ranges, fewer object IDs, and so on. |
| `complexity_score` | Second throttling factor `complexity_score`. Supported values: * `actual_score`—Actual `complexity_score` of this app. Value: `0.1` * `limit`—`complexity_score` limit of this app. Value: `0.01` * `more_info`—High `complexity_score` means your queries are very complex and request large amounts of data. We suggest to simplify queries with shorter time ranges, fewer object IDs, metrics or breakdowns, and so on. Split large, complex queries into multiple smaller queries and space them out. |

### Best Practices

*   When the limit has been reached, stop making API calls. Continuing to make calls will continue to increase your call count, which will increase the time before calls will be successful again.

*   Spread out queries evenly to avoid traffic spikes.

*   Use filters to limit the data response size and avoid calls that request overlapping data.

*   Check the `X-App-Usage` HTTP header to see how close your app is to its limit and when you can resume making calls when the limit has been reached.

*   If Users are being throttled, be sure your app is not the cause. Reduce the user’s calls or spread the user’s calls more evenly over time.

## Business Use Case Rate Limits

All Marketing API requests, and Pages API requests made with a system or page access token, are subject to Business Use Case (BUC) Rate Limits, and depend on the endpoints you are querying.

For Marketing API, the rate limit is applied to the ad account across the same Business Use Case. For example, all endpoints with the Ads Management business use case will share the total quota within the same ad account. If a certain endpoint makes a lot of API requests and causes throttling, other endpoints configured with the same business use case will also receive rate limiting errors. The quota depends on the app's Marketing API Access Tier. The standard access Marketing API tier will have more quotas than the development access Marketing API tier. By default, an new app should be on the development tier. If you need to upgrade to get more rate limiting quota, upgrade to Advanced Access of [Ads Management Standard Access](http://developers.facebook.com/docs/features-reference/ads-management-standard-access/) in App Review.

*   [Ad Insights](http://developers.facebook.com/docs/graph-api/overview/rate-limiting/#ads-insights)
*   [Ads Management](http://developers.facebook.com/docs/graph-api/overview/rate-limiting/#ads-management)
*   [Catalog](http://developers.facebook.com/docs/graph-api/overview/rate-limiting/#catalog)
*   [Custom Audience](http://developers.facebook.com/docs/graph-api/overview/rate-limiting/#custom-audience)
*   [Instagram Platform](http://developers.facebook.com/docs/graph-api/overview/rate-limiting/#instagram-platform)
*   [Lead Generation](http://developers.facebook.com/docs/graph-api/overview/rate-limiting/#leadgen)*   [Messenger](http://developers.facebook.com/docs/graph-api/overview/rate-limiting/#messenger)
*   [Pages](http://developers.facebook.com/docs/graph-api/overview/rate-limiting/#pages)
*   [Spark AR Commerce Effect Management](http://developers.facebook.com/docs/graph-api/overview/rate-limiting/#spark-ar)
*   [WhatsApp Business Management API](http://developers.facebook.com/docs/graph-api/overview/rate-limiting/#wa-biz-api)

### Ads Insights

Requests made by your app to the Ads Insights API are counted against the app's rate limit metrics such as call count, total CPU time and total time. An app's call count is the number of calls it can make during a rolling one hour window and is calculated as follows:

For apps with [Standard Access](http://developers.facebook.com/docs/graph-api/overview/access-levels/#standard-access) to the Ads Management Standard Access feature:

`Calls within one hour = 600 + 400 * Number of Active ads - 0.001 * User Errors`

For apps with [Advanced Access](http://developers.facebook.com/docs/graph-api/overview/access-levels/#advanced-access) to the Ads Management Standard Access feature:

`Calls within one hour = 190000 + 400 * Number of Active ads - 0.001 * User Errors`

The Number of Active ads is the number of ads currently running per ad account. User Errors is the number of errors received when calling the API. To get a higher rate limit, you can apply for the [Ads Management Standard Access](http://developers.facebook.com/docs/marketing-api/overview/authorization#layer-2--access-levels--permissions--and-features) feature.

Rate limiting may also be subject to the total CPU time and total wall time during a rolling one hour window. For more details, check the HTTP [`X-Business-Use-Case`](http://developers.facebook.com/docs/graph-api/overview/rate-limiting/#headers-2) header `total_cputime` and `total_time`.

If you are receiving rate limiting errors, you can also refer to `estimated_time_to_regain_access` in the [`X-Business-Use-Case`](http://developers.facebook.com/docs/graph-api/overview/rate-limiting/#headers-2) header for the estimated blocking time.

### Ads Management

Requests made by your app to the Ads Management API are counted against the app's rate limit metrics such as call count, total CPU time and total time. An app's call count is the number of calls it can make during a rolling one hour window and is calculated as follows:

For apps with [Standard Access](http://developers.facebook.com/docs/graph-api/overview/access-levels/#standard-access)to the Ads Management Standard Access feature:

`Calls within one hour = 300 + 40 * Number of Active ads`

For apps with [Advanced Access](http://developers.facebook.com/docs/graph-api/overview/access-levels/#advanced-access) to the Ads Management Standard Access feature:

`Calls within one hour = 100000 + 40 * Number of Active ads`

The Number of Active Ads is the number of ads for each ad account.

Rate limiting may also be subject to the total CPU time and total wall time during a rolling one hour window. For more details, check the HTTP [`X-Business-Use-Case`](http://developers.facebook.com/docs/graph-api/overview/rate-limiting/#headers-2) header `total_cputime` and `total_time`.

If you are receiving rate limiting errors, you can also refer to `estimated_time_to_regain_access` in the [`X-Business-Use-Case`](http://developers.facebook.com/docs/graph-api/overview/rate-limiting/#headers-2) header for the estimated blocking time.

### Catalog

#### Catalog Batch

Requests made by your app are counted against the rate limit metrics such as call count, total CPU time and total time your app can make in a rolling one minute period per each catalog ID and is calculated as follows:

`Calls within one minute = 8 + 8 * log2(DA impressions + PDP visits)`

The DA impressions and PDP visits are a number of dynamic ads impressions and product detail page visits of the individual catalog with intent in the last 28 days. The more users see products from your catalogs, the more call quota is allocated.

| Type of Call | Endpoint |
| --- | --- |
| POST | /{catalog_id}/items_batch |
| POST | /{catalog_id}/localized_items_batch |
| POST | /{catalog_id}/batch |

#### Catalog Management

Requests made by your app are counted against the number of calls your app can make in a rolling one hour period per each catalog ID and is calculated as follows:

`Calls within one hour = 20,000 + 20,000 * log2(DA impressions + PDP visits)`

The DA impressions and PDP visits are a number of dynamic ads impressions and product detail page visits of the business (on all catalogs) with intent in the last 28d. The more users see products from your catalogs, the more call quota is allocated.

This formula is applied on various catalog endpoints.

For more information on how to get your current rate usage, see [Headers](http://developers.facebook.com/docs/graph-api/overview/rate-limiting/#headers).

Rate limiting may also be subject to the total CPU time and total wall time during a rolling one hour window. For more details, check the HTTP [`X-Business-Use-Case`](http://developers.facebook.com/docs/graph-api/overview/rate-limiting/#headers-2) header `total_cputime` and `total_time`.

If you are receiving rate limiting errors, you can also refer to `estimated_time_to_regain_access` in the [`X-Business-Use-Case`](http://developers.facebook.com/docs/graph-api/overview/rate-limiting/#headers-2) header for the estimated blocking time.

### Custom Audience

Requests made by your app to the Custom Audience API are counted against the app's rate limit metrics such as call count, total CPU time and total time. An app's call count is the number of calls it can make during a rolling one hour window and is calculated as follows but will never exceed 700000:

For apps with [Standard Access](http://developers.facebook.com/docs/graph-api/overview/access-levels/#standard-access) to the Ads Management Standard Access feature:

`Calls within one hour = 5000 + 40 * Number of Active Custom Audiences`

For apps with [Advanced Access](http://developers.facebook.com/docs/graph-api/overview/access-levels/#advanced-access) to the Ads Management Standard Access feature:

`Calls within one hour = 190000 + 40 * Number of Active Custom Audiences`

The Number of Active Custom Audiences is the number of active [custom audiences](https://developers.facebook.com/docs/marketing-api/audiences-api) for each ad account.

Rate limiting may also be subject to the total CPU time and total wall time during a rolling one hour window. For more details, check the HTTP [`X-Business-Use-Case`](http://developers.facebook.com/docs/graph-api/overview/rate-limiting/#headers-2) header `total_cputime` and `total_time`.

If you are receiving rate limiting errors, you can also refer to `estimated_time_to_regain_access` in the [`X-Business-Use-Case`](http://developers.facebook.com/docs/graph-api/overview/rate-limiting/#headers-2) header for the estimated blocking time.

### Instagram Platform

Calls to the Instagram Platform endpoints, excluding messaging, are counted against the calling app's call count. An app's call count is unique for each app and app user pair, and is the number of calls the app has made in a rolling 24 hour window. It is calculated as follows:

`Calls within 24 hours = 4800 * Number of Impressions`

The Number of Impressions is the number of times any content from the app user's Instagram professional account has entered a person's screen within the last 24 hours.

#### Notes

*   Business Discovery and Hashtag Search API are subject to [Platform Rate Limits](http://developers.facebook.com/docs/graph-api/overview/rate-limiting#platform-rate-limits).

### Messaging Rate Limits

Calls to the Instagram messaging endpoints are counted against the number of calls your app can make per Instagram professional account and the API used.

#### Conversations API

*   Your app can make 2 calls per second per Instagram professional account.

#### Private Replies API

*   Your app can make 100 calls per second per Instagram professional account for private replies to Instagram Live comments
*   Your app can make 750 calls per hour per Instagram professional account for private replies to comments on Instagram posts and reels

#### Send API

*   Your app can make 100 calls per second per Instagram professional account for messages that contain text, links, reactions, and stickers
*   Your app can make 10 calls per second per Instagram professional account for messages that contain audio or video content

### LeadGen

Requests made by your app to the LeadGen API are counted against the app’s call count. An app’s call count is the number of calls it can make during a rolling 24 hour window and is calculated as follows:

`Calls within 24 hours = 4800 * Leads Generated`

The Number of Leads Generated is the number of leads generated per Page for this Ad Account over the past 90 days.

### Messenger Platform

Rate limits for the Messenger Platform are dependent on the API used and, in some instances, the message content.

### Messenger API

Requests made by your app are counted against the number of calls your app can make in a rolling 24 hour period and is calculated as follows:

`Calls within 24 hours = 200 * Number of Engaged Users`

The Number of Engaged Users is the number of people the business can message via Messenger.

**Conversations API**

*   Your app can make 2 calls per second per Facebook Page

**Send API**

*   Your app can make 300 calls per second per Facebook Page for messages that contain text, links, reactions, and stickers
*   Your app can make 10 calls per second per Facebook Page account for messages that contain audio or video content
*   Your app may be rate limited if too many messages are being sent to a single thread

**Private Replies API**

*   Your app can make 750 calls per hour per Facebook Page for private replies to comments on Instagram posts and reels

### Messenger API for Instagram

Requests made by your app are counted against the number of calls your app can make per Instagram professional account and the API used.

**Conversations API**

*   Your app can make 2 calls per second per Instagram professional account 

**Send API**

*   Your app can make 300 calls per second per Instagram professional account for messages that contain text, links, reactions, and stickers
*   Your app can make 10 calls per second per Instagram professional account for messages that contain audio or video content
*   Your app may be rate limited if too many messages are being sent to a single thread

**Private Replies API**

*   Your app can make 100 calls per second per Instagram professional account for private replies to Instagram Live comments
*   Your app can make 750 calls per hour per Instagram professional account for private replies to comments on Instagram posts and reels

### Pages

The Page Rate Limits may use either the Platform or BUC rate limit logic depending on the type of token used. Any Pages API calls that are made using a [Page](https://developers.facebook.com/docs/facebook-login/access-tokens#pagetokens) or [system user access token](https://developers.facebook.com/docs/marketing-api/businessmanager/systemuser#systemusertoken) use the rate limit calculation below. Any calls made with [application](https://developers.facebook.com/docs/facebook-login/access-tokens#apptokens) or [user access tokens](https://developers.facebook.com/docs/facebook-login/access-tokens#usertokens) are subject to application or User rate limits.

Requests made by your app to the Pages API using a Page access token or system User access token are counted against the app’s call count. An app’s call count is the number of calls it can make during a rolling 24 hour window and is calculated as follows:

`Calls within 24 hours = 4800 * Number of Engaged Users`

The Number of Engaged Users is the number of Users who engaged with the Page per 24 hours.

Requests made by your app to the Pages API using a User access token or App access token follow the [Platform Rate Limit logic](http://developers.facebook.com/docs/graph-api/overview/rate-limiting/#platform-rate-limits).

To avoid [rate limiting](http://developers.facebook.com/docs/graph-api/overview/rate-limiting#pages) issues when using the [Page Public Access Content feature](http://developers.facebook.com/docs/pages/overview/permissions-features#features), using a [system user access token](https://www.facebook.com/business/help/503306463479099) is recommended.

### Spark AR Commerce Effect Management

Requests made by your app to any Commerce endpoints are counted against the app’s call count. An app’s call count is the number of calls it can make during a rolling one hour window and is calculated as follows:

`Calls within one hour = 200 + 40 * Number of Catalogs`

The Number of Catalogs is the total number of catalogs across all commerce accounts managed by your app.

### Threads

Calls to the Threads API are counted against the calling app's call count. An app's call count is unique for each app and app user pair and is the number of calls the app has made in a rolling 24-hour window. It is calculated as follows:

`Calls within 24 hours = 4800 * Number of Impressions`

The Number of Impressions is the number of times any content from the app user's Threads account has entered a person's screen within the last 24 hours. Rate limiting may also be subject to total CPU time per day:

```
720000 * number_of_impressions for total_cputime 
      2880000 * Number of Impressions for total_time
```

**Note:** The minimum value for impressions is 10 (so if the impressions is less than 10 we default to 10).

### WhatsApp Business Management API

Requests made by your app on your WhatsApp Business Account (WABA) are counted against your app's request count. An app's request count is the number of requests it can make during a rolling one hour.

For the following endpoints, your app can make 200 requests per hour, per app, per WABA, by default. For active WABAs with at least one registered phone number, your app can make 5000 requests per hour, per app, per active WABA.

| Type of request | Endpoint |
| --- | --- |
| `GET` | `/<WHATSAPP_BUSINESS_ACCOUNT_ID>` |
| `GET`, `POST`, and `DELETE` | `/<WHATSAPP_BUSINESS_ACCOUNT_ID>/assigned_users` |
| `GET` | `/<WHATSAPP_BUSINESS_ACCOUNT_ID>/phone_numbers` |
| `GET`, `POST`, and `DELETE` | `/<WHATSAPP_BUSINESS_ACCOUNT_ID>/message_templates` |
| `GET`, `POST`, and `DELETE` | `/<WHATSAPP_BUSINESS_ACCOUNT_ID>/subscribed_apps` |
| `GET` | `/<WHATSAPP_BUSINESS_ACCOUNT_TO_NUMBER_CURRENT_STATUS_ID>` |

For the following [Credit Line API](http://developers.facebook.com/docs/whatsapp/embedded-signup/manage-accounts/share-and-revoke-credit-lines) requests, your app can make 5000 requests per hour.

| Type of request | Endpoint |
| --- | --- |
| `GET` | `/<BUSINESS_ID>/extendedcredits` |
| `POST` | `/<EXTENDED_CREDIT_ID>/whatsapp_credit_sharing_and_attach` |
| `GET` and `DELETE` | `/<ALLOCATION_CONFIG_ID>` |
| `GET` | `/<EXTENDED_CREDIT_ID>/owning_credit_allocation_configs` |

For more information on how to get your current rate usage, see [Headers](http://developers.facebook.com/docs/graph-api/overview/rate-limiting/#headers).

All API responses made by your app that are rate limited using the BUC logic include an `X-Business-Use-Case-Usage` (for v3.3 and older Ads API calls) HTTP header with a JSON-formatted string that describes current application rate limit usage. This header can return up to 32 objects in one call.

#### X-Business-Use-Case Usage Header Contents

| Error Code | Value Description |
| --- | --- |
| `business-id` | The ID of the business associated with the token making the API calls. |
| `call_count` | A whole number expressing the percentage of allowed calls made by your app over a rolling one hour period. |
| `estimated_time_to_regain_access` | Time, in minutes, until calls will not longer be throttled. |
| `total_cputime` | A whole number expressing the percentage of CPU time allotted for query processing. |
| `total_time` | A whole number expressing the percentage of total time allotted for query processing. |
| `type` | Type of rate limit applied. Value can be one of the following: `ads_insights`, `ads_management`, `custom_audience`, `instagram`, `leadgen`, `messenger`, or `pages`. |
| `ads_api_access_tier` | For `ads_insights` and `ads_management` types only. Tiers allows your app to access the Marketing API. By default, apps are in the `development_access` tier. `Standard_access` enables lower rate limiting. To get a higher rate limit and get to the standard tier, you can apply for the "Advanced Access" to the [Ads Management Standard Access](http://developers.facebook.com/docs/marketing-api/overview/authorization#layer-2--access-levels--permissions--and-features) feature. |

#### Total CPU Time

The amount of CPU time the request takes to process. When total_cputime reaches 100, calls may be throttled.

#### Total Time

The length of time the request takes to process. When total_time reaches 100, calls may be throttled.

#### Ads API Access Tier

For `ads_insights` and `ads_management` types only. Tiers allows your app to access the Marketing API. By default, apps are in the `development_access` tier. `Standard_access` enables lower rate limiting. To get a higher rate limit and get to the standard tier, you can apply for the "Advanced Access" to the [Ads Management Standard Access](http://developers.facebook.com/docs/marketing-api/overview/authorization#layer-2--access-levels--permissions--and-features) feature.

#### Sample X-Business-Use-Case-Usage Header Value

x-business-use-case-usage: { "{business-object-id}": [ { "type": "{rate-limit-type}", //Type of BUC rate limit logic being applied. "call_count": 100, //Percentage of calls made. "total_cputime": 25, //Percentage of the total CPU time that has been used. "total_time": 25, //Percentage of the total time that has been used. "estimated_time_to_regain_access": 19, //Time in minutes to regain access. "ads_api_access_tier": "standard_access" //Tiers allows your app to access the Marketing API. standard_access enables lower rate limiting. } ], "66782684": [ { "type": "ads_management", "call_count": 95, "total_cputime": 20, "total_time": 20, "estimated_time_to_regain_access": 0, "ads_api_access_tier": "development_access" } ], "10153848260347724": [ { "type": "ads_insights", "call_count": 97, "total_cputime": 23, "total_time": 23, "estimated_time_to_regain_access": 0, "ads_api_access_tier": "development_access" } ], "10153848260347724": [ { "type": "pages", "call_count": 97, "total_cputime": 23, "total_time": 23, "estimated_time_to_regain_access": 0 } ],...}
### Error Codes

When your app reaches its Business Use Case rate limit, subsequent requests made by your app will fail and the API will respond with an error code.

| Error Code | BUC Rate Limit Type |
| --- | --- |
| `error code 80000, error subcode 2446079` | Ads Insights |
| `error code 80004, error subcode 2446079` | Ads Management |
| `error code 80003, error subcode 2446079` | Custom Audience |
| `error code 80002` | Instagram |
| `error code 80005` | LeadGen |
| `error code 80006` | Messenger |
| `error code 32` | Page calls made with a User access token |
| `error code 80001` | Page calls made with a Page or System User access token |
| `error code 17, error subcode 2446079` | V3.3 and Older Ads API excluding Ads Insights |
| `error code 80008` | WhatsApp Business Management API |
| `error code 80014` | Catalog Batch |
| `error code 80009` | Catalog Management |

#### SampleError Code Message

{ "error": { "message": "(#80001) There have been too many calls to this Page account. Wait a bit and try again. For more info, please refer to https://developers.facebook.com/docs/graph-api/overview/rate-limiting.", "type": "OAuthException", "code": 80001, "fbtrace_id": "AmFGcW_3hwDB7qFbl_QdebZ" }}
### Best Practices

*   When the limit has been reached, stop making API calls. Continuing to make calls will continue to increase your call count, which will increase the time before calls will be successful again.
*   Check the `X-Business-Use-Case-Usage` HTTP header to see how close your ad account is to its limit and when you can resume making calls.
*   Verify the error code and API endpoint to confirm the throttling type.
*   Switch to other ad accounts and come back to this account later.
*   It is better to create a new ad than to change existing ones.
*   Spread out queries evenly between two time intervals to avoid sending traffic in spikes.
*   Use filters to limit the data response size and avoid calls that request overlapping data.

## FAQ

#### What do we consider an API call?

All calls count towards the rate limits, not just individual API requests. For example, you can make a single API request specifying multiple IDs, but each ID counts as one API call.

The following table illustrates this concept.

| Example Request(s) | Number of API Calls |
| --- | --- |
| `GET https://graph.facebook.com/photos?ids=4` `GET https://graph.facebook.com/photos?ids=5` `GET https://graph.facebook.com/photos?ids=6` | 3 |
| `GET https://graph.facebook.com/photos?ids=4,5,6` | 3 |

We strongly recommend specifying multiple IDs in one API request when possible, as this improves performance of your API responses.

#### I'm building a scraper, is there anything else I should worry about?

If you are building a service that scrapes data, please read [our scraping terms](https://www.facebook.com/apps/site_scraping_tos_terms.php?hc_location=ufi).

Title: Graph API Reference v26.0: Ad Set Copies - Documentation - Meta for Developers

URL Source: http://developers.facebook.com/docs/marketing-api/reference/ad-campaign/copies/

Markdown Content:
![Image 1](https://facebook.com/security/hsts-pixel.gif)

[Docs](http://developers.facebook.com/docs/)[Graph API](http://developers.facebook.com/docs/graph-api)[Reference](http://developers.facebook.com/docs/graph-api/reference/)[Ad Set](http://developers.facebook.com/docs/graph-api/reference/ad-campaign/)[Copies](http://developers.facebook.com/docs/graph-api/reference/ad-campaign/copies)

[Graph API](http://developers.facebook.com/docs/graph-api)

*   [Overview](http://developers.facebook.com/docs/graph-api/overview)
*   [Get Started](http://developers.facebook.com/docs/graph-api/get-started)
*   [Batch Requests](http://developers.facebook.com/docs/graph-api/batch-requests)
*   [Debug Requests](http://developers.facebook.com/docs/graph-api/guides/debugging)
*   [Handle Errors](http://developers.facebook.com/docs/graph-api/guides/error-handling)
*   [Field Expansion](http://developers.facebook.com/docs/graph-api/guides/field-expansion)
*   [Secure Requests](http://developers.facebook.com/docs/graph-api/guides/secure-requests)
*   [Changelog](http://developers.facebook.com/docs/graph-api/changelog)
*   [Reference](http://developers.facebook.com/docs/graph-api/reference)

On This Page

[Ad Set Copies](http://developers.facebook.com/docs/marketing-api/reference/ad-campaign/copies/#overview)

[Reading](http://developers.facebook.com/docs/marketing-api/reference/ad-campaign/copies/#Reading)

[Example](http://developers.facebook.com/docs/marketing-api/reference/ad-campaign/copies/#example)

[Parameters](http://developers.facebook.com/docs/marketing-api/reference/ad-campaign/copies/#parameters)

[Fields](http://developers.facebook.com/docs/marketing-api/reference/ad-campaign/copies/#fields)

[Error Codes](http://developers.facebook.com/docs/marketing-api/reference/ad-campaign/copies/#error-codes)

[Creating](http://developers.facebook.com/docs/marketing-api/reference/ad-campaign/copies/#Creating)

[Asynchronous](http://developers.facebook.com/docs/marketing-api/reference/ad-campaign/copies/#async)

[Targeting DSA Regulated Locations (European Union)](http://developers.facebook.com/docs/marketing-api/reference/ad-campaign/copies/#targeting-dsa-regulated-locations--european-union-)

[Parameters](http://developers.facebook.com/docs/marketing-api/reference/ad-campaign/copies/#parameters-2)

[Return Type](http://developers.facebook.com/docs/marketing-api/reference/ad-campaign/copies/#return-type)

[Error Codes](http://developers.facebook.com/docs/marketing-api/reference/ad-campaign/copies/#error-codes-2)

[Updating](http://developers.facebook.com/docs/marketing-api/reference/ad-campaign/copies/#Updating)

[Deleting](http://developers.facebook.com/docs/marketing-api/reference/ad-campaign/copies/#Deleting)

Graph API Version

[v26.0](http://developers.facebook.com/docs/marketing-api/reference/ad-campaign/copies/#)

# Ad Set Copies

[](http://developers.facebook.com/docs/marketing-api/reference/ad-campaign/copies/#)

Create a duplicate ad set based on an existing one.

The Marketing API has it is own rate limiting logic. If you are encountering errors mentioning a reached limit, see [Rate Limiting](http://developers.facebook.com/docs/marketing-apis/rate-limiting).

[](http://developers.facebook.com/docs/marketing-api/reference/ad-campaign/copies/#)

## Reading

Endpoint to read the copies of an Ad Set.

### Example

HTTP PHP SDK JavaScript SDK Android SDK iOS SDK[Graph API Explorer](http://developers.facebook.com/tools/explorer/?method=GET&path=%7Bad-set-id%7D%2Fcopies&version=v26.0)

```
GET /v26.0/{ad-set-id}/copies HTTP/1.1
Host: graph.facebook.com
```

```
/* PHP SDK v5.0.0 */
/* make the API call */
try {
  // Returns a `Facebook\FacebookResponse` object
  $response = $fb->get(
    '/{ad-set-id}/copies',
    '{access-token}'
  );
} catch(Facebook\Exceptions\FacebookResponseException $e) {
  echo 'Graph returned an error: ' . $e->getMessage();
  exit;
} catch(Facebook\Exceptions\FacebookSDKException $e) {
  echo 'Facebook SDK returned an error: ' . $e->getMessage();
  exit;
}
$graphNode = $response->getGraphNode();
/* handle the result */
```

```
/* make the API call */
FB.api(
    "/{ad-set-id}/copies",
    function (response) {
      if (response && !response.error) {
        /* handle the result */
      }
    }
);
```

```
/* make the API call */
new GraphRequest(
    AccessToken.getCurrentAccessToken(),
    "/{ad-set-id}/copies",
    null,
    HttpMethod.GET,
    new GraphRequest.Callback() {
        public void onCompleted(GraphResponse response) {
            /* handle the result */
        }
    }
).executeAsync();
```

```
/* make the API call */
FBSDKGraphRequest *request = [[FBSDKGraphRequest alloc]
                               initWithGraphPath:@"/{ad-set-id}/copies"
                                      parameters:params
                                      HTTPMethod:@"GET"];
[request startWithCompletionHandler:^(FBSDKGraphRequestConnection *connection,
                                      id result,
                                      NSError *error) {
    // Handle the result
}];
```

If you want to learn how to use the Graph API, read our [Using Graph API guide](http://developers.facebook.com/docs/graph-api/using-graph-api/).

### Parameters

| Parameter | Description |
| --- | --- |
| `date_preset` enum{today, yesterday, this_month, last_month, this_quarter, maximum, data_maximum, last_3d, last_7d, last_14d, last_28d, last_30d, last_90d, last_week_mon_sun, last_week_sun_sat, last_quarter, last_year, this_week_mon_today, this_week_sun_today, this_year} | Preset date range used to aggregate insights metrics |
| `effective_status` list<enum{ACTIVE, PAUSED, DELETED, PENDING_REVIEW, DISAPPROVED, PREAPPROVED, PENDING_BILLING_INFO, CAMPAIGN_PAUSED, ARCHIVED, ADSET_PAUSED, IN_PROCESS, WITH_ISSUES}> | Filter adsets by effective status |
| `is_completed` boolean | Filter adsets by completed status |
| `time_range` {'since':YYYY-MM-DD,'until':YYYY-MM-DD} | Time range used to aggregate insights metrics |
| `since` datetime | A date in the format of "YYYY-MM-DD", which means from the beginning midnight of that day. |
| `until` datetime | A date in the format of "YYYY-MM-DD", which means to the beginning midnight of the following day. |

### Fields

Reading from this edge will return a JSON formatted result:

{ "`data`": [], "`paging`": {}, "`summary`": {} }

#### `data`

A list of [AdSet](http://developers.facebook.com/docs/graph-api/reference/ad-campaign/) nodes.

#### `paging`

For more details about pagination, see the [Graph API guide](http://developers.facebook.com/docs/graph-api/using-graph-api/#paging).

#### `summary`

Aggregated information about the edge, such as counts. Specify the fields to fetch in the summary param (like `summary=insights`).

| Field | Description |
| --- | --- |
| `insights` Edge<AdsInsights> | Analytics summary for all objects |
| `total_count` unsigned int32 | Total number of objects [Default](https://developers.facebook.com/docs/graph-api/using-graph-api/#fields) |

### Error Codes

| Error | Description |
| --- | --- |
| 100 | Invalid parameter |

[](http://developers.facebook.com/docs/marketing-api/reference/ad-campaign/copies/#)

## Creating

If you are copying an adset that already finished, the copy will be scheduled to start at the creation's time with the same duration of the original adset.

### Asynchronous

This endpoint supports [asynchronous batch requests](http://developers.facebook.com/docs/graph-api/asynchronous-batch-requests), which enables you to send up to 50 requests in a single HTTP request. If you want to copy large amount of objects, you should use asynchronous batch request. To do so, set `deep_copy` to `true`, and you can copy the adset and all of its ads in one sub-request. For example if you have two adsets and each of them has 50 ads, you can copy 2 adsets and all their ads:

curl -F 'access_token=...'\ -F 'asyncbatch=[{ "method":"POST", "relative_url":"<ad-set-id>/copies","name":"async_copy1", body":"name=copy_adset_1&deep_copy=true" },{ "method":"POST", "relative_url":"<ad-set-id>/copies","name":"async_copy2", body": "name=copy_adset_2&deep_copy=true"}]' \ https://graph.facebook.com/<VERSION>
### Targeting DSA Regulated Locations (European Union)

To copy an ad set targeted in the European Union's Digital Services Act (DSA) regulated locations, please set the payor/beneficiary information first. Otherwise the copying request may respond with one of the following errors: 

**Payor missing error**

{ "error": { "message": "Invalid parameter", "type": "FacebookApiException", "code": 100, "error_data": "{\"blame_field_specs\":[[\"dsa_payor\"]]}", "error_subcode": 3858079, "is_transient": false, "error_user_title": "No payor provided in DSA regulated region", "error_user_msg": "The DSA requires ads to provide payor information in regulated regions. Updating/creating ad needs to provide payor of the ad.", "fbtrace_id": "fbtrace_id" }, "__fb_trace_id__": "fbtrace_id", "__www_request_id__": "request_id"}**Beneficiary missing error**{ "error": { "message": "Invalid parameter", "type": "FacebookApiException", "code": 100, "error_data": "{\"blame_field_specs\":[[\"dsa_beneficiary\"]]}", "error_subcode": 3858081, "is_transient": false, "error_user_title": "No payor/beneficiary provided in DSA regulated location", "error_user_msg": "The DSA requires ads to provide beneficiary information in regulated regions. Updating/creating ad needs to provide beneficiary of the ad.", "fbtrace_id": "fbtrace_id" }, "__fb_trace_id__": "fbtrace_id", "__www_request_id__": "request_id"}

You can make a POST request to `copies` edge from the following paths: 
*   [`/{ad_set_id}/copies`](http://developers.facebook.com/docs/graph-api/reference/ad-campaign/copies/)

When posting to this edge, an[AdSet](http://developers.facebook.com/docs/graph-api/reference/ad-campaign/) will be created.

### Parameters

| Parameter | Description |
| --- | --- |
| `campaign_id` numeric string or integer | Single ID of a campaign to make parent of the copy. The copy inherits all campaign settings, such as budget from the parent.Ignore if you want to keep the copy under the original campaign parent. |
| `deep_copy` boolean | Default value: `false` Whether to copy all the child ads. Limits: the total number of children ads to copy should not exceed 3 for a synchronous call and 51 for an asynchronous call. |
| `end_time` datetime | The end time of the set, e.g. `2015-03-12 23:59:59-07:00` or `2015-03-12 23:59:59 PDT`. UTC UNIX timestamp. When creating a set with a daily budget, specify `end_time=0` to set the set to be ongoing without end date. If not set, the copied adset will inherit the end time from the original set |
| `rename_options` JSON or object-like arrays | Rename options |
| `rename_strategy` enum {DEEP_RENAME, ONLY_TOP_LEVEL_RENAME, NO_RENAME} | Default value: `ONLY_TOP_LEVEL_RENAME` `DEEP_RENAME`: will change this object's name and children's names in the copied object. `ONLY_TOP_LEVEL_RENAME`: will change the this object's name but won't change the children's name in the copied object. `NO_RENAME`: will change no name in the copied object |
| `rename_prefix` string | A prefix to copy names. Defaults to null if not provided. |
| `rename_suffix` string | A suffix to copy names. Defaults to null if not provided and appends a localized string of `- Copy` based on the ad account locale. |
| `start_time` datetime | The start time of the set, e.g. `2015-03-12 23:59:59-07:00` or `2015-03-12 23:59:59 PDT`. UTC UNIX timestamp. If not set, the copied adset will inherit the start time from the original set |
| `status_option` enum {ACTIVE, PAUSED, INHERITED_FROM_SOURCE} | Default value: `PAUSED` `ACTIVE`: the copied adset will have active status. `PAUSED`: the copied adset will have paused status. `INHERITED_FROM_SOURCE`: the copied adset will have the status from the original set. |

### Return Type

This endpoint supports [read-after-write](http://developers.facebook.com/docs/graph-api/overview/#read-after-write) and will read the node represented by `copied_adset_id` in the return type.

 Struct {

`copied_adset_id`: numeric string, 

`ad_object_ids`: List [

 Struct {

`ad_object_type`: enum {unique_adcreative, ad, ad_set, campaign, opportunities, privacy_info_center, topline, ad_account, product}, 

`source_id`: numeric string, 

`copied_id`: numeric string, 

}

], 

}

### Error Codes

| Error | Description |
| --- | --- |
| 100 | Invalid parameter |
| 200 | Permissions error |
| 190 | Invalid OAuth 2.0 Access Token |
| 2695 | The ad set creation reached its campaign group(ios14) limit. |
| 2635 | You are calling a deprecated version of the Ads API. Please update to the latest version. |

[](http://developers.facebook.com/docs/marketing-api/reference/ad-campaign/copies/#)

## Updating

You can't perform this operation on this endpoint.

[](http://developers.facebook.com/docs/marketing-api/reference/ad-campaign/copies/#)

## Deleting

You can't perform this operation on this endpoint.

[](http://developers.facebook.com/docs/marketing-api/reference/ad-campaign/copies/#)

On This Page

[Ad Set Copies](http://developers.facebook.com/docs/marketing-api/reference/ad-campaign/copies/#overview)

[Reading](http://developers.facebook.com/docs/marketing-api/reference/ad-campaign/copies/#Reading)

[Example](http://developers.facebook.com/docs/marketing-api/reference/ad-campaign/copies/#example)

[Parameters](http://developers.facebook.com/docs/marketing-api/reference/ad-campaign/copies/#parameters)

[Fields](http://developers.facebook.com/docs/marketing-api/reference/ad-campaign/copies/#fields)

[Error Codes](http://developers.facebook.com/docs/marketing-api/reference/ad-campaign/copies/#error-codes)

[Creating](http://developers.facebook.com/docs/marketing-api/reference/ad-campaign/copies/#Creating)

[Asynchronous](http://developers.facebook.com/docs/marketing-api/reference/ad-campaign/copies/#async)

[Targeting DSA Regulated Locations (European Union)](http://developers.facebook.com/docs/marketing-api/reference/ad-campaign/copies/#targeting-dsa-regulated-locations--european-union-)

[Parameters](http://developers.facebook.com/docs/marketing-api/reference/ad-campaign/copies/#parameters-2)

[Return Type](http://developers.facebook.com/docs/marketing-api/reference/ad-campaign/copies/#return-type)

[Error Codes](http://developers.facebook.com/docs/marketing-api/reference/ad-campaign/copies/#error-codes-2)

[Updating](http://developers.facebook.com/docs/marketing-api/reference/ad-campaign/copies/#Updating)

[Deleting](http://developers.facebook.com/docs/marketing-api/reference/ad-campaign/copies/#Deleting)

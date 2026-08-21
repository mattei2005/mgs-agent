Title: Facebook Login for Business

URL Source: http://developers.facebook.com/docs/facebook-login/facebook-login-for-business/

Markdown Content:
Updated:Jun 30, 2026

Copy for LLM

Facebook Login for Business is the preferred authentication and authorization solution for tech providers building integrations with Meta’s business tools to create marketing, messaging, and selling solutions.

Facebook Login for Business allows you to create a login experience in the Meta App Dashboard based on the needs of your app. You can specify the access token type, assets, and permissions your app needs, and save it as a **configuration**. During login your app users are presented with this configuration that allows them to grant your app access to their business assets.

*   All permissions that your app asks for during login must be granted by your app user or your app won’t be granted any permissions.

*   The `email` and `public_profile` permissions are automatically granted to all apps but at least one other supported permission must be included for each app installation.

*   To serve businesses that you do not own or manage, your app must be approved for **Advanced Access** via [**Meta’s App Review**](http://developers.facebook.com/docs/app-review)

*   Apps with Advanced Access are required to undergo [Ongoing Review](http://developers.facebook.com/documentation/resp-plat-initiatives/individual-processes/ongoing-reviews) to retain access. However, apps using Facebook Login for Business have reduced requirements for certain ongoing compliance reviews because they are limited to accessing business permissions and features.

The following table shows the available permissions for Facebook Login for Business.

| Available Permissions | User access tokens | Business Integration System User access tokens |
| --- | --- | --- |
| [`ads_management`](http://developers.facebook.com/docs/permissions#ads_management) | ✓ | ✓ |
| [`ads_read`](http://developers.facebook.com/docs/permissions#ads_read) | ✓ | ✓ |
| [`business_management`](http://developers.facebook.com/docs/permissions#business_management) | ✓ | ✓ |
| [`catalog_management`](http://developers.facebook.com/docs/permissions#catalog_management) | ✓ | ✓ |
| `commerce_account_manage_orders` | ✓ | ✓ |
| `commerce_account_read_orders` | ✓ | ✓ |
| `commerce_account_read_reports` | ✓ | ✓ |
| `commerce_account_read_settings` | ✓ | ✓ |
| `commerce_manage_accounts` | ✓ | ✓ |
| [`email`](http://developers.facebook.com/docs/permissions#email) | ✓ | N/A |
| [`instagram_basic`](http://developers.facebook.com/docs/permissions#instagram_basic) | ✓ | ✓ |
| [`instagram_content_publish`](http://developers.facebook.com/docs/permissions#instagram_content_publish) | ✓ | ✓ |
| [`instagram_manage_comments`](http://developers.facebook.com/docs/permissions#instagram_manage_comments) | ✓ | ✓ |
| [`instagram_manage_insights`](http://developers.facebook.com/docs/permissions#instagram_manage_insights) | ✓ | ✓ |
| [`instagram_manage_messages`](http://developers.facebook.com/docs/permissions#instagram_manage_messages) | ✓ | ✓ |
| [`instagram_shopping_tag_products`](http://developers.facebook.com/docs/permissions#instagram_shopping_tag_products) | ✓ | ✓ |
| [`leads_retrieval`](http://developers.facebook.com/docs/permissions#leads_retrieval) | ✓ | ✓ |
| [`manage_app_solutions`](http://developers.facebook.com/docs/permissions#manage_app_solution) | ✓ | ✓ |
| [`manage_fundraisers`](http://developers.facebook.com/docs/permissions#manage_fundraisers) | ✓ | ✓ |
| [`pages_manage_cta`](http://developers.facebook.com/docs/permissions#pages_manage_cta) | ✓ | ✓ |
| [`page_events`](http://developers.facebook.com/docs/permissions#page_events) | ✓ | ✓ |
| [`pages_manage_ads`](http://developers.facebook.com/docs/permissions#pages_manage_ads) | ✓ | ✓ |
| [`pages_manage_engagement`](http://developers.facebook.com/docs/permissions#pages_manage_engagement) | ✓ | ✓ |
| [`pages_manage_instant_articles`](http://developers.facebook.com/docs/permissions#pages_manage_instant_articles) | ✓ | ✓ |
| [`pages_manage_metadata`](http://developers.facebook.com/docs/permissions#pages_manage_metadata) | ✓ | ✓ |
| [`pages_manage_posts`](http://developers.facebook.com/docs/permissions#pages_manage_posts) | ✓ | ✓ |
| [`pages_messaging`](http://developers.facebook.com/docs/permissions#pages_messaging) | ✓ | ✓ |
| [`pages_read_engagement`](http://developers.facebook.com/docs/permissions#pages_read_engagement) | ✓ | ✓ |
| [`pages_read_user_content`](http://developers.facebook.com/docs/permissions#pages_read_user_content) | ✓ | ✓ |
| [`pages_show_list`](http://developers.facebook.com/docs/permissions#pages_show_list) | ✓ | ✓ |
| [`private_computation_access`](http://developers.facebook.com/docs/permissions#private_computation_access) | ✓ | ✓ |
| [`public_profile`](http://developers.facebook.com/docs/permissions#public_profile) | ✓ | N/A |
| [`publish_video`](http://developers.facebook.com/docs/permissions#publish_video) | ✓ | ✓ |
| [`read_insights`](http://developers.facebook.com/docs/permissions#read_insights) | ✓ | ✓ |
| [`read_audience_network_insights`](http://developers.facebook.com/docs/permissions#read_audience_network_insights) | ✓ | ✓ |
| [`whatsapp_business_management`](http://developers.facebook.com/docs/permissions#whatsapp_business_management) | ✓ | ✓ |
| [`whatsapp_business_messaging`](http://developers.facebook.com/docs/permissions#whatsapp_business_messaging) | ✓ | ✓ |

*   Marketing API Access Tier
*   Business Asset User Profile Access
*   Human Agent
*   Instagram Public Content Access

*   Live Video API
*   Page Mentions
*   Page Public Content Access
*   Page Public Metadata Access

You can use Facebook Login for Business to get either Business Integration System User access tokens or User access tokens.

User access tokens should be used if your app takes actions in real time, based on input from the user. For example, use a user access token if your app requires a user to input text and click a button in order to post content to their Page. User access tokens should also be used if you require an API that requires admin permissions on a business portfolio.

Business integration system user access tokens should be used if your app performs programmatic, automated actions on your business clients’ assets without having to rely on input from an app user, or require re-authentication at a future date. For example:

*   Hourly, automated server-to-server conversion API calls
*   Sending automated responses as a Facebook Page or WhatsApp business portfolio
*   Continuous, automated updates to product catalog inventories
*   Automated retrieval of ads insights

To get business integration system user access tokens from your business clients:

*   Your app can only request logins from web surfaces

*   Businesses onboarding to your app must have, or be willing to create, a [business portfolio⁠](https://www.facebook.com/business/help/2199735813629697)

*   Your app must be associated with a [business portfolio,⁠](https://www.facebook.com/business/help/2199735813629697) which you have full control. This needs to be separate from the business portfolio owned by your business client.

To test the business integration system user access token flow, the tester must have a role on the app and full control of the client business.

If you need different access setups for different purposes or departments, you can use multiple granular business integration system user access tokens per client business to improve the scalability and security of your integrations.

Granular access tokens are still specific to a client business portfolio. They are not shareable and accessible across different client businesses. Their scope and asset list are a subset of the original business integration system user access token.

To isolate potential security incidents in the event of a compromised token, only that specific client business will be impacted, instead of impacting all business portfolios across all client businesses.

![Image 1: Diagram of a tech provider app linked to two client businesses, each deriving three granular tokens from its business integration system user access token](https://scontent-atl3-3.xx.fbcdn.net/v/t39.2365-6/653700966_1459945775864072_8056443032003340873_n.png?_nc_cat=110&ccb=1-7&_nc_sid=e280be&_nc_ohc=jJaC_6IT1u8Q7kNvwEkRr86&_nc_oc=AdpIP6rdsfXj_338GsXo7pxgO2k1SgWj9UcsyTd9A7PuXETzJSmWsECQ5iworW-0svo&_nc_zt=14&_nc_ht=scontent-atl3-3.xx&_nc_gid=o8bpnuAUxAtFyXRv8paHhQ&_nc_ss=7b289&oh=00_AQFjnmLf3xGy7jGRRaihAkZXTNycorrDxUHnq_3Jbf8phw&oe=6AA2031E)

|  | Business Integration System User access tokens | User access tokens |
| --- | --- | --- |
| Access Designations | Access is **explicitly delegated** at the time of authorization. Your app can only access the assets that were designated by your business client when they completed the Facebook Login for Business flow. Tech Providers only. | Access is **inherited** from your app user’s current account access; your app can access the same business assets that the app user currently has access to. |
| Account association | Associated with your business client’s business portfolio rather than a specific user. Any admin in your business client’s admin group can grant your app a system user access token. | Associated with your app user’s personal Facebook account. |
| Expiration and refresh | Defaults to **never expire** for the common offline server-to-server communication. | A **short-lived** token for online activities such as web browsers. |
| OAuth grant type | **Authorization Code** grant only. | **Implicit** grant by default, and can support authorization code grant for improved security. Mainly used for user-agent based clients such as web browsers and mobile apps. |
| Representation | Part of the Tech Provider integration’s infrastructure, initialized by a client business through Tech Provider’s app installation. | Represents servers or software making API calls to assets owned or managed by a [Business Manager.](http://developers.facebook.com/docs/business-manager-api) |
| Token Invalidation | Your business clients can invalidate business integration system User access tokens by going to **[Business Manager⁠](https://business.facebook.com/)> Settings > Business Settings > Integrations > Connected apps** and removing your app. | Your business clients can invalidate User access tokens by going to Facebook and navigating to **Settings & privacy**>**Settings**>**Security and login**>**Business Integrations** and removing your app. |

When a client business installs an app through Facebook Login for Business and generates a business integration system user access token, the token includes a client business ID. This ID represents the client business and is used by your app to make API calls.

To get a client business ID from the business integration system user access token, send a `GET` request to the `/me` endpoint with the `fields` parameter set to `client_business_id` and the `access_token` parameter to your app user’s business integration system user access token.

curl -i -X GET \
"https://graph.facebook.com/<API_VERSION>/me \
  ?fields=client_business_id
  &access_token=<BUSINESS_INTEGRATION_SYSTEM_USER_ACCESS_TOKEN>"

On success your app receives a JSON response with your app user’s client business ID.

{
  "client_business_id": "<CLIENT_BUSINESS_ID>",
  "id": "<APP_SCOPED_ID>"
}

The `/<CLIENT_BUSINESS_ID>/system_user_access_tokens` endpoint allows you to manage your existing business integration system user access tokens. Actions include:

*   Generate granular business integration system user access tokens from the existing business integration system user access tokens
*   Fetch any existing business integration system user access tokens

##### Parameters

| Object | Description |
| --- | --- |
| `access_token`_string_ | **Required.** This access token requires the `business_management` permission |
| `appsecret_proof`_string_ | **Required.** The [`appsecret_proof`](http://developers.facebook.com/docs/graph-api/guides/secure-requests#generate-the-proof) is a `sha256` hash of your access token ensuring API calls are from a server are more secure. |
| `asset`_int_ | Optional. When you want to generate a more granular token, you can set a list of `asset` IDs, separated by commas. The list of assets will have to be a subset of assets from the original access token. |
| `fetch_only`_bool_ | Optional. The flag you want to use to fetch the existing token and indicate this operation is read only |
| `scope`_bool_ | Optional. When you want to generate a more granular token, you can set a list of `scope` ids, separated by a comma. The list of assets will have to be a subset of scopes from the original access token. |
| `set_token_expires_in_60_days`_bool_ | Optional. When you generate a new token, set to `true` so that the token expires in 60 days. |
| `system_user_id`_int_ | Optional. The ID for the system user included in the access token. |

##### Sample request

_Formatted for readability._

```
curl -i -X POST "https://graph.facebook.com/v26.0/<CLIENT_BUSINESS_ID>/system_user_access_tokens
    ?appsecret_proof=<APPSECRET_PROOF_HASH>
    &access_token=<ACCESS_TOKEN>
    &system_user_id=<SYSTEM_USER_ID>
    &fetch_only=true"
```

On success your app receives a JSON response with a new access token to be used in subsequent API calls.

```
{
  "access_token": "<NEW_ACCESS_TOKEN>"
}
```

| User access token login flow | Business integration system user access token login flow |
| --- | --- |
| ![Image 2](https://scontent-atl3-3.xx.fbcdn.net/v/t15.5256-10/628518251_1224238395873366_961930347200670210_n.jpg?_nc_cat=109&ccb=1-7&_nc_sid=b07905&_nc_ohc=HcDBgRDVXvMQ7kNvwGz8Pvi&_nc_oc=AdqiTzRjdubdbg_jB0J195_lV90bXSjgo1L8T3oM5w6pmmLNHsPxoC0hSNkCv_RgRn8&_nc_zt=23&_nc_ht=scontent-atl3-3.xx&_nc_gid=o8bpnuAUxAtFyXRv8paHhQ&_nc_ss=7b289&oh=00_AQE-2fbnO1CKKrXywiZh_ye5zPzoF8alkxVFbXWaoKRBqw&oe=6A8D9556) | ![Image 3](https://scontent-atl3-2.xx.fbcdn.net/v/t15.5256-10/344303707_1061948651445158_8496308741180122348_n.jpg?_nc_cat=105&ccb=1-7&_nc_sid=861778&_nc_ohc=YS5sT4Y_09MQ7kNvwEkrgA5&_nc_oc=AdrdDbnE2dHth1GwzuA95fZhryK5ni_1YyiZtZ5IcAVy4-dQGcUuhbb_dVYJP-nrfTc&_nc_zt=23&_nc_ht=scontent-atl3-2.xx&_nc_gid=o8bpnuAUxAtFyXRv8paHhQ&_nc_ss=7b289&oh=00_AQG9C0s0atvlRZnnx8c82UjCzOx2sZEcARTY6-ip-5rRgg&oe=6A8D7E92) |

The following are the steps required to set up Facebook Login for Business if you don’t already have an app.

2.   Add the **Facebook Login for Business** product.

3.   In the left side menu select **Configurations**.

4.   You can either **+ Create configuration** to create a configuration or **Create from template** to select one of Meta’s preset configurations.

You can create multiple configurations and present them to different sets of users.

5.   Name your configuration

6.   Choose the type of access token you want to request from your business clients, a User access token or System-user access token and token expiration.

If you select User access token then your app users will log in using their personal Facebook account. If you select System-user access token your app users will be required to log in using a business portfolio. This is only required if this configuration needs continuous access to business assets, such as Facebook Pages, ad accounts or Instagram accounts.

7.   Select all the assets your app needs access to.

8.   Select the permissions your app needs and click **Create**.

You will receive a **Configuration ID** that you will use in your code to invoke the login dialog.

Invoke a login dialog using one of our SDKs (recommended) or manually build your login flow.

You can use any of our SDKs to invoke the login dialog by replacing the list of scopes (permissions) your app needs with your configuration ID and the access token’s required OAuth grant type.

If you are unfamiliar with our SDKs, we recommend that you first install the JavaScript SDK and get it working with the consumer Facebook Login product before proceeding, as the following examples reference the SDK.

##### Business integration system user access token configurations

Here’s an example of the JavaScript SDK’s `FB.login()` method modified to use a configuration for a System User access token. Note that `config_id` has replaced `scope` (which should not be used), the `response_type` has been set to `code`, since SUAT’s require the authorization code grant type, and `override_default_response_type` must be set to `true`. When true, any response types passed in the `response_type` will take precedence over the default types.

```
FB.login(
  function(response) [
    console.log(response);
  ],
  [
    config_id: '<CONFIG_ID>',
    response_type: 'code',
    override_default_response_type: true
  ]
);
```

When the user completes the login dialog flow we will redirect the user to your redirect URL and include a code. You must then exchange this code for an access token by performing a server-to-server call to our servers.

```
GET https://graph.facebook.com/v26.0/oauth/access_token?
  client_id=<APP_ID>
  &client_secret=<APP_SECRET>
  &code=<CODE>
```

##### User access token configurations

Here’s an example of the JavaScript SDK’s `FB.login()` method modified to use a configuration for a User access token. Note that `config_id` has replaced `scope` (although `scope` can still be included, we recommend that you do not use it).

```
FB.login(
  function(response) {
    console.log(response);
  },
  {
    config_id: '<CONFIG_ID>' // configuration ID goes here
  }
);
```

Here’s an example of the JavaScript SDK’s **login** button modified to use a User access token configuration:

<fb:login-button config_id="<CONFIG_ID>" onlogin="checkLoginState();">
</fb:login-button>

```
config_id=<CONFIG_ID>
```

It is recommended you conduct [testing](http://developers.facebook.com/documentation/facebook-login/facebook-login-for-business#getting-started) and learn about potentially encountered problems[](http://developers.facebook.com/documentation/facebook-login/facebook-login-for-business#troubleshooting) before switching to Facebook Login for Business.

If your app is eligible to switch to Facebook Login for Business, you should be able to see an opt in banner by the following steps:

1.   Select your app in the App Dashboard

2.   Go to or add the Facebook Login product

3.   Click either **Settings** or **Quickstart** in the left side menu

4.   Click the “Get started with Facebook Login for Business” button at the top of the page.

Note that your current access tokens will not be impacted upon switching to Facebook Login for Business. Additionally, any test app(s) associated with this app will also switch to Facebook Login for Business.

After switching, your app type will be under **Business type**. If your app is not functioning as intended, each app is allowed to roll back to Facebook Login within **30 days** after the switch.

Business clients might encounter error messages for the following reasons:

*   Config ID is invalid
*   Business System User Access Token is not currently supported on Mobile devices
*   Business System User Access Token is set up with incorrect response_type

Potential breaking changes:

*   If your app type is currently **None**, switching to Facebook Login for Business will change your app’s type to **Business** and will only retain access to the [permissions](http://developers.facebook.com/docs/facebook-login/facebook-login-for-business/#supported-permissions), [features](http://developers.facebook.com/docs/facebook-login/facebook-login-for-business/#supported-features) and [products](http://developers.facebook.com/docs/facebook-login/facebook-login-for-business/#supported-products) listed above.
*   If you request permissions or features from business clients that Facebook Login for Business doesn’t support, those permissions and features will be **revoked immediately** once you switch your app to Facebook Login for Business.
*   If you only request `email` and/or `public_profile` from your business clients, switching the app to Facebook Login for Business will lead to the invalidation of all previously installed tokens for these clients.
*   If your app has both Facebook Login for Business and Meta Business Extension, the Meta Business Extension experience will be limited to permissions supported by Facebook Login for Business.
*   Business Asset User Profile Access may affect how user profile data is accessed and managed through our APIs.
*   Note that if the login dialog for Facebook Login for Business is invoked via configuration id, and if you decide to rollback to Facebook Login, the login dialog might fail to load as Facebook Login does not support the `config_id` parameter and you need to replace the `config_id` parameter with the `scope` parameter instead.

Only available when an existing app has switched to Facebook Login for Business; Newly created Business Type apps cannot switch back to Facebook Login.

After switching to Facebook Login for Business, if your app is not functioning as intended after switching to Facebook Login for Business, you can roll back to Facebook Login by going to the **App Dashboard**>**Facebook Login for Business**>**Settings** and clicking the **Switch to Facebook Login** link. You will be presented with a survey which helps us improve the Facebook Login for Business configuration experience. Each app is allowed to roll back to Facebook Login within **30 days** after the switch.

**Facebook Login for Business isn’t available for my app - what should I do?**

The easiest way to add Facebook Login for Business is to create a new Business Type app, where Facebook Login for Business is automatically available, and request supported business permissions through Meta App Review. If you want to use it for an existing None type app, your app must have advanced access to at least one supported business permission.

**What should I use for authentication if my app is not intended for businesses or if I am not a Tech Provider building an app for other businesses to use?**

If you are not a Tech Provider building solutions using Meta’s business APIs, Facebook Login is recommended for consumer authentication.

**What permissions do I need to request when implementing Facebook Login for Business?**

Only request the minimum permissions necessary for your app’s functionality. Be transparent with users about why you need each permissions and features. Note that the `email` and `public_profile` permissions must be requested with at least one other supported [business permission](http://developers.facebook.com/docs/facebook-login/facebook-login-for-business/#supported-permissions).

**Is advanced access to the public_profile permission required before a Facebook Login for Business app goes live?**

Yes, advanced access to the `public_profile` permission is required for Facebook Login for Business apps before they go live. This requirement is crucial to ensure that the app can support authorization from users who do not have an app role, commonly referred to as external users.

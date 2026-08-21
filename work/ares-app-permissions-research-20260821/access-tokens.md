Title: Access Tokens for Meta Technologies

URL Source: http://developers.facebook.com/docs/facebook-login/guides/access-tokens/

Markdown Content:
Updated:Nov 25, 2025

Copy for LLM

An access token is an opaque string that identifies a user, app, or Facebook Page and can be used by the app to make Graph API calls. The token includes information about when it expires and which app generated it. Most API calls on Meta apps require an access token for privacy checks. Different types of access tokens support different use cases.

![Image 1: Diagram showing the access token generation flow between your app, Meta, and the user](https://scontent-atl3-1.xx.fbcdn.net/v/t39.2365-6/615891931_1414612790397371_1506827232831674175_n.png?_nc_cat=100&ccb=1-7&_nc_sid=e280be&_nc_ohc=fnpkYhxrv4cQ7kNvwF0qlZf&_nc_oc=AdrsnBxa3Ti_EeE2DBexptJtma5e7S_JXjyRV0IgW7Hdi5alB6lTYpfZzAjZbNdxoco&_nc_zt=14&_nc_ht=scontent-atl3-1.xx&_nc_gid=S7Vt5H1lPOb522YABiJazg&_nc_ss=7b289&oh=00_AQFNpql1zRsdOHhDG-5k9go5FZBSksDJWzZ61qrxP3uGdQ&oe=6AA2194C)

| Access Token Type | Description |
| --- | --- |
| App Access Token | App access tokens let you read and modify app settings. Generate one using your Meta app secret via a server-to-server call. |
| Client Token | Client tokens identify your app when calling app-level APIs from native or desktop apps. Because client tokens are embedded in apps, they are not secret. Find your client token in the Meta App Dashboard. |
| Page Access Token | Page access tokens let you read, write, and modify data belonging to a Facebook Page. To obtain one, first get a user access token, then exchange it for a Page access token via the Graph API. |
| System User Access Token | System User access tokens let your app perform programmatic, automated actions on Ad objects or Pages without requiring input from an app user or re-authentication. |
| User Access Token | User access tokens let your app take actions in real time based on input from the user. You need a User access token any time your app reads, modifies, or writes a person’s Facebook data on their behalf. Obtain one via a login dialog that requires the person to grant your app permission. |

User access tokens let your app take actions in real time based on input from the user. You need a User access token any time your app reads, modifies, or writes a person’s Facebook data on their behalf. Obtain one via a login dialog that requires the person to grant your app permission.

Different platforms have different methods to kick off this process and include functionality to manage access tokens on behalf of the developer and the person granting permissions:

```
@Override
public void onCreate(Bundle savedInstanceState) {
    super.onCreate(savedInstanceState);
    accessToken = AccessToken.getCurrentAccessToken();
}
```

```
- (void)viewDidLoad
{
  [super viewDidLoad];
  NSString *accessToken = [FBSDKAccessToken currentAccessToken];
}
```

The [Facebook SDK for Javascript](http://developers.facebook.com/docs/javascript) obtains and persists user access tokens automatically in browser cookies. You can retrieve the user access token by making a call to [`FB.getAuthResponse`](http://developers.facebook.com/docs/reference/javascript/FB.getAuthResponse) which will include an `accessToken` property within the response.

```
FB.getLoginStatus(function(response) {
  if (response.status === 'connected') {
    var accessToken = response.authResponse.accessToken;
  }
} );
```

App access tokens let you read and modify app settings. Generate one using your Meta app secret via a server-to-server call.

App access tokens don’t expose all user data that a user access token would. To read user data in your app, use a user access token instead.

App access tokens are insecure if your app is set to `Native/Desktop` in the Advanced settings of your [App Dashboard](http://developers.facebook.com/apps). Native or desktop apps typically embed the app secret in the code, making the generated app access token insecure.

To generate an app access token, you need:

*   Your [App ID](http://developers.facebook.com/docs/apps#app-id)
*   Your [App Secret](http://developers.facebook.com/documentation/facebook-login/security#appsecret)

curl -X GET "https://graph.facebook.com/oauth/access_token
  ?client_id={your-app-id}
  &client_secret={your-app-secret}
  &grant_type=client_credentials"

This call returns an app access token that you can use in place of a user access token for API calls. Never hard-code app access tokens into client-side code or app binaries — doing so exposes your app secret and gives anyone who loads your webpage or decompiles your app full access to modify it. Only use app access tokens in server-to-server calls.

**Important**: This request uses your app secret, so it must only be made using server-side code. Never share your app secret with anyone.

There is another method to make calls to the Graph API that doesn’t require using a generated app access token. You can just pass your app ID and app secret as the `access_token` parameter when you make a call:

curl -i -X GET "https://graph.facebook.com/{api-endpoint}&access_token={your-app_id}|{your-app_secret}"

The choice to use a generated access token or this method depends on where you hide your app secret.

Page access tokens let you read, write, and modify data belonging to a Facebook Page. To obtain one, first get a user access token, then exchange it for a Page access token via the Graph API.

```
curl -i -X GET "https://graph.facebook.com/{your-user-id}/accounts?access_token={user-access-token}"
```

This returns a list of Pages you have a role on, including the Page category, your permissions on each Page, and the Page access token.

```
{
  "data": [
    {
      "access_token": "EAACEdE...",
      "category": "Brand",
      "category_list": [
        {
          "id": "1605186416478696",
          "name": "Brand"
        }
      ],
      "name": "Ash Cat Page",
      "id": "1353269864728879",
      "tasks": [
        "ANALYZE",
        "ADVERTISE",
        "MODERATE",
        "CREATE_CONTENT",
        "MANAGE"
      ]
    },
    {
      "access_token": "EAACEdE...",
      "category": "Pet Groomer",
      "category_list": [
        {
          "id": "163003840417682",
          "name": "Pet Groomer"
        },
        {
          "id": "2632",
          "name": "Pet"
        }
      ],
      "name": "Unofficial: Tigger the Cat",
      "id": "1755847768034402",
      "tasks": [
        "ANALYZE",
        "ADVERTISE",
        "MODERATE",
        "CREATE_CONTENT"
      ]
    }
  ]
}
```

With a Page access token, you can make [API calls on behalf of a Page](http://developers.facebook.com/docs/pages), such as posting a status update to a Page or reading Page Insights data.

Page access tokens are unique to each Page, admin, and app combination.

System User access tokens let your app perform programmatic, automated actions on Ad objects or Pages without requiring input from an app user or re-authentication.

System tokens rely on system users. When you use a system token, endpoints check whether the identified user has access to the requested resource. If the user lacks access, the request is rejected.

System users can be admins or employees:

*   **Admin system users** have full access to all assets owned by or shared with your business portfolio by default. Admin system users are useful if your app needs access to all of the business portfolio’s assets, without having to manually grant business asset access to each asset whenever it is created or shared with your business portfolio.
*   **Employee system users** must be granted access to individual assets that are owned by, or shared with, your business portfolio. If your app will only need access to a few assets that you own, an employee system user should be sufficient.

To generate a system token:

1.   Access the [**Business settings**⁠](https://business.facebook.com/settings/) panel and click **System Users**.
2.   Click the **+Add** button. In the **Create system user** window, enter a system user name and assign it an **Admin** or **Employee** role.
3.   Click the system user’s name to display the asset assignment overlay.
4.   Click the **Assign assets** button, select your app, and grant your system user the **Manage app** permission.
5.   Reload the page to confirm your system user has been granted **Full control** of your app.
6.   Click the **Generate token** button. In the window that appears, select your app, choose a token expiration preference, and assign the required permissions for your use case.
7.   Click **Generate token** and copy the token when it appears.

Client tokens identify your app when calling app-level APIs from native or desktop apps. Because client tokens are embedded in apps, they are not secret. Find your client token in the Meta App Dashboard.

Unlike other tokens, client access tokens cannot be used in requests on their own. You must combine them with your App ID by appending the token to the end of the App ID, separated by a pipe symbol (`|`):

`{app-id}|{client-token}`

For example:

`access_token=1234|5678`

To get your app’s client access token:

1.   Sign into your [developer account](http://developers.facebook.com/).
2.   On the [Apps page](http://developers.facebook.com/apps), select an app to open the dashboard for that app.
3.   On the **Dashboard**, navigate to **Settings**>**Advanced**>**Security**>**Client token**.

Access tokens come in two forms: short-lived and long-lived. Short-lived tokens typically last about one to two hours, while long-lived tokens last about 60 days. Do not depend on these lifetimes remaining the same — they may change without warning or expire early. See [handling errors](http://developers.facebook.com/docs/facebook-login/access-tokens/debugging-and-error-handling) for more information.

Access tokens generated via web login are short-lived, but you can [convert them to long-lived tokens](http://developers.facebook.com/documentation/facebook-login/guides/access-tokens/get-long-lived) by making a server-side API call with your app secret.

Mobile apps that use Facebook’s iOS and Android SDKs get long-lived tokens by default.

Apps with [Standard access](http://developers.facebook.com/documentation/ads-commerce/marketing-api/get-started/authorization) to the Marketing API receive long-lived tokens that do not expire based on time, though they are still subject to invalidation for other reasons. This also applies to access tokens for [System Users in Business Manager](http://developers.facebook.com/docs/marketing-api/businessmanager/systemuser).

Most access tokens are portable — you can use them from a mobile client, a web browser, or your server. If you obtain a token on a client, you can send it to your server for server-to-server calls. If you obtain a token via a server call, you can send it to a client for client-side calls. However, Apple does not allow moving tokens to servers.

Always transfer tokens between your client and server securely over HTTPS to protect user accounts. Learn more about [token portability implications](http://developers.facebook.com/documentation/facebook-login/access-tokens/portability).

When testing an API call, you can include the `access_token` parameter set to your access token value. However, when making secure calls from your app, use the access token class provided by the platform SDK instead of passing raw token strings. This ensures tokens are managed securely and refreshed automatically.

The length of access tokens changes over time as Meta updates what they store and how they are encoded. Use a variable-length data type without a specific maximum size to store access tokens.

*   Use the [Access Token Tool](https://developers.facebook.com/tools/accesstoken) to see a list of your access tokens and debugging information for each token in.

Title: Marketing API Access Tier Simplification and Lead Ads Retrieval

URL Source: http://developers.facebook.com/ads/blog/post/v2/2018/07/02/marketing-api-tier-simplification/

Markdown Content:
Today, we are announcing some changes to [Marketing API](https://developers.facebook.com/docs/marketing-api) access structure. We are simplifying the legacy Marketing API access structure that has three access levels into a two-tier structure: **Dev Tier** and **Standard Tier**. This new structure is effective as of **July 2, 2018**. All developers who integrate with Marketing API will need adjust the new structure before **February 1, 2019**.

![Image 1](https://scontent-atl3-1.xx.fbcdn.net/v/t39.2365-6/36586141_816996365160831_70415073989885952_n.png?_nc_cat=106&ccb=1-7&_nc_sid=e280be&_nc_ohc=-Q0_JM83cuIQ7kNvwFbfBoL&_nc_oc=AdpO7589e-NCbobOzAkub22FCIsHZS24E0vwULw5QHsJ0l1GLmHGgBTZB2Zfw50CPrE&_nc_zt=14&_nc_ht=scontent-atl3-1.xx&_nc_gid=N5HNY11BsjQlKU0gc6heRg&_nc_ss=7b289&oh=00_AQFgyMa3TFj3mstZk6NY-5j3hHd32lRJG5P93ZXD9V8Zxg&oe=6AA224AB)

To adjust to the new structure:

*   **Existing Developers on Legacy Development Access** - You do not need to do anything. You will be moved to the new **Dev Tier** automatically and will have access to all APIs for development and test purposes. A comparison of legacy Development Access and **Dev Tier** under the new structure is as follows:

| Description | Legacy Development Access | New Dev Tier |
| --- | --- | --- |
| Rate limits, system user, admin user | No Change | No Change |
| Business Manager API access | No Access | No Access |
| Pages API access | No Access | Access as long as the Pages are owned by you |
| Ad Account Limits | Access up to five ad accounts | No limit as long as the ad accounts are owned by you |
| [App Review](https://developers.facebook.com/docs/apps/review) and [Business Verification](https://developers.facebook.com/docs/apps/review#business-verification) | Not Applicable | Not Applicable |

*   **Existing Developers on Legacy Basic Access, either in legacy live mode or dev mode** - Will be upgraded to the new **Standard Tier**; there will be no changes to your mode. You will get an email and notifications in your [App Dashboard](https://developers.facebook.com/apps/) with instructions to apply for necessary permissions. To operate at scale with the new **Standard Tier**, we recommend that you turn your app to live mode and then submit it for [App Review](https://developers.facebook.com/docs/apps/review) before **February 1, 2019**. As part of your [App Review](https://developers.facebook.com/docs/apps/review) submission and subsequent business verification, you need to apply for these three permissions: **Standard Tier**, [`ads_read`](https://developers.facebook.com/docs/facebook-login/permissions#reference-ads_read), and [`ads_management`](https://developers.facebook.com/docs/facebook-login/permissions#reference-ads_management). Upon approval, you will get an email and an [App Dashboard](https://developers.facebook.com/apps/) notification to remind you to move to Live Mode within _2 weeks_, if you are not already in that mode. If you do not move to Live Mode in time, you will be downgraded to the Dev Tier.

*   **Existing Developers on Legacy Standard Access, either in legacy live mode or dev mode** - Will be temporarily moved to the new **Standard Tier**; there will be no changes to your mode. You will get an email and notifications in your [App Dashboard](https://developers.facebook.com/apps/) with instructions to apply for necessary permissions. In order to operate at scale with the new **Standard Tier**, we recommend that you turn your app to Live Mode and then submit it for [App Review](https://developers.facebook.com/docs/apps/review) before **February 1, 2019**. As part of the [App Review](https://developers.facebook.com/docs/apps/review) submission and subsequent business verification, you need to apply for these three permissions: **Standard Tier**, [`ads_read`](https://developers.facebook.com/docs/facebook-login/permissions#reference-ads_read), and [`ads_management`](https://developers.facebook.com/docs/facebook-login/permissions#reference-ads_management). Upon approval of your permissions, you will get an email and an [App Dashboard](https://developers.facebook.com/apps/) notification to remind you to move to Live Mode within **2 weeks**, if you are not already in that mode. If you do not move to Live Mode in time, you will be downgraded to the Dev Tier.

A comparison of the legacy Standard Access and the new Standard Tier, is as follows:

| Description | Legacy Standard Access | New Standard Tier |
| --- | --- | --- |
| Rate limits, system user, admin user, ad account limit | No Change | No Change |
| [`ads_management`](https://developers.facebook.com/docs/facebook-login/permissions#reference-ads_management) permission | Have access by default | Need to apply when you submit Standard Tier application |
| [`ads_read`](https://developers.facebook.com/docs/facebook-login/permissions#reference-ads_read) permission | Have access by default | Need to apply when you submit Standard Tier application |
| [Business Manager API](https://developers.facebook.com/docs/marketing-api/business-manager-api) | No change, need to apply | No change, need to apply |
| Page creation | Part of Standard Access by default | Need to apply via your Facebook Representative and get added to a whitelist |
| [App Review](https://developers.facebook.com/docs/apps/review) and [Business Verification](https://developers.facebook.com/docs/apps/review#business-verification) | Not Applicable | Required |

## Key Timelines

Developers have from now to February 1, 2019 to submit their apps to [App Review](https://developers.facebook.com/docs/apps/review) and request Marketing API **Standard Tier**, [`ads_read`](https://developers.facebook.com/docs/facebook-login/permissions#reference-ads_read), and [`ads_management`](https://developers.facebook.com/docs/facebook-login/permissions#reference-ads_management) permissions. During this period:

*   Existing apps that have a rejected permission, feature, or business verification, for the first time, will have additional time to resubmit before losing access.

*   Existing apps that have an approved permission and business verification will get the permissions and access that you applied for.

*   
Existing apps that have a pending review of a permission, feature, or business verification:

    *   On legacy Development Access behave as if apps are in the new Dev Tier

    *   On legacy Basic or legacy Standard Access behave as if apps are in the new Standard Tier with [`ads_read`](https://developers.facebook.com/docs/facebook-login/permissions#reference-ads_read) and/or [`ads_management`](https://developers.facebook.com/docs/facebook-login/permissions#reference-ads_management) permission.

### Frequently Asked Questions

**Q: Will the new structure impact third party developers only, or also advertisers?**

The new tier structure applies to all apps which integrate with [Marketing API](https://developers.facebook.com/docs/marketing-apis/). As long as advertisers integrate with [Marketing API](https://developers.facebook.com/docs/marketing-apis/), you will need to adjust to the new structure.

**Q: I'm on the legacy development access level. What do I need to do to move to the new structure?**

You don't need to do anything. We will automatically move you to the new Dev Tier.

**Q: I am on legacy basic access level. What do I need to do to move to the new structure?**

You need to submit your app to [App Review](https://developers.facebook.com/docs/apps/review) before February 1, 2019. During the submission, you need to apply for the new **Standard Tier** and get [`ads_read`](https://developers.facebook.com/docs/facebook-login/permissions#reference-ads_read) and [`ads_management`](https://developers.facebook.com/docs/facebook-login/permissions#reference-ads_management) permissions.

**Q: I am on legacy standard access, live mode. What do I need to do to move to the new structure?**

You need to do the following:

*   We will send notifications through [App Dashboard](https://developers.facebook.com/apps/) and will send an email reminding you to submit your app to [App Review](https://developers.facebook.com/docs/apps/review) before February 1, 2019. 
*   During the [App Review](https://developers.facebook.com/docs/apps/review) submission, you need to apply for the new _Standard Tier_, [`ads_management`](https://developers.facebook.com/docs/facebook-login/permissions#reference-ads_management) and [`ads_read`](https://developers.facebook.com/docs/facebook-login/permissions#reference-ads_read) permissions. 

Once approved, you will be on the new Standard Tier.

**Q: I am on legacy standard access, development mode. What do I need to do to move to the new structure?**

You need to switch to live mode, then apply for the new Standard Tier, [`ads_management`](https://developers.facebook.com/docs/facebook-login/permissions#reference-ads_management) and [`ads_read`](https://developers.facebook.com/docs/facebook-login/permissions#reference-ads_read) permissions, otherwise you will lose access to everything. You need to do the following to move to the new Standard Tier:

*   We will send notifications through [App Dashboard](https://developers.facebook.com/apps/) and email reminding you to submit your app to [App Review](https://developers.facebook.com/docs/apps/review) before February 1, 2019. During the [App Review](https://developers.facebook.com/docs/apps/review) submission, you need to apply for the new Standard Tier, [`ads_management`](https://developers.facebook.com/docs/facebook-login/permissions#reference-ads_management) and [`ads_read`](https://developers.facebook.com/docs/facebook-login/permissions#reference-ads_read) permissions. 
*   Once approved, you will need to switch to Live Mode. 

**Q: What access do I have during the transition period?**

Existing apps will have a transition period until February 1, 2019 to onboard with the new structure. You should request [`ads_read`](https://developers.facebook.com/docs/facebook-login/permissions#reference-ads_read) and/or [`ads_management`](https://developers.facebook.com/docs/facebook-login/permissions#reference-ads_management) permissions and the new Standard Tier during this period. During this period:

*   Existing apps that have a **rejected** permission, feature, or business verification, for the first time, will have additional time to resubmit before losing access.

*   Existing apps that have an **approved** permission and business verification behave according to the new structure.

*   
Existing apps that have an **pending** review of a permission, feature, or business verification:

    *   Existing apps on legacy development access level behave as if they are in the **Dev Tier** under the new structure

    *   Existing apps on legacy basic or legacy standard access levels behave as if they are in the new **Standard Tier** with [`ads_read`](https://developers.facebook.com/docs/facebook-login/permissions#reference-ads_read) and/or [`ads_management`](https://developers.facebook.com/docs/facebook-login/permissions#reference-ads_management) permission.

**Q: What would happen if my submission is still pending review when the transition period expires?**

Existing apps that have pending [App Review](https://developers.facebook.com/docs/apps/review) submissions created during the transition period and which have not been rejected in [App Review](https://developers.facebook.com/docs/apps/review) behave as if apps are still in the transition period.

**Q: How do I get the permission to create pages through the API?**

Page creation will be separate functionality from Marketing API. You need to apply for Page creation permission with your Facebook Representative to be added to a whitelist through a capabilities tool.

**Q: How long does it take Facebook to approve my submission for Standard Tier access?**

Due to increased volume in expected submissions, it may take several weeks for submitted apps to complete review. Please provide as much information as possible to help the reviewer, including clear screenshots, detailed step-by-step instructions and a screencast recording of your app and its Facebook integration.

**Q: I have multiple apps at different tiers. Do I need to go through app [App Review](https://developers.facebook.com/docs/apps/review) and [Business Verification](https://developers.facebook.com/docs/apps/review#business-verification) for all my apps?**

You need to do [App Review](https://developers.facebook.com/docs/apps/review) for each app. You only need to do [Business Verification](https://developers.facebook.com/docs/apps/review#business-verification) for one Business Manager. The Business Manager should for the business that ultimately operates the app and has access to the data being generated from the app.

For full details and documentation, see:

*   [Marketing API, Access and Authentication](https://developers.facebook.com/docs/marketing-api/access)
*   [App Review and Business Verification](https://developers.facebook.com/apps/review)
*   [App Development, Feature Review](https://developers.facebook.com/docs/apps/review/feature)
*   [Facebook App Review, FAQs](https://developers.facebook.com/docs/apps/review/faqs).

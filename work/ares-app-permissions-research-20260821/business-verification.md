Title: Business Verification

URL Source: http://developers.facebook.com/docs/development/release/business-verification/

Markdown Content:
Updated:Jul 7, 2023

Copy for LLM

Business Verification is a process that allows us to gather information about you and your Business so we can verify your identity as a business entity.

Apps that request [advanced access](http://developers.facebook.com/docs/graph-api/overview/access-levels#advanced-access) for permissions and apps that allow other [Businesses⁠](https://business.facebook.com/) to access their own data must be connected to a Business that has completed Business Verification. Until then, app users from other Businesses will be unable to grant these apps [permissions](http://developers.facebook.com/docs/permissions/reference) and all [features](http://developers.facebook.com/docs/apps/features-reference) will be inactive.

If your app will only be used by app users who have a [role](http://developers.facebook.com/documentation/development/build-and-test/app-roles) on the app itself you do not need to complete verification; these users can grant your app any permissions at any time and all features are always active.

You can use the App Dashboard to connect your app to a Business that you’re an Admin of, regardless of whether or not the Business has been verified, but the verification process itself must be completed in the Facebook Business Manager. If you do not have a Business, you will be given the option to create one.

Note that anyone with an Administrator role on your app can connect it to a Business, but only someone with an Admin role in the Business will be able to complete the verification process.

Load your app in the App Dashboard and go to **Settings**>**Basic**>**Verification** and click the Start Verification button or the **+ Business Verification** link if you have previously completed Individual Verification.

![Image 1: Verification section in the Basic Settings panel.](https://scontent-atl3-2.xx.fbcdn.net/v/t39.2365-6/143865101_957211231353134_6810255425904105080_n.png?_nc_cat=102&ccb=1-7&_nc_sid=e280be&_nc_ohc=QE078Hk1UaQQ7kNvwHrf9cF&_nc_oc=AdofTus9E2wPQt4jbqjKVVECzRlJCT-EAeP2LWeZz0zqye-xbMFQf5dgr51VRJ_mLcU&_nc_zt=14&_nc_ht=scontent-atl3-2.xx&_nc_gid=Mu5c1c8BnCbZOnYNkBzi4A&_nc_ss=7b289&oh=00_AQEddp6DGTYkU__T5icJZ0fo-mV57kxeEtHIMxxQGdFa0Q&oe=6AA1FEA7)

If your Facebook developer account is already associated with a Facebook Business account, you will be given the option to select a Business within it:

![Image 2: Business selection modal with a verified Business selected.](https://scontent-atl3-2.xx.fbcdn.net/v/t39.2365-6/144081810_241994877493212_2655917975499900173_n.png?_nc_cat=102&ccb=1-7&_nc_sid=e280be&_nc_ohc=IFvQwgWD_A8Q7kNvwGVF4Em&_nc_oc=AdpZgiSsWOT3jjOP9pv80Eu0_Al0_3WaSI0rxqirTvj-X6eI2HhkrqQHk3cNree7fa4&_nc_zt=14&_nc_ht=scontent-atl3-2.xx&_nc_gid=Mu5c1c8BnCbZOnYNkBzi4A&_nc_ss=7b289&oh=00_AQENfvm1sRHbWb3FEURqlp2OVsPtiJglSHKEuelsIyEQOA&oe=6AA21A6E)

If you don’t have a Facebook Business account, or if your account contains no Businesses, you will be prompted to create one.

Connecting your app to a verified Business completes the connection process and there’s nothing else you have to do. The **Verification** section should show that your app is now connected to a verified Business:

![Image 3: Verification section showing 'Verified' alongside the name of the Business that has been connected to the app.](https://scontent-atl3-2.xx.fbcdn.net/v/t39.2365-6/142987006_267806678357731_3713867277959890685_n.png?_nc_cat=104&ccb=1-7&_nc_sid=e280be&_nc_ohc=_C93M9KKZ8UQ7kNvwFCh7C9&_nc_oc=AdpQjRcw1jFzmBpsTvfq6-TTSd84M9Z6zZdWMHv09AfN0hLSBApYqk49Imc1cgn9VUw&_nc_zt=14&_nc_ht=scontent-atl3-2.xx&_nc_gid=Mu5c1c8BnCbZOnYNkBzi4A&_nc_ss=7b289&oh=00_AQFDGzjW9uiPusgA6KAliT_XUP7G0z5N5Vyri-HjEJJETQ&oe=6AA20B31)

If, however, you connected your app to an unverified Business, you must complete the verification process in the Business Manager.

If you connected your app to an unverified Business, you or Admin of the Business must complete the verification process within the Business Manager.

![Image 4: Business selection modal with an unverified Business selected.](https://scontent-atl3-2.xx.fbcdn.net/v/t39.2365-6/143769130_241837180871082_6770952626487554480_n.png?_nc_cat=104&ccb=1-7&_nc_sid=e280be&_nc_ohc=S2pnb7jvUj8Q7kNvwHxfTIV&_nc_oc=Ado5Jvj5w1FZwmXcUikzelIBsorh0wyJKfncnydVF19WP_db6GINFg-BqUdmJQJhhXU&_nc_zt=14&_nc_ht=scontent-atl3-2.xx&_nc_gid=Mu5c1c8BnCbZOnYNkBzi4A&_nc_ss=7b289&oh=00_AQFKmqJGpuVuCi7VOAc79Aqh1k5AkeNOaEW9mIzCgW2v-Q&oe=6AA1FEC5)

Click Start Business Verification to load the unverified Business in the Business Manager and complete the verification process.

Refer to our Business Manager Help Center’s [About Business Verification⁠](https://www.facebook.com/business/help/1095661473946872) topic for an explanation of the process and a list of documents you will need.

Once you have completed verification, return to the Basic Settings panel. You should see that your app is now connected to a verified Business:

![Image 5: Verification section showing 'Verified' alongside the name of the Business that has been connected to the app.](https://scontent-atl3-3.xx.fbcdn.net/v/t39.2365-6/144376827_121772393150711_6581279437038461255_n.png?_nc_cat=110&ccb=1-7&_nc_sid=e280be&_nc_ohc=ITalwVj07XcQ7kNvwHUIPIU&_nc_oc=AdqneHxBuGKySRJoAMeJIn9V2Qov24UCYxa2QMaww47hAnexWhPMDxikGO734xigWTk&_nc_zt=14&_nc_ht=scontent-atl3-3.xx&_nc_gid=Mu5c1c8BnCbZOnYNkBzi4A&_nc_ss=7b289&oh=00_AQHADxu6c8YNvEeRCFOV_KIeiFunBeWqmlGwYN5XYotsuA&oe=6AA1F738)

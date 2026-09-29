# Retiring a Blocked/Down Page from DTR Social Accounts

Use this procedure only when Rodolfo explicitly asks to remove one exact Facebook Page that is already classified `Blocked`/`IGNORE` or equivalent and remains visible in DigitalTRChat despite being unavailable on Facebook.

## Identity and liveness gates

1. Freeze the exact tuple before any write:
   - DTR login (`bot_user`);
   - imported DTR account ID and Segurador name;
   - DTR small Page ID (`PAGE_ID`/`PG`);
   - Facebook large Page ID (`FB_PAGE_ID`);
   - Page name only as a corroborating label.
2. Require one unique global-ignore entry by large `FB_PAGE_ID`, or the exact current blocking decision from Rodolfo. Cached DTR photos are not liveness evidence.
3. Open `https://facebook.com/<FB_PAGE_ID>` inside the matching AdsPower/Facebook profile. Require the explicit unavailable/deleted-content state. A reachable Page that is merely absent from `/me/accounts` is an access/tasks blocker and must not be retired under this procedure.
4. Confirm that the Page no longer appears in Facebook's managed Pages for that Segurador. Stop on any identity disagreement.

## DTR deletion gate

1. Resolve the exact DTR login from 1Password; never use a near-match item.
2. Open `https://digitaltrchat.com/social_accounts/index` and activate the exact imported account by immutable account ID plus exact Segurador name.
3. Locate exactly one Social Accounts card matching both `PG` and `FB_PAGE_ID`; corroborate the Page name.
4. Record the before-state identity and whether the bot/webhook connection is enabled. The active delete control is `.page_delete` with the product label `Delete this page from database.`
5. If the connection is still enabled and deletion is disabled, do not silently disable it: that is an additional production write and must already be inside the authorized retirement scope.
6. The confirmation modal states that deleting the Page also deletes all campaigns corresponding to it. Treat that as an intrinsic destructive consequence of Page retirement: disclose it before confirmation unless Rodolfo has already explicitly authorized the exact Page deletion after seeing its identity and purpose.
7. Use the product confirmation control; do not call an inferred private endpoint directly. When browser/CDP automation reports an unverified click, inspect real modal/network/page state before retrying. Never replay the confirmation while the outcome is ambiguous.

## Required readback

Deletion is successful only when all checks pass:

- the confirmation returns to a freshly loaded Social Accounts page;
- the exact `FB_PAGE_ID` and `PG` card are absent after reload;
- a second fresh tab or independent session, still on the exact Segurador account, also returns zero exact matches;
- Messenger Bot inventory contains no exact large/small-ID match;
- the canonical global-ignore record remains in place unless Rodolfo separately removes it.

Record the DTR login, account ID/name, Page name, PG, FB Page ID, public-Facebook liveness result, destructive modal consequence, and both readbacks in the audit event. Never include credentials, cookies, access tokens, avatar URLs, or full DOM output.

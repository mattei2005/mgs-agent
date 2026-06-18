# OpenzedFinanzas clone — token OK, page permission, no-IG creative, POST /ads block (2026-06-18)

## Why this reference exists

Rodolfo asked to continue the clone thread after a wrong-thread message and then authorized action, but noted the prior explanation was too technical. For this class of Meta clone troubleshooting, report in simple operational language first: what passed, what blocked, and what the buyer/user must do next. Keep API codes as evidence, not as the main explanation.

## Token validation result

After the 1Password update, the token became valid again:

```text
Check                 | Result
----------------------|------------------------------
1Password item         | Token Meta API
Field                  | credential
Token len              | 198
GET /me                | 200 OK
Ad account GET         | 200 OK
Ad account             | OpenzedFinanzas-ES-CC-ES-03
Currency/timezone      | USD / Europe/Madrid
```

This resolved the earlier `code=190 Application has been deleted` state.

## Page permission probe

A focused page/adset permission probe showed the token/user could create adsets for some pages but not others:

```text
Page/group        | Page ID          | Source campaign     | Adset create
------------------|------------------|---------------------|-------------
Elena Santana     | 990898360783030  | 120248940367540604  | OK
Patricia Flores   | 1063171606876651 | 120248290564280604  | blocked
Carla Rojas       | 1037297262803284 | 120247501687810604  | blocked
Gabriela López    | 1097045910150412 | 120246399685010604  | blocked
```

Blocked page/adset error:

```text
code/subcode | 100 / 1487202
Meaning      | Page permission insufficient for ads
Action       | Use a page the token can advertise for, or grant the user full/control ad access to that Page.
```

Audit path:

```text
/root/mgs-agent/data/ares/meta-ads/audit/clone/page-adset-permission-probe-20260618T215403Z.json
```

## No-Instagram creative probe

On the page that passed adset creation (`Elena Santana`), the next failure was Instagram asset access when copying `instagram_user_id` from the source creative:

```text
code/subcode | 200 / 1815199
Meaning      | Ad account lacks access to the Instagram account
Fix tested   | Omit `instagram_user_id` from the rebuilt creative
```

The script gained/used `--omit-instagram-user-id` so the creative is page-only. With this flag:

```text
Step                         | Result
-----------------------------|------------------
Create campaign PAUSED       | OK
Create adset PAUSED          | OK
Create creative no-IG        | OK
Create ad                    | blocked by Meta
Cleanup temporary campaign   | OK, DELETED verified
```

Audit path:

```text
/root/mgs-agent/data/ares/meta-ads/audit/clone/clone-by-parts-noig-probe-20260618T215740Z.json
```

## Remaining hard blocker

The final blocker remains at `POST /ads`:

```text
code/subcode | 31 / 3858385
Title        | Autentica tu cuenta
Meaning      | Meta requires the user/account to authenticate or complete a pending action in Ads Manager before API can create/modify ads.
```

This means the standard-enhancements/creative path can be improved enough to pass campaign, adset, and creative creation, but it does **not** bypass Meta's final account-authentication checkpoint.

## Operational sequence for future retests

1. Run quick read-only token check (`/me` + ad account). If `code=190`, stop: token/app invalid.
2. Probe page permission before full clone. Do not assume all campaign pages are usable by the token.
3. If source creative includes Instagram and creative creation fails with `1815199`, retest with `--omit-instagram-user-id` to isolate IG asset permission.
4. If campaign/adset/creative all pass but `POST /ads` returns `31/3858385`, stop and ask Rodolfo/user to authenticate the account in Ads Manager; do not keep trying payload variations.
5. Always create temporary test objects PAUSED and delete/verify them if the build is not a complete accepted replacement.

## User-facing reporting style

For Rodolfo, explain this class of failure without leading with API jargon:

- Good: "O token funciona; a Meta deixou criar campanha, adset e creative. O bloqueio agora é no último botão: criar o anúncio. A Meta está pedindo autenticação no Ads Manager."
- Avoid: long first-pass explanations about `standard_enhancements`, `object_story_spec`, async sessions, or Graph payloads unless he asks for detail.

Keep the technical codes in a short evidence table after the plain-language summary.

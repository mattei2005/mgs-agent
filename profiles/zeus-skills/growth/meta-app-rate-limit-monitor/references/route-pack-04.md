## Operational Symptom Monitor

Graph API app/page headers are necessary but not sufficient. Also monitor business outcomes from SB/DigitalTrChat/ChatPion:

```text
Metric              Why it matters
------------------  -----------------------------------------------------
BD_SENDS            Intended broadcast pressure.
BD_DELIVEREDS       Actual delivered volume.
DRIP_DELIVEREDS     First-24h automation pressure.
LEADS               Lead generation health.
LEADS_TOTAL         Broader volume baseline.
Revenue by site     Business impact; Openzed/Zuout/Cliquet may be AV, not SB.
```

Primary pressure formula when Messenger Pages data exists:

```text
msg_load = DRIP_DELIVEREDS + max(BD_SENDS, BD_DELIVEREDS)
```

For AV/non-SB sites such as Openzed/Zuout/Cliquet, missing SB send/revenue data is not proof of low value. Use page count plus strategic revenue context until a direct source exists.

## B011 — BM restriction / advanced-permission capability collapse

B011 uses Advanced Access so seguradores can connect through DTR/ChatPion without being app developers. A valid `debug_token` proves only token identity and app ownership; it does **not** prove that advanced page/Messenger permissions remain operational. When the app-owning Business Manager is restricted or business verification becomes required, DTR can still show the seguradores/pages and accept a broadcast action while Meta fails OAuth and does not deliver.

Verified incident pattern (2026-07-21):

```text
DTR pages visible                         267
Valid B011 debug_token accounts            22/22
/me/accounts HTTP 200                       22
Graph pages returned                         0
App /permissions endpoint                  still reported live
App Dashboard advanced permissions         Inactive / Verification required
Business portfolio                         restricted
```

Therefore, never use `/{app_id}/permissions = live` or token validity alone as delivery-health proof. The safe read-only functional detector is the cross-account DTR-versus-Graph inventory:

```text
blocked when:
- at least 3 linked accounts have valid B011 debug_token;
- at least 3 /me/accounts checks return HTTP 200;
- DTR exposes one or more pages in aggregate;
- Graph returns zero pages in aggregate; and
- at least 3 linked accounts individually show DTR pages > 0 but Graph pages = 0.

healthy when the same evidence floor is met and Graph returns pages > 0.
otherwise preserve the prior incident as inconclusive; do not auto-resolve.
```

Alert immediately in `#b011-app-rate-limit` with Rodolfo mention and title `B011 — Messenger bloqueado por permissões/BM`. Include DTR pages, Graph pages, valid-token/check counts, the operational impact (DTR may register the send while Meta rejects OAuth/no delivery), and action: pause B011 sends, request BM review/verification or move the app to a healthy BM, then resume when the monitor confirms functional recovery of advanced permissions/pages through Meta Graph. Repeat an unchanged blocked incident only after the standard 6-hour cooldown. When Graph pages return, post one green recovery alert; that functional recovery is sufficient and requires no manual confirmation.

Treat B011 monitoring as two independent layers: (1) segurador/user token linkage to the app; and (2) health of the Business Manager attached to the app, inferred through app-wide Messenger/page capability. A healthy user-link layer never overrides a blocked BM/capability layer.

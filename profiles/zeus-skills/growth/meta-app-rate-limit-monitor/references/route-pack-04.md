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


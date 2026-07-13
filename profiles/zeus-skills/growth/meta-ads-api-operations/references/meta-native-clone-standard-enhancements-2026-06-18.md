# Meta native clone vs rebuild — standard_enhancements pitfall (2026-06-18)

## Context

Rodolfo corrected the operating assumption for Ares replacement campaigns: for the MGS Meta workflow, the target route is **clone existing ads/campaigns**, not create campaigns/ads from zero. Creating from zero can hit Meta account/app/page/authentication checkpoints and is outside the intended flow. System User is also explicitly out of scope for Rodolfo unless he reopens that path.

## Evidence from the thread

Thread: `1517244349891608607` (`Status Operacional do Ares - Rodolfo`).

Observed sequence:

- New token was valid for read/dry-run.
- Manual/rebuild route could create some objects (`campaign`, sometimes `adset`, sometimes `adcreative`) but failed at page permission or `POST /ads` checkpoint.
- Native clone/copy route was then tested and revealed a different blocker:
  - `code=100`
  - `error_subcode=3858504`
  - Spanish title: `El anuncio no debe incluir mejoras estándar`
  - Meaning: source ad includes legacy/obsolete `standard_enhancements`; Meta wants individual creative feature controls instead.

## Durable lesson

Do not collapse these into one diagnosis:

```text
Route                         Meaning
----------------------------- --------------------------------------------
Create from zero / rebuild    Wrong primary path for MGS replacement clones
Native Meta copy/clone         Correct primary path to pursue
Manual rebuild                Fallback/diagnostic only, not success criterion
System User                   Out of Rodolfo's scope
```

If native clone fails with `standard_enhancements`, the blocker is likely the **source ad's legacy creative features**, not proof that cloning is impossible.

## Recommended next tests

1. Prefer native Meta copy endpoints (`/{campaign_id}/copies`, `/{adset_id}/copies`, `/{ad_id}/copies`) over hand-building campaign/adset/ad payloads.
2. Keep all copied objects `PAUSED`.
3. Select another source ad/campaign that does not carry the legacy `standard_enhancements` field, preferably a newer clean ad.
4. If all promising source ads carry the field, research/test copy parameters that suppress or normalize standard enhancements into the newer individual creative feature controls.
5. Do not keep creating/deleting partial campaigns from scratch unless the test is explicitly diagnostic and approved.

## Reporting language

Use precise wording:

- Good: `Clone nativo bloqueou por standard_enhancements legado no source ad.`
- Bad: `Meta não deixa clonar.`
- Bad: `Precisa de System User.`
- Bad: `Vamos criar do zero com payload limpo.`

## Safety

Writes still require explicit approval. Partial objects created during tests must remain `PAUSED` and be cleaned up (`DELETED`) with GET verification before reporting completion.

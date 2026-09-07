# Meta Business success-popup acceptance and cron replacement

## Scope

Session-specific detail for a scheduled Digital Trust ad-account batch where Rodolfo explicitly changed the acceptance contract: the exact Meta success modal is sufficient even when the subsequent account list or `People` tab does not render.

## Diagnostic distinction

`people_tab_count_0` means the automation found zero DOM tabs named `People`; it does **not** mean zero people are assigned to the account. Never report it as an access count.

In the observed control flow, that exception occurred only after:

1. the `Create ad account` mutation was clicked;
2. Meta displayed `Ad account created` / `Ad account created successfully`;
3. the resulting internal asset identifier existed;
4. the success dialog's `Done` step ran; and
5. the later detail/People readback failed to render.

Under the explicit success-popup acceptance contract, recover that tick as one confirmed creation while retaining the real Ad Account ID, owner and access as unverified if they were not persisted before the rendering failure. Do not fabricate those fields.

## Runner contract

- Success modal captured: advance the batch by exactly one.
- Details available: persist ID, internal asset ID, owner and access separately with their verification flags.
- List or `People` missing after success: keep the creation successful; store unavailable evidence as `null`/unverified.
- Error popup captured: stop immediately; no automatic retry.
- Neither success nor error captured: stop as ambiguous; do not replay the write.
- Preserve the original target guard and one-write-per-tick lock so a confirmation-only record cannot create account 41.

## Exhausted recurring cron

A finite recurring Hermes cron that has consumed every repeat is terminal. Attempts to edit/update or plain-resume it may be rejected as activation of a terminal job; one-shot re-arm options do not apply to recurring jobs.

The validated recovery pattern is:

1. leave the exhausted job disabled as historical evidence;
2. create one replacement recurring job against the **same durable checkpoint and request ID**;
3. set its repeat budget to `remaining writes + bounded recovery reserve`;
4. preserve the existing cadence, delivery thread, script-only mode and target guard;
5. update the checkpoint with both the replacement job ID and superseded job ID;
6. read back the replacement as enabled with the expected next run;
7. classify the lane as `scheduled` until its first natural post-change tick satisfies the active acceptance contract.

This is replacement of an exhausted scheduler wrapper, not creation of a new business batch. Never reset completed entries, preexisting IDs, target, defaults or authorization scope.
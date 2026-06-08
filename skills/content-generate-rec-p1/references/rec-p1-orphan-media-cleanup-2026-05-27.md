# REC/P1 orphan media cleanup after failed runs (2026-05-27)

## Why this reference exists

During a live REC+P1 benchmark for `Nationwide Balance Transfer Credit Card`, the first REC attempt uploaded a user-supplied/manual card image to WordPress as media ID `62295`, then failed later during featured-image/audit gates before any post was created. A later attempt published using different media IDs. Cleanup initially removed only the final published-operation artifacts and missed `62295`, which remained as an orphan attachment.

This exposed a durable production pitfall: media uploads can happen before all downstream gates finish, so failed runs can leave orphan WordPress media unless cleanup is explicit.

## Operational lesson

For REC/P1/REC+P1 production and cleanup:

1. A failed runner/orchestrator execution can create WordPress media even when no post is created.
2. Cleanup must include all media created by the operation, not only media referenced by the final published posts.
3. Cleanup audits should search by operation slug/card slug and timestamp window for orphan attachments.
4. Manual card images that fail identity/quality validation should ideally block before upload.
5. If upload-before-final-gates is unavoidable, the exception handler must delete media uploaded during that same attempt.

## Evidence pattern from incident

```text
17:59:27 | upload-image OK file=card-nationwide-balance-transfer-credit-card.png id=62295
17:59:35 | featured generation/audit attempt 1
17:59:55 | featured generation/audit attempt 2
18:00:10 | featured generation/audit attempt 3
18:00:28 | flow failed before post creation
18:01:14 | second attempt uploaded different card image id=62296
18:01:53 | REC post created id=62298
```

`62295` was not linked to a post (`post=null`) and visual inspection showed it was a Nationwide FlexAccount Visa Debit image, not the requested Balance Transfer credit card.

## Required future behavior

When deleting a bad REC/P1/REC+P1 operation:

```text
Required cleanup scope
------------------------------------------------------------
Published posts                         | trash/delete confirmed IDs
Media referenced by posts                | delete confirmed IDs
Orphan media from failed attempts         | search/delete by slug + timestamp
Fingerprint/QA rows for bad operation     | delete matching rows
Editorial card-cache                      | should not be used; if any entry exists, remove it
```

When changing runners:

- keep a `created_media` list live as soon as each upload succeeds;
- include that list in failure JSON, not only success JSON;
- in `except`, attempt safe deletion for media created in the current attempt when no successful post owns it;
- log cleanup results in final JSON/report;
- never claim cleanup complete until orphan search is done.

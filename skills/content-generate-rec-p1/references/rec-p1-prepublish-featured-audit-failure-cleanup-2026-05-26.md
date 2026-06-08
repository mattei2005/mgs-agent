# REC+P1 pre-publication featured-image audit failure cleanup (2026-05-26)

## Trigger

Use this reference when a published REC+P1 request reaches the REC runner, but the REC stops before WordPress post creation because `audit-featured-image.py` rejects the generated featured image.

Observed with The Royal Bank Credit Card on eggbev: official source and card facts passed, card image was found/normalised/uploaded, but featured-image audit failed twice before any REC post was created. Since P1 depends on the REC URL, the P1 must not be started.

## Correct handling

1. Treat the failure as a valid quality gate, not as a publish success.
2. Do **not** start the P1 runner when the REC has not published.
3. Check whether the runner uploaded card media before the failure. Pre-publish featured-image failures can leave card-image media in WordPress even though no post exists.
4. Delete only media created by this failed run that are not used by any post:
   - Use `content-publish-wordpress/scripts/delete-media-safe.sh <site_key> <media_id>`.
   - Keep the output concise and do not expose credentials.
5. Report the blocker naturally to Rodolfo/Raquel:
   - REC blocked before publication.
   - P1 not started because it depends on the REC.
   - Official source/facts passed if true.
   - Featured image failed visual audit and needs regeneration/runner repair.
   - Orphan media from the attempt were cleaned up if deleted.

## Why this matters

The runner can fail after `card_image_uploaded` but before `featured_media_uploaded` and `create-post`. A normal final summary would be misleading, and leaving uploaded card media creates WordPress Media Library clutter. This is a pre-publication failure path, so use a concise blocker report rather than Rodolfo's success summary template.

## User-facing posture

Do not over-explain internal scripts or raw JSON unless Rodolfo asks for technical details. For human-facing Discord, say the pipeline blocked before publication because the featured-image quality gate failed, and that cleanup was done.
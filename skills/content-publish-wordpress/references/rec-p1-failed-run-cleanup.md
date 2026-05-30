# REC+P1 failed-run cleanup

Use this when a REC+P1 pipeline run creates draft posts or media and later fails validation/readability/public verification.

## Failure mode to guard against

A runner can create/upload media, create a draft post, then fail a later gate. If cleanup deletes media but leaves the draft post behind, WordPress ends up with:

- duplicate REC drafts from retries;
- P1 drafts with `featured_media=0`;
- HTML blocks referencing deleted media IDs/URLs;
- editorial admin polluted with unusable drafts.

Draft is not a harmless sandbox: it is production editorial state and must be treated transactionally.

## Cleanup order

1. Scope the incident by explicit post IDs and card slug. Do not broad-delete by generic terms.
2. Fetch each post with auth/context=edit and record: status, slug, title, `featured_media`, and media IDs referenced in raw content (`wp-image-<id>`, image block IDs, LazyBlock media IDs).
3. Fetch candidate media and confirm slug/title/source URL matches the card slug or the known incident IDs.
4. Delete/trash the created posts first, or make sure post deletion is part of the same cleanup transaction.
5. Delete only scoped media after posts are gone, including card image and generated featured images that match the card slug.
6. Validate post IDs and media IDs return 404 through WP REST.
7. Report any media already 404 separately; do not imply it was deleted in the current cleanup.

## Runner hardening lesson

For future pipeline patches, make post creation fail-clean:

- Track every created post ID immediately after `create_post` returns.
- If any later gate fails, cleanup must remove both created posts and created media.
- Retrying should not create a second REC when a draft already exists for the same card/slug unless the old draft was deliberately deleted or reused.
- Readability/Yoast/public verification should not leave partial drafts with broken media references.

## Confirmation

Deleting WP posts/media is destructive. If the user explicitly asks for deletion, still follow the critical-operation double-confirmation policy before executing permanent deletion.
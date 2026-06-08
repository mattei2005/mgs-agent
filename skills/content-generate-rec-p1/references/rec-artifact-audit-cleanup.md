# REC Artifact Audit + Safe Media Cleanup

Use this reference when auditing REC runs, changing the REC runner, or reviewing why WordPress Media Library contains extra images after a loop/error.

## Trigger

Atena generated multiple WordPress media images during a REC run but used only two in the final post: one card image and one featured image. The user only discovered the extra images by manually logging into WordPress → Media Library.

Operational lesson: reporting the visible error is not enough. REC completion must report the final state of artifacts created by the run.

## Required behavior

Every REC final summary must include:

```text
ARTIFACT AUDIT
Created in run: N
Used in post:   N
Extra:          N
Deleted:        N
Skipped:        media_id + reason, if any
```

Minimum fields in machine JSON from the runner:

```json
{
  "images": {
    "card_id": 123,
    "card_url": "https://...",
    "featured_id": 456,
    "featured_url": "https://...",
    "created_media": [
      {"role": "card", "id": 123, "url": "https://...", "used": true},
      {"role": "featured", "id": 456, "url": "https://...", "used": true}
    ],
    "artifact_audit": {
      "created_count": 2,
      "used_count": 2,
      "extra_count": 0,
      "deleted_count": 0,
      "items": []
    }
  }
}
```

## Safe auto-delete rules

Auto-delete is allowed only when ALL are true:

1. The media item was uploaded by the current REC runner execution.
2. Its media ID is not the post `featured_media`.
3. Its `source_url` and `wp-image-{id}` are not present in the post HTML/content.
4. It is not attached to a different parent post.
5. The deletion uses authenticated WP REST with `force=true` and logs the result.

If any check is uncertain, do not delete. Report the media ID and reason to the user.

## Current implementation

- Runner: `/root/mgs-agent/scripts/mgs-rec-runner.py`
  - tracks `created_media`
  - returns `images.artifact_audit`
  - runs cleanup after post creation/public verification
- Safe delete helper: `/root/mgs-agent/skills/content-publish-wordpress/scripts/delete-media-safe.sh`
  - fetches media via WP REST
  - fetches post via WP REST when post ID is known
  - refuses deletion for featured media, content references, or different parent post
- Summary rule: `content-generate-rec/SKILL.md` Step 13 must reflect the artifact audit in the single final message.

## UX rule

Do not make the user discover extra media manually. If a loop/error caused extra artifacts, report the artifact count and the cleanup action in the same final REC summary.
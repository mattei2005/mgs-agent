# REC John Lewis blocked official source + image/title repair (2026-05-19)

## Trigger

Use this reference when a REC request has a real official URL, but the issuer page is blocked by normal runner fetch and Chromium/browser automation, especially for UK credit-card pages using Akamai/HTTP2 protections.

## What happened

- Initial `mgs-rec-runner.py --source-url https://www.johnlewismoney.com/partnership-credit-card` failed before content generation with `HTTP Error 403: Forbidden`.
- Browser/Chromium navigation to the same official URL failed with `net::ERR_HTTP2_PROTOCOL_ERROR`.
- Google/Bing browser search hit bot challenges, but DuckDuckGo HTML exposed official related URLs and a CTFAssets terms PDF.
- `https://r.jina.ai/http://https://www.johnlewismoney.com/partnership-credit-card` successfully rendered the same official John Lewis Money page as Markdown, including APR, reward rates and official image URLs.
- `https://r.jina.ai/http://https://www.johnlewismoney.com/partnership-credit-card/terms-and-conditions` exposed reward-program rules and exclusions.

## Durable fallback pattern

1. Keep the source of truth official. Do not replace financial facts with comparator-site claims.
2. If runner fetch and Chromium both fail, try the reader/render fallback on the same official URL:

```text
https://r.jina.ai/http://https://<official-host>/<official-path>
```

3. Extract only facts visible in official rendered page/terms.
4. Rerun `mgs-rec-runner.py` with explicit facts:

```bash
python3 /root/mgs-agent/scripts/mgs-rec-runner.py \
  --site <site> \
  --card "<card name>" \
  --status draft \
  --source-url "<official URL>" \
  --annual-fee "<officially stated value or conservative unknown phrasing>" \
  --apr "<official APR/purchase rate>" \
  --benefit "<official benefit 1>" \
  --benefit "<official benefit 2>" \
  --benefit "<official benefit 3>" \
  --competitor "<reasonable market comparator>" \
  --competitor "<reasonable market comparator>"
```

5. If the reader exposes official image URLs, do **not** blindly pass promotional/lifestyle images as `--card-image-url`. The LazyBlock card image must be card-only. Use official images only when they are isolated card artwork, or run bounded card-image search and validate with vision before upload.
6. If a required fact (example: annual account fee) is not clearly stated in the accessible official material, write conservatively: say it is not clearly stated and tell readers to confirm with the issuer. Do not infer `no annual fee` from third-party pages.

## Repair lessons from Post 62146

The first draft had multiple unacceptable defects:

- WordPress post title was blank because Yoast update was given top-level `title: ""`. Yoast scoring can still pass even when WP title is blank. Always verify the saved title through WP REST after update.
- The LazyBlock card image used an official promotional/composite image with a person/scene. This violates the card-only requirement. For card/LazyBlock, only isolated horizontal card artwork is acceptable.
- The featured image placed the card like a badge/crachá and looked low-quality. Featured must be a realistic 16:9 lifestyle composition where the card is naturally placed, not attached to a person.
- A later replacement featured image was visually acceptable but still failed the user's prompt because it had no human character. Aesthetic quality is not enough: REC featured images must pass all mandatory prompt gates.
- The final summary omitted separate character counts for title, subtitle and meta description, despite the user requesting detailed fields.

## Featured-image hard gates learned from this repair

For REC featured images, validate the local image before upload against all five gates:

```text
Gate                          | Required outcome
------------------------------|---------------------------------------------------------
Card identity                 | Card design preserved from reference, preferably horizontal
Human presence                | One realistic person/character is visible in the scene
Contextual setting            | Scene surrounds the card and connects to real-life use
Cinematic/humanized style     | Premium editorial look, not sterile product-only art
Payment-card readability      | Card reads as a card, not a badge/crachá or UI label
```

Reject and regenerate even a beautiful image if any gate fails. Real-use props such as coffee, desk, POS machine, passport, shopping bags or phone can support the story, but they never replace the required person.

## Verification checklist after repair

Before final reply, verify all of these:

```text
Check                         | Required result
------------------------------|-----------------------------------------------
Same post ID                  | No replacement post created
Status                        | Preserved as requested, usually draft
WP title                      | Non-empty saved title via REST/context=edit
Card image                    | New LazyBlock `imagem` ID/URL is card-only
Old card image                | No longer referenced in content
Featured media                | New featured ID set on post
Old media                     | Deleted only after safe-delete gates pass
Validation                    | Final exact content PASS
Yoast                         | Re-run update + scorer after repairs
Summary counts                | Title chars, subtitle chars, meta chars shown
```

## Reporting requirement

If the user requested detailed final fields, report character counts as explicit separate rows/fields:

- `Título — caracteres`
- `Sub-title — caracteres`
- `Meta description — caracteres`

Do not rely on a combined `Title/Sub-title/Meta` shorthand when the request enumerates fields individually.
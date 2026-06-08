# Vitality REC+P1 — low-res manual card benchmark + draft P1 source handling (2026-05-26)

## Trigger
Rodolfo asked for a REC+P1 draft on eggbev for the Vitality American Express Credit Card and supplied the official Amex URL plus a direct Amex CDN card image. The normal manual-card gate rejected the image because the useful crop width was 480px, below the 600px source-quality threshold. Rodolfo explicitly approved trying that same image anyway to validate whether the rule scope should change.

## Durable lessons

### 1. Low-res manual card image can be an explicit benchmark exception
The default rule remains strict: a manual card image with useful crop width below 600px should stop before upload.

However, when Rodolfo/Raquel explicitly say to try the exact image anyway for visual validation, the runner may continue as a controlled benchmark exception, while preserving the warning in the final summary. Do not silently relax the canonical rule.

Recommended implementation pattern:
- Keep the default hard gate unchanged.
- Add/use an explicit one-run switch such as `MGS_ALLOW_LOW_QUALITY_MANUAL_CARD=1`.
- Record a warning such as `manual_card_image_low_quality_source_allowed_by_user`.
- Report that the low-res source was used by explicit approval and that the canonical rule was not changed yet.

### 2. Amex UK official pages may require rendered extraction
Amex UK card pages can return too little useful text to urllib/curl but load correctly in a rendered browser. A bounded Playwright local render fallback is appropriate for `americanexpress.com` when stripped HTML text is below the content gate.

Important Amex quirk: the page disables `eval`, so `page.evaluate("document.body.innerText")` can fail. Use Playwright locator extraction instead:

```python
page.goto(url, wait_until="domcontentloaded", timeout=45000)
page.wait_for_timeout(2000)
text = page.locator("body").inner_text(timeout=10000)
```

Avoid `networkidle` on Amex pages because background requests may keep the page from becoming idle and cause false content-gate failures.

### 3. Draft REC to P1 handoff needs authenticated `?p=<id>` handling
P1 creation from a draft REC cannot rely on public GET because draft permalinks commonly return 404. If the REC URL is a draft permalink like `https://site/?p=62220`, the P1 runner should parse the post ID and load the REC through authenticated WP REST instead of public HTML.

Pattern:
```python
m = re.search(r"[?&]p=(\d+)", rec_url)
if m:
    rec_id = int(m.group(1))
    rec = wp_get_post(site_key, rec_id)
    public_html = f"<body class='postid-{rec_id}'>" + (rec['content']['rendered'] or rec['content']['raw']) + "</body>"
else:
    public_html = get_public(rec_url)
    rec_id = post_id_from_public_html(public_html, rec_url)
```

### 4. Draft public verification is not the same as publish verification
A draft REC/P1 may be created successfully while public verification returns 404. For draft status, report the future permalink/draft edit link and avoid treating unauthenticated public 404 as a publication failure. For publish status, keep public verification strict.

## Final-reporting rule for this exception
When using a low-res manual card by explicit approval, final summary must include:
- the card image URL used;
- the source-quality warning (`useful crop width 480px below 600px`, or actual value);
- that the exception was user-approved for validation;
- that the canonical image-quality rule has not been changed yet.
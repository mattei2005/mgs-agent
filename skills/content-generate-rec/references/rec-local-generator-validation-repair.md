# REC local generator validation repair

Use this when `mgs-rec-runner.py` falls back to `article_generated_local` and stops before media/publish with `Article validation failed` even though `word_count` and `subtitle` pass.

## Symptom

Runner output looks like:

```json
{
  "success": false,
  "error": "Article validation failed: {... \"word_count\": \"pass\", \"subtitle\": \"pass\", \"editorial_style\": \"fail\", ...}",
  "steps": ["config_loaded", "reference_extracted_deterministic", "article_generated_local"]
}
```

Common validator details:
- `max_paragraph_words` just over the limit, often `31` when limit is `30`.
- `long_sentence_ratio` may still pass.
- No WordPress post/media/Yoast exists yet because validation happens before upload.

## Durable cause pattern

The deterministic fallback can insert extracted official-page fields directly into prose. Some fields are longer than expected, especially APR strings polluted by nearby page text such as eligibility disclaimers. A paragraph template that is safe with a short APR becomes invalid when the extracted APR is long.

## Repair pattern

1. Reproduce with dry-run using the supported runner flags only:

```bash
python3 /root/mgs-agent/scripts/mgs-rec-runner.py \
  --site <site_key> \
  --card "<exact card name>" \
  --status draft \
  --source-url "<official URL>" \
  --dry-run
```

Do not pass `--vertical`, `--type`, or `--official-url`; those are not runner flags.

2. Inspect the generated temp file when the validator fails:

```bash
python3 - <<'PY'
from pathlib import Path
import re, html
p = Path('/tmp/final-<card-slug>.html')
content = p.read_text()
for i, raw in enumerate(re.findall(r'<p>(.*?)</p>', content, flags=re.S), 1):
    text = html.unescape(re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', raw)).strip())
    wc = len([t for t in text.split() if re.search(r'[A-Za-z0-9]', t)])
    if wc >= 29:
        print(i, wc, text)
PY
```

3. Prefer fixing the local generator template/field shortening, not weakening the validator. Example fix that worked: introduce a shortened display variable for APR before interpolating it into article prose:

```python
apr_display = esc_text(shorten_words(card_data.get("apr") or "N/A", 8))
```

Then use `apr_display` in the paragraph instead of the raw `apr` value.

4. Validate before declaring fixed:

```bash
python3 -m py_compile /root/mgs-agent/scripts/mgs-rec-runner.py
python3 /root/mgs-agent/scripts/mgs-rec-runner.py --site <site> --card "<card>" --status draft --source-url "<url>" --dry-run
```

Expected dry-run evidence:
- `success: true`
- `validation.status: PASS`
- `validation.style.style: pass`
- `max_paragraph_words <= 30`
- steps include `content_validated_pre_upload` and `content_validated_final`

## Reporting note

If the failure happened before upload/publish, say explicitly that WordPress, media, Yoast, and artifact audit did not run. This prevents the user from looking for a missing draft or orphan media that were never created.

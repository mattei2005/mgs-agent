# Fast runner cache-miss fallbacks

Use this reference when `mgs-rec-runner.py` is the requested execution path but the card is not in cache and one of the legacy automated paths is unavailable.

## Known runner failure modes

### 1. Anthropic extraction path disabled

Typical runner error:

```json
{
  "success": false,
  "error": "Anthropic/Claude API disabled by policy. Provide explicit --benefit/--annual-fee facts or migrate this extraction path to GPT-5.5/OAuth before running cache-miss RECs."
}
```

Correct response:
1. Do not abandon the deterministic runner.
2. Fetch/verify official facts from the source page with browser tools or another allowed source-of-truth method.
3. Re-run `mgs-rec-runner.py` with explicit facts:
   - `--annual-fee "..."`
   - `--apr "..."`
   - repeated `--benefit "..."`
   - repeated `--competitor "..."`
4. Keep all facts conservative and sourced. If APR or a key fact is not stated precisely, pass the exact official wording rather than inventing a number.

Example:

```bash
python3 /root/mgs-agent/scripts/mgs-rec-runner.py \
  --site eggbev \
  --card "Marbles Credit Card" \
  --status publish \
  --source-url "https://www.marbles.com/marbles-card/" \
  --annual-fee "No annual fee" \
  --apr "The APR applicable to your account will depend on marbles' assessment of your application" \
  --benefit "No annual fee" \
  --benefit "No interest on purchases if every statement balance is paid in full by the payment date" \
  --benefit "marbles Mastercard is accepted all over the world" \
  --benefit "Manage your account online" \
  --benefit "Free SMS alerts to help manage your account" \
  --competitor "Aqua Classic Credit Card" \
  --competitor "Capital One Classic Credit Card"
```

### 2. Card image wrapper returns empty JSON / fails silently

Observed pattern:
- Runner fails with `Card image search failed: {}`.
- Direct `search-card-image.sh` exits non-zero with no stdout.
- Direct Bing fallback script succeeds:

```bash
python3 /root/mgs-agent/skills/content-generate-rec/scripts/search-card-image-bing.py "<Card Name>"
```

Correct response:
1. Run the direct Bing fallback script once.
2. Use the returned `source` URL with runner `--card-image-url "<source>"`.
3. Do not enter manual browser/image-search loops.
4. Report that the card image came from fallback/source URL and still include artifact audit.

## Important cautions

- These fallbacks are still part of the deterministic runner path; do not switch to the full manual REC pipeline unless the runner cannot publish after a bounded retry.
- Do not invent benefits, APR, fees, or competitor positioning. Use official wording when exact numbers are absent.
- If using a temporary local helper to satisfy a deprecated local API path, disclose the operational caveat in the final summary and stop/clean up the helper afterwards. Prefer a permanent runner/API migration over repeating the temporary helper pattern.
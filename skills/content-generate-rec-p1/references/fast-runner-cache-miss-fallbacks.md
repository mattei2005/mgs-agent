# Fast runner cache-miss fallbacks

Use this reference when `mgs-rec-runner.py` is the requested execution path but the card is not in cache and one of the legacy automated paths is unavailable.

## Known runner failure modes

### 1. Cache MISS with legacy Anthropic extraction disabled

Historical runner error:

```json
{
  "success": false,
  "error": "Anthropic/Claude API disabled by policy. Provide explicit --benefit/--annual-fee facts or migrate this extraction path to GPT-5.5/OAuth before running cache-miss RECs."
}
```

Current expectation after the 2026-05-18 MBNA patch:
- `mgs-rec-runner.py` should not call Anthropic/Claude on cache MISS.
- It should use deterministic source-snippet extraction and continue into local article generation.
- `steps` should show `reference_extracted_deterministic`, not `reference_extracted_llm`.
- `cost_usd.extract_llm_est` should remain `0.0` for this path.

Correct response if this error reappears:
1. Treat it as a runner regression, not an editorial/user prompt problem.
2. Do not abandon the deterministic runner or switch into broad manual workflow.
3. Patch/restore the deterministic cache-miss path in `mgs-rec-runner.py`.
4. Validate with `py_compile` and a safe `--dry-run` for the failing card.
5. If deterministic extraction returns only bot-block boilerplate, re-run with explicit facts rather than inventing details.

Explicit facts remain the higher-quality fallback:
- `--annual-fee "..."`
- `--apr "..."`
- repeated `--benefit "..."`
- repeated `--competitor "..."`

Keep all facts conservative and sourced. If APR or a key fact is not stated precisely, pass the exact official wording rather than inventing a number.

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
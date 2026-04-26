---
name: content-repair-readability
description: >
  Diagnose and fix Yoast readability violations on existing WordPress posts.
  Covers sentence length, transition words, and passive voice — the three
  most common causes of a red readability score. Rewrites the post body
  in-place and re-scores via yoast-score-post.sh.
tags: [yoast, readability, wordpress, eggbev, rewrite]
---

# content-repair-readability

Repairs an existing WordPress post that has a 🔴 or 🟡 Yoast readability score
by diagnosing which rules are violated, rewriting the body text, and publishing
the update.

## When to use

- User shares a post URL with "Readability red/yellow" or "needs improvement"
- Post was published before the readability adendo was in the template
- Any REC or content post where Yoast flags readability violations

## Inputs

- Post URL (e.g. `https://eggbev.com/rec-gb-cc-virgin-atlantic-reward/`)
- Site key (e.g. `eggbev`)

## Step 1 — Find the post ID

The WP REST `?slug=` filter may return `[]` even for existing posts (known
eggbev bug — see content-generate-rec SKILL.md). Always use the public HTML:

```bash
curl -s "https://<domain>/<slug>/" | grep -oE 'post-[0-9]+' | head -1
# e.g. → post-62013 → ID is 62013
```

Then fetch full raw content:

```bash
curl -s -u "$WP_USER:$WP_PASS" \
  "$WP_URL/wp-json/wp/v2/posts/<id>?context=edit&_fields=id,title,slug,content,meta,featured_media,tags,categories"
```

## Step 2 — Diagnose violations

Extract plain text from the raw Gutenberg HTML (strip tags, exclude LazyBlocks),
then run this Python diagnostic:

```python
import re

# Strip HTML tags
text = re.sub(r'<!--.*?-->', '', raw_content, flags=re.DOTALL)  # remove Gutenberg comments
text = re.sub(r'<[^>]+>', '', text)
text = re.sub(r'\s+', ' ', text).strip()

sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip() and len(s.split()) > 3]

# Violation 1: sentence length
long = [s for s in sentences if len(s.split()) > 20]
pct_long = len(long) / len(sentences)
print(f"Long sentences: {len(long)}/{len(sentences)} = {pct_long:.0%} (target <25%)")

# Violation 2: transition words
transitions = ['additionally','moreover','furthermore','however','therefore',
               'consequently','in addition','for example','as a result',
               'this means','in contrast','also','thus','meanwhile','indeed',
               'furthermore,','moreover,']
found = [t for s in sentences for t in transitions if t.lower() in s.lower()]
ratio = len(found) / len(sentences)
print(f"Transitions: {len(found)}/{len(sentences)} = {ratio:.0%} (target ~25-33%)")

# Violation 3: passive voice (non-idiomatic)
passives = [s for s in sentences if re.search(r'\b(is|are|was|were|be|been|being)\b.{1,20}\b\w+ed\b', s, re.I)]
print(f"Passive candidates: {len(passives)}")
```

Target thresholds (Yoast defaults, English):
| Metric | Limit | Green |
|---|---|---|
| Sentences >20 words | <25% | ✅ |
| Transition words | ≥25% of sentences | ✅ |
| Passive voice | <10% of sentences | ✅ |

## Step 3 — Rewrite rules

Apply ONLY the rules that are violated. Do not over-engineer.

### Sentence length (most common violation)
- Break sentences at natural clause boundaries — full stop, not comma chain
- Target: 2–3 sentences per ~35-word paragraph
- Each split should be logically coherent on its own

**Before (31 words):**
> Cardholders earn 0.75 Virgin Points per £1 on everyday spending, rising to 1.5 Virgin Points per £1 when booking directly with Virgin Atlantic or Virgin Holidays.

**After (two sentences, 14 + 14 words):**
> Cardholders earn **0.75 Virgin Points per £1** on everyday spending. The rate doubles to **1.5 points per £1** on direct Virgin Atlantic and Virgin Holidays bookings.

### Transition words
- Target: at least 1 transition every 3–4 sentences, distributed across all sections
- Vary the words — never use the same one twice in a row
- Preferred: Additionally, Moreover, Furthermore, However, Therefore, Consequently,
  In addition, As a result, In contrast, Also, This means, Meanwhile

**Before (no transitions):**
> The card carries no annual fee. It suits UK travellers looking for genuine reward value.

**After:**
> The card carries no annual fee. Additionally, it suits UK travellers who want genuine reward value without a premium price tag.

### Passive voice
- Prefer active when equally natural: "the card earns" not "points are earned"
- Passive is acceptable in idiomatic financial constructions:
  - "cashback is credited monthly" ✅
  - "the fee is waived automatically" ✅
  - "points are redeemable for flights" ✅
- Only rewrite if the passive is clearly avoidable

## Step 4 — Validate before publishing

Run the validator on the rewritten body:

```bash
bash /root/mgs-agent/skills/content-generate-rec/scripts/validate-article.sh /tmp/rewritten.html
```

Expected output: `{"status": "PASS", "count": 450-500, "subtitle_chars": <=100}`

If count changed significantly, re-check with the Python diagnostic above:

```python
# Quick check before publishing
long_pct = len([s for s in sentences if len(s.split()) > 20]) / len(sentences)
trans_count = len([t for s in sentences for t in transitions if t in s.lower()])
print(f"Long: {long_pct:.0%} | Transitions: {trans_count}")
```

## Step 5 — Publish the update

```bash
curl -s -X POST "$WP_URL/wp-json/wp/v2/posts/<id>" \
  -u "$WP_USER:$WP_PASS" \
  -H "Content-Type: application/json" \
  -d "{\"content\": $(python3 -c "import json,sys; print(json.dumps(open('/tmp/rewritten.html').read()))")}"
```

Verify response includes `"status":"publish"` and a new `"modified"` timestamp.

## Step 6 — Re-score

```bash
bash /root/mgs-agent/skills/content-generate-rec/scripts/yoast-score-post.sh <site_key> <post_id>
```

Expected: `readability_score >= 71` (green). If still yellow/red, re-diagnose —
Yoast may weight violations differently than the Python heuristic.

## Pitfalls

- **LazyBlocks must be preserved exactly** — do NOT alter the `<!-- wp:lazyblock/... /-->`
  blocks, their JSON payloads, or blockIds. Only rewrite the `<!-- wp:paragraph -->` and
  `<!-- wp:heading -->` blocks. The table block can also be rewritten but the
  `<!-- wp:table -->` / `<figure>` wrapper must remain intact.

- **Subtitle (first paragraph) has a 100-char hard limit** — if rewriting the subtitle,
  count chars: `python3 -c "print(len('your subtitle text.'))"`. Do not exceed 100.

- **Word count must stay 450–500** — splitting sentences adds no words, but rewriting
  introductions might. Always validate after rewriting.

- **LazyBlock strip before analysis** — the Python diagnostic must strip `<!-- wp:lazyblock -->` 
  blocks before counting sentences, or the JSON payloads inside them will be counted
  as prose sentences (false positives in passive/transition analysis).

  ```python
  import re
  text = re.sub(r'<!-- wp:lazyblock.*?/-->', '', raw_content, flags=re.DOTALL)
  ```

- **Table content counts toward word count** — the Comparative Table paragraphs
  and table cells are included in the 450–500 count. Budget accordingly.

- **Yoast scores reset to notAnalyzed after REST update** — always run
  `yoast-score-post.sh` after updating the content, or instruct Raquel to click
  Update in the editor. The mu-plugin v4 (yoast-rest-meta.php) no longer forces
  fake scores — what you see after the scorer runs is real.

## Example outcome

Virgin Atlantic Reward REC (post 62013, eggbev):

| Metric | Before | After |
|---|---|---|
| Sentences >20 words | 82% 🔴 | 6% ✅ |
| Transition words | 0 🔴 | 12 (39%) ✅ |
| Readability score | 🔴 | 🟢 90 |
| SEO score | — | 🟢 79 |

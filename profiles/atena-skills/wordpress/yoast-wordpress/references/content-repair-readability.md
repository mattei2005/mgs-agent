# Content Repair — Readability Violations

> Absorbed from: `content-repair-readability` skill (archived 2026-04-29)

Repairs a WordPress post with a 🔴/🟡 Yoast readability score by diagnosing which
rules are violated, rewriting the body text, and publishing the update.

## Inputs
- Post URL (e.g. `https://eggbev.com/rec-gb-cc-virgin-atlantic-reward/`)
- Site key (e.g. `eggbev`)

---

## Step 1 — Find the post ID

The WP REST `?slug=` filter may return `[]` even for existing posts (known eggbev bug).
Always use the public HTML:

```bash
curl -s "https://<domain>/<slug>/" | grep -oE 'post-[0-9]+' | head -1
# e.g. → post-62013 → ID is 62013
```

Then fetch full raw content:
```bash
curl -s -u "$WP_USER:$WP_PASS" \
  "$WP_URL/wp-json/wp/v2/posts/<id>?context=edit&_fields=id,title,slug,content,meta,featured_media,tags,categories"
```

---

## Step 2 — Diagnose violations

Strip LazyBlocks FIRST, then run Python diagnostic:

```python
import re

# Strip LazyBlocks before analysis (or JSON inside them counts as sentences)
text = re.sub(r'<!-- wp:lazyblock.*?/-->', '', raw_content, flags=re.DOTALL)
# Strip remaining HTML
text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
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
               'this means','in contrast','also','thus','meanwhile','indeed']
found = [t for s in sentences for t in transitions if t.lower() in s.lower()]
ratio = len(found) / len(sentences)
print(f"Transitions: {len(found)}/{len(sentences)} = {ratio:.0%} (target ~25-33%)")

# Violation 3: passive voice
passives = [s for s in sentences if re.search(r'\b(is|are|was|were|be|been|being)\b.{1,20}\b\w+ed\b', s, re.I)]
print(f"Passive candidates: {len(passives)}")
```

**Target thresholds (Yoast defaults, English):**
| Metric | Limit | Green |
|--------|-------|-------|
| Sentences >20 words | <25% | ✅ |
| Transition words | ≥25% of sentences | ✅ |
| Passive voice | <10% of sentences | ✅ |

---

## Step 3 — Rewrite rules (apply ONLY violated rules)

### Sentence length (most common violation)
- Break at natural clause boundaries — full stop, not comma chain
- Target: 2–3 sentences per ~35-word paragraph

**Before (31 words):**
> Cardholders earn 0.75 Virgin Points per £1 on everyday spending, rising to 1.5 Virgin Points per £1 when booking directly with Virgin Atlantic or Virgin Holidays.

**After (two sentences):**
> Cardholders earn **0.75 Virgin Points per £1** on everyday spending. The rate doubles to **1.5 points per £1** on direct Virgin Atlantic and Virgin Holidays bookings.

### Transition words
- Target: at least 1 transition every 3–4 sentences, distributed across all sections
- Vary words — never repeat consecutively
- Preferred: Additionally, Moreover, Furthermore, However, Therefore, Consequently,
  In addition, As a result, In contrast, Also, This means, Meanwhile

### Passive voice
- Prefer active: "the card earns" not "points are earned"
- Idiomatic financial passives are acceptable: "cashback is credited", "fee is waived", "points are redeemable"
- Only rewrite if clearly avoidable

---

## Step 4 — Validate before publishing

```bash
bash /root/mgs-agent/skills/content-generate-rec/scripts/validate-article.sh /tmp/rewritten.html
```

Expected: `{"status": "PASS", "count": 450-500, "subtitle_chars": <=100}`

---

## Step 5 — Publish the update

```bash
curl -s -X POST "$WP_URL/wp-json/wp/v2/posts/<id>" \
  -u "$WP_USER:$WP_PASS" \
  -H "Content-Type: application/json" \
  -d "{\"content\": $(python3 -c "import json,sys; print(json.dumps(open('/tmp/rewritten.html').read()))")}"
```

Verify response includes `"status":"publish"` and a new `"modified"` timestamp.

---

## Step 6 — Re-score

```bash
bash /root/mgs-agent/skills/content-generate-rec/scripts/yoast-score-post.sh <site_key> <post_id>
```

Expected: `readability_score >= 71` (green). If still yellow/red, re-diagnose.

---

## Pitfalls

- **LazyBlocks MUST be preserved exactly** — never alter `<!-- wp:lazyblock/... /-->` blocks or their JSON. Only rewrite `<!-- wp:paragraph -->` and `<!-- wp:heading -->` blocks.
- **Subtitle ≤ 100 chars hard limit** — count: `python3 -c "print(len('your text.'))"`
- **Word count must stay 450–500** — validate after every rewrite
- **Table content counts toward word count** — budget the Comparative Table paragraphs
- **Yoast scores reset to notAnalyzed after REST update** — always run `yoast-score-post.sh` after updating

---

## Example outcome (Virgin Atlantic Reward REC, post 62013, eggbev)

| Metric | Before | After |
|--------|--------|-------|
| Sentences >20 words | 82% 🔴 | 6% ✅ |
| Transition words | 0 🔴 | 12 (39%) ✅ |
| Readability score | 🔴 | 🟢 90 |
| SEO score | — | 🟢 79 |

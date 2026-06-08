# REC/P1 cross-corpus boilerplate audit — 2026-05-28

## Trigger

Rodolfo flagged that the latest REC+P1 output was editorially poor because it repeated whole phrases from earlier articles. The investigation used the RBS Reward Black Credit Card run on Eggbev as the concrete case.

## Finding

The issue was not caused by Hermes v15. It came from the REC/P1 runner design, especially the P1 path.

Observed duplication against recent `gb-cc-en` Eggbev posts:

```text
Target P1                         Duplicate exact sentences
--------------------------------- --------------------------------
RBS Reward Black vs HSBC Rewards  25
RBS Reward Black vs NatWest       21
RBS Reward Black vs Nationwide    21
RBS Reward Black vs several P1s   16-17 each
```

Examples of repeated full sentences:

```text
If the official page shows different fees, APR, transfer terms or reward rules from what you expected, pause and reassess before submitting personal information.

Also consider how the card would fit alongside any existing borrowing, because multiple credit products can affect affordability and future applications.

Keep the official page open while applying so you can confirm the latest rates, exclusions and reward conditions before submitting personal information.

Finally, compare the same product against at least one alternative so the fee, reward structure and repayment terms are easier to judge.

The value is not about chasing perks.
```

## Root cause

`/root/mgs-agent/scripts/mgs-p1-runner.py` had deterministic copy blocks that were too rigid:

- `generate_p1_body()` assembled most of the P1 from fixed paragraphs and category buckets.
- `infer_p1_positioning()` used broad reusable buckets such as travel/reward and balance-transfer.
- `fit_word_count()` padded to the minimum word count with fixed filler sentences.
- `qa-content-validator.py` compared P1 against the paired REC but did not block reuse against prior published posts.

This made the flow safe against invention but weak against scaled editorial sameness.

## Durable rule

For REC/P1 production, especially P1:

1. Do not use fixed filler sentences to hit a word-count target.
2. If the article is short, add card-specific sections from current official facts or accept a shorter P1 if the contract allows it.
3. Add cross-corpus duplicate QA against recent same-vertical posts before publish.
4. Block when full sentences or high n-gram overlap repeat across unrelated articles, except for unavoidable UI/legal microcopy.
5. Treat `semantic QA OK` as insufficient unless it includes cross-corpus repetition checks.
6. Repetition against prior articles is a production blocker even when Yoast, word count, public links and REC↔P1 similarity pass.

## Recommended implementation pattern

Cross-corpus QA should fetch or load recent same-vertical posts, normalize visible article body, then compute:

- exact repeated sentences with minimum 7 words;
- 8- or 10-gram overlap after stripping HTML/LazyBlock/UI artifacts;
- separate thresholds for P1 and REC;
- allowlist for unavoidable UI copy such as button labels.

Blocking guidance:

```text
Condition                                      Status
---------------------------------------------- ------
>= 5 exact body sentences reused from one post BLOCK
>= 10 exact body sentences reused total        BLOCK
High 10-gram overlap with one same-type post   BLOCK/WARN by threshold
Only repeated button/UI phrases                ignore or WARN only
```

## Editorial interpretation

Rodolfo's correction means the runner must optimize for both:

- factual safety/no invention; and
- fresh article-level writing at scale.

Do not solve this by loosening source-of-truth rules. Solve it by removing deterministic filler, generating fact-specific prose, and enforcing cross-corpus duplication gates.

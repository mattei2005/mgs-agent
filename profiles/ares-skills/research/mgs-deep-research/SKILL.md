---
name: mgs-deep-research
description: "Use when MGS agents need deep external web research."
version: 1.0.0
author: MGS Digital Corp
license: Proprietary
metadata:
  hermes:
    tags: [research, perplexity, web-search, citations, mgs]
---

# MGS Deep Research

## Purpose

Provide one cross-agent method for deep, current, regulatory, competitive, or high-impact external research. Perplexity improves source discovery; it does not replace the Hermes model that reasons and writes the conclusion.

## Routing

- **Simple lookup or known URL:** use normal `web_search` and `web_extract`; do not spend Perplexity credits unnecessarily.
- **Deep/current/regulatory/competitive research:** compare Perplexity Search API against the free Hermes route with identical queries and limits.
- **Internal MGS state:** query the canonical dashboard, API, database, Sheet, logs, or MGS OS source instead of public web research.

Domain ownership remains unchanged:

- Zeus: executive, technical, regulatory, vendor and cross-area research.
- Atena: issuer, card, editorial and SEO source research; no publishing side effect from this skill.
- Ares: campaign, creative, competitor, platform and acquisition research; no campaign/budget write from this skill.

## Deep-research procedure

1. State the research question, current date, countries, decision to support, and source classes required.
2. Decompose it into 3–5 precise subqueries. Use the same strings and the same `--limit` for both backends.
3. Run the shared harness with the current profile:

```text
/root/mgs-agent/scripts/run-hermes-web-backend-benchmark.sh \
  --profile <zeus|atena|ares> \
  --output /root/.hermes/profiles/<profile>/cache/research/<slug>.json \
  --limit 10 \
  --query '<query 1>' \
  --query '<query 2>'
```

4. Preserve the raw result artifact. Deduplicate exact URLs and canonical equivalents that differ only by locale, tracking parameters, `.md`, or a trailing slash; preserve country-selecting parameters when they change policy content.
5. Compare at minimum: initial success/failure, retry outcome, total and canonical-unique URLs, primary/official sources, top-3 relevance, latency, overlap, and estimated Perplexity request cost.
6. Extract the strongest primary sources with the normal `web_extract` backend so both search methods are judged against the same page content. Escalate to browser only for JS/login/WAF pages; never substitute snippets for a required full-source read.
7. Cross-check every material claim against the extracted primary source. Third-party pages are discovery aids, not authority when an official source exists.
8. Produce one synthesis that separates: confirmed finding, source, operational implication, unresolved country/account-level gap, and recommendation.

## Failure recovery

A single `web_search` or `web_extract` failure triggers immediate diagnosis, safe correction/failover, exact-query retry, and real validation of both search and extraction. Preserve the first failure in benchmark metrics; a successful retry is recovery, not retroactive initial success.

After five failures of the same tool, or earlier on a loop, stop and escalate. Never auto-create credentials, change billing, expand budget, perform Critical Subset work, or restart the current gateway.

## Perplexity and secret safety

- Use the official Hermes `plugins/web/perplexity` provider and Search API; do not scaffold a parallel SDK/demo integration.
- Resolve `PERPLEXITY_API_KEY` only through each profile's Hermes 1Password mapping. Never print, log, attach, commit, or copy the value into a profile `.env`.
- Secret cache TTL remains `0`; the canonical wrapper is `/root/mgs-agent/scripts/mgs-op-with-service-account.sh`.
- Search API returns ranked results/snippets, not a synthesized answer. The Hermes model performs synthesis after source validation.
- Verify current official pricing before budget projections. Do not enable auto-reload or promote Perplexity to the default backend without Rodolfo's explicit decision.

## Current operating posture

- Normal defaults remain free; Perplexity is a deep-research canary/on-demand path.
- Initial MGS benchmark on 2026-09-05: Perplexity completed 8/8 initial queries, produced 25% more official canonical-unique sources, and had 35.99% lower observed mean latency; DDGS recovered its 1/8 initial failure on exact retry and remained useful for `site:` searches and contraprova.
- Report evidence lives under `/root/mgs-agent/reports/perplexity-search-ab-20260905/`.

## Completion checklist

- [ ] Identical queries and limits used for both backends
- [ ] Raw results preserved and canonical-deduplicated
- [ ] Primary sources extracted and cited
- [ ] Initial failures and retries reported honestly
- [ ] No secret value persisted or exposed
- [ ] Cost labeled measured from billing or estimated from successful requests
- [ ] Recommendation says where Perplexity adds value and where the free route remains sufficient

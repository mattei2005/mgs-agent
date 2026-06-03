# Honcho Targeted Rounds — 2026-06-02

Session learning from the first MGS Honcho managed evaluation beyond synthetic smoke tests.

## What was tested

Three manual rounds were run against workspace `mgs-agents` using 1Password-backed `HONCHO_API_KEY` and sanitized datasets:

```text
Round                         Items  Messages  Session
----------------------------  -----  --------  --------------------------------
Authorization                 31     32        mgs-sanitized-auth-spike-001
REC/P1 content / Atena        43     44        mgs-sanitized-content-spike-001
Hermes/gateway by agent       63     64        mgs-sanitized-gateway-spike-001
```

The SDK rejects `session.add_messages()` with more than 100 messages per call (`List should have at most 100 items`). Keep each batch at <=99 events plus one policy/context message, or chunk explicitly.

## Main outcome

Honcho performed best when the input was already domain-shaped and aggregated. It was weaker on raw gateway/log excerpts.

```text
Input shape                    Result
-----------------------------  ------------------------------------------------
Synthetic operational story    Good: produced correct hypothesis + uncertainty
Sanitized REC/P1 aggregates    Useful: identified real production bottleneck themes
Raw-ish authorization logs     Mixed: conflated security controls/config with auth state
Raw-ish gateway logs           Weak: did not reason well over per-agent aggregates
```

Durable rule: **feed Honcho deterministic operational aggregates, not raw logs, when evaluating production usefulness.**

## Useful deterministic content aggregates

For REC/P1/content, a simple deterministic pre-pass counted categories before ingestion. This helped Zeus validate Honcho output and is a better input shape for future briefings:

```text
Category                         Count in tail
--------------------------------  -------------
image_quality_or_lookup           67
runner_failures                   54
wordpress_publish_or_rest         53
provider_ttfb                     30
dependency_or_tooling             20
official_source_or_data           7
comparison_table_gate             3
yoast_quality_gate                1
```

Future runs should produce these aggregates first, then send concise category summaries + 2–4 sanitized examples per category.

## Secret-scan pitfall discovered

Sanitized logs can still contain placeholder-looking strings such as `OP_SERVICE_ACCOUNT_TOKEN=***`. A naive scanner matching `(token|password|secret)=\S+` will block these even though no real secret is present. Prefer to normalize all credential-field names to a neutral placeholder before scanning, e.g. `[REDACTED_CREDENTIAL_FIELD]`, so the scanner does not match the field name itself.

Still abort on real patterns such as:

- `hch-v3-*`
- `sk-*`
- `ghp_*`
- `github_pat_*`
- `AKIA*`
- URLs with embedded credentials

## Querying pitfall

When asking Honcho about a specific just-ingested dataset, scope `.chat()` to the session when the SDK supports it. Unscoped chat may search global representation and miss the fresh batch or mix unrelated observations.

Preferred pattern:

```python
try:
    response = zeus.chat(query, target=target_peer, session=session.id)
except TypeError:
    response = zeus.chat(query, target=target_peer)
```

## Interpretation rule

Do not report Honcho output alone as operational truth. Final report should separate:

```text
Honcho hypothesis              Zeus canonical validation
-----------------------------  --------------------------------------------
pattern suggested              confirmed / plausible / false-positive / control working
```

In this run, Honcho's REC/P1 bottleneck output was useful, but gateway risk ranking was not. Zeus should rely on deterministic aggregates for gateway risk until the prompt/input shape is improved.

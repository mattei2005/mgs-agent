---
name: hermes-web-tooling
description: Inspect, configure, and benchmark Hermes Agent native web search/extract tooling as an alternative to browser automation. Covers web_search/web_extract, provider backends, MCP checks, toolset inspection for Zeus/Atena, and MGS-specific evaluation for Atena image/source search.
tags:
  - hermes
  - web-search
  - web-extract
  - toolsets
  - mcp
  - atena
  - zeus
---

# Hermes Web Tooling

Use this skill when Rodolfo asks about Hermes Agent web/search/fetch capabilities, alternatives to Playwright/browser automation, MCP search servers, native toolsets, web provider setup, or benchmarking search providers for MGS agents.

## Operating stance

- Ground answers in the live Hermes install and profile configs; do not answer from memory.
- Use concise executive output: answer the numbered questions first, then give the operational recommendation.
- Do not expose API keys or tokens. Report only provider names and whether env vars/config values are set.
- Distinguish clearly between:
  - toolset enabled in Hermes;
  - provider/backend configured;
  - provider actually usable.
- Avoid hard negative claims like “Hermes cannot do web search.” Say whether this install has it configured and what setup is missing.

## Core facts to verify

Hermes native web tooling is normally exposed through the `web` toolset:

- `web_search` — search results/metadata: URLs, titles, descriptions.
- `web_extract` — fetch/extract content from specific URLs without full browser automation; may use LLM processing/summarization depending on config.

Provider support varies by installed Hermes version. Inspect the live code/config before claiming availability.

## Discovery workflow

1. Read the project master instructions if working inside MGS:
   - `/root/mgs-agent/AGENT.md`

2. Load/inspect Hermes CLI help for exact commands:
   - `hermes tools --help`
   - `hermes mcp --help`
   - `hermes version`

3. List active toolsets per profile:
   - `hermes -p zeus tools list`
   - `hermes -p atena tools list`

   Pitfall: `hermes -p <profile> toolsets list` is not the current command shape; the correct command is `tools list`.

4. Check configured MCP servers:
   - `hermes -p zeus mcp list`
   - `hermes -p atena mcp list`

5. Check relevant skills, if asked:
   - `hermes -p zeus skills list 2>&1 | grep -iE "search|fetch|web|browse" || true`
   - `hermes -p atena skills list 2>&1 | grep -iE "search|fetch|web|browse" || true`

6. Inspect profile config without leaking secrets:
   - `/root/.hermes/profiles/zeus/config.yaml`
   - `/root/.hermes/profiles/atena/config.yaml`

   Fields to look for:
   - `toolsets:`
   - `agent.disabled_toolsets:`
   - `web.backend:`
   - `web.search_backend:`
   - `web.extract_backend:`

7. Inspect live backend availability safely. Do not print env var values; print only set/unset and lengths if necessary.

## Provider matrix to validate against live code

The Hermes v0.14.0-era code supports provider plugins like these, but exact availability should be checked in the live checkout:

```text
Provider       Search   Extract/fetch   Typical requirement
───────────── ──────── ─────────────── ───────────────────────────
Firecrawl      yes      yes             FIRECRAWL_API_KEY or Nous gateway
Parallel       yes      yes             PARALLEL_API_KEY
Tavily         yes      yes             TAVILY_API_KEY
Exa            yes      yes             EXA_API_KEY
SearXNG        yes      no              SEARXNG_URL
Brave-free     yes      no              BRAVE_SEARCH_API_KEY
DDGS           yes      no              ddgs Python package installed
```

Search-only providers can replace browser-based search result discovery, but they cannot replace URL content extraction by themselves. Pair them with `web_extract`, direct Python/curl fetch, or browser automation depending on the target page.

## MGS Brave Search API workflow

When Rodolfo says the Brave key is in 1Password, verify the item shape before testing. Current known MGS item:

```text
Vault default        ${OP_DEFAULT_VAULT:-MGS Conteúdo}
Item                 Brave Search API - MGS
Field label          api key
Required op flag     --reveal
```

Pitfalls:

- `--fields api_key` is wrong for the current item; use `--fields "api key"`.
- Without `--reveal`, 1Password returns a placeholder string, not the secret. Brave will reject it as `SUBSCRIPTION_TOKEN_INVALID`.
- Do not print the key. Report item/vault/field and `len=N` only.
- Directly importing `tools.web_tools.web_search_tool()` from Python may not initialize Hermes plugin providers. Validate provider behavior with a real `hermes -p <profile> -z ...` invocation when testing agent runtime behavior.

Quick deterministic probe:

```bash
bash /root/.hermes/profiles/zeus/skills/ops/hermes-web-tooling/scripts/test-brave-search-mgs.sh \
  "AIB Visa Gold credit card UK official"
```

Temporary Hermes runtime test:

```bash
cd /root/mgs-agent
set -a; [ -f .env ] && source .env; set +a
KEY="$(op item get "Brave Search API - MGS" --vault "${OP_DEFAULT_VAULT:-MGS Conteúdo}" --fields "api key" --reveal)"
BRAVE_SEARCH_API_KEY="$KEY" hermes -p atena -z "Teste web_search nativo: procure 'AIB Visa Gold credit card UK official' com no máximo 3 resultados e responda só os URLs encontrados."
```

Brave Images direct endpoint can be tested separately at `https://api.search.brave.com/res/v1/images/search`. Treat image results as candidates only; affiliate/competitor domains can rank above issuer domains.

See `references/brave-search-mgs-2026-05-17.md` for the session-specific command outputs and caveats.

## MGS recommendation pattern

For Atena image/source search alternatives to Playwright:

```text
Need                              Preferred path
──────────────────────────────── ─────────────────────────────────────
Official/source URL discovery      Hermes web_search + Brave first
Image candidate discovery          Brave Images API direct endpoint
Specific static URL fetch          Python/curl/direct HTTP where sufficient
Structured content extraction      web_extract with Firecrawl/Tavily/Exa/Parallel
JS-heavy pages / visual checks     Browser/Playwright remains appropriate
Fallback while benchmarking        Current Playwright Bing flow
```

For MGS, start with the cheapest stable native path before a $50/mo provider:

1. Configure/search-test Brave Search API if suitable.
2. Benchmark against current Playwright Bing flow.
3. If relevance is poor for financial/card queries, test Serper/SerpAPI externally or another Hermes-supported provider.
4. Keep Playwright Bing as fallback while it works.

## Reporting template

When Rodolfo asks a numbered technical question, answer in this order:

```text
Pergunta                                      Resposta
──────────────────────────────────────────── ─────────────────────────────
1. Tem web_search nativo?                    Sim/Não + tool name
2. Tem web_fetch nativo?                     Sim/Não + web_extract mapping
3. MCP de busca configurado?                 Sim/Não + profile results
4. Versão trouxe capability nova?            Versão + concise delta
5. Toolsets ativos Zeus/Atena                table below
```

Then provide:

- toolsets table for Zeus and Atena;
- backend availability table;
- direct recommendation;
- `Próximo passo pendente:` line naming the next concrete action.

## References

- `references/hermes-web-tooling-2026-05-17.md` — session-derived command outputs and provider conclusions from the MGS Hermes v0.14.0 inspection.
- `references/brave-search-mgs-2026-05-17.md` — Brave Search API 1Password item shape, direct API tests, Hermes runtime test, and Atena image-search caveats.
- `scripts/test-brave-search-mgs.sh` — deterministic Brave web-search probe using the MGS 1Password item without printing the key.
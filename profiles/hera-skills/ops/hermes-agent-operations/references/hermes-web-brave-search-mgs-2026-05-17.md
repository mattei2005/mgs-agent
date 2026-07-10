# Brave Search API on MGS Hermes — 2026-05-17

Session context: Rodolfo added a Brave Search API key to 1Password and asked Zeus to test it as an alternative to Playwright/Bing for Atena image/source search.

## 1Password item shape

Do not print the key. Retrieve only for use in env vars or request headers.

```bash
cd /root/mgs-agent
set -a; [ -f .env ] && source .env; set +a
op item get "Brave Search API - MGS" \
  --vault "${OP_DEFAULT_VAULT:-MGS Conteúdo}" \
  --fields "api key" \
  --reveal
```

Observed item details:

```text
Vault               MGS Conteúdo
Item                Brave Search API - MGS
Field label         api key
Field type          CONCEALED
Key length          31
```

Pitfalls:

- `--fields api_key` failed because the field label is `api key`.
- Without `--reveal`, `op` returns a placeholder text like `[use 'op item get ... --reveal]`, which Brave rejects as `SUBSCRIPTION_TOKEN_INVALID`.
- The command Rodolfo suggested used `--vault MGS`; in this environment the available vault was `MGS Conteúdo`. Prefer `${OP_DEFAULT_VAULT:-MGS Conteúdo}`.

## Direct Brave API tests that passed

Web search endpoint:

```bash
curl -sS 'https://api.search.brave.com/res/v1/web/search?q=AIB%20Visa%20Gold%20credit%20card%20UK%20official&count=5&country=GB&search_lang=en' \
  -H 'Accept: application/json' \
  -H "X-Subscription-Token: $BRAVE_SEARCH_API_KEY"
```

Good result set for `AIB Visa Gold credit card UK official` included:

```text
https://aibgb.co.uk/personal-banking/credit-cards/visa-gold-card
https://aibni.co.uk/our-products/credit-cards/gold-card
https://aibgb.co.uk/content/dam/gb/business/Documents/Personal-Banking/PersonalCreditCards/visa-gold-information-guide.pdf
```

Image search endpoint also passed:

```bash
curl -sS 'https://api.search.brave.com/res/v1/images/search?q=AIB%20Visa%20Gold%20credit%20card%20image&count=5&country=GB&search_lang=en' \
  -H 'Accept: application/json' \
  -H "X-Subscription-Token: $BRAVE_SEARCH_API_KEY"
```

Operational caveat: image results can include affiliates/competitors such as Finder or Memivi rather than the issuer. Use Brave Images for candidate discovery only; keep domain/dimension/dedupe validation before accepting card art.

## Hermes native web_search test that passed

Temporarily inject the key into the Hermes process:

```bash
BRAVE_SEARCH_API_KEY="$KEY" hermes -p atena -z \
  "Teste web_search nativo: procure 'AIB Visa Gold credit card UK official' com no máximo 3 resultados e responda só os URLs encontrados."
```

Both Zeus and Atena returned relevant AIB URLs when launched with `BRAVE_SEARCH_API_KEY` in the environment.

Important distinction:

- Direct Python import of `tools.web_tools.web_search_tool()` may not load plugin providers unless the Hermes runtime/plugin loader has initialized them.
- A real `hermes -p <profile> -z ...` invocation did load/use the Brave provider when `BRAVE_SEARCH_API_KEY` was present.

## Recommendation captured

For Atena:

```text
Step                         Recommended path
──────────────────────────── ─────────────────────────────────
Official/source URL search    Hermes web_search + Brave
Image candidate search        Brave Images API direct endpoint
Validation                    dimension + domain + dedupe filters
Fallback                      current Playwright Bing flow
```

Do not configure persistently without explicit scope approval if it changes service env files or agent startup config. For a benchmark, temporary env injection is enough.
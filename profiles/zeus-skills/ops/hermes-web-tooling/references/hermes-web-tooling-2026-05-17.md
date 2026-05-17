# Hermes web tooling inspection — 2026-05-17

Session context: Rodolfo asked whether Hermes Agent has native alternatives to Atena's Playwright/Bing image-search flow before paying for Serper/SerpAPI.

## Commands requested by Rodolfo

```bash
hermes -p zeus toolsets list 2>&1 || echo "tentar outro comando"
hermes -p atena toolsets list 2>&1 || true
hermes -p zeus skills list 2>&1 | grep -iE "search|fetch|web|browse" || true
hermes -p atena skills list 2>&1 | grep -iE "search|fetch|web|browse" || true
```

Observed: `toolsets list` is not a valid Hermes CLI subcommand. Correct command is `hermes -p <profile> tools list`.

## Live result summary

Hermes version checked:

```text
Hermes Agent v0.14.0 (2026.5.16)
Update available: 125 commits behind — run 'hermes update'
```

MCP status:

```text
Zeus:  No MCP servers configured.
Atena: No MCP servers configured.
```

Toolsets active in both Zeus and Atena:

```text
Toolset             Zeus    Atena
────────────────── ─────── ───────
web                enabled enabled
browser            enabled enabled
terminal           enabled enabled
file               enabled enabled
code_execution     enabled enabled
vision             enabled enabled
image_gen          enabled enabled
tts                enabled enabled
skills             enabled enabled
todo               enabled enabled
memory             enabled enabled
session_search     enabled enabled
clarify            enabled enabled
delegation         enabled enabled
cronjob            enabled enabled
messaging          enabled enabled
computer_use       enabled enabled

video              disabled disabled
video_gen          disabled disabled
x_search           disabled disabled
moa                disabled disabled
homeassistant      disabled disabled
spotify            disabled disabled
yuanbao            disabled disabled
```

Profile config highlights:

```text
Zeus:
  toolsets:
    - hermes-cli
  agent.disabled_toolsets: []
  web.backend: ''
  web.search_backend: ''
  web.extract_backend: ''

Atena:
  toolsets:
    - hermes-cli
  no explicit web backend found in visible config section
```

Backend availability probe returned all unconfigured/unavailable:

```text
backend firecrawl
search_backend firecrawl
extract_backend firecrawl
firecrawl available= False
parallel available= False
tavily available= False
exa available= False
searxng available= False
brave-free available= False
ddgs available= False
```

Relevant env vars were unset at the time of inspection:

```text
EXA_API_KEY unset
PARALLEL_API_KEY unset
TAVILY_API_KEY unset
FIRECRAWL_API_KEY unset
FIRECRAWL_API_URL unset
FIRECRAWL_GATEWAY_URL unset
TOOL_GATEWAY_DOMAIN unset
TOOL_GATEWAY_SCHEME unset
TOOL_GATEWAY_USER_TOKEN unset
SEARXNG_URL unset
BRAVE_SEARCH_API_KEY unset
```

Do not treat the above as a permanent fact; re-run probes in future sessions.

## Code-level evidence from Hermes v0.14.0 checkout

`toolsets.py` defines:

```python
"web": {
    "description": "Web research and content extraction tools",
    "tools": ["web_search", "web_extract"],
    "includes": []
}
```

`tools/web_tools.py` reported provider support/dispatch for:

```text
brave-free, ddgs, searxng, exa, parallel, tavily, firecrawl
```

`web_search_tool` returns search result metadata only: title, URL, description, position.

`web_extract_tool` extracts content from explicit URLs and has SSRF/secrets checks plus optional LLM processing.

## Operational conclusion from the session

Hermes has native web search/extract tooling, but in this MGS install the backend was not configured at the time of inspection. For Atena image search:

- Try Hermes `web_search` with Brave Search API before paying Serper/SerpAPI.
- Remember Brave-free is search-only; pair it with direct Python/curl fetch or a real `web_extract` backend for page content.
- Keep Playwright/Bing as fallback until benchmark proves the native path is faster and reliable.

## Answer shape that worked

Rodolfo wanted direct executive output, not generic docs. Useful response structure:

1. Answer each numbered question directly.
2. Show command corrections and live results.
3. Provide toolset table for Zeus/Atena.
4. Provide backend availability table.
5. Give the recommendation.
6. End with `Próximo passo pendente:` naming the concrete next action.

## 2. Web tooling nativo, search/extract e MCP

Use quando a pergunta envolver busca web, fetch/extract sem Playwright, MCP search servers, toolsets ativos, ou benchmark de providers para Atena/Zeus.

### Discovery workflow

```bash
# comandos e help atuais
hermes tools --help
hermes mcp --help
hermes --version

# toolsets e MCP por profile
hermes -p zeus tools list
hermes -p atena tools list
hermes -p zeus mcp list
hermes -p atena mcp list
```

Inspecionar configs sem vazar segredos:

- `/root/.hermes/profiles/zeus/config.yaml`
- `/root/.hermes/profiles/atena/config.yaml`

Campos relevantes: `toolsets`, `agent.disabled_toolsets`, `web.backend`, `web.search_backend`, `web.extract_backend`.

### Matriz de providers a validar no código vivo

| Provider | Search | Extract/fetch | Requisito típico |
|---|---:|---:|---|
| Firecrawl | sim | sim | `FIRECRAWL_API_KEY` ou gateway Nous |
| Parallel | sim | sim | `PARALLEL_API_KEY` |
| Tavily | sim | sim | `TAVILY_API_KEY` |
| Exa | sim | sim | `EXA_API_KEY` |
| SearXNG | sim | não | `SEARXNG_URL` |
| Brave-free | sim | não | `BRAVE_SEARCH_API_KEY` |
| DDGS | sim | não | pacote `ddgs` |

Providers só de search não substituem extração de conteúdo; combinar com `web_extract`, HTTP direto/Python/curl ou browser conforme a página.

### Brave Search MGS

Item conhecido no 1Password:

```text
Vault default: ${OP_DEFAULT_VAULT:-MGS Conteúdo}
Item: Brave Search API - MGS
Field label: api key
Required: --reveal
```

Pitfalls: `--fields api_key` está errado; usar `--fields "api key"`. Sem `--reveal`, 1Password retorna placeholder. Não imprimir a key.

Probe determinístico:

```bash
bash /root/.hermes/profiles/zeus/skills/ops/hermes-agent-operations/scripts/test-brave-search-mgs.sh \
  "AIB Visa Gold credit card UK official"
```

Ver detalhes: `references/hermes-web-brave-search-mgs-2026-05-17.md` e `references/hermes-web-tooling-2026-05-17.md`.

### Recomendação MGS padrão

| Necessidade | Caminho preferido |
|---|---|
| Descobrir URL oficial/source | `web_search` + Brave primeiro |
| Descobrir imagens candidatas | endpoint Brave Images direto |
| Fetch de URL estática | Python/curl/HTTP direto quando suficiente |
| Extração estruturada | `web_extract` com provider de extract |
| JS-heavy/visual | Browser/Playwright |
| Fallback durante benchmark | fluxo Playwright/Bing atual |

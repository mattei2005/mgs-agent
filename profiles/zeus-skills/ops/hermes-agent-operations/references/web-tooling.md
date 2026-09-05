# Hermes Web Tooling

> Extracted from the former monolithic `SKILL.md` on 2026-07-10. Load this file only when its branch is relevant.

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

### Autorrecuperação obrigatória de web

Para `web_search` e `web_extract`, uma única falha já dispara intervenção; esta regra específica reduz de três para uma ocorrência o limiar geral do Zeus:

1. capturar backend, erro exato e se a falha ocorreu em busca ou extração;
2. corrigir imediatamente quando for seguro e estiver dentro da autoridade vigente, incluindo instalar dependência opcional ausente, reparar configuração válida ou rotear para um backend gratuito já disponível;
3. repetir a operação original e validar separadamente `web_search` e `web_extract` por chamada real;
4. preservar o backend explícito validado e registrar mudanças de package/config em inventário, audit log e REPORT-INFRA;
5. se a causa for indisponibilidade externa, aplicar failover seguro e informar o risco residual em vez de declarar o fornecedor reparado;
6. nunca criar/alterar credencial, contratar serviço, mudar cobrança, executar Critical Subset ou reiniciar o próprio gateway automaticamente; escalar esses bloqueios com diagnóstico exato;
7. após cinco falhas consecutivas da mesma ferramenta, ou antes se houver loop, parar e escalar conforme o kernel geral.

Sucesso de uma chamada não prova disponibilidade permanente de fornecedor externo; reportar “funcional nos testes atuais” com a evidência real.

### Matriz de providers a validar no código vivo

| Provider | Search | Extract/fetch | Requisito típico |
|---|---:|---:|---|
| Firecrawl | sim | sim | `FIRECRAWL_API_KEY` ou gateway Nous |
| Parallel | sim | sim | `PARALLEL_API_KEY` |
| Tavily | sim | sim | `TAVILY_API_KEY` |
| Perplexity | sim | sim (snippets relevantes, não dump integral) | `PERPLEXITY_API_KEY` |
| Exa | sim | sim | `EXA_API_KEY` |
| SearXNG | sim | não | `SEARXNG_URL` |
| Brave-free | sim | não | `BRAVE_SEARCH_API_KEY` |
| DDGS | sim | não | pacote `ddgs` |

Providers só de search não substituem extração de conteúdo; combinar com `web_extract`, HTTP direto/Python/curl ou browser conforme a página.

### Perplexity Search API — canário MGS

- Provider nativo oficial do Hermes: `plugins/web/perplexity`; o runtime MGS v0.21 recebeu backport cirúrgico do upstream `f1ccf436a27522c1bb5d36383a6f13b950676338` em vez de absorver o delta divergente completo.
- A chave permanece no 1Password e entra no processo por `secrets.onepassword.env.PERPLEXITY_API_KEY`; nunca copiar ou imprimir o valor.
- Referências `op://` com nomes contendo espaços/acentos falharam no CLI atual. Usar IDs de vault/item/field e o wrapper `/root/mgs-agent/scripts/mgs-op-with-service-account.sh`, que autentica pelo ambiente canônico MGS sem duplicar o token bootstrap no profile.
- `secrets.onepassword.cache_ttl_seconds: 0` evita cache de valores secretos em disco.
- Backend padrão permanece `web.search_backend: ddgs` e `web.extract_backend: keenable`. Para pesquisa profunda comparativa, executar `/root/mgs-agent/scripts/benchmark-hermes-web-search-backends.py` com consultas idênticas e o mesmo limite; isso permite canário Perplexity sem trocar silenciosamente o padrão.
- Benchmark inicial de 2026-09-05: Perplexity teve 8/8 consultas sem falha, 25% mais fontes oficiais canônicas únicas e latência média 35,99% menor; DDGS manteve vantagem pontual em buscas `site:` da Meta e segue como fallback/contraprova.
- O provider Perplexity usa `search_context_size=low`; a síntese continua no modelo Hermes. Para fatos críticos, extrair a página oficial integralmente e validar o claim.
- Não promover Perplexity a padrão geral nem habilitar auto-reload/budget adicional sem decisão explícita de Rodolfo.

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

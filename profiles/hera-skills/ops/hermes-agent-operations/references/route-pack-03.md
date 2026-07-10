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
## 3. Providers, modelos e OpenAI Codex OAuth

Use quando Rodolfo quiser trocar provider de Zeus/Atena/Ares, usar GPT via assinatura ChatGPT, reduzir custo Anthropic/Claude, autenticar `openai-codex`, validar cron jobs após migração, ou auditar chamadas LLM pagas.

### Fatos essenciais

- Endpoint Codex: `https://chatgpt.com/backend-api/codex` (não `api.openai.com`).
- Auth: OAuth device-code via assinatura ChatGPT; tokens em `auth.json`.
- Billing Hermes: `openai-codex` deve aparecer como `subscription_included`/included, sem pay-per-token.
- Modelo MGS atual conhecido: `gpt-5.5` via plano ChatGPT.
- Política operacional MGS: zero Anthropic/Claude API pay-per-token por padrão, salvo autorização explícita de Rodolfo.

### Login inicial

```bash
hermes model
# selecionar openai-codex, abrir URL, inserir device code e autorizar
```

O login no perfil raiz atualiza `~/.hermes/auth.json`; profiles Zeus/Atena usam seus próprios `auth.json` e precisam receber as credenciais.

### Copiar credenciais para Zeus/Atena

```bash
python3 - <<'EOF'
import json
with open('/root/.hermes/auth.json') as f:
    root = json.load(f)
codex_creds = root['providers']['openai-codex']
for profile in ['zeus', 'atena']:
    path = f'/root/.hermes/profiles/{profile}/auth.json'
    with open(path) as f:
        d = json.load(f)
    d['providers']['openai-codex'] = codex_creds
    d['active_provider'] = 'openai-codex'
    with open(path, 'w') as f:
        json.dump(d, f, indent=2)
    print(f'{profile}: OK')
EOF
```

Formato esperado em cada `config.yaml`:

```yaml
model:
  default: gpt-5.5
  provider: openai-codex
  base_url: 'https://chatgpt.com/backend-api/codex'
```

### Verificação sem vazar tokens

```bash
python3 - <<'EOF'
import json
for path in ['/root/.hermes/auth.json', '/root/.hermes/profiles/zeus/auth.json', '/root/.hermes/profiles/atena/auth.json']:
    print(path)
    with open(path) as f:
        d=json.load(f)
    p=d.get('providers',{}).get('openai-codex',{})
    tokens=p.get('tokens',{}) if isinstance(p,dict) else {}
    print('  active_provider:', d.get('active_provider'))
    print('  auth_mode:', p.get('auth_mode') if isinstance(p,dict) else None)
    print('  access_token_len:', len(tokens.get('access_token','')))
    print('  refresh_token_present:', bool(tokens.get('refresh_token')))
EOF

grep "provider:\|default:" /root/.hermes/profiles/zeus/config.yaml /root/.hermes/profiles/atena/config.yaml | grep -v "auto\|haiku\|edge\|local"
```

### Cron jobs e custo após migração

- Cron agent-based sem override herda provider/model do perfil. Após migração para Codex, jobs com `model/provider: null` passam a herdar `openai-codex` + `gpt-5.5`.
- Preferir `script` + `no_agent: true` para watchdogs determinísticos.
- Antes de reativar cron antigo, auditar model/provider e evitar fallback Anthropic acidental.
- Procurar `ANTHROPIC_API_KEY`, `api.anthropic.com`, `anthropic.Anthropic`, `claude-*`, `provider: anthropic` em serviços/repos ativos.

Referências: `references/openai-codex-cron-model-pinning.md`, `references/openai-codex-anthropic-api-decommission.md`, `references/openai-codex-cost-monitoring-gpt-oauth.md`.

### Purge total Anthropic/Claude quando Rodolfo exigir GPT-5.5 para tudo

Quando Rodolfo disser “GPT-5.5 pra tudo”, “zero Anthropic”, “deleta de tudo” ou equivalente, usar o playbook `references/openai-codex-gpt55-all-profiles-purge.md`. Regra operacional: depois de confirmação crítica, limpar **root + profiles + backups/snapshots**, não só `config.yaml`. Validar `providers.anthropic=false`, `credential_pool.anthropic=false`, `active_provider=openai-codex`, auxiliares pinados em `openai-codex/gpt-5.5`, scan de `sk-ant-*` real igual a zero fora do código-fonte/testes/docs upstream, e gateways reconectados.

### Imagem criativa com OpenAI/GPT-5.5

Quando Rodolfo pedir que a Hera use GPT-5.5/ChatGPT para criativos visuais, separar duas camadas:

```text
Camada                       Verificação
───────────────────────────  ─────────────────────────────────────────
Modelo principal do agente    `model.default: gpt-5.5`, `provider: openai-codex`, auth ChatGPT presente.
Backend de imagem             Tool `image_gen` habilitada e provider de imagem apontando para OpenAI/GPT Image ou equivalente.
```

Se o modelo principal já estiver em `openai-codex/gpt-5.5`, mas a imagem falhar por credencial/backend visual, não dizer que “GPT-5.5 não está configurado”. O correto é: GPT-5.5 está ok para brief/copy/direção; falta configurar **geração visual**.

Resposta operacional recomendada:

```text
Necessário
──────────
OPENAI_API_KEY ou provider visual OpenAI equivalente no Hermes
Image Generation apontando para OpenAI/GPT Image, não para FAL quando a meta for qualidade ChatGPT
Restart/reload do profile/gateway afetado após config
Smoke test com 1 imagem simples antes de prometer produção final
```

Não imprimir chaves. Se a ferramenta cair para FAL por padrão e a qualidade desejada for ChatGPT, orientar a troca do backend em vez de aceitar fallback visual inferior.

### Pitfalls de provider/OAuth

- `hermes model --status` não existe; verificar config/auth diretamente.
- Endpoint Codex não lista modelos via API (`/codex/models` pode retornar 400; `/backend-api/models` 403).
- Token expira; refresh deve ser automático, mas falhas exigem novo `hermes model` e recópia para profiles.
- Não manter Claude/Haiku como fallback silencioso após decisão de custo.
- Quando limpar Anthropic/Claude, remover também `credential_pool.anthropic`, root `~/.hermes/auth.json`, root `~/.hermes/.env`, snapshots/backups com credenciais e espelhos versionados em `/root/mgs-agent/profiles/`; só limpar `providers.anthropic` nos profiles é insuficiente.
- Alguns serviços fora do gateway podem continuar chamando Anthropic mesmo depois de migrar Zeus/Atena/Ares.
- OpenHands “funcionando” não basta: se wrapper/trajectory usa `anthropic/claude-*` + API key 1Password, isso é uma falha de custo/governança salvo autorização explícita de Rodolfo. Diagnóstico canônico: `references/atena-openhands-provider-diagnostic.md`.
- Para OpenHands na Atena/Zeus, a política correta é **GPT-5.5/OpenAI-Codex OAuth para tudo por padrão**. Não sugerir “backend não-Anthropic aprovado” genérico, OpenRouter, Haiku ou Claude como workaround. Se OpenHands precisar de compatibilidade com Codex, forçar `openai/gpt-5.5`, usar OAuth do profile sem imprimir token e validar o modelo real no output. Playbook: `references/openhands-gpt55-codex-wrapper.md`.

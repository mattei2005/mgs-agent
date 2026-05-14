# Playwright Local — Install & Usage Notes

## Contexto

`mcp_browser_navigate` usa **Browserbase** (browser cloud remoto).
Playwright local roda diretamente na máquina via `python3` — IPs diferentes, comportamento diferente.

**Quando usar Playwright local em vez de `mcp_browser_navigate`:**
- Bing Images / sites que não bloqueiam IP do servidor mas bloqueiam Browserbase
- Quando você precisa do atributo `m` dos links do Bing (contém `murl` = URL original da imagem)
- Qualquer tarefa que não precise de proxy residencial e onde Browserbase falha por bot-detection

## Instalação no servidor MGS

Python 3.12 está em `/usr/bin/python3`. O `pip` não está no PATH mas o wheel existe:

```bash
# 1. Extrair pip do wheel (só na primeira vez)
cd /tmp && python3 -c "import zipfile; z=zipfile.ZipFile('/usr/share/python-wheels/pip-24.0-py3-none-any.whl'); z.extractall('pip_extracted')"

# 2. Instalar playwright
python3 /tmp/pip_extracted/pip install playwright --break-system-packages -q

# 3. Instalar browser (chromium headless shell, ~112MB)
python3 -m playwright install chromium
# Instala em: /root/.hermes/profiles/atena/home/.cache/ms-playwright/chromium_headless_shell-1217

# 4. Verificar
python3 -c "from playwright.sync_api import sync_playwright; print('ok')"
```

**Notas:**
- `pip3` não existe como comando direto — usar `python3 /tmp/pip_extracted/pip`
- `--break-system-packages` é necessário pois o ambiente é "externally-managed"
- Playwright fica em `/usr/local/lib/python3.12/dist-packages/playwright/`
- `execute_code` tool NÃO tem acesso ao playwright instalado (usa env diferente) — usar `mcp_terminal` com heredoc `python3 - <<'EOF' ... EOF`

## Uso básico (Bing Images)

```python
# Rodar via: python3 - <<'EOF' ... EOF  (não execute_code)
from playwright.sync_api import sync_playwright
import json, time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        locale="en-GB",
        viewport={"width": 1280, "height": 900}
    )
    page = context.new_page()
    page.goto("https://www.bing.com/images/search?q=<query>&qft=+filterui:imagesize-large", timeout=30000)
    time.sleep(3)

    # Extrair URLs originais via atributo 'm' dos links .iusc
    items = page.query_selector_all('a.iusc')
    for item in items[:20]:
        m_attr = item.get_attribute('m')
        if m_attr:
            data = json.loads(m_attr)
            murl = data.get('murl', '')
            desc = data.get('t', '')[:80]
            print(f"{desc}\n{murl}\n")
    browser.close()
```

## Sites geo-bloqueados (IP não-UK)

Mesmo Playwright local é bloqueado quando o site rejeita IPs não-UK:
- `lloydsbank.com` → Error 1007 (geolocalização, não bot-detection)
- Solução: usar Bing Images como fonte alternativa da card image

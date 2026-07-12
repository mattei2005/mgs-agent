# Sessão — provider padrão, variação real de vídeo e OAuth Grok/xAI

Use esta referência quando o Ares receber pedidos de variação de criativo/vídeo ou precisar alternar GPT/OpenAI e Grok/xAI.

## Correções operacionais capturadas

### 1. Provider padrão

Quando o solicitante não especificar ferramenta, a criação deve seguir **GPT/OpenAI/ChatGPT como padrão**.

```text
Pedido sem provider explícito      GPT/OpenAI
Pedido “com GPT”                   GPT/OpenAI
Pedido “com Grok”                  Grok/xAI
Pedido “os dois / compara”         gerar/validar ambos ou reportar provider bloqueado
```

Não escolher Grok por conta própria para vídeo/avatar se o usuário não pediu Grok. Se Grok for usado como fallback, rotular claramente e pedir/autorização quando isso muda o resultado esperado.

### 2. Variação de vídeo não é overlay

Se o pedido for “faça uma variação desse criativo/vídeo” e o usuário pedir ou implicar recriação, não entregue apenas o mesmo vídeo com legenda em cima.

Checklist mínimo para variação real:

```text
Dimensão                           Deve mudar quando for recriação
─────────────────────────────────  ─────────────────────────────────────────
Pessoa/apresentador                novo rosto/persona quando pedido
Cenário                            novo ambiente quando pedido
Voz/narração                       nova voz quando pedido
Cenas/enquadramentos               não reaproveitar literalmente o vídeo inteiro
Oferta/gatilhos                    manter fiel ao briefing
Produto/carro                      preservar tipo/cor/modelo aproximado quando pedido
```

Se por limitação de backend o resultado for slideshow, imagem animada ou motion leve, entregar como **preview**, não como vídeo final profissional.

### 3. Autenticação Grok/xAI em Discord/headless

Fluxo limpo:

```bash
HERMES_HOME=/root/.hermes/profiles/ares hermes auth add xai-oauth --manual-paste
```

Regras:

- Em thread Discord, não usar `watch_patterns` para `Callback URL:` porque isso despeja aviso técnico na thread.
- Rodar o processo e extrair internamente o link de autorização.
- Responder ao usuário apenas com o link limpo e instrução objetiva: abrir, autorizar, enviar URL/código retornado.
- Ao receber o código/URL, enviar no stdin do processo aberto e aguardar término.
- Validar com uma chamada real ao wrapper antes de dizer que Grok está autenticado.

### 4. Wrapper Grok/xAI e venv Hermes

O wrapper `/root/mgs-agent/scripts/mgs-grok-generate.py` depende de módulos do Hermes Agent. Se rodar com Python do sistema pode não resolver `httpx`/runtime auth e parecer sem credencial mesmo após OAuth salvo.

Fix aplicado no wrapper:

```text
shebang: /root/.hermes/hermes-agent/venv/bin/python3
```

Validação esperada após autenticação:

```bash
/root/mgs-agent/scripts/mgs-grok-generate.py image \
  --profile ares \
  --output-dir /tmp/grok-auth-test \
  --aspect-ratio 9:16 \
  --resolution 1k \
  --timeout 180 \
  --prompt 'Tiny auth test image: a simple clean white circle on dark blue background, no text.'
```

Resultado válido deve indicar `provider: xai-oauth` e retornar um `path` local.

## Pitfall principal

Não confundir “pedido de variação” com “trocar texto no asset original”. Quando houver crítica de qualidade como “ficou só legenda”, corrigir a abordagem para recriação real e registrar a diferença no handoff.
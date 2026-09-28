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
hermes -p ares auth add xai-oauth --type oauth --no-browser
```

Regras:

- Em thread Discord, não usar notificações automáticas/watch patterns porque isso despeja output técnico na thread.
- Rodar o processo e extrair internamente o link de autorização.
- Responder ao usuário apenas com o link clicável e o código device-code; a CLI faz polling até a aprovação.
- Fazer readback do `auth.json` sem imprimir valores e validar com uma chamada real antes de dizer que Grok está autenticado.
- No Hermes v0.21.5, `auth add` pode imprimir sucesso sem persistir a primeira credencial xAI de um named profile. Se access/refresh continuarem ausentes, usar o login device-code profile-scoped com `_save_xai_oauth_tokens(..., set_active=False)` no checkout/venv ativo; nunca copiar tokens entre agentes nem mudar o GPT padrão.

### 4. Wrapper Grok/xAI e venv Hermes

O wrapper `/root/mgs-agent/scripts/mgs-grok-generate.py` depende de módulos do Hermes Agent. Ele resolve o executável `hermes` ativo, reexecuta no mesmo venv e adiciona o checkout correspondente ao `sys.path`; isso evita caminhos fixos quebrarem após updates/cutovers.

Bootstrap aplicado no wrapper:

```text
shebang portátil + resolução do checkout/venv por `command -v hermes`
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
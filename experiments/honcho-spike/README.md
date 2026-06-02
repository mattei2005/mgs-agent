# Honcho Spike — MGS

Sandbox para testar Honcho como camada de conclusões/contexto, sem dados reais sensíveis.

## Política

- Não enviar credenciais, senhas, tokens, application passwords ou dados operacionais brutos.
- Usar apenas dados sintéticos ou logs sanitizados.
- Honcho não é fonte de verdade; ele gera hipóteses/conclusões.
- Zeus valida qualquer conclusão contra fontes canônicas antes de agir/reportar.

## Managed API

1. Criar API key em https://app.honcho.dev/api-keys
2. Exportar localmente, sem colar no chat:

```bash
export HONCHO_API_KEY='...'
```

3. Rodar:

```bash
uv run python honcho_smoke.py
```

## Self-host

Ainda não configurado neste VPS porque Docker não está instalado. Requer aprovação separada para instalar Docker/Postgres/Redis ou rodar em host isolado.

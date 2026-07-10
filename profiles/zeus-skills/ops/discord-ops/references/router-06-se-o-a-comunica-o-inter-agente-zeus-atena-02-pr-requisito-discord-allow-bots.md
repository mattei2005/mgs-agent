### Pré-requisito: DISCORD_ALLOW_BOTS

Por padrão o Hermes **ignora mensagens de bots silenciosamente**:

```bash
# No .env do agente DESTINO (ex: Atena)
DISCORD_ALLOW_BOTS=mentions   # aceita bots apenas se @mencionado (recomendado)
DISCORD_ALLOW_BOTS=all        # aceita qualquer bot (não recomendado)
```

Após editar o `.env`, **reiniciar o agente destino** para carregar a variável.


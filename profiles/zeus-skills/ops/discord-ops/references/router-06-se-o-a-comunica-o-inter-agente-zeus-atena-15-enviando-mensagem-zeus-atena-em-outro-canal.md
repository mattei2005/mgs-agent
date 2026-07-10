### Enviando mensagem Zeus → Atena em outro canal

Para comunicação **cross-channel** Zeus → Atena, incluir `<@BOT_ID>` porque Atena usa `DISCORD_ALLOW_BOTS=mentions`:

```python
send_message(
    message="<@1496306920494202950> Atena, aqui é o Zeus. [pergunta]",
    target="discord:1496267571543019653"
)
```

Sem o user mention do bot Atena, Atena ignora silenciosamente.

Em thread compartilhada, não usar esse padrão automaticamente; só acionar Atena com mention se Rodolfo pedir explicitamente.


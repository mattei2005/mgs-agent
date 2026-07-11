# Discord tool progress — política MGS atual

## Estado canônico

A experiência de live tool-call trace foi testada no passado, mas está desativada na MGS. O padrão obrigatório atual é não publicar breadcrumbs de ferramentas no Discord:

- `display.tool_progress: 'off'`
- `display.platforms.discord.tool_progress: 'off'`
- manter ambos como string YAML entre aspas; `off` sem aspas vira booleano `false` e pode acionar fallback incorreto;
- só reativar `all` após autorização explícita do Rodolfo.

A mensagem `Queued for the next turn...` é separada: vem de `busy_input_mode: steer` quando uma mensagem chega durante um turno ativo. Ela não é controlada por `tool_progress`.

## Diagnóstico

1. Ler os valores efetivos nos quatro profiles e nos mirrors versionados.
2. Conferir tanto o valor global quanto o override `display.platforms.discord`; o override por plataforma vence.
3. Verificar o tipo carregado pelo YAML: o valor correto é a string `off`, não o booleano `false`.
4. Após qualquer mudança, reiniciar gateways pelo finalizador seguro e validar o canal real sem expor trace bruto.

## Config por profile

Padrão MGS obrigatório:

```yaml
display:
  tool_progress: 'off'
  platforms:
    discord:
      tool_progress: 'off'
      cleanup_progress: true
      interim_assistant_messages: false
      long_running_notifications: true
      busy_ack_detail: false
```

Aplicar nos profiles ativos e mirrors versionados de Zeus, Atena, Ares e Hera. Não reutilizar a configuração histórica `tool_progress: all` como padrão.

## Validação

- parser YAML retorna `str` com valor `off` nos dois níveis;
- live e mirror são idênticos;
- gateways ativos após restart seguro, Zeus por último;
- smoke real no Discord não cria mensagem acumulada de `Reading`, `terminal`, `Updating skill` ou comandos;
- mensagens enviadas durante turno ativo ainda podem receber o ACK de fila por causa de `busy_input_mode: steer`; avaliar essa UX separadamente.

## Pitfalls

- Alterar somente o global não funciona quando o override Discord continua em `all`.
- `off` sem aspas pode virar `False` no YAML e cair em fallback.
- `cleanup_progress: true` não substitui `tool_progress: 'off'`; cleanup atua depois que breadcrumbs já foram publicados.
- Desabilitar tool progress reduz ruído visível, mas não remove do contexto interno as tool calls necessárias ao raciocínio.
- Não reiniciar gateways na cadeia ativa; usar finalizador externo e reiniciar Zeus por último.

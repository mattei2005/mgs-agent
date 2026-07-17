# MGS Discord tool progress toggle — 2026-07-05

## Contexto

Rodolfo perguntou por que o progresso linha-a-linha das tool calls não aparecia mais no Discord. A investigação mostrou que Zeus havia desligado `display.platforms.discord.tool_progress` em 2026-06-30 por decisão operacional própria após reclamação de ruído/travamento. Rodolfo esclareceu que queria o comportamento antigo de volta para todos os agentes.

## Regra operacional aprendida

Não interpretar reclamações genéricas de ruído/travamento no Discord como autorização permanente para desligar tool progress. Se a intenção do Rodolfo for ambígua, reportar a causa e perguntar antes de mudar uma preferência visual global.

## Config para religar progresso ao vivo

Aplicar nos profiles vivos e mirrors versionados de Zeus/Atena/Ares/agente legado:

```yaml
display:
  tool_progress: 'all'
  tool_preview_length: 40
  tool_progress_grouping: accumulate
  platforms:
    discord:
      tool_progress: 'all'
      tool_preview_length: 40
      cleanup_progress: true
```

`cleanup_progress: true` deve permanecer ligado para preservar o comportamento antigo: aparece durante a execução e some depois da resposta final.

## Validação

Validar com `gateway.display_config.resolve_display_setting(config, 'discord', key)` para cada profile:

- `tool_progress == 'all'`
- `tool_preview_length == 40`
- `cleanup_progress == True`

Também validar que os gateways estão ativos.

## Restart

Normalmente **não precisa reiniciar gateways** para essa mudança. O código vivo do Hermes resolve `tool_progress` a partir do config no início de cada novo turno/mensagem no gateway. A mudança deve valer na próxima interação com tool calls.

Se a próxima tool call ainda não mostrar progresso, aí fazer restart leve/seguro dos gateways como fallback.

## Reporting

Como altera config/mirror/data operacional, registrar audit log e enviar REPORT-INFRA. Em updates futuros, preservar a preferência atual do Rodolfo; não reverter para `off` por default sem nova autorização explícita.
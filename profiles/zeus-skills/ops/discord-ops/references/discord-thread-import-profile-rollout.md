# Discord thread import — rollout para profiles MGS

## Classe de problema

Rodolfo fornece um ID/link de thread Discord e espera que o agente leia o histórico sob demanda. O agente não deve limitar a resposta ao contexto entregue pelo gateway se existe ID/link e o bot tem acesso Discord.

## Padrão correto

Usar o importador read-only canônico com o profile do agente que recebeu o pedido:

```bash
/root/mgs-agent/scripts/import-discord-thread.py --profile zeus --limit 1000 '<id-ou-link>'
/root/mgs-agent/scripts/import-discord-thread.py --profile atena --limit 1000 '<id-ou-link>'
/root/mgs-agent/scripts/import-discord-thread.py --profile ares --limit 1000 '<id-ou-link>'
/root/mgs-agent/scripts/import-discord-thread.py --profile legacy-agent --limit 1000 '<id-ou-link>'
```

Depois ler o snapshot local:

```text
/root/mgs-agent/data/discord-thread-imports/<thread_id>.md
/root/mgs-agent/data/discord-thread-imports/<thread_id>.json
```

Reportar contagem de mensagens, período e modo read-only.

## Pitfall validado

O importador tinha lista hardcoded de profiles (`choices=["zeus", "atena"]`). Isso fez Ares não conseguir usar `--profile ares`, apesar de possuir token e acesso à thread. A correção durável é aceitar nomes seguros de profile por regex (`[a-zA-Z0-9_-]+`) e carregar `/root/.hermes/profiles/<profile>/.env`.

## Validação mínima

1. `python3 -m py_compile /root/mgs-agent/scripts/import-discord-thread.py`
2. Rodar import com o profile afetado e `--limit 5`.
3. Se precisar validar escopo total, repetir com `--limit 1000`.
4. Se retornar `403 Missing Access`, validar acesso do bot ao canal/thread; reportar falta de acesso, não incapacidade geral.

## Handoff para agentes novos

Ao criar novo agente MGS, incluir no SOUL/config/channel prompt uma regra curta:

```text
Se Rodolfo fornecer ID/link de thread Discord e pedir para ler/analisar/continuar, importar em modo read-only com /root/mgs-agent/scripts/import-discord-thread.py --profile <agent> --limit 1000 <id-ou-link>. Não responder que só lê contexto do gateway antes de tentar. Se der 403 Missing Access, reportar falta de acesso do bot à thread/canal.
```

## Relação com permissões de canal

Thread import por ID e envio direto para canal são capacidades diferentes. Um bot pode conseguir importar uma thread onde está presente e ainda receber `403 Missing Access` ao postar no canal Zeus/home. Para envio direto, aplicar overwrite no canal para o user ID do bot e validar com GET/POST reais.
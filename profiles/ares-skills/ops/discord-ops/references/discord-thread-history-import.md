# Discord Thread History Import — Read-only por link/ID

## Quando usar

Use quando Rodolfo/Raquel pedir para Zeus, Atena ou Ares ler uma thread antiga do Discord, resumir seu contexto ou transferir uma análise, e fornecer:

- link da thread;
- ID da thread/canal;
- link de mensagem Discord.

## Script canônico

```bash
/root/mgs-agent/scripts/import-discord-thread.py --profile zeus '<LINK_OU_ID>'
/root/mgs-agent/scripts/import-discord-thread.py --profile atena '<LINK_OU_ID>'
/root/mgs-agent/scripts/import-discord-thread.py --profile ares '<LINK_OU_ID>'
```

O script é read-only contra Discord e grava snapshots locais em:

```text
/root/mgs-agent/data/discord-thread-imports/<thread_id>.json
/root/mgs-agent/data/discord-thread-imports/<thread_id>.md
```

`data/discord-thread-imports/` deve permanecer local-only/ignored no git; o script é versionado, os históricos importados não.

## Sequência operacional

1. Receber link/ID do usuário.
2. Rodar o importador com o profile do agente que precisa ler a thread.
3. Ler o `.md` gerado.
4. Responder apenas com base no histórico importado ou em logs locais.
5. Se a API retornar 403/404, reportar acesso insuficiente do bot ou ID/link inválido — não inventar conteúdo.

## Transferir resumo ou análise para outra thread

1. Resolver origem e destino pelos IDs fornecidos ou já confirmados na conversa. Importar a origem com o profile executor; ler o destino em recorte limitado para conferir contexto e evitar duplicatas.
2. Determinar o conteúdo solicitado. Para resumo, selecionar pedidos, correções, decisões e ponto de retomada. Para análise apontada por prints, identificar no histórico a mensagem inicial pelo cabeçalho, horário ou frase distintiva e recuperar todas as partes contíguas do mesmo autor. Não escolher automaticamente o último resumo publicado.
3. Extrair `messages[].content` do snapshot JSON, preservando texto, identificadores e ordem; usar os prints para conferir que a seleção corresponde ao relatório. Antes de publicar, conferir por GET os IDs selecionados se o snapshot puder estar desatualizado. Não reconstruir tabelas por OCR quando o texto original estiver disponível.
4. Preparar uma introdução curta, separada do relatório: autor original, origem, data/hora/fuso da consulta e aviso de reprodução histórica sem nova consulta ao sistema. Não reescrever afirmações do autor original como validação feita pelo agente que transfere.
5. Reutilizar as partes originais se cada uma couber no limite de 2000 caracteres e tiver fences balanceados. Se precisar repaginar, aplicar `references/route-pack-03.md`, preservando linhas completas e cabeçalhos. Validar tamanho, sequência, fechamento de blocos e presença de todas as seções antes do primeiro POST.
6. Usar a identidade do próprio profile e confirmar o bot por `GET /users/@me` antes do envio direto. Conferir o canal/thread por `GET /channels/{destino}`; configurar `allowed_mentions: {parse: []}` para reprodução sem notificação involuntária. Um helper com identidade padrão diferente não deve ser usado sem selecionar explicitamente o profile correto.
7. Reconciliar mensagens recentes do destino por autor e conteúdo exato. Publicar somente as partes ausentes em `POST /channels/{destino}/messages`; persistir o ID retornado de cada parte antes de avançar. Em falha parcial ou resposta perdida, reler IDs e destino antes de repetir; não reenviar o relatório inteiro.
8. Fazer `GET /channels/{destino}/messages/{message_id}` de cada publicação e exigir `channel_id`, `author.id` e `content` exatos. Contar as partes em código e conferir a quantidade planejada, distinguindo introdução de partes do relatório. Encerrar com confirmação curta e link da primeira parte da análise, sem ecoar novamente o relatório na origem.

### Critérios de verificação

- **Seleção:** prints, data/hora e mensagens de origem apontam para a mesma análise; nenhuma seção, conta ou invoice foi omitida.
- **Fidelidade:** cada conteúdo republicado corresponde ao original; apenas a introdução de atribuição é nova.
- **Entrega:** todas as partes retornam GET 200 no destino e conteúdo exato; recibo registra os IDs verificados.
- **Retomada:** partes já entregues não são duplicadas; a correção adiciona somente o conteúdo faltante, sem apagar o resumo anterior sem pedido.

## Pitfalls

- Usar o profile do agente executor: `--profile atena`, `--profile zeus` ou `--profile ares`. Isso evita usar o token do bot errado em private threads; não usar identidade de outro agente como fallback para acesso negado.
- Não expor `DISCORD_BOT_TOKEN`, headers de autorização ou payloads sensíveis no chat.
- Link de mensagem é aceito; o parser extrai o channel/thread ID do formato `/channels/{guild}/{channel_or_thread}/{message}`.
- Se a thread for private, o bot precisa ser membro da thread ou ter permissão suficiente (`Read Message History`).

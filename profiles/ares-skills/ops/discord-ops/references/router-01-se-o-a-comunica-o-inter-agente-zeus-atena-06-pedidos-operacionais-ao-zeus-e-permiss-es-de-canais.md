### Pedidos operacionais ao Zeus e permissões de canais

Quando Rodolfo pedir para acionar/pedir algo ao Zeus, enviar no canal/thread operacional do Zeus **mencionando explicitamente o bot Zeus (`<@1496296175014252634>`)**. Sem user mention, Zeus pode não ler/agir por causa de `DISCORD_ALLOW_BOTS=mentions`.

Quando o pedido for adicionar pessoas a um canal de logs, primeiro verificar se o bot do perfil atual tem permissão real no canal (`GET /channels/<id>` + permissões computadas, especialmente `MANAGE_ROLES`/`MANAGE_CHANNELS`). Se tiver, aplicar permission overwrite por usuário e validar com novo `GET /channels/<id>` antes de reportar sucesso. Se não tiver, aí sim encaminhar ao Zeus/admin com mention explícita e IDs.

Se Rodolfo corrigir que uma mensagem ao Zeus foi enviada sem mention, reenviar a mensagem corrigida imediatamente com o user mention real do Zeus no início; não tratar como já entregue nem apenas explicar a regra. Para pedidos de permissão/canal (ex.: adicionar usuários ao `logs-aquisicao`), listar IDs em texto normal fora de bloco de código se a mention do Zeus precisa acordar o bot. Antes de concluir que precisa do Zeus, porém, verificar se o bot do agente atual já ganhou permissão no canal: `GET /channels/{channel_id}`, `GET /guilds/{guild_id}/members/{bot_id}`, roles/overwrites e flags efetivas (`MANAGE_ROLES`/`MANAGE_CHANNELS`, `CREATE_PUBLIC_THREADS`, `SEND_MESSAGES_IN_THREADS`). Se a permissão existir, aplicar `PUT /channels/{channel_id}/permissions/{user_id}` para os usuários pedidos e validar os overwrites por GET; só acionar Zeus/admin quando faltar permissão real.

Não enviar tarefa operacional em `#alerts-infra`. `#alerts-infra` é para `[REPORT-INFRA]`, alertas e rastreabilidade de mudanças; abrir tarefa lá polui o canal e cria thread fora do contexto correto.

Fluxo:
1. Tentar enviar no alvo do Zeus (`discord:#zeus` ou canal ID do Zeus disponível no ambiente).
2. Se `send_message` retornar `403 Missing Access`, **não usar `#alerts-infra` como fallback de tarefa**.
3. Reportar o bloqueio ao Rodolfo e pedir/corrigir permissão do bot no canal do Zeus, ou usar outro alvo do Zeus explicitamente autorizado por Rodolfo.
4. Só usar `#alerts-infra` quando a mensagem for realmente um `[REPORT-INFRA]`/alerta de infra, não um pedido operacional.

Pitfall validado no Ares: pedido ao Zeus sobre capacidade de leitura de threads foi enviado para `#alerts-infra` após `#zeus` retornar 403; Rodolfo corrigiu que isso não fazia sentido porque abriu thread no canal de alertas.


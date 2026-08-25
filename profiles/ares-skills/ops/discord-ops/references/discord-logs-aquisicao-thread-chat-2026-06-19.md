# Conversa em threads fixas de Campaign Ops

Use quando um relatório automático e as respostas humanas compartilham uma thread operacional.

## Contrato

- A thread vem do arquivo da operação; não criar substituta quando a rota fixa existir.
- O relatório declara conta, período, timezone, moeda, fonte e modo.
- Respostas humanas curtas (`feito`, `ignorar`, `segurar`, `pausei`, `reativei`, `não mexer`) entram no state/audit com autor e timestamp.
- Na próxima leitura, validar o estado real pela API antes de assumir que a ação foi concluída.
- Uma resposta humana não amplia budget, autonomia ou escopo além do pedido correspondente.
- Incidente técnico, mudança estrutural ou investigação de criativo pode usar thread separada quando o contrato permitir.

## Segurança

Nunca expor token, cookie, credencial, payload secreto ou trace bruto. IDs técnicos completos permanecem no audit, salvo quando o operador pedir um ID necessário para ação manual.

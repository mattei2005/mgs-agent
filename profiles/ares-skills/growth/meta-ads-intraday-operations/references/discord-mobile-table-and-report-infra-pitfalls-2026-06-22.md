# Relatório Discord: mobile + desktop e REPORT-INFRA

## Layout

- Começar com conclusão e contexto: conta, período, timezone, moeda, fonte e modo.
- Manter tabela alinhada em bloco `text` para consolidação desktop.
- Quando a operação exigir mobile, acrescentar cards verticais curtos por campanha; não substituir a tabela consolidada.
- Dividir mensagens somente entre linhas/blocos e fechar todos os fences.
- Contagem declarada deve coincidir com linhas/cards enviados.

## Entrega

- Usar thread fixa do contrato.
- Wrapper direto: cron `deliver=local`, `no_agent=true`, stdout vazio.
- Persistir IDs das mensagens e não duplicar partes já confirmadas.

## Infra

Mudança em script/config/data operacional requer inventário e envio por `/root/mgs-agent/scripts/send-report-infra-embed.sh`, com embed, `content` vazio, sem mentions, sem thread e sem segunda cópia em texto. A conversa operacional recebe apenas conclusão útil.

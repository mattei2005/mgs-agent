### Layout de alertas automáticos via webhook

Quando ajustar ou criar alertas nos canais `#mgs-alerts` / `#alerts-yoast`, evitar mensagens longas em texto corrido. Rodolfo considera esse formato poluído e difícil de entender.

Padrão preferido:
- `content`: só mention/push + frase curta quando precisa notificação (`<@344196393512075265> alerta de ...`). Sem blocos longos no content.
- `embeds`: título curto, cor por severidade e `fields` separados por assunto (`Script`, `Estado`, `Ação`, `Detalhe técnico`, `API calls`, etc.).
- Resoluções: embed verde simples com título curto (`Cron recuperado`, `Service normalizado`) e descrição de 1 linha.
- Custo/volume: separar `Custo real`, `Custo hipotético`, `API calls`, `Tokens estimados`, `Referência`, `Nota` em fields; não jogar tudo em uma descrição Markdown única.
- Emojis: usar só como indicador de severidade no resumo/título; não repetir em toda linha.

#### Listas longas no Discord mobile: agrupar por chave, não forçar tabela

Quando um alerta precisa mostrar lista de pessoas/contas com campos longos — especialmente `email`, `nome`, `perfil ID`, `role` — não insistir em tabela de 4 colunas. Mesmo em bloco monoespaçado, o Discord mobile corta/trunca emails e deixa a leitura ruim.

Padrão validado com Rodolfo para Meta App Roles:

```text
Usuários do app - B002
Ordenado por BOT EMAIL

disparosconecta@gmail.com
• Adalberto Vilela Oliveira — adalbertovilelaoliveira — Admin
• Afonso Araujo — fernandadossanto678 — Admin

disparosfinanceadx@gmail.com
• Fernando Narciso Acosta — 100009006839947 — Admin
```

Regra prática:
- embed curto para status/resumo;
- mensagem normal separada para a lista;
- chave agrupadora longa em linha própria (`BOT EMAIL`, domínio, site, conta);
- itens em bullets: `Nome — ID — Role/estado`;
- linha em branco entre grupos;
- ordenar pela chave agrupadora;
- validar visualmente em 1 canal canário antes de disparar em massa.

Não usar aliases artificiais (`D1`, `D2`) nem responder que é questão de “modo desktop”: o render depende do client Discord, então o layout deve ser mobile-first. Detalhe: `references/discord-mobile-grouped-list-alert-layout-2026-06-30.md`.

Exemplo jq compacto para webhook:

```bash
PAYLOAD=$(jq -n \
  --arg c "<@344196393512075265> alerta de cron stale" \
  --arg script "$SCRIPT" \
  --arg detail "$DETAIL" \
  '{content:$c, embeds:[{title:"Cron sem log recente", color:15158332, fields:[
    {name:"Script", value:("`"+$script+"`"), inline:true},
    {name:"Estado", value:"STALE", inline:true},
    {name:"Ação", value:"Verificar cron, script e log.", inline:false},
    {name:"Detalhe técnico", value:("```text\n"+$detail+"\n```"), inline:false}
  ]}]}')
```

Validação mínima antes de reportar sucesso: `bash -n` no script alterado e dry-run quando existir (`--dry-run`, sem envio Discord). Se o script for monitor cron, evitar disparar alerta real de teste para não sujar o canal; validar payload estrutural/localmente quando possível.

Em execuções multi-etapa de infra para Rodolfo, cada relatório parcial, final ou bloqueado deve terminar com `Próximo passo pendente:` e nomear a próxima ação operacional concreta até o checklist estar concluído. Mesmo quando a execução fica bloqueada por safety gate/falta de permissão, declarar o próximo comando/manual action esperado e a evidência que deve ser validada depois.

---

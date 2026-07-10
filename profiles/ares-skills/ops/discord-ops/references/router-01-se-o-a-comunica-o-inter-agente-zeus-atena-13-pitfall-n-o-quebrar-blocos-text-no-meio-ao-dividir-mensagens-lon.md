### Pitfall: não quebrar blocos ```text no meio ao dividir mensagens longas

Quando um helper postar relatórios longos no Discord e precisar dividir por limite de 2000 caracteres, **nunca dividir no meio de um bloco fenced** (` ```text ... ``` `). Isso faz o Discord renderizar metade da tabela como código e metade como texto solto, deixando a formatação “horrível/bagunçada”. O chunker deve preferir boundaries entre blocos completos; validar antes do envio que cada chunk tem code fences balanceados (`count('```') == 0 ou 2`) e tamanho `<2000`. Para relatórios tabulares longos, gere blocos menores com cabeçalho repetido (`bloco 1/N`, `bloco 2/N`) em vez de uma tabela única gigante.

Para cron/report posters que fazem `POST /channels/{id}/messages` direto na API Discord, implementar chunking no helper de postagem para nunca enviar `content` acima de 2000 caracteres. Preferir chunks de ~1900 chars, split por linha, labels `[parte N/T]`, e dry-run com `chunks`, `chunk_lengths` e `max_chunk_len`. Em modo thread existente, postar todas as partes na própria thread; em modo criar thread, criar a thread pela parte 1 e postar as demais dentro dela. Caso real e validação: `references/discord-cron-message-chunking.md`.

Padrão preferido:
- `content`: só mention/push + frase curta quando precisa notificação (`<@344196393512075265> alerta de ...`). Sem blocos longos no content.
- `embeds`: título curto, cor por severidade e `fields` separados por assunto (`Script`, `Estado`, `Ação`, `Detalhe técnico`, `API calls`, etc.).
- Resoluções: embed verde simples com título curto (`Cron recuperado`, `Service normalizado`) e descrição de 1 linha.
- Custo/volume: separar `Custo real`, `Custo hipotético`, `API calls`, `Tokens estimados`, `Referência`, `Nota` em fields; não jogar tudo em uma descrição Markdown única.
- Emojis: usar só como indicador de severidade no resumo/título; não repetir em toda linha.

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

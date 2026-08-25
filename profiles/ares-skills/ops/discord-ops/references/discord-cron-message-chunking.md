# Discord cron message chunking

Use quando um wrapper determinístico precisa publicar relatório extenso em thread fixa sem exceder o limite do Discord.

## Fluxo

1. Renderizar cabeçalho, resumo e linhas completas.
2. Medir cada mensagem em caracteres/bytes antes do envio.
3. Dividir apenas entre blocos ou linhas; nunca no meio de uma linha ou de um fence ```text.
4. Numerar partes somente quando houver mais de uma.
5. Publicar na thread fixa registrada no contrato da operação.
6. Confirmar cada mensagem por readback; contagem enviada deve igualar a enumerada.
7. Cron usa `deliver=local` e stdout vazio quando o wrapper publica diretamente.

## Falhas

- Retry bounded por parte, sem duplicar mensagens já confirmadas.
- Persistir IDs das mensagens confirmadas.
- Em erro, publicar resumo sanitizado; detalhes ficam no audit/REPORT-INFRA.
- Nunca incluir token, PID, path interno ou trace bruto no texto operacional.

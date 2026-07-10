### REPORT-INFRA canal inacessível pelo agente

Se o agente precisar enviar `[REPORT-INFRA]` para `#alerts-infra` e receber Discord `403 Missing Access`, não descartar o reporte nem fingir envio. Com autorização explícita de Rodolfo para liberar acesso:

```text
1. Validar que o bot do agente não acessa o canal: GET /channels/{alerts_infra_id} com token do agente => 403.
2. Usar um bot/admin operacional autorizado para aplicar permission overwrite no canal para o bot do agente.
3. Considerar liberado apenas se PUT /channels/{channel_id}/permissions/{bot_id} retornar HTTP 204.
4. Validar com o token do agente: GET /channels/{channel_id} => HTTP 200.
5. Reenviar o REPORT-INFRA e registrar o message_id.
```

Não imprimir tokens. Reportar apenas códigos HTTP, IDs de canal/bot e resultado.


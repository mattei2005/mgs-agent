# SB Utility Templates — reduzir para melhores 70 mensagens

Sessão: 2026-06-30, Rodolfo/Zeus, após conversa do Rodolfo com Ciro sobre tempo de aprovação.

## Aprendizado operacional

Ciro explicou que o gargalo de Utility Template não é só importar template; é o tempo de aprovação por página/mensagem:

```text
~8s por mensagem
~10 mensagens por página
~3k páginas
≈66h para aprovar o necessário do dia
```

O servidor cacheia aprovações: se a copy/template já foi aprovada, não tenta aprovar de novo, só envia. Mesmo assim, templates com ~200 mensagens reduzem a chance de pegar copy já aprovada e aumentam muito o tempo de aprovação. Ciro recomendou reduzir de ~200 para ~70 mensagens: mantém variação aceitável e acelera approval em ~3x.

## Regra prática

Para templates operacionais de envio imediato, **não usar 187/200 mensagens por padrão**. Use ~70 mensagens melhores quando o gargalo for aprovação em muitas páginas.

Manter lotes 187/200 como banco/reserva/experimento, mas o template operacional ativo deve ser enxuto quando houver urgência de aprovação diária.

## Seleção correta das 70

Quando Rodolfo pedir “deixa só 70”, não cortar simplesmente as primeiras 70. Selecionar as melhores por apelo/conversão:

- gancho forte no início;
- card / credit profile / approval / limit / delivery;
- curiosidade/urgência sem virar genérico;
- CTA forte;
- coerência comercial com credit-card funnel;
- evitar filler tipo “update available” sem card/credit context.

Exemplo de critério aplicado em US-CC-EN:

```text
Templates reduzidos       13
Antes                     187 mensagens cada
Depois                    70 mensagens cada
Seleção                   rank por apelo/conversão, não primeiras 70
Validação                 API SB confirmou 70 em todos
```

## Técnica segura usada

1. Capturar o payload atual de `/broadcast/Messenger` autenticado pela SPA da SB.
2. Fazer backup JSON + CSV de cada template antes de mexer.
3. Parsear `MESSAGES` de cada template.
4. Rankear mensagens por score operacional de apelo.
5. Selecionar 70, renumerar `MESSAGE_ID` sequencialmente e preservar `TEXT`, `CTA_1`, `LINK_1` das mensagens escolhidas.
6. Atualizar o mesmo template por `POST /broadcast/Messenger` com o payload completo alterado.
7. Reconsultar `/broadcast/Messenger` e validar `len(MESSAGES) == 70` para todos.

Observação: a API interna depende de headers/auth da SPA. Em automação Playwright, capture a request real feita pela página e reaproveite headers seguros internamente; nunca imprimir bearer/cookies no chat.

## Pitfalls

- **Não cortar primeiras 70** quando Rodolfo pede qualidade/apelo. Ele quer as melhores mensagens.
- **Não confundir banco aprovado com template operacional.** 187/200 é bom como banco; 70 pode ser melhor para aprovação diária em escala.
- **Não rodar Run Approvals automaticamente** se Rodolfo só pediu reduzir/importar. Deixar Ciro/agenda executar approval quando combinado.
- **Backup antes de reduzir** é obrigatório porque a redução remove 117 mensagens do template ativo.
- **Validação real**: só declarar concluído após re-read da API SB confirmar 70 mensagens no template ativo.

## Artefatos da sessão

```text
Auditoria:
/root/mgs-agent/work/meta-utility/us-cc-en-reduce-to-70-20260630/reduce70-results.json

Backups:
/root/mgs-agent/backups/sb-templates/*before-reduce70-20260630-005536*
```

Esses caminhos são referência histórica; em sessão futura gerar novos paths com timestamp atual.

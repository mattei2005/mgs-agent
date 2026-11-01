# REPORT-INFRA — publicação e readback exato

## Procedimento

1. Publique uma única vez pelo helper canônico `/root/mgs-agent/scripts/send-report-infra-embed.sh`, preenchendo ação, tipo, alvo, motivo e evidência. Capture o `message_id` retornado; sucesso do POST ainda não comprova o conteúdo armazenado.
2. Leia `GET /channels/{channel_id}/messages/{message_id}` com a identidade Zeus usada pelo transporte. Para REPORT-INFRA normal, o destino é `#alerts-infra`, sem criar thread.
3. Se a ferramenta de mensagens não expuser embeds, faça o GET direto em vez de interpretar `content == ""` como mensagem vazia. Confira o ID e canal exatos, `content == ""`, exatamente um embed, título/campos correspondentes à ação e `mentions == []`.
4. Registre o ID e o resultado do readback no recibo/inventário. Marque `sent_verified` somente após essa leitura; publicação confirmada com readback bloqueado deve permanecer uma pendência explícita.
5. Entregue apenas o resumo operacional na origem. Não publique outra cópia textual do report após o helper ter enviado o embed.

## GET direto com transporte equivalente

Carregue a credencial internamente pelo loader de `/root/mgs-agent/scripts/discord-bot-post.py`; nunca a imprima. Construa o request com os mesmos headers usados pelo poster:

```python
request = urllib.request.Request(
    f"https://discord.com/api/v10/channels/{channel_id}/messages/{message_id}",
    headers={
        "Authorization": "Bot " + token,
        "User-Agent": "MGS-Zeus/1.0",
    },
)
with urllib.request.urlopen(request, timeout=20) as response:
    message = json.load(response)
assert str(message["id"]) == str(message_id)
assert str(message["channel_id"]) == str(channel_id)
assert message["content"] == ""
assert len(message.get("embeds", [])) == 1
assert not message.get("mentions")
# Compare também título e fields com o payload esperado.
```

Antes de atribuir um 403 do probe à permissão do bot, compare identidade e headers com o poster que conseguiu enviar. Corrija uma diferença de transporte e repita somente o GET: o User-Agent padrão do urllib pode receber uma resposta diferente do cliente canônico. Se a leitura equivalente continuar negada, registre HTTP/código sanitizados e investigue o acesso; não gire a credencial, amplie permissões nem repita o POST para testar.

## Saída segura

Imprima somente IDs, flags de validação e diagnóstico sanitizado. Não despeje headers de autorização, variáveis de ambiente ou respostas brutas. Uma listagem resumida comprova a presença da mensagem, mas não substitui a validação dos campos do embed.

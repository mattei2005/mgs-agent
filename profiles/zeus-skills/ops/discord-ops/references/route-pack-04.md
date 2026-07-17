### Enviar arquivos grandes/anexos no Discord

Quando Rodolfo pedir “anexa aqui”, não responda apenas caminhos `MEDIA:/path` como texto esperando que o Discord converta se houver risco de truncamento ou múltiplos arquivos grandes. Para arquivos fonte/logs grandes, criar um pacote único em `/tmp` (`tar -czf /tmp/nome.tar.gz ...`) e colocar `MEDIA:/tmp/nome.tar.gz` sozinho/claramente na resposta final. Validar tamanho e conteúdo antes de responder. Se o envio anterior apareceu como texto no Discord, corrigir imediatamente com pacote único anexável.

### Enviar/anexar arquivos no Discord

Quando Rodolfo pedir em linguagem natural “manda/envia/anexa esse arquivo”, entregar como **anexo nativo do Discord**, não como texto contendo `MEDIA:/path`. Pitfall validado: final response com `MEDIA:/root/.../title_generator.py` apareceu literalmente no chat. Use o caminho de envio que realmente faz upload; se necessário, copie para `/tmp`, gere uma variante `.txt` para source code e/ou `.tar.gz` com o original, envie para o target exato da thread e, se Rodolfo disser que não chegou, liste/valide o target antes de retry. Referência: `references/discord-file-attachments-and-thread-title-rename-2026-06-13.md`.

### Enviando mensagem Zeus → Atena em outro canal

Para comunicação **cross-channel** Zeus → Atena, incluir `<@BOT_ID>` porque Atena usa `DISCORD_ALLOW_BOTS=mentions`:

```python
send_message(
    message="<@1496306920494202950> Atena, aqui é o Zeus. [pergunta]",
    target="discord:1496267571543019653"
)
```

Sem o user mention do bot Atena, Atena ignora silenciosamente.

Em thread compartilhada, não usar esse padrão automaticamente; só acionar Atena com mention se Rodolfo pedir explicitamente.

### Verificando que Atena recebeu

```bash
tail -20 /root/.hermes/profiles/atena/logs/agent.log
# Esperar: inbound message: platform=discord user=Zeus ...
```

### Lendo a resposta da Atena

```bash
ls -t /root/.hermes/profiles/atena/sessions/session_*.json | head -1
python3 -c "
import json
with open('/root/.hermes/profiles/atena/sessions/session_XXXXXXXX.json') as f:
    s = json.load(f)
for m in s.get('messages', []):
    if m.get('role') == 'assistant':
        content = m.get('content','')
        if isinstance(content, list):
            for c in content:
                if isinstance(c, dict) and c.get('type') == 'text':
                    print(c['text'])
        elif content:
            print(content)
"
```

### Formato REPORT-INFRA (Atena/Ares/agente legado → Zeus)

Ao processar `[REPORT-INFRA]`, seguir o playbook operacional em `references/report-infra-processing-playbook.md`: validar artefatos/hashes/crons, atualizar `infra-inventory.json` quando aplicável, registrar audit log, commitar só arquivos relevantes e responder apenas com o ACK canônico curto.

**Regra de roteamento para Zeus em tarefa interativa:** não despejar o bloco `[REPORT-INFRA]` na thread onde Rodolfo pediu a execução. Essa thread deve receber só conclusão/detalhes úteis. O report formal deve ser enviado ao canal correto de infra (`#alerts-infra` / webhook correspondente, com mention quando for thread nova). Se o report precisar existir como evidência, poste lá primeiro e depois responda na thread original com resumo limpo. Se a sessão atual não tiver rota/API para postar no canal certo, registre audit/inventário e não simule o report dentro da thread. Referência: `references/report-infra-thread-destination-pitfall-2026-07-01.md`.

**Verificação de entrega obrigatória:** antes de dizer na thread original que um `REPORT-INFRA` foi enviado, validar duas coisas: (1) helper/webhook retornou sucesso real (`HTTP 204` ou equivalente); (2) Discord API mostra a mensagem no destino esperado (`#alerts-infra` / `1498132022634483894`, ou thread específica quando aplicável). Isso evita falso positivo quando o webhook aponta para outro canal, mensagem sai como embed vazio, ou o agente confunde canais de alerta. Detalhe: `references/report-infra-delivery-verification-2026-07-02.md`.

**Layout obrigatório novo:** REPORT-INFRA enviado por Zeus deve usar embed Discord, não bloco de texto cru. Use o helper canônico:

```bash
/root/mgs-agent/scripts/send-report-infra-embed.sh \
  --action modificada \
  --type script/data \
  --path '/root/mgs-agent/scripts/foo.sh; /root/mgs-agent/data/infra-inventory.json' \
  --reason 'motivo operacional curto' \
  --evidence 'bash -n OK; dry-run OK; HTTP 204'
```

O helper mantém `content` vazio por padrão: sem mention do Zeus, do Rodolfo ou de qualquer pessoa. Ação/Tipo/Path/Motivo/Evidência ficam em fields de embed. Em `#alerts-infra`, REPORT-INFRA/alerta operacional normal é silencioso e não abre thread. Só usar mention em alerta crítico real com push explicitamente necessário. Não voltar para `[REPORT-INFRA] ...` em texto corrido salvo emergência/manual fallback.

Detalhe/pitfall validado: `references/report-infra-embed-no-mention-no-thread-2026-07-02.md`.

Formato legado em texto não deve mais ser publicado. Adaptadores antigos precisam converter seus campos para o helper canônico. Depois de sucesso do helper, nunca enviar o mesmo report novamente por `send_message` ou resposta comum.

### Diagnóstico e padronização de layout misto

Quando Rodolfo perguntar por que alguns reports estão “bonitos” e outros aparecem como texto cru:

1. Buscar as mensagens recentes no canal e comparar os caminhos de entrega.
2. Mensagem com `content` vazio pode ser um embed válido; confirmar por readback da API (`embeds`, título e fields), não classificar como vazia só pela listagem resumida da ferramenta.
3. Mensagem com `[REPORT-INFRA]` no `content` veio de fluxo legado ou de uma segunda resposta direta do agente.
4. Se embed e texto aparecem com poucos segundos de diferença para a mesma ação, tratar como duplicidade: helper canônico + publicação manual posterior.
5. Para corrigir toda a classe, atualizar a regra global MGS, SOUL/instruções dos agentes e adaptadores legados; não basta mudar apenas a aparência de um script.
6. Preservar compatibilidade convertendo inputs legados (`Ação`, `Tipo`, `Path`, `Motivo`, `Evidência`) para o helper canônico, em vez de manter um segundo transporte em texto.
7. Validar com `bash -n`, dry-run do helper, dry-run do adaptador legado e um único envio real com readback: `content == ""`, exatamente um embed e fields esperados.
8. Nunca reiniciar agentes durante outras threads ativas quando Rodolfo pedir para aguardar; a mudança de scripts vale imediatamente, enquanto instruções já carregadas em sessões antigas só ficam integralmente vigentes em sessões novas ou após restart autorizado.

Regra de comunicação: explicar que a mudança é interna da MGS, não uma alteração estrutural do Hermes. Se a implementação exigir editar `AGENT.md` ou skills de outros agentes, aplicar o Critical Subset e obter a confirmação adicional antes da escrita.


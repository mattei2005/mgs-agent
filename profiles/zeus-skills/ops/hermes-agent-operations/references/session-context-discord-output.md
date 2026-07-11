# Sessions, Context Compression, and Discord Output

> Extracted from the former monolithic `SKILL.md` on 2026-07-10. Load this file only when its branch is relevant.

## 6. Session reset / manter contexto em threads

Use quando Rodolfo perguntar sobre mensagens do Hermes como:

```text
◐ Session automatically reset (daily schedule at 4:00). Conversation history cleared.
Use /resume to browse and restore a previous session.
Adjust reset timing in config.yaml under session_reset.
```

Interpretação correta: isso é política de `session_reset` do gateway, não erro do modelo nem apagamento de mensagens do Discord. O efeito é limpar o contexto interno daquela conversa/thread para o agente; o histórico visual do Discord continua existindo, mas a sessão precisa de `/resume` ou reconstrução via logs/mensagens se o agente responder depois do reset.

Se Rodolfo disser que não quer perder contexto nas threads, o ajuste canônico do profile é:

```yaml
session_reset:
  mode: none
```

`mode: none` é o modo Hermes oficial para desabilitar reset automático: sem reset diário e sem reset por idle. Isso não remove o limite físico de contexto do modelo; conversas muito grandes ainda dependem de compression/summary. Para MGS, preferir `session_reset.mode: none` + compression ativa em vez de reset bruto por agenda.

Workflow seguro:

1. Confirmar qual profile/gateway será afetado, normalmente `/root/.hermes/profiles/zeus/config.yaml` para Zeus.
2. Verificar o schema no código vivo quando houver dúvida: `gateway/config.py` → `SessionResetPolicy` (`daily`, `idle`, `both`, `none`) e overlay de `config.yaml` via chave top-level `session_reset`.
3. Aplicar no `config.yaml` do profile:

```bash
hermes config set session_reset.mode none
```

ou patch YAML equivalente se o CLI não suportar bem nested keys.

4. Validar que o arquivo contém `session_reset: {mode: none}` ou bloco equivalente.
5. Reiniciar/recarregar o gateway com o padrão MGS de restart seguro; não reiniciar Zeus no meio de tool calls foreground ou sem finalizer externo.
6. Explicar o limite operacional: “não haverá reset automático; contexto extremo ainda pode compactar por limite de tokens”.

Pitfalls:

- Não responder “não dá” só porque a mensagem menciona `/resume`; `session_reset.mode: none` existe.
- Não confundir `compression.threshold` com `session_reset`: compression resume contexto grande; session reset zera por política de tempo/idle.
- Se a ordem for só explicativa (“tem como?”), responder o caminho e pedir “aplica?” antes de mutar config/restart. Se Rodolfo mandar “aplica”, executar.

## 6. Context compression / Codex gpt-5.5 notices

Use quando Rodolfo perguntar sobre mensagens do Hermes como:

```text
ℹ Codex gpt-5.5 caps context at 272K, so auto-compaction was raised to 85% (from X%)...
```

Interpretação correta: isso é um aviso de inicialização/primeiro turno, não erro e não alerta de que a thread já chegou a 85%. O Hermes detecta `openai-codex/gpt-5.5` e auto-eleva o threshold de compactação para 85% porque a rota Codex limita a janela em ~272K tokens; a mensagem apenas explica que mudou de `compression.threshold` antigo para `0.85`.

Workflow recomendado MGS:

1. Explicar de forma executiva: auto-compaction resume a conversa só quando o contexto fica grande; 85% usa mais janela antes de resumir.
2. Se Rodolfo quiser manter o comportamento mas remover o aviso repetitivo, **não desativar a compactação** e **não desligar o auto-raise como primeira opção**. Definir o threshold global do profile para o mesmo valor do auto-raise:

```bash
hermes config set compression.threshold 0.85
```

3. Validar no arquivo do profile, porque versões atuais do CLI têm `hermes config show`, mas não necessariamente `hermes config get`:

```bash
grep -n -A8 '^compression:' /root/.hermes/profiles/zeus/config.yaml
hermes config check
```

4. Se Rodolfo pedir explicitamente 90%/95%, aí desligar o auto-raise e setar manualmente:

```bash
hermes config set compression.codex_gpt55_autoraise false
hermes config set compression.threshold 0.90   # ou 0.95
```

Pitfalls:

- Não confundir “auto-compaction was raised” com “a compactação acabou de rodar”. É startup notice.
- Para MGS, 85% é a recomendação segura: em 272K, compacta em ~231K e deixa ~40.8K de folga. 90% deixa ~27.2K; 95% só ~13.6K e é arriscado com tool outputs/system prompt.
- Se uma sessão já aberta ainda mostrar o aviso, validar em nova sessão/novo init antes de concluir que a configuração falhou.

## 6. Discord link previews / suppressão de embeds automáticos

Use quando Rodolfo pedir que links enviados por Zeus, Atena, Ares, Hera ou futuros agentes não gerem cards/previews automáticos no Discord.

### Diagnóstico canônico

1. Consulte a documentação Hermes e o código vivo do adapter Discord; não presuma que exista uma chave de config.
2. Diferencie:
   - **preview automático de URL**: card gerado pelo Discord para um link comum;
   - **embed explícito do bot**: UI usada por aprovações, clarify, model picker e outros fluxos interativos.
3. No Hermes v0.18.2, o envio textual normal passa por `plugins/platforms/discord/adapter.py::DiscordAdapter.send()` e chama `channel.send(content=..., reference=...)`; não há configuração pública documentada para suprimir previews globalmente.

### Solução recomendada

Implementar uma opção comportamental em `config.yaml` e propagá-la pelo adapter para aplicar `suppress_embeds=True` nos envios de texto normal. Cobrir todos os caminhos equivalentes, não apenas `DiscordAdapter.send()`:

- mensagens normais e retries sem `reference`;
- continuações após overflow;
- posts/follow-ups de fórum quando aplicável;
- mensagem inicial e edições do streaming, preservando a flag;
- mensagens de ferramentas/cross-platform delivery que reutilizem o adapter.

Não aplicar a supressão indiscriminadamente aos fluxos que constroem `discord.Embed` explicitamente. Aprovações, clarify, prompts e model picker devem continuar renderizando suas interfaces.

### Alternativa não recomendada

Remover a permissão Discord **Embed Links** do role do bot também impede previews automáticos, mas pode quebrar embeds explícitos e fluxos interativos. Use apenas se Rodolfo aceitar essa perda funcional.

### Contrato de implementação

- Preferir uma chave pública como `discord.suppress_link_previews: true`, traduzida pelo hook YAML do plugin; não criar variável `.env` como superfície de configuração.
- O default upstream deve preservar compatibilidade; o default MGS pode ser habilitado em Zeus/Atena/Ares/Hera.
- Adicionar testes para URL comum sem preview e para embed explícito ainda presente.
- Validar no Discord real com mensagem contendo URL e readback da flag/ausência do card.
- Proteger o patch MGS contra updates e seguir restart seguro dos gateways, com Zeus por último.
- Se a pergunta for apenas “tem como?”, explicar a estratégia e pedir autorização antes de mutar config/código/reiniciar.

### Pitfall

Não confundir “suprimir preview de link” com “proibir qualquer embed”. A primeira é uma preferência visual de mensagens textuais; a segunda pode remover controles operacionais importantes.

## 6. Reporting templates

### Resposta executiva para tooling web

```text
Pergunta                                      Resposta
──────────────────────────────────────────── ─────────────────────────────
1. Tem web_search nativo?                    Sim/Não + tool name
2. Tem web_fetch nativo?                     Sim/Não + web_extract mapping
3. MCP de busca configurado?                 Sim/Não + profile results
4. Versão trouxe capability nova?            Versão + delta conciso
5. Toolsets ativos Zeus/Atena                tabela abaixo
```

Depois: tabela de toolsets, tabela de backends, recomendação direta e `Próximo passo pendente:`.

### Resposta executiva para update

Use **blocos simples sem language tag** ou bullets curtos para qualquer matriz de status/validação/novidades. Não usar tabela Markdown crua (`|---|---|`) em Discord: Rodolfo considera visualmente regressivo e já corrigiu esse padrão. Não usar fences com linguagem como ` ```text`, ` ```bash` ou ` ```json` em respostas Discord: em algumas renderizações isso vaza uma linha solta `text` e quebra a leitura. Cabeçalhos devem nascer do contexto real do update; não copiar exemplos. Se houver drift de estilo ou dúvida sobre renderização de tabelas, ver `references/discord-table-format-and-standards-drift.md`.

Regra de anexos para Rodolfo: **nunca enviar arquivo/anexo por iniciativa própria**. Se ele pedir “mostra por aqui”, “no chat” ou apenas pedir explicação/review, responder inline. Só enviar `MEDIA:/...`/anexo quando ele pedir explicitamente arquivo/anexo. Para documentos longos, oferecer resumo inline e perguntar se quer anexo. O guard local `/root/mgs-agent/scripts/discord-response-lint.py --check` deve acusar language-tagged fences, linha solta `text`, tabela Markdown crua e diretivas `MEDIA:/...` em drafts.

Correção operacional 2026-07-07: em respostas normais de update para Rodolfo, **não colar blocos `[REPORT-INFRA]` inline na própria thread de update**. REPORT-INFRA é feed/canal operacional separado; se Zeus não tiver entrega explícita para esse destino no momento, registrar a mudança em Git/audit/inventário e resumir no report final como “infra alterada: paths + commits”, sem transformar a resposta executiva em alerta de infra.

Quando a resposta longa foi redigida em arquivo/stdin antes de enviar, validar quando prático com:

```bash
python3 /root/mgs-agent/scripts/discord-response-lint.py --check < draft.md
```

**Se Rodolfo apontar regressão visual/legibilidade após update** (ex.: “por que não está em tabela?” ou “voltou aos padrões?”), não trate como mera preferência de resposta. Faça auditoria de padrões: config viva dos profiles, backups/snapshots, SOUL/style rules, gateways e patch guard. Se o problema for regra permissiva no SOUL, fortaleça a regra para “não usar tabela Markdown crua no Discord; usar bloco `text` alinhado” nos agentes afetados. Detalhe em `references/discord-table-format-and-standards-drift-2026-06-09.md`.

```text
Resumo: atualizar agora / deferir / janela controlada.
Evidências: commits atrás, highlights, risco local, backup/checks.
Impacto: gateways offline ~1-2 min; Zeus pode interromper sessão ativa.
Próximo passo: comando exato ou validação pendente.
```

Exemplo de matriz final:

```text
Item                    | Estado
------------------------|-------------------------------
Hermes                  | v0.16.0 / behind 0
Gateways                | Zeus/Atena/Ares/Hera active
Patches MGS             | guard OK / py_compile OK
Backup                  | removido ou path preservado
Pendência               | nenhuma ou ação concreta
```

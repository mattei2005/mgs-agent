# Honcho Spike — MGS

Sandbox para testar Honcho como camada de **conclusões sobre memória/contexto** para agentes MGS.

## Decisão operacional

Honcho **não é fonte de verdade** na MGS.

```text
Camada                         Fonte ideal
-----------------------------  -----------------------------------------
Fatos canônicos                JSONs, DB, Git, WordPress, audit logs
Procedimentos reutilizáveis    Skills Hermes
Preferências estáveis          Memory Hermes
Histórico bruto                Logs, Discord/session_search, events JSONL
Hipóteses/conclusões           Honcho
Validação final                Zeus contra fontes canônicas
```

Uso aprovado por enquanto: **briefing experimental manual**, sob demanda.

Uso não aprovado ainda: cron automático, produção direta, ingestão de logs brutos sensíveis ou decisões operacionais sem validação Zeus.

## Política de segurança

- Nunca enviar credenciais, senhas, tokens, application passwords ou dados operacionais sensíveis.
- Buscar a API key do Honcho somente via 1Password.
- Não hardcodar `HONCHO_API_KEY` em script, README, shell history ou Discord.
- Datasets gerados são sanitizados e ignorados pelo git.
- Honcho pode sugerir hipótese; Zeus valida antes de reportar ou agir.

1Password esperado:

```text
Vault   MGS Conteúdo
Item    Honcho API - MGS
Field   api key
```

## Comando principal

```bash
/root/mgs-agent/scripts/run-honcho-briefing
```

O comando executa:

```text
1. Regenera datasets sanitizados
2. Reexecuta rodadas Honcho
3. Gera briefing experimental
4. Renderiza output limpo para Discord/Markdown
```

## Arquivos principais

```text
scripts/run-honcho-briefing                                  wrapper canônico
experiments/honcho-spike/run-honcho-briefing                 runner interno
experiments/honcho-spike/run_targeted_rounds.py              coleta/sanitiza/ingere rodadas
experiments/honcho-spike/manual_briefing.py                  cria briefing Honcho+Zeus
experiments/honcho-spike/render_discord_briefing.py          renderiza Markdown Discord
experiments/honcho-spike/run_*_with_1password.sh             wrappers seguros via 1Password
```

Arquivos runtime ignorados pelo git:

```text
sanitized_*.json
manual_briefing_report.json
manual_briefing_discord.md
targeted_rounds_report.json
*_output*.txt
*_output*.md
*_error.log
.venv/
.env
```

## Rodadas atuais

```text
Rodada                         Objetivo
-----------------------------  ------------------------------------------------
auth                           Eventos de autorização e estado autorizado
content                        REC/P1/Atena: imagens, runners, WP, Yoast, TTFB
gateway                        Hermes/gateway por agente: erros, TTFB, lifecycle
manual briefing                Síntese executiva com camada determinística Zeus
```

## Resultado validado em 2026-06-02

```text
Área                  Honcho conseguiu concluir?  Veredito Zeus
--------------------  --------------------------  ----------------------------------------
Autorização           Parcial                     Misturou segurança/config com auth real
REC/P1 Atena          Sim                         Útil; achou gargalos reais
Gateway/agentes       Fraco                       Usar contadores determinísticos primeiro
```

Principais sinais de conteúdo no tail validado:

```text
Categoria                  Ocorrências
-------------------------  -----------
image_quality_or_lookup    67
runner_failures            54
wordpress_publish_or_rest  53
provider_ttfb              30
dependency_or_tooling      20
official_source_or_data    7
comparison_table_gate      3
yoast_quality_gate         1
```



## Copiloto de memória/raciocínio — Honcho

Honcho está disponível como **copiloto de memória/raciocínio**, não como fonte de verdade.

```text
Permitido                 Não permitido
------------------------  --------------------------------------------
Contexto auxiliar          Fonte canônica
Hipóteses                  Autorização
Padrões recorrentes        Publicação/execução automática
Ajuda em respostas         Decisão financeira/operacional final
```

Comando comum aos agentes:

```bash
/root/mgs-agent/scripts/mgs-memory-copilot --agent <zeus|atena|ares> --question "pergunta" --context "contexto sanitizado"
```

Regras:
- enviar apenas contexto sanitizado/agregado;
- tratar a resposta como hipótese/contexto auxiliar;
- validar fatos operacionais em JSON, DB, WordPress, Git, audit logs ou logs canônicos antes de reportar/agir;
- nunca colar ou imprimir `HONCHO_API_KEY`; o runner busca no 1Password.

## Critérios para evoluir

Antes de cron automático:

```text
Critério                                      Estado atual
--------------------------------------------  -------------------------------
Sanitização confiável                         OK básico, precisa maturar
Output determinístico por domínio             Parcial
Separação hipótese vs fato                     OK via camada Zeus
Gateway briefing útil                          Ainda fraco
Content briefing útil                          Sim
Secret scan em todo output                     OK
```

Recomendação atual: manter manual. Evoluir primeiro o sumarizador por domínio, especialmente gateway.

## Troubleshooting

```text
Sintoma                                  Ação
---------------------------------------- ---------------------------------------
HONCHO_API_KEY missing                   Verificar item/field no 1Password
Secret scan FAIL                         Não enviar output; corrigir redator
Gateway rodada fraca                     Usar agregados determinísticos, não bruto
Content sem conclusão útil               Conferir categorias em collect_content()
stderr com warning Python                Corrigir antes de reportar PASS
```

## Validação manual rápida

```bash
python3 -m py_compile \
  /root/mgs-agent/experiments/honcho-spike/run_targeted_rounds.py \
  /root/mgs-agent/experiments/honcho-spike/manual_briefing.py \
  /root/mgs-agent/experiments/honcho-spike/render_discord_briefing.py

/root/mgs-agent/scripts/run-honcho-briefing >/tmp/honcho-briefing.md
```

Depois verificar que o output não contém tokens/keys e está em formato Discord legível.

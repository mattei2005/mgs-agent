# Hermes busy input steering — diagnóstico e rollout MGS

## Quando usar

Quando o usuário envia uma segunda mensagem enquanto o agente aparece como ocupado/“digitando” e ela só é respondida depois da primeira resposta, ou quando quer que complementos sejam incorporados à resposta em andamento.

## Modelo mental

`display.busy_input_mode` controla o que uma nova mensagem de texto faz enquanto a sessão já está executando:

- `queue` — preserva o turno atual e agenda a mensagem como próximo turno. Sintoma: primeira resposta termina; depois o agente responde à segunda mensagem separadamente.
- `interrupt` — interrompe/redireciona a execução atual. Não é o modo correto quando o objetivo é preservar o trabalho e consolidar a resposta.
- `steer` — chama o mecanismo `/steer`, que injeta o texto no turno ativo no próximo ponto seguro de ferramenta, usando o marcador out-of-band confiável. É o modo correto para complementos durante diagnóstico/execução.

O recurso existir no código não significa estar ativo no profile. Nunca responder “já está ativo” sem ler o valor vivo.

## Diagnóstico mínimo

1. Ler `display.busy_input_mode` no `config.yaml` vivo do profile.
2. Verificar overrides legados/ambiente: `busy_text_mode` e `HERMES_GATEWAY_BUSY_INPUT_MODE` quando presentes.
3. Validar o mirror versionado correspondente em `/root/mgs-agent/profiles/<agent>-config.yaml` para detectar drift.
4. Se necessário, confirmar o valor resolvido com o Python do venv Hermes e o contexto do profile.
5. Diferenciar configuração em disco de runtime já carregado: o gateway mantém `_busy_input_mode` em memória; uma alteração de arquivo pode exigir restart seguro.

Nota: com `busy_input_mode=steer`, `_load_busy_text_mode()` pode resolver `interrupt` por desenho interno; o gate principal de steer é `_load_busy_input_mode()`. Não tratar isso isoladamente como falha.

## Cobertura MGS obrigatória de payload

Rodolfo definiu que o padrão mid-turn vale para **qualquer tipo de mensagem** enquanto o agente está ocupado:

- texto;
- imagem sem caption;
- imagem com texto;
- áudio/voice sem texto adicional;
- áudio com texto;
- múltiplos anexos e demais arquivos suportados pelo Discord/Hermes.

O Hermes stock pode limitar `AIAgent.steer()` a uma string, mas isso não autoriza o gateway MGS a mandar mídia para o próximo turno. O adapter já normaliza/cacha a mídia antes do busy handler; o runtime deve construir uma string de steer que preserve caption/transcrição e os marcadores/caminhos locais dos anexos, permitindo ao agente chamar `vision_analyze`, processamento de áudio ou a ferramenta adequada dentro do mesmo turno. Invariantes:

1. Payload multimodal chega uma vez ao turno ativo.
2. Não é replayado novamente como próximo turno após steer bem-sucedido.
3. Caption/transcrição e todos os anexos permanecem associados ao evento original.
4. Falha real de normalização/steer é explícita; não chamar `queue` de sucesso.
5. O smoke final cobre texto, imagem, imagem+texto, áudio e áudio+texto.

## Aplicação multiagente MGS

Para Zeus, Atena, Ares e Hera:

1. Inventariar live + mirror antes da alteração.
2. Aplicar no live pelo CLI oficial, evitando edição direta bloqueada de config sensível:

```bash
hermes -p <agent> config set display.busy_input_mode steer
```

3. Atualizar o mirror versionado do mesmo agente para `steer`.
4. Carregar YAML de todos os pares e exigir `4/4 live=steer` e `4/4 mirror=steer` antes do restart.
5. Registrar audit log, atualizar `infra-inventory.json` e enviar REPORT-INFRA no canal dedicado; não colar o bloco na thread operacional.
6. Reiniciar gateways com finalizer detached; agentes executores primeiro e Zeus por último. Nunca reiniciar Zeus em foreground durante tool calls.
7. Fazer validação pós-restart: serviços `active/running`, novos timestamps/PIDs, config resolvida `steer`, ausência de traceback/OOM/auth failure recente.
8. Fazer smoke funcional real: iniciar uma tarefa com ferramenta, enviar complemento durante a execução e confirmar uma única resposta final incorporando as duas mensagens.

## Limites que devem ser explicados

- Steer depende de haver um turno ativo e um próximo ponto seguro, normalmente após tool call.
- Se o complemento chegar depois da resposta final, ele vira novo turno.
- Se o agente ainda estiver iniciando ou a mensagem chegar depois do encerramento do turno, ela pode virar próximo turno; isso não se aplica a mídia recebida enquanto o turno já está ativo.
- Steer melhora consolidação, mas não justifica prometer fusão absoluta em qualquer timing.

## Pitfalls

- Confundir “mid-turn steering é nativo” com “o profile está configurado em steer”.
- Usar `queue` esperando consolidação; queue foi feito para separar turnos.
- Usar `interrupt` para complementos e perder trabalho/tool calls em andamento.
- Alterar só o live ou só o mirror, criando drift que reaparece em sync/update.
- Declarar concluído após validar YAML, sem restart/runtime e sem smoke funcional.
- Reiniciar todos os gateways em foreground a partir da conversa do Zeus.

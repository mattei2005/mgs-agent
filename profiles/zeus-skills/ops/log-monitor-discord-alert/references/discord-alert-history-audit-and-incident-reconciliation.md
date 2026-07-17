# Auditoria histórica de alertas Discord e reconciliação de incidentes

Use quando Rodolfo pedir para revisar alertas vermelhos de uma janela, separar o que segue aberto do que já foi corrigido e apontar apenas ações reais.

## Procedimento

1. **Defina a janela por timestamp UTC**, não por quantidade de mensagens. Registre início, fim e total varrido.
2. **Leia os objetos completos da API Discord**, incluindo `embeds`, `message_reference`, `color`, `fields` e autor. Se a ferramenta resumida de mensagens omitir embeds, use a API Discord autenticada pelo bot do profile e pagine com `before=<oldest_id>` até atravessar o cutoff.
3. **Reduza e sanitize na origem**:
   - nunca imprima token, cookie, autorização ou segredo;
   - retenha apenas ID, timestamp, autor, título, cor, campos sanitizados e referência;
   - agrupe repetições pelo incidente/título + assinatura normalizada, removendo timestamps/hashes voláteis.
4. **Classifique cor com precisão**. Para MGS, vermelho canônico é `15158332`; não misture laranja/amarelo com vermelho sem rotular separadamente.
5. **Reconcilie cada alerta em ordem cronológica**:
   - procure mensagem verde/resolução que referencie o alerta original;
   - depois valide o estado atual no runtime, state file e log canônico;
   - uma mensagem verde sozinha não prova saúde atual;
   - um log saudável atual sem resolução registrada prova estado técnico, mas a lacuna de comunicação deve ser indicada.
6. **Conte incidentes, não apenas mensagens**. Um monitor repetindo o mesmo alerta a cada ciclo é um incidente ativo com spam, não dezenas de falhas independentes.
7. **Cheque o produtor do alerta**. Resolutores que ignoram mensagens do próprio bot podem deixar alertas Zeus-authored sem tratamento automático; isso deve ser verificado explicitamente.
8. **Reporte conclusão primeiro**: incidentes abertos, incidentes resolvidos, evidência atual, risco e ação proposta. Não despeje IDs/logs completos no Discord.

## Guardrail sensível e auto-push

Quando o auto-commit bloquear um path apenas por palavra sensível no nome:

1. identifique o path exato no log do watcher;
2. rode secret scan sem imprimir snippets/valores;
3. confirme Git (`HEAD`, `origin/main`, mudanças locais) para separar “push pendente” de “mudanças ainda não commitadas”;
4. prefira renomear o artefato seguro quando isso não exigir operação crítica; se renomear/remover path cair no Critical Subset, proponha allowlist **exato e mínimo** após scan limpo, nunca relaxe o regex global;
5. preserve o bloqueio quando houver qualquer hit ou dúvida.

## Anti-spam correto para falhas imediatas

“Alertar na primeira detecção” não significa alertar em todos os ciclos. A lógica correta é:

- primeira ocorrência nova/estado transitando para bloqueado → alerta imediato;
- bloqueio persistente → respeitar `last_alert_sent` e a janela anti-spam;
- mudança material no detalhe/target → novo alerta imediato pode ser permitido;
- recuperação confirmada → uma mensagem verde e reset do estado.

Evite branches como `if guardrail_blocked: SEND_ALERT=true` sem verificar primeira ocorrência ou anti-spam; isso transforma um único incidente em mentions a cada execução.

## Verificação mínima

- janela e paginação completas;
- contagem por cor e por incidente;
- relação alerta → resolução quando disponível;
- live state/log/runtime confirma aberto ou resolvido;
- secret scan seguro para bloqueios por nome;
- monitor não repete push em cada ciclo durante falha persistente;
- relatório final diferencia fato confirmado, lacuna e risco.

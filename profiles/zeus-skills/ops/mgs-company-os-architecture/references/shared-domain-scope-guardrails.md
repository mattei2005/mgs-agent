# Guardrails de escopo compartilhável entre agentes

Use quando um agente de equipe pode acessar uma conta ou inventário que também contém ativos particulares, externos ou de outra área. O objetivo é permitir apenas os ativos corporativos aprovados sem confirmar que os itens filtrados existem.

## Procedimento

1. **Defina o limite de confiança antes da implementação.** Registre quais agentes e canais são restritos e quais conversas privadas do executivo são exceção. Autorização de usuário não deve ampliar automaticamente o conjunto compartilhável.
2. **Adote uma allowlist positiva com proveniência por entrada.** Inclua cada identificador somente quando uma fonte canônica afirmar explicitamente que o ativo pertence ao escopo corporativo; preserve um ponteiro auditável para essa afirmação. Antes de publicar a allowlist, reconcilie todas as evidências em uma fonte afirmativa de ownership e faça o checker exigir cobertura literal exata de 100% dos identificadores — validar apenas que o arquivo de fonte existe não detecta entradas sem prova. Lista de monetização, conjunto operacional protegido, inventário de hospedagem, origem de receita, campanha, manutenção, DNS/HTTPS alcançável ou capacidade técnica de acesso não prova propriedade. Nunca crie denylist de itens particulares: a própria denylist revela o inventário protegido.
3. **Resolva um handoff bloqueado sem contornar o gate.** Quando o agente executor rejeitar o alvo ausente, pare antes de enviar o handoff e peça ao executivo uma confirmação normal e exata de duas coisas: ownership corporativo e autorização para incluir o identificador no escopo compartilhável. Após a confirmação, grave primeiro a afirmação literal na fonte canônica de ownership e depois a entrada ordenada na allowlist; só então repita o `check` para cada consumidor que participará do fluxo. A autorização da tarefa não deve ser reinterpretada silenciosamente como prova de ownership quando o executivo ainda não afirmou isso.
4. **Mantenha um registro mínimo e compartilhável.** Grave apenas identificadores corporativos aprovados, consumidores, fonte, versão e semântica de `default=deny`. Não copie para ele nomes externos, projetos particulares, caminhos de hospedagem ou justificativas de bloqueio.
4. **Imponha o gate antes da ferramenta.** Toda listagem, confirmação, consulta de provedor ou operação sobre um alvo deve passar por um checker determinístico antes de RunCloud, Cloudflare, WordPress, Drive ou API equivalente. Filtrar somente a resposta é insuficiente porque a consulta já pode ter exposto dados a logs, traces ou contexto.
5. **Separe três modos do checker.**
   - `check`: um alvo, correspondência exata e fail-closed;
   - `filter`: pedido misto, retorna apenas os alvos permitidos e nunca ecoa os bloqueados;
   - `list`: enumera somente a allowlist, nunca o inventário global do provedor.
6. **Normalize sem ampliar.** Aceite URL completa e alias `www` somente quando o host canônico estiver explícito. Não autorize subdomínio por sufixo, wildcard, IP, credencial embutida ou similaridade de nome.
7. **Use recusa sem confirmação lateral.** O agente não repete o alvo bloqueado nem confirma existência, propriedade, relação com executivo, provedor, servidor, conta, caminho ou motivo. A resposta pública deve ser genérica e estável.
8. **Aplique defesa em profundidade.** Atualize a política institucional, a fonte de verdade, o SOUL live e seu mirror versionado, e faça o agente chamar o checker. Trate separação de conta/token e privilégio mínimo como camada adicional: prompt + checker obrigatório não substituem isolamento de credencial.
9. **Teste com identificadores sintéticos.** Use domínios reservados como `*.invalid`; nunca transforme nomes particulares reais em fixture, log ou evidência. Cubra alvo permitido, desconhecido, pedido misto, URL/porta, `www`, subdomínio implícito, credencial embutida, registro inválido e ausência de eco na recusa.
10. **Valide arquivo e runtime separadamente.** Primeiro determine se o checker relê o registro em cada chamada ou mantém cache. Quando somente um registro dinâmico mudou, valide `validate`, `list`, `check` e `filter` diretamente e não reinicie gateways sem necessidade; mudança de prompt/política ainda exige cutover de sessão pela rotina do `discord-ops`. Um one-shot novo comprova que o SOUL em disco e o modelo obedecem, mas não prova que uma sessão Discord antiga recarregou instruções.
11. **Institucionalize e reporte.** Registre decisão/política, caso de regressão, checkpoint e audit; atualize inventário e REPORT-INFRA para script, data operacional, AGENT/SOUL ou contexto estrutural.

## Critérios de aceitação

- Registro ordenado, único, sem wildcard e validado por schema.
- Cada host permitido aparece literalmente na fonte afirmativa de ownership, e o checker rejeita o registro inteiro se a cobertura não for 100%; um ponteiro genérico para um arquivo existente não basta.
- A suíte de regressão de produção passa após a mudança; se ela contém uma asserção intencional da cardinalidade da allowlist, atualize essa asserção junto com a nova entrada em vez de aceitar uma falha ou enfraquecer o teste.
- O novo alvo passa em `check` como host exato, URL completa e alias `www` para cada consumidor autorizado antes de qualquer handoff.
- DNS e HTTPS podem comprovar existência e saúde do host, mas nunca substituem a evidência afirmativa de propriedade corporativa.
- Após qualquer remoção, host exato e alias `www` ficam negados para cada consumidor, com resposta genérica e sem eco do alvo.
- Falha do registro ou alvo ambíguo resulta em negação antes de qualquer provider lookup.
- Pedido misto produz somente os itens corporativos permitidos; nenhum valor bloqueado aparece em stdout, resposta ou log compartilhado.
- SOUL live e mirror têm hashes idênticos.
- Testes determinísticos passam e um canário novo de cada agente demonstra a política no runtime de destino.
- Inventário, audit, checkpoint e REPORT-INFRA têm readback.

## Pitfalls

- **Não use inventário do provedor nem lista operacional, protegida ou parceira como allowlist — acesso, manutenção ou monetização transformam envolvimento técnico em falsa propriedade corporativa.**
- **Não envie o handoff antes de repetir o checker após a inclusão — uma mensagem cross-agent pode iniciar trabalho sobre um alvo que o runtime ainda deve negar.**
- **Não deixe uma asserção de contagem da allowlist quebrada — ela é um contrato de mudança deliberada, então atualize-a somente junto com a entrada autorizada e mantenha os demais testes intactos.**
- **Não infira propriedade pelo nome do domínio — similaridade lexical não é fonte canônica.**
- **Não liste os itens excluídos nem a contagem deles ao usuário — metadados do filtro também podem revelar o tamanho do inventário protegido.**
- **Não declare proteção ativa após editar somente arquivos — gateways long-lived podem continuar com o prompt anterior até um cutover validado.**

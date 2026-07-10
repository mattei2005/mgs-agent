# DigitalTRChat roxo em template — diagnóstico por página e mitigação

## Contexto

Rodolfo explicou um falso positivo importante no fluxo de templates do DigitalTRChat/ChatPion:

- Um template pode estar vinculado a muitas páginas e vários seguradores/sites.
- Ao clicar em `Run Approval`, o sistema do Ciro pode escolher primeiro uma página com restrição de envio.
- Quando a primeira página está restrita, a barra do template pode ficar inteira roxa, mesmo que outras páginas/seguradores estejam saudáveis.
- Portanto, `roxo` no template não deve decidir troca de mensagem sozinho.

## Evidência observada

No DigitalTRChat, a tela de broadcast expõe o erro real por subscriber/campanha:

```text
/messenger_bot_enhancers/subscriber_broadcast_campaign
```

Tabela visível:

```text
First Name | Last Name | Subscriber id | Sent at | Delivered at | Sent response
```

Erro confirmado:

```text
(#2022) You're temporarily restricted from messaging users until July 22 at 11:44 PM.
```

Interpretação: a página/perfil usado para envio está temporariamente restrito para mensagens. Isso explica falha de entrega e pode contaminar o approval/template com roxo.

## Fontes práticas

1. **DigitalTRChat / ChatPion**
   - Usar a página `subscriber_broadcast_campaign` para ver `Sent response` real.
   - Melhor alvo técnico: endpoint AJAX interno que alimenta essa tabela.
   - Se endpoint interno não for fácil, usar browser automation logada para extrair a tabela.

2. **Smart Bidding > Accounts > Messenger > Page**
   - Usar como painel operacional para bloquear/pausar páginas restritas.

## Mitigação operacional no Smart Bidding

### Restrição temporária de envio

Quando o erro for temporário, como `#2022 ... restricted until DATA`:

1. Abrir `Smart Bidding > Accounts`.
2. Selecionar `Messenger`.
3. Abrir aba `Page`.
4. Localizar a página afetada.
5. Clicar no lápis/editar.
6. Abrir modal `Edit Messenger Page`.
7. Ir para aba `Broadcast`.
8. Preencher `Restricted Until` com a data/hora do erro.
9. Salvar.

Texto da tela observado:

```text
While set to a future date, the scheduling automation won't route broadcasts to this page
```

Efeito: a automação não roteia broadcasts para essa página até a data futura. Isso remove a página restrita do pool e reduz risco de o `Run Approval` escolher essa página primeiro.

### Bloqueio direto da página

Quando a página/perfil estiver quebrado, permanentemente restrito ou não deve operar:

1. Mesmo modal `Edit Messenger Page`.
2. Aba `Page`.
3. Campo `Status`.
4. Trocar para `Blocked`.
5. Salvar.

Opções vistas no dropdown:

```text
Ready
Campaign
Broadcast
Blocked
Review
Incomplete
```

## Nova semântica do roxo

```text
Sinal                             Ação correta
--------------------------------- ---------------------------------------------
Roxo + #2022 temporário           Marcar Restricted Until; não trocar copy ainda.
Roxo + página/perfil permanente   Status = Blocked ou migrar/remover página.
Roxo depois de restringir páginas Investigar developer/perfil/template/sistema.
Roxo sem causa identificada       Extrair Sent response antes de mexer em mensagem.
```

## Decisão de template

Não criar um template por segurador como solução padrão: tecnicamente limpo, mas operacionalmente insustentável em escala.

Preferir:

- manter templates compartilhados quando saudável;
- isolar páginas/seguradores problemáticos via `Restricted Until` ou `Blocked`;
- só separar templates por grupo de risco/site/idioma quando houver contaminação recorrente.

## Regra executiva

`Roxo` é fila de diagnóstico, não fila automática de troca de mensagem.

Antes de trocar copy por roxo, identificar se a causa é:

- página temporariamente restrita;
- página permanentemente bloqueada;
- perfil/segurador caiu;
- developer/app caiu;
- erro real do template/copy;
- bug de agregação/primeira página do Ciro.

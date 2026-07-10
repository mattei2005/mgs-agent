## Hard gate — referência, backend e pré-requisitos antes de produzir

Quando o pedido criativo exigir uma referência externa específica, comparação entre backends (ex.: GPT vs Grok), ou um asset/estilo que depende de insumo visual, **não produza uma versão aproximada no escuro** se a referência/backend estiver bloqueado.

Fluxo obrigatório:

```text
1. Validar acesso real à referência/asset/backend antes de criar.
2. Se a referência não puder ser lida integralmente, tentar rotas razoáveis: import/download, oEmbed/thumbnail/frame, browser/headless, cookies/sessão autenticada quando permitido.
3. Se o backend solicitado estiver sem autenticação/credencial, abrir o fluxo de reauth/configuração ou pedir o artefato necessário.
4. Se ainda estiver bloqueado, parar a produção e reportar o blocker com evidência curta e próximo passo concreto.
5. Só produzir depois que o insumo crítico estiver acessível ou depois de o usuário aprovar explicitamente trabalhar com fallback parcial.
```

Regra de qualidade: se Rodolfo pedir “faça com GPT e Grok”, a entrega deve especificar claramente qual asset veio de qual backend. Não rotular uma versão local/GPT como Grok. Se Grok estiver bloqueado, dizer `Grok bloqueado` e resolver a autenticação antes de prometer comparação.

Para vídeos de convite/peças inspiradas em referência, primeiro analisar a referência e extrair linguagem visual/ritmo/composição; depois gerar o criativo. O usuário corrigiu explicitamente que começar a criar antes de resolver a referência é erro operacional.

Ver também: `references/video-reference-and-backend-gating.md` e `references/personal-invitation-video-workflow.md`.

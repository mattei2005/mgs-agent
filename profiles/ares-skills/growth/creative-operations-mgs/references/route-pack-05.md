## Padrão para vídeo curto

Para reels/shorts/stories em vídeo, use cenas simples:

```text
Duração sugerida: 15s / 20s / 30s

Cena 1 — 0-3s
Visual:
Texto na tela:
Fala/locução:
Objetivo:

Cena 2 — 3-8s
...

Cena final
CTA:
```

### Variação de vídeo não é só legenda/overlay

Quando o pedido for “faça uma variação desse criativo/vídeo”, trate como recriação criativa, não como edição superficial, salvo se o usuário pedir explicitamente apenas trocar legenda/copy no mesmo vídeo.

```text
Pedido/sinal do usuário                         Interpretação operacional
──────────────────────────────────────────────  ─────────────────────────────────────────────
“variação desse criativo”                       Nova peça com linguagem derivada da referência.
“mesma oferta / mesmos gatilhos”                Manter promessa/copy central, não necessariamente reaproveitar frames.
“mantendo o carro”                              Preservar tipo/cor/modelo aproximado do carro como referência visual.
“outra pessoa, outro cenário, outra voz”        Recriar vídeo do zero: novo apresentador, novo ambiente e nova narração.
“só troca a copy/legenda”                       Aí sim é permitido editar o mesmo vídeo com overlay.
```

Antes de entregar uma variação final, confirme que há mudança real em pelo menos 3 dimensões quando o usuário pediu recriação: pessoa/apresentador, cenário, enquadramentos/cenas, voz/narração, ritmo/movimento, props/ambiente. Se o resultado for apenas imagem animada, slideshow ou motion leve por limitação de backend, rotule claramente como **preview**, não como vídeo final profissional.

Para anúncios de financiamento/auto com gatilhos fortes, mantenha a oferta legível e curta, mas evite alterar o valor ou a promessa. Exemplo de checagem obrigatória: `Sem Entrada`, `Parcelas a partir de R$299`, `Score Baixo`, `CTA` aparecem corretos e sem erro de leitura.

### Convites pessoais em vídeo — integração profissional de foto e texto

Quando o vídeo for convite pessoal/familiar com foto de criança/pessoa e referência visual, trate como **composição por slides/cenas**, não como fundo + foto quadrada + caixas de texto.

Regras obrigatórias:

```text
Item                       Regra de qualidade
─────────────────────────  ─────────────────────────────────────────────
Foto da pessoa/criança      Integrar em elemento do cenário: para-brisa, círculo, porta-retrato, placa, janela etc.
Máscara da foto             Acompanhar o formato real do elemento; nunca entregar foto quadrada/retangular colada se o cenário pede curva/círculo.
Textos                      Usar placas, fitas, madeira, pergaminho, folhas ou elementos do tema; evitar caixas brancas/TXT sobreposto.
Estrutura                   Preferir slides: 1) hero/foto, 2) convite, 3) dados fixos e legíveis.
Dados críticos              Data, horário e endereço devem ficar estáveis tempo suficiente para leitura em celular.
Validação                   Gerar contact sheet e checar se foto/textos parecem parte do design antes de entregar.
```

Se o usuário disser que “os fundos ficaram bons” mas criticar foto/texto, preserve o fundo aprovado e refaça **layout/compositing**, não gere novo conceito do zero. Ver detalhe em `references/personal-invitation-video-workflow.md`.

### Variação rápida de copy em vídeo existente

Quando o usuário enviar um vídeo base/anexo e pedir uma **variação mantendo o mesmo carro/produto**, trate o asset original como referência obrigatória antes de editar.

Fluxo mínimo:

```text
1. Baixar/importar o anexo real.
2. Gerar contact sheet do original e analisar produto, cenas, textos e áreas seguras.
3. Trocar apenas a copy/overlay quando o pedido for variação rápida, sem alterar o carro/produto.
4. Gerar contact sheet da variação e validar visualmente a oferta exata antes de entregar.
5. Se houver valores monetários, confirmar no preview que `R$299`, `R$399` etc. não perderam símbolo/dígito por escaping de ferramenta.
6. Sanitizar metadata e entregar somente `.metadata-clean.*`.
```

Ver detalhe em `references/video-copy-variation-from-existing-asset.md`.

### Gate obrigatório para vídeo com referência externa ou backend específico

Quando o usuário pedir vídeo criativo baseado em **referência externa** (YouTube Shorts/Reels/TikTok/link) ou exigir backend específico (**GPT/OpenAI** e/ou **Grok/xAI**), não comece a produzir a peça final antes de validar os pré-requisitos.

```text
Etapa  Regra
─────  ─────────────────────────────────────────────────────────────
1      Capturar/analisar a referência real: vídeo, frames ou anexo.
2      Se o vídeo externo exigir login/cookie/anti-bot, tentar rotas técnicas razoáveis; se continuar bloqueado, parar e reportar o bloqueio antes de criar.
3      Validar backend solicitado: GPT/OpenAI via image_generate; Grok/xAI via `/root/mgs-agent/scripts/mgs-grok-generate.py --profile ares`, conforme pedido. O wrapper deve resolver o profile explícito no contexto Hermes, não apenas por `HERMES_HOME`.
4      Separar autenticação de capacidade comercial. Antes de lançar job longo/background xAI, fazer preflight bounded: confirmar credencial no profile e executar um canário pequeno. `403 team has no credits` é bloqueio de billing/licença, mesmo com chave válida; não repetir a submissão.
5      Se Grok/xAI estiver sem autenticação ou créditos e o usuário tiver exigido Grok, não substituir por GPT/local/Veo sem autorização explícita e nunca rotular fallback como Grok. Se Grok foi apenas escolha interna do Ares e o usuário pediu o resultado, é permitido usar um backend corporativo já aprovado: listar modelos disponíveis, gerar um canário, validar o arquivo por ffprobe/contact sheet e registrar o provider real.
6      Só produzir a versão final depois que referência e backends mínimos estiverem resolvidos ou o fallback permitido tiver passado no canário.
```

Regra prática: se o pedido é “faça igual/ inspirado neste link” e o link não foi visto de verdade, o status correto é `bloqueado`, não `em_criacao`. Entregue evidência curta do bloqueio e a ação necessária para desbloquear.

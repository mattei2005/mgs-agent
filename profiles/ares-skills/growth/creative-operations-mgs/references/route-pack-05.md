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

Quando o conjunto de anúncios trata o **mesmo produto como categoria** — por exemplo, três anúncios de “e-bike” — e o usuário pede exemplares diferentes, cada anúncio deve usar uma identidade de produto realmente distinta, não a mesma bike reencenada. Validar uma imagem-base mecânica por exemplar e derivar da própria bike os ângulos, os recursos citados, a locução e a ordem do review; nunca narrar componentes que a imagem-base não comprova.

Para classificar visualmente uma bicicleta como **e-bike**, cor, geometria ou aparência moderna não bastam. Antes da animação, a imagem-base precisa comprovar ao mesmo tempo: bateria elétrica plausível e visível, motor no cubo ou central, e display/controle de assistência no guidão; validar também cabo de potência e integração mecânica quando visíveis. Se um desses três sinais principais estiver ausente ou ambíguo, reprovar a base e gerar outra — nunca entregar ou rotular a bicicleta como elétrica.

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
7      Preflight de duração deve usar o limite vivo do endpoint. No xAI validado, reference-to-video rejeita duração acima de 10s e video edit rejeita fonte acima de 8,7s; tratar a mensagem da API como verdade se o limite mudar. Para edit, reduzir a fonte de forma explícita (trim ou aceleração controlada) antes do upload, sem repetir a chamada rejeitada.
8      Se geração multi-shot alterar rodas/quadro/texto ou criar ghosting, não entregar. Preferir uma imagem-base Grok aprovada mecanicamente por variante e então image-to-video com uma tomada contínua, movimento material de câmera/ambiente e QA quadro a quadro. Se o resultado for só motion leve, continua sendo preview; só promover a final quando ffprobe, contact sheet e inspeção visual aprovarem consistência do produto, copy e enquadramento.
9      Referência em vídeo com fala deve ser analisada como arquivo audiovisual completo antes do prompt final: validar duração real, transcrever a locução com timestamps, mapear cenas/ações por tempo e registrar música/efeitos. Contact sheet sozinho não comprova narrativa, timing nem áudio.
10     Em vídeo Grok multi-shot, inspecionar transições em pelo menos 4 fps quando o QA de 1–2 fps indicar dissolves. Se houver dupla exposição, remontar somente trechos comprovadamente limpos com cortes secos e revalidar o vídeo inteiro, áudio e sequência antes de sanitizar.
```

Regra prática: se o pedido é “faça igual/ inspirado neste link” e o link não foi visto de verdade, o status correto é `bloqueado`, não `em_criacao`. Entregue evidência curta do bloqueio e a ação necessária para desbloquear.

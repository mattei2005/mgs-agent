# CAR video reference recreation — lessons from Rodolfo/Geizian correction

Use this reference when a gestor asks Hera to create a **variation of an existing car-financing video** using a reference video, ad library, or prior creative.

## Core correction

A “variation” of a CAR video reference means recreating the **audiovisual language**, not merely changing text or placing captions over the same footage.

Rodolfo explicitly rejected:

```text
- same original video with new caption overlay;
- static AI image with zoom/pan presented as video;
- generic premium ad that ignores the reference rhythm;
- saying GPT video path is unavailable without checking prior GPT+Grok workflow precedent.
```

## What must be preserved from the reference

```text
Dimension                  Preserve / translate into the new creative
─────────────────────────  ─────────────────────────────────────────────
Format                     Vertical 9:16, social ad/Reels/TikTok feel.
Energy                     Real seller/concessionária, direct-response tone.
Rhythm                     Fast cuts, multiple camera angles, 1–3s moments.
Structure                  Seller → car front → angle/lateral → interior → seller CTA.
Text style                 Large uppercase, white/yellow, black outline/shadow, lower third.
Car                        Same category/color/protagonism when requested.
Voice                      Natural Brazilian seller voice, not institutional narration.
Scenario                   Realistic dealership/showroom/lot; not generic corporate set.
```

## Correct pre-generation response when prompt is being refined

When Rodolfo/Geizian is reviewing the prompt before generation, show:

```text
Entendimento do pedido
──────────────────────
[What Hera understood from the reference and requested changes]

Prompt que vou usar
───────────────────
[Editable prompt with scenes, text overlays, voice, style and constraints]

Pontos que assumi
─────────────────
- provider path: GPT preview / Grok preview / both
- duration and format
- vertical and language
- whether this is preview or final
```

Then wait for the gestor’s edited prompt if they indicate they will review it.

## Provider handling

```text
Case                              Action
────────────────────────────────  ─────────────────────────────────────────────
No provider specified             Use GPT/OpenAI by default.
GPT + Grok requested              Generate both or report exact provider blocker.
Prior thread cited                Import/read the thread before contradicting history.
GPT output is only keyframe/motion Label as GPT preview/structural, not final video.
Grok output has better dynamics    Label as Grok preview/social/dynamic and validate contact sheet.
```

Known precedent: thread `1516611205517807680` had a valid operational comparison pattern:

```text
GPT preview   = cleaner/polished/offer-forward.
Grok preview  = more dynamic/social/closer to native video.
V003 híbrida  = candidate combining GPT clarity with Grok movement.
```

## Quality gate before delivery

Do not deliver as final unless the contact sheet confirms:

- [ ] not just a single AI image with zoom;
- [ ] multiple visual moments or at least a clearly dynamic generated clip;
- [ ] seller/concessionária/car pattern visible;
- [ ] all values/text are correct (`R$299`, not malformed);
- [ ] CTA wording is natural (`TOQUE E SAIBA MAIS` or `TOQUE EM “SAIBA MAIS”`);
- [ ] metadata-clean file is used;
- [ ] if only preview, the response says preview clearly.

## Prompt skeleton for CAR financing variation

```text
Crie uma variação do vídeo de referência, mantendo o mesmo estilo de anúncio real de concessionária brasileira, mas com outra pessoa, outro cenário dentro/fora de uma loja de veículos e outra voz.

Formato vertical 9:16, [DURAÇÃO] segundos, estilo Reels/TikTok/Meta Ads, aparência de gravação real com celular. Um consultor ou consultora brasileira apresenta um hatch compacto branco semelhante ao carro da referência, preservando cor, categoria e protagonismo do veículo.

O vídeo deve ter cortes rápidos e naturais:
1. apresentador falando para câmera ao lado do carro;
2. close da dianteira do carro branco;
3. take lateral/diagonal do veículo;
4. detalhe do interior, volante e painel;
5. apresentador apontando para o carro;
6. CTA final olhando para a câmera.

Usar textos grandes em caixa alta, branco e amarelo com contorno preto, estilo oferta direta de concessionária, sempre no terço inferior.

Textos na tela:
- “FINANCIE SEU VEÍCULO”
- “COMPRE SEM ENTRADA”
- “PARCELAS A PARTIR DE R$299”
- “MESMO COM SCORE BAIXO”
- “TOQUE E SAIBA MAIS”

A voz deve ser natural, de vendedor brasileiro, com energia comercial:
“Quer financiar seu veículo? Você pode comprar sem entrada, com parcelas a partir de R$299, mesmo com score baixo. Toque e saiba mais e consulte agora.”

O resultado deve parecer um vídeo real de vendedor em concessionária, não slideshow, não imagem com zoom, não anúncio institucional genérico.
```

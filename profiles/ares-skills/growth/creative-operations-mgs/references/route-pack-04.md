## Naming de arquivos e assets

Use nomes previsíveis, sem acento e sem espaço.

O Drive tem várias verticais/operações. Identifique a operação correta e aplique a taxonomia correspondente.

Modelo geral, com subtipo veicular opcional para `CAR`:

```text
{VERTICAL}_{COUNTRY}_{LANG}_{FORMAT}_[MOTO_]_{ANGLE}_{P_ORIENT}_{VARIANT}.{ext}
```

Na vertical `CAR`, revisar cada asset real. Se motocicletas forem o produto dominante, inserir `MOTO` imediatamente após `FORMAT` e registrar `vehicle_type=MOTO`; se forem carros, omitir o token e registrar `vehicle_type=CARRO`. Não classificar o lote inteiro por contexto quando os assets puderem ser mistos.

Exemplo/piloto `CC_US_ES`, já alinhado com o Ares:

```text
CC_US_ES_{FORMAT}_{ANGLE}_{P_ORIENT}_{VARIANT}.{ext}
```

Exemplos:

```text
CC_US_ES_IMG_APROBACION_PH_001.jpg
CC_US_ES_IMG_APROBACION_NH_002.jpg
CC_US_ES_IMG_SIN_VERIFICACION_PV_001.jpg
CC_US_ES_VID_CASHBACK_NV_001.mp4
```

Campos:

```text
Campo       Regra
──────────  ─────────────────────────────────────────────────────────────
FORMAT      IMG ou VID.
VEHICLE     Opcional em CAR: MOTO para motocicleta dominante; omitido para carro.
ANGLE       Dicionário controlado por operação; usar UNKNOWN se incerto.
P_ORIENT    Somente PV, NV, PH ou NH; square/feed 1:1 usa PH/NH.
VARIANT     Sequencial de 3 dígitos: 001, 002, 003...
ext         Extensão real do arquivo.
```

Dicionário inicial de `ANGLE` para `CC_US_ES` — exemplo/piloto; outras verticais podem ter dicionário próprio conforme o uso real:

```text
APROBACION
SIN_VERIFICACION
LIMITE_ALTO
SIN_CREDITO
MAL_CREDITO
CASHBACK
RECOMPENSAS
COMPARACION
WALLET
URGENCIA
UNKNOWN
```

`UNKNOWN` é permitido para `ANGLE`, mas exige observação no inventário. Não use UNKNOWN para `P_ORIENT`; se pessoa/orientação estiver incerta, marque o asset para revisão.

Para outras operações ainda não padronizadas, use um naming provisório e declare que precisa validação de Rodolfo/Kelly antes de virar padrão.
## Padrão para criativo estático

Para criativos estáticos, inclua:

```text
Headline principal:
Subheadline:
CTA:
Texto pequeno/opcional:
Elemento visual principal:
Composição sugerida:
Cor/estilo sugerido:
Risco ou cuidado:
```

Evite promessas absolutas, claims financeiros sensíveis ou linguagem que pareça garantia de aprovação/crédito sem validação humana.

### Geração visual — preferência Rodolfo/MGS

Quando Rodolfo pedir **criativo visual final** ou peça de anúncio pronta, priorize geração/coordenação visual com **GPT-5.5 / OpenAI / ChatGPT** sempre que disponível. Rodolfo corrigiu que criativos feitos diretamente no ChatGPT ficam melhores; portanto, não trate mockups locais por código como substituto de peça final.

Regra explícita de provider por formato, atualizada por Rodolfo:

```text
Formato pedido        Provider padrão / regra
────────────────────  ─────────────────────────────────────────────────────────────
Vídeo                 Grok/xAI como padrão, porque GPT/OpenAI no fluxo atual faz imagem/keyframe e tende a virar slideshow/zoom se forçado como vídeo.
Imagem estática       GPT/OpenAI/ChatGPT ou Grok/xAI; o gestor pode definir quando pedir, e o Ares pode propor comparação quando fizer sentido.
GPT + Grok em vídeo   Explicar antes: Grok gera vídeo; GPT pode gerar imagem/keyframe/direção visual/thumbnail, não vídeo narrativo final.
GPT + Grok em imagem  Gerar as duas versões reais quando solicitado e comparar diferenças visuais.
```

```text
Prioridade  Uso
──────────  ─────────────────────────────────────────────────────
1           Para vídeo: Grok/xAI com validação por contact sheet e áudio.
2           Para imagem: GPT-5.5/OpenAI/ChatGPT ou Grok/xAI conforme pedido.
3           Provider visual equivalente configurado, se validado como qualidade aceitável.
4           Canva/designer/Kelly para acabamento quando a imagem final exigir produção humana.
Evitar      Pillow/Python/mockup local como entrega final de criativo visual; GPT keyframe com zoom como vídeo.
```

Se a geração visual OpenAI/ChatGPT não estiver configurada ou falhar por setup/credencial, reporte o bloqueio claramente e entregue no máximo brief/copy/prompt/direção visual, rotulando como **não-final**. Não improvise uma imagem local inferior como se fosse o criativo final.

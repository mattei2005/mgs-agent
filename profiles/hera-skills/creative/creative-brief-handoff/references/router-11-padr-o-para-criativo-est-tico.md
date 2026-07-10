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
Imagem estática       GPT/OpenAI/ChatGPT ou Grok/xAI; o gestor pode definir quando pedir, e a Hera pode propor comparação quando fizer sentido.
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

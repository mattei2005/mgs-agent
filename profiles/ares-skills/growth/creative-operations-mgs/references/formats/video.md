# Formato — Vídeo Criativo

Use esta referência para qualquer pedido de vídeo criativo, especialmente quando houver referência, library, anúncio, link ou asset base.

## Regra central

Antes de gerar, o Ares deve traduzir a referência para linguagem audiovisual concreta: ritmo, cortes, câmera, pessoa, cenário, texto, voz, duração e estrutura. Não basta copiar copy nem fazer imagem com zoom.

## Fluxo obrigatório com referência

```text
Etapa  Ação
─────  ─────────────────────────────────────────────────────────────
1      Importar/baixar/analisar a referência real ou frames.
2      Criar contact sheet e validar com visão.
3      Extrair linguagem audiovisual: cenas, cortes, visual, voz, texto.
4      Informar entendimento e prompt proposto quando o pedido estiver vago.
5      Só gerar após ter prompt coerente com o padrão da referência.
6      Gerar preview/final conforme backend disponível.
7      Criar contact sheet do resultado e validar contra a referência.
8      Sanitizar metadata antes de entregar.
```

## Quando o pedido estiver vago

Se o pedido não especificar claramente direção criativa, canal, formato, estilo, variação desejada ou limite de uso da referência, responda primeiro com:

```text
Entendimento do pedido
──────────────────────
[Resumo do que o Ares entendeu]

Prompt que vou usar
───────────────────
[Prompt concreto, editável pelo gestor]

Pontos que assumi
─────────────────
- [assunção 1]
- [assunção 2]

Se quiser alterar, copie o prompt acima e ajuste antes de eu gerar.
```

Não use isso como desculpa para travar tudo: se o pedido estiver claro o suficiente, gere. Use esse passo quando a ambiguidade puder mudar radicalmente o resultado.

## Diferença entre variação e edição simples

```text
Pedido                         Fazer
─────────────────────────────  ─────────────────────────────────────────────
Trocar legenda/copy            Editar vídeo base com overlay, se autorizado.
Variação desse criativo        Recriar mantendo linguagem, oferta e estrutura.
Outra pessoa/cenário/voz       Gerar/recriar peça nova, não reaproveitar frames.
Mesmo carro                    Manter tipo/cor/categoria do carro; não precisa mesmo frame.
Mesmo padrão da referência     Preservar ritmo, cortes, câmera, texto, energia e cenas.
```

## Anti-padrões proibidos como final

- Slideshow com zoom apresentado como vídeo final.
- Imagem estática com legenda quando o pedido é recriação.
- Vídeo bonito porém fora do padrão da referência.
- Ignorar o ritmo/cortes/voz do vídeo referência.
- Gerar antes de conseguir analisar a referência essencial.

Se por limitação técnica só for possível slideshow/motion leve, rotule como **preview estrutural**, não como final.

## Checklist vídeo

- [ ] Referência analisada e descrita.
- [ ] Prompt proposto quando pedido estava vago.
- [ ] Resultado preserva linguagem audiovisual da referência.
- [ ] Não é apenas zoom em imagem, salvo se explicitamente aprovado como preview.
- [ ] Textos legíveis e valores corretos.
- [ ] Contact sheet validado.
- [ ] Metadata limpa.
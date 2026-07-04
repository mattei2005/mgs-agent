# CAR branded featured image — logo overlay workflow (2026-07-02)

## Contexto
Rodolfo testou um prompt para imagens Eggbev CAR/BR: fotografia ultra-realista 16:9 com carro protagonista e logo oficial do site em um pequeno painel branco no canto inferior direito.

A amostra feita no GPT tinha impacto comercial forte — carro grande, asfalto molhado, reflexos de golden hour e boa leitura como thumbnail — mas apresentou defeitos típicos de IA:

- artefato preto grande perto de uma bandeira do Brasil;
- placa com texto estranho/sem sentido;
- logo Eggbev grande demais e com aparência de banner colado;
- risco de parecer criativo de anúncio, não featured editorial.

A versão mais segura foi gerar a cena sem logo e aplicar o logo oficial posteriormente por processamento determinístico.

## Lição
Para featured image editorial com branding de site, o melhor padrão é:

1. gerar apenas a fotografia/cena;
2. deixar o canto de branding limpo;
3. aplicar o logo oficial depois;
4. validar visualmente antes de upload/publicação.

Isso evita logo deformado, lettering falso e artefatos de sobreposição.

## Prompt recomendado para carro/financiamento BR

> Crie uma fotografia publicitária ultra-realista em 16:9 relacionada ao tema de artigo sobre financiamento de carro no Brasil. O carro deve ser o protagonista, com aparência de foto profissional, iluminação cinematográfica, reflexos realistas e fundo levemente desfocado (bokeh). Varie carro, cenário, iluminação, clima e composição. Não insira texto, logotipos, marcas de montadora, placas legíveis, selos, botões ou sobreposições. Deixe o canto inferior direito visualmente limpo para receber posteriormente um pequeno painel branco de assinatura visual. Estilo premium, fotografia editorial realista, alta qualidade.

## Overlay recomendado

- usar o logo oficial do site, não redesenhado pela IA;
- painel branco pequeno no canto inferior direito;
- cantos arredondados;
- sombra discreta;
- opacidade/presença premium;
- tamanho suficiente para legibilidade, mas pequeno o bastante para não competir com o carro.

## Checklist de validação

Antes de considerar a imagem pronta:

- [ ] formato 16:9;
- [ ] carro/tema é o protagonista;
- [ ] fundo tem profundidade/bokeh sem parecer borrado demais;
- [ ] não há texto, placa legível estranha, bandeira deformada ou artefato grande;
- [ ] logo está correto e legível;
- [ ] painel não parece banner publicitário;
- [ ] imagem parece editorial publicável.

## Veredito comparativo desta sessão

A imagem GPT venceu em impacto visual, mas perdeu em segurança editorial por artefatos e branding grande demais. A imagem Atena ficou mais limpa e publicável. O caminho ideal é regenerar usando a direção visual forte do GPT, mas com branding aplicado deterministicamente e sem elementos propensos a artefato.

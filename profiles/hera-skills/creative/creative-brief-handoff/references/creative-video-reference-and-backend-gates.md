# Creative video — referência externa e gates de backend

Use esta referência quando a Hera precisar criar vídeo/convite/peça animada inspirada em um link externo e/ou comparar backends como GPT/OpenAI e Grok/xAI.

## Princípio operacional

Se a referência ou o backend solicitado é parte essencial do pedido, ele é um **pré-requisito**, não um detalhe. Não gere uma versão “aproximada” antes de validar esse pré-requisito, salvo aprovação explícita do usuário para fallback parcial.

## Sequência recomendada

```text
1. Confirmar requisitos do pedido:
   - backend(s): GPT/OpenAI, Grok/xAI, ambos, Canva etc.
   - referência: link, anexo, vídeo, imagem, áudio.
   - saída: vídeo final, prévia, roteiro, prompt ou direção visual.

2. Validar referência antes de produzir:
   - tentar download/importação do vídeo/imagem;
   - se YouTube/Shorts bloquear, tentar oEmbed, thumbnails oficiais, browser/Playwright e frontends alternativos;
   - se ainda faltar o vídeo completo, pedir cookie/sessão autenticada ou o arquivo anexado.

3. Validar backend antes de produzir:
   - GPT/OpenAI: usar `image_generate`/provider configurado e registrar provider real.
   - Grok/xAI: usar wrapper MGS ou ferramenta Grok oficial; se `xai-oauth` estiver deslogado, iniciar reauth ou pedir XAI_API_KEY aprovada.

4. Só criar depois:
   - referência analisada; ou
   - backend validado; ou
   - usuário aprovou fallback parcial.

5. Entrega deve rotular origem real:
   - `Versão GPT/OpenAI` para assets criados pelo provider OpenAI;
   - `Versão Grok/xAI` apenas quando gerada por Grok/xAI;
   - `bloqueado` quando não houve geração real.
```

## YouTube Shorts protegidos — padrão de desbloqueio

Sinais comuns:

```text
yt-dlp: Sign in to confirm you’re not a bot
Playwright embed: Error 153 / Video player configuration error
ytInitialPlayerResponse: LOGIN_REQUIRED
```

Correção operacional preferida:

```text
1. Usuário abre YouTube logado no navegador.
2. Usuário exporta cookies em formato Netscape por extensão local confiável.
3. Cookies são enviados como arquivo/anexo ou guardados no 1Password; nunca colar no chat.
4. Rodar yt-dlp com `--cookies /path/cookies.txt`.
5. Extrair frames e analisar antes de produzir.
```

Fallback parcial permitido apenas para diagnóstico/brief:

```text
- oEmbed para título/canal/thumbnail;
- `https://i.ytimg.com/vi/<id>/maxresdefault.jpg`, `sddefault.jpg`, `hqdefault.jpg`;
- análise visual dos thumbnails deixando claro que não é análise frame a frame.
```

## Grok/xAI OAuth — padrão de reauth

Quando Grok retornar ausência de credenciais ou `xai-oauth` estiver sem `access_token`, use o fluxo Hermes atual de seleção/modelo/auth. Em Hermes moderno, `hermes login` pode estar removido; o caminho interativo é `hermes model --manual-paste --refresh`, selecionar `xAI Grok` → `xAI Grok OAuth` → `Reauthenticate` e colar o callback/código aprovado pelo usuário.

Não imprimir tokens/cookies. Reportar apenas status, provider e validação resumida.

## Critério de bloqueio

Pare e reporte antes de criar quando:

```text
- a referência central não pôde ser acessada integralmente;
- o backend explicitamente pedido não está autenticado;
- a saída depende de um anexo/foto/vídeo que não foi recebido;
- o usuário pediu comparação real entre backends e só um backend funcionou.
```

Formato de blocker:

```text
Bloqueio:
Evidência:
Próximo passo necessário:
O que consigo fazer agora sem inventar:
```

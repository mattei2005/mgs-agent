# Convite animado com vídeo de referência — workflow validado

Use quando Ares receber pedido de convite/vídeo criativo com referência externa (YouTube/Shorts/Reels/anexo) e o usuário exigir comparação GPT vs Grok.

## Lições operacionais

1. **Não produza antes de validar a referência.**
   Se o usuário forneceu uma referência visual, primeiro obtenha o vídeo/frames ou declare bloqueio operacional. Não crie uma versão “no escuro” baseada só em descrição parcial.

2. **Tente recuperar anexo da própria thread.**
   Se o usuário disser “aqui está a referência”, importe a thread read-only e procure anexos:
   ```bash
   /root/mgs-agent/scripts/import-discord-thread.py --profile ares --limit 1000 '<thread_id_ou_link>'
   ```
   Depois leia o `.md/.json` em `/root/mgs-agent/data/discord-thread-imports/` e baixe o anexo com `curl -L -A 'Mozilla/5.0'`.

3. **YouTube pode bloquear VPS/datacenter mesmo quando abre anônimo para o usuário.**
   Valide com browser real/Playwright, mas não assuma que basta “usar Chromium”. Cheque o objeto `<video>`:
   - `currentSrc` preenchido
   - `readyState > 0`
   - `videoWidth/videoHeight > 0`
   - screenshot sem “Sign in to confirm you’re not a bot”

4. **Cookies/proxy são setup persistente, não por vídeo.**
   Para referências recorrentes de YouTube, use uma sessão/cookies persistentes ou Browserbase/proxy residencial. Não peça cookies a cada vídeo.
   Caminho local aprovado para cookie jar do Ares:
   ```text
   /root/.hermes/profiles/ares/secrets/youtube-cookies.txt
   ```
   Nunca colar cookies no chat.

5. **Grok explícito exige validação real do wrapper MGS.**
   Para “faz com GPT e Grok”, gere a versão GPT via `image_generate`/OpenAI e a versão Grok via:
   ```bash
   /root/mgs-agent/scripts/mgs-grok-generate.py image|video --profile ares ...
   ```
   Só rotule como Grok se o output mostrar `provider=xai-oauth`/xAI e arquivo real gerado.

6. **Analise a referência antes da produção.**
   Baixe o vídeo, rode `ffprobe`, extraia frames/contact sheet e use visão para levantar:
   - sequência de cenas;
   - composição;
   - paleta;
   - tratamento de texto;
   - animações/transições;
   - onde inserir foto e dados.

## Padrão de resposta ao usuário

Se referência ou Grok estiver bloqueado, pare e reporte o bloqueio com o próximo passo concreto. Não entregue arte final improvisada.

```text
Bloqueio
────────
Referência: [estado real]
Grok: [estado real]
Próximo passo: [cookie/proxy/anexo/reauth]
```

## Estrutura que funcionou para convite Safari infantil

- Entrada: placa de madeira + folhas + jipe safari.
- Título: `SAFÁRI DO / DANIEL / 1 ANINHO` em fonte infantil, verde com contorno claro.
- Foto: integrar Daniel no jipe ou em moldura de folhas; não parecer colagem solta.
- Transição: folhas em primeiro plano como wipe.
- Mensagem: `EMBARQUE NESSE SAFARI E VENHA COMEMORAR MEU PRIMEIRO ANINHO!`.
- Dados: data, horário e endereço em painel fixo/legível; não aparecer-sumir em blocos rápidos.
- Áudio: se usar trilha da referência/anexo, preservar como áudio de referência quando autorizado; caso contrário usar trilha original mais marcada, não placeholder vaga.

## Checklist de validação

- [ ] Referência real baixada ou bloqueio reportado antes de gerar.
- [ ] `ffprobe` confirma duração/dimensões/áudio.
- [ ] Contact sheet analisado.
- [ ] Versões GPT e Grok são arquivos reais e corretamente rotulados.
- [ ] Dados ficam fixos e legíveis.
- [ ] Foto da criança permanece visível o suficiente.
- [ ] Metadata final limpa com sanitizer oficial.

# Workflow — variação de vídeo com GPT + Grok

Use quando Rodolfo pedir uma variação de um vídeo e comparar `GPT` versus `Grok`.

## Procedimento resumido

1. Se o anexo de vídeo do Discord não aparecer diretamente no contexto, importe a thread read-only:
   ```bash
   /root/mgs-agent/scripts/import-discord-thread.py --profile ares --limit 1000 '<thread_id_ou_link>'
   ```
   Leia o JSON importado e pegue `referenced_message.attachments[].url`.

2. Baixe o vídeo com User-Agent simples antes de declarar bloqueio:
   ```bash
   curl -L -A 'Mozilla/5.0' -o video.mov '<attachment_url>'
   ```

3. Valide propriedades reais com `ffprobe` e extraia frames/contact sheet para entender o criativo antes de gerar variações:
   ```bash
   ffprobe -v error -show_entries format=duration,size,format_name:stream=codec_type,codec_name,width,height,avg_frame_rate -of json video.mov
   ffmpeg -y -i video.mov -vf 'fps=1/2,scale=480:-1' frames/frame_%02d.jpg
   ffmpeg -y -framerate 1 -pattern_type glob -i 'frames/*.jpg' -vf 'scale=240:-1,tile=4x2:padding=8:margin=8:color=white' contact_sheet.jpg
   ```
   Use visão no contact sheet para identificar oferta, idioma, ângulo, CTA e problemas visuais.

4. Regra de provider atualizada por Rodolfo:
   - Se o pedido for **vídeo**, use **Grok/xAI** como padrão, porque GPT/OpenAI no fluxo atual serve para imagem/keyframe e tende a virar slideshow/zoom quando forçado como vídeo.
   - Se o pedido for **imagem**, pode usar **GPT/OpenAI** ou **Grok/xAI**; o gestor pode definir o provider no pedido, ou o Ares pode propor comparação quando fizer sentido.
   - Se o usuário pedir explicitamente GPT+Grok para vídeo, explique antes a capacidade real: Grok gera vídeo; GPT gera imagem/keyframe/direção visual, não vídeo narrativo final. Só entregue GPT como imagem/keyframe/thumbnail se isso estiver claro.
   - Se o usuário citar precedente/thread onde GPT+Grok já funcionou, importe a thread e verifique o padrão antes de afirmar bloqueio ou limitação.

5. Para a comparação solicitada:
   - **GPT/OpenAI**: gerar preview criativo mais limpo/polido. Quando houver somente geração de imagem/keyframe disponível, rotular claramente como `GPT preview` ou `preview estrutural`, não como vídeo final profissional.
   - **Grok/xAI**: gerar vídeo/motion mais dinâmico e social. Pode usar o keyframe GPT como `image_url` para uma variação animada polida, e/ou um frame do vídeo original como `image_url` para uma variação mais fiel/dinâmica.
   - Quando fizer sentido, sugerir **V003 híbrida**: clareza/oferta do GPT + dinâmica/naturalidade social do Grok.

6. Precedente operacional: ver `references/video-gpt-grok-precedent.md` para o padrão validado de entrega GPT preview + Grok preview e o pitfall de não negar capacidade sem consultar histórico.

7. Autenticação Grok/xAI em Discord/headless:
   - Use `HERMES_HOME=/root/.hermes/profiles/ares hermes auth add xai-oauth --manual-paste`.
   - Se rodar em background, **não use `watch_patterns`**, porque isso envia aviso técnico `Callback URL:` para a thread. Use `process.poll/log` internamente e responda ao usuário só com o link limpo.
   - Após o usuário enviar o código/URL, use `process.submit` no processo aberto e valide com comando real do wrapper antes de dizer que Grok está liberado.

8. Baixe URLs remotas de vídeo para caminho local antes de entregar no Discord, porque o handoff final deve apontar para arquivo local verificável quando possível.

9. Passe todos os assets finais pelo sanitizer antes de entregar:
   ```bash
   /root/mgs-agent/scripts/clean-creative-metadata.sh clean /path/to/asset.mp4 --agent ares
   /root/mgs-agent/scripts/clean-creative-metadata.sh verify /path/to/asset.metadata-clean.mp4
   ```

10. Faça uma checagem visual rápida dos vídeos gerados criando contact sheets e usando visão. Reporte diferenças curtas: legibilidade, estilo, problemas visuais graves.

11. Para pedidos de vídeo com pessoa falando, não conserte um vídeo mudo/ruim com TTS externo robótico por cima. Se a voz precisa parecer da pessoa em cena, o provider precisa gerar fala/voz integrada ou o resultado deve ser reprovado/bloqueado antes da entrega.

12. Se xAI/Grok retornar `429 Too Many Requests` ao gerar múltiplas variações, não trate como falha criativa. Rode as gerações sequencialmente, aguardando alguns segundos entre chamadas, e continue a validação normal.

## Pedido de “mais duas variações” após previews GPT/Grok

Quando Rodolfo pedir apenas “faz mais duas variações” numa thread que já tem V001/V002:

1. Não peça novo brief se a thread já contém referência, oferta e previews. Importe a thread read-only e recupere o contexto anterior.
2. Procure primeiro os artefatos locais já gerados na pasta da thread, por exemplo:
   ```text
   /root/mgs-agent/data/ares/creative-ops/<thread_id>/generated/
   /root/mgs-agent/data/ares/creative-ops/<thread_id>/frames/
   /root/mgs-agent/data/ares/creative-ops/<thread_id>/contact_sheet.jpg
   ```
3. Revalide rapidamente o contact sheet da referência/original antes de criar, para confirmar oferta, carro, idioma, CTA e estilo.
4. Continue a numeração sequencial: se existem V001 e V002, as novas são V003 e V004. Não pule para V004/V005.
5. Para V003, se a conversa anterior recomendou uma híbrida, use um keyframe/preview GPT como referência visual e gere uma versão com acabamento premium + dinâmica social.
6. Para V004, crie um ângulo diferente real, não só troca de legenda: exemplo `TRUST/FAST_APPROVAL`, atendimento, cliente, handoff de chave, prova social ou confiança.
7. Use prompts que preservem claims críticos exatamente como aprovados (`NO DOWN PAYMENT`, `$299/mo`, `APPLY TODAY`, `DRIVE TODAY`, `FAST APPROVAL`) e impeçam preço/oferta extra.
8. Depois de gerar, renomeie para nomes operacionais claros, gere contact sheets, valide visualmente, passe sanitizer e entregue somente `.metadata-clean.mp4`.
9. Responda curto e operacional com os arquivos anexados; não acione Ares novamente enquanto Rodolfo ainda estiver em revisão.

## Naming sugerido para preview

Quando a vertical ainda for inferida, use naming operacional provisório e deixe claro que é preview/revisão:

```text
CAR_US_EN_VID_NO_DOWN_PAYMENT_PV_001_GPT_PREVIEW.mp4
CAR_US_EN_VID_NO_DOWN_PAYMENT_PV_002_GROK_PREVIEW.mp4
CAR_US_EN_IMG_NO_DOWN_PAYMENT_PV_001_GPT_KEYFRAME.png
```

Não marcar como aprovado/ready-for-ares sem revisão humana explícita.

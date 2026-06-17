# Workflow — variação de vídeo com GPT + Grok

Use quando Rodolfo pedir uma variação de um vídeo e comparar `GPT` versus `Grok`.

## Procedimento resumido

1. Se o anexo de vídeo do Discord não aparecer diretamente no contexto, importe a thread read-only:
   ```bash
   /root/mgs-agent/scripts/import-discord-thread.py --profile hera --limit 1000 '<thread_id_ou_link>'
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

4. Para a comparação solicitada:
   - **GPT/OpenAI**: gerar um keyframe/peça estática vertical com `image_generate`, priorizando composição limpa, oferta legível e estilo polido.
   - **Grok/xAI**: gerar vídeo com `video_generate`. Pode usar o keyframe GPT como `image_url` para uma variação animada polida, e/ou um frame do vídeo original como `image_url` para uma variação mais fiel/dinâmica.

5. Baixe URLs remotas de vídeo para caminho local antes de entregar no Discord, porque o handoff final deve apontar para arquivo local verificável quando possível.

6. Passe todos os assets finais pelo sanitizer antes de entregar:
   ```bash
   /root/mgs-agent/scripts/clean-creative-metadata.sh clean /path/to/asset.mp4 --agent hera
   /root/mgs-agent/scripts/clean-creative-metadata.sh verify /path/to/asset.metadata-clean.mp4
   ```

7. Faça uma checagem visual rápida dos vídeos gerados criando contact sheets e usando visão. Reporte diferenças curtas: legibilidade, estilo, problemas visuais graves.

## Naming sugerido para preview

Quando a vertical ainda for inferida, use naming operacional provisório e deixe claro que é preview/revisão:

```text
CAR_US_EN_VID_NO_DOWN_PAYMENT_PV_001_GPT_PREVIEW.mp4
CAR_US_EN_VID_NO_DOWN_PAYMENT_PV_002_GROK_PREVIEW.mp4
CAR_US_EN_IMG_NO_DOWN_PAYMENT_PV_001_GPT_KEYFRAME.png
```

Não marcar como aprovado/ready-for-ares sem revisão humana explícita.

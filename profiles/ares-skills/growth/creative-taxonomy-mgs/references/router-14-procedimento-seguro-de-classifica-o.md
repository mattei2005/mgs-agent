## Procedimento seguro de classificação

1. Inventariar arquivos em modo read-only.
2. Validar formato real (`IMG`/`VID`) por arquivo, não por nome.
3. Extrair dimensão e calcular orientation/placement.
4. Para vídeos, não classificar por thumbnail/frame inicial apenas: amostrar múltiplos frames, porque conteúdo/CTA pode aparecer só depois de alguns segundos.
5. Script canônico para vídeos: `/root/mgs-agent/scripts/ares-drive-video-frame-sampler.py` com frames padrão em `0.5s`, `2.0s`, `3.2s`, `4.5s` e `6.0s`; usar `--discard-videos` em execução grande para não guardar MP4 local desnecessário.
6. Chamar o artefato visual de vídeo de **timeline de frames** ou **imagem de revisão**; evitar o termo “sheet” com Rodolfo, porque ele pode entender como Google Sheet/planilha.
7. Para piloto de nomenclatura, selecionar uma amostra balanceada pequena para validar o método; uma vez validado, escalar para o lote completo restante, não ficar repetindo novas amostras pequenas. Usar lotes apenas como detalhe técnico de estabilidade/auditoria.
8. Não criar Google Sheet/planilha para esse fluxo salvo pedido explícito; usar CSV/JSON local como log/plano técnico e explicar se algum arquivo é apenas evidência local.
9. Detectar idioma/país por texto visível, nome, pasta e/ou OCR quando disponível; evidência visual pode corrigir o guess automático. Para vídeos, o classificador OCR-assisted canônico é `/root/mgs-agent/scripts/ares-classify-video-timelines-ocr.py`.
10. Para escala completa de vídeos, seguir `references/upload-canvas-video-classification-scale.md`.
11. Classificar vertical por evidência visual/textual; se incerto, `UNKNOWN`.
12. Classificar pessoa/orientação usando apenas `PV`, `PH`, `NV`, `NH`; FEED 1:1 entra como `HORIZONTAL` para fins de nome.
13. Sugerir `ANGLE` somente com evidência suficiente; se incerto, `UNKNOWN` + baixa confiança.
14. Gerar plano de renomeação/cópia em CSV/JSON com `confidence` e `notes`.
14. Gerar plano de renomeação/cópia em CSV/JSON com `confidence` e `notes`.
15. Antes de executar qualquer rename/copy, validar que `VARIANT` está em 3 dígitos (`001-999`) em todos os nomes finais e corrigir qualquer saída legada de script que ainda gere `01`, `02`, etc.
16. Quando houver itens em `00_REVIEW`, revisar ativamente com evidência visual/contact sheet/timeline e tomar decisão operacional: promover para `01_READY_CANDIDATE`, mover para `05_REJECTED`, ou manter em review somente com motivo concreto. Não deixar `00_REVIEW` como pendência genérica se os arquivos estão acessíveis no Drive.
15. Antes de executar qualquer rename/copy, validar que `VARIANT` está em 3 dígitos (`001-999`) em todos os nomes finais e corrigir qualquer saída legada de script que ainda gere `01`, `02`, etc.
16. Mostrar proposta ao Rodolfo antes de qualquer alteração em Drive/campanha.
17. Após aprovação, executar cópia/renomeação com logs e validação.
18. Em fluxos RAW → clean-copy, preservar `UPLOAD_CANVAS` como fonte original. Ao agir sobre itens revisados, usar o ID da cópia limpa (`dest_drive_id` nos reports de copy-clean), não o `source_drive_id` do RAW, salvo pedido explícito para mexer no RAW.
19. Se Rodolfo pedir para corrigir criativos já feitos, executar a correção no Drive, validar por novo scan que não restam nomes finais com 2 dígitos, e atualizar artefatos locais/propostas para o mesmo padrão.
19. Para colisões de nome já existentes em `01_READY_CANDIDATE`, manter um nome canônico por variante e renomear as cópias conflitantes para a próxima variante livre com 3 dígitos. Simular antes para garantir zero colisões pós-plano e registrar `old_name`, `new_name`, `drive_id`, `verified_name` e relatório hash.

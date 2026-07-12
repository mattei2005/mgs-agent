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
12. Classificar pessoa/formato usando `PV/NV` para vertical, `PS/NS` para square e `PH/NH` para horizontal; não colapsar FEED 1:1 em horizontal.
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
## Sanitização antes de campanha

Antes de usar criativo em campanha/teste, validar metadados:

```bash
/root/mgs-agent/scripts/clean-creative-metadata.sh verify /path/to/creative.png
```

Se `clean: false`, limpar uma cópia:

```bash
/root/mgs-agent/scripts/clean-creative-metadata.sh clean /path/to/creative.png --agent ares
```

Usar o arquivo `.metadata-clean` como asset final. Não sanitizar RAW original in-place.
## Regras de segurança

- Em pedido autorizado de tratar/mover uma pasta de entrada, validar o clean em `01_READY` e mover o RAW para `99_LEGACY`, sem deletar; fora desse fluxo, não mover/renomear RAW sem confirmação explícita.
- Não subir criativo em campanha sem metadata gate aprovado.
- Não inventar performance ou histórico de teste.
- Não expor tokens, cookies, IDs sensíveis sem necessidade, client secrets ou credenciais.
- Alterações em campanha, orçamento, tracking, pixel ou billing exigem confirmação explícita; billing exige double-confirm.
## Checklist de validação

Antes de finalizar uma taxonomia ou plano de renomeação:

```text
Check                                      | Exigência
-------------------------------------------|-----------------------------------------------
Modelo de nome completo                    | VERTICAL_COUNTRY_LANG_FORMAT_ANGLE_P_ORIENT_VARIANT
FORMAT validado por arquivo real           | Sim
ANGLE vem de dicionário controlado         | Sim ou UNKNOWN
P_ORIENT coerente com pessoa/orientação    | Sim
Status fora do nome                        | Sim
IDs fora do nome                           | Sim
Origem/gestor no inventário                | Sim
RAW preservado                             | Sim
Metadados verificados antes de campanha    | Sim
Plano aprovado antes de write              | Sim
```
## Pitfalls comuns

1. Separar por site no Drive: ruim porque o mesmo criativo pode rodar em múltiplos sites.
2. Colocar status no nome: gera renomeações constantes conforme ciclo de vida muda.
3. Inferir vídeo/imagem pelo nome do Canva: pode estar errado; validar arquivo real.
4. Forçar ângulo sem evidência: prejudica análise de performance por criativo.
5. Misturar RAW com assets limpos: manter original e versão final auditáveis.
6. Deixar pessoa/orientação desconhecida virar nome final: melhor revisar antes.
7. Deixar script legado emitir variantes `01-99`: isso quebra ordenação alfabética quando passa de 99 ou mistura lotes. O padrão MGS é sempre `001-999`; valide CSVs, propostas e reports antes de Drive write.
8. Usar `VARIANT` com 2 dígitos: quebra ordenação quando surgem `_100+`; corrigir para 3 dígitos em nomes reais, propostas e inventários.
8. Fazer replace global em relatórios de auditoria sem preservar `old_name`: pode destruir evidência da mudança. Ao normalizar logs, preservar ou reconstruir o valor antigo em campo próprio.
9. Confundir RAW com cópia final: `UPLOAD_CANVAS` é fonte original, enquanto pastas por operação carregam derivados limpos/renomeados. MD5 diferente entre RAW e final é esperado após limpeza de metadata; isso não significa que o asset não veio do RAW.
10. Agir no ID errado em revisão final: reports de copy-clean costumam ter `source_drive_id`=RAW e `dest_drive_id`=cópia limpa. Promoção para `01_READY`, rejeição e rename final devem usar `dest_drive_id`; se o RAW for movido por engano, restaurar o RAW antes de encerrar.
10. Dizer que não consegue revisar assets do Drive quando existe acesso/pipeline Drive: se os arquivos estão em `MGS-CRIATIVOS`, inventarie, gere evidência visual e revise. Só reporte bloqueio real de permissão/credencial.
11. Fechar `00_REVIEW` movendo RAW em vez da cópia limpa: `UPLOAD_CANVAS` é origem preservada; decisões finais devem agir sobre a cópia limpa em review/final. Conferir `source_drive_id` vs `dest_drive_id` nos relatórios antes de PATCH no Drive.

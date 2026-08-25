## Procedimento seguro de classificação

1. Inventariar arquivos em modo read-only.
2. Validar formato real (`IMG`/`VID`) por arquivo, não por nome.
3. Extrair dimensão e calcular orientation/placement.
4. Para vídeos, não classificar por thumbnail/frame inicial apenas: amostrar múltiplos frames, porque conteúdo/CTA pode aparecer só depois de alguns segundos.
5. Script canônico para vídeos: `/root/mgs-agent/scripts/ares-drive-video-frame-sampler.py` com frames padrão em `0.5s`, `2.0s`, `3.2s`, `4.5s` e `6.0s`; usar `--discard-videos` em execução grande para não guardar MP4 local desnecessário.
6. Chamar o artefato visual de vídeo de **timeline de frames** ou **imagem de revisão**; evitar o termo “sheet” com Rodolfo, porque ele pode entender como Google Sheet/planilha.
7. Para piloto de nomenclatura, selecionar uma amostra balanceada pequena para validar o método; uma vez validado, escalar para o lote completo restante, não ficar repetindo novas amostras pequenas. Usar lotes apenas como detalhe técnico de estabilidade/auditoria.
8. Não criar Google Sheet/planilha para esse fluxo salvo pedido explícito; usar CSV/JSON local como log/plano técnico e explicar se algum arquivo é apenas evidência local.
9. Detectar idioma/país por texto visível, nome, pasta e/ou OCR quando disponível; evidência visual pode corrigir o guess automático. Para vídeos, o classificador OCR-assisted canônico é `/root/mgs-agent/scripts/ares-classify-video-timelines-ocr.py`. Se uma abordagem auxiliar não estiver disponível, continuar com a timeline de frames e outra evidência real em vez de encerrar a classificação.
10. Para escala completa de vídeos, seguir `references/upload-canvas-video-classification-scale.md`.
11. Classificar vertical por evidência visual/textual; se incerto, `UNKNOWN`. Para a vertical `CAR`, classificar também `vehicle_type=MOTO|CARRO` pela imagem/timeline real: moto usa o token `MOTO` imediatamente após `FORMAT`; carro mantém o padrão sem token adicional. Em lote misto, decidir por asset, nunca pelo pedido ou nome do lote.
12. Classificar pessoa/orientação usando somente `PV/NV` para vertical e `PH/NH` para square/feed 1:1 ou horizontal/landscape; `PS/NS` não entram em nomes finais.
13. Sugerir `ANGLE` somente com evidência suficiente; se incerto, `UNKNOWN` + baixa confiança.
14. Gerar plano de renomeação/cópia em CSV/JSON com `confidence` e `notes`.
15. Antes de executar rename/copy, validar `VARIANT` com 3 dígitos (`001-999`) em todos os nomes finais e corrigir qualquer saída legada que ainda gere `01`, `02`, etc.
16. Quando houver itens em `00_REVIEW`, revisar ativamente com evidência visual/timeline e decidir: promover para `01_READY_CANDIDATE`, mover para `05_REJECTED`, ou manter em review somente com motivo concreto. Não deixar review como pendência genérica quando os arquivos estão acessíveis.
17. Pedido autorizado de tratar/mover dentro da estrutura canônica já aprova o plano rotineiro; não pedir confirmação redundante. Mostrar proposta e pedir decisão somente para ambiguidade material, nova estrutura, destino não canônico, alteração de campanha ou mudança de escopo.
18. Executar cópia/renomeação com logs e validação. No fluxo `UPLOAD MANUAL` → clean-copy, validar a cópia limpa em `01_READY`, mover o original para `99_LEGACY` sem deletar e usar `dest_drive_id` para promoção/rejeição/rename final.
19. Se Rodolfo pedir correção de criativos já feitos, executar no Drive, validar por novo scan que não restam nomes finais com 2 dígitos e atualizar artefatos locais/propostas para o mesmo padrão.
20. Para colisões de nome em `01_READY_CANDIDATE`, manter um nome canônico por variante e renomear cópias conflitantes para a próxima variante livre com 3 dígitos. Simular antes para garantir zero colisões e registrar `old_name`, `new_name`, `drive_id`, `verified_name` e hash do relatório.
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
Modelo de nome completo                    | VERTICAL_COUNTRY_LANG_FORMAT_[MOTO_]_ANGLE_P_ORIENT_VARIANT
Subtipo veicular CAR                       | MOTO só com motocicleta dominante; carro omite o token
FORMAT validado por arquivo real           | Sim
ANGLE vem de dicionário controlado         | Sim ou UNKNOWN
P_ORIENT coerente com pessoa/orientação    | Sim
Status fora do nome                        | Sim
IDs fora do nome                           | Sim
Origem/gestor no inventário                | Sim
RAW preservado                             | Sim
Metadados verificados antes de campanha    | Sim
Pedido/plano autorizado antes do write  | Pedido natural basta no fluxo canônico; decisão extra só nos desvios
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
9. Confundir entrada com asset final: `UPLOAD MANUAL` é fila temporária; pastas por operação carregam a cópia limpa/renomeada e `99_LEGACY` preserva o original após o READY passar nos gates. MD5 diferente entre original e final é esperado após limpeza de metadata.
10. Agir no ID errado em revisão final: reports de copy-clean costumam ter `source_drive_id`=RAW e `dest_drive_id`=cópia limpa. Promoção para `01_READY`, rejeição e rename final devem usar `dest_drive_id`; se o RAW for movido por engano, restaurar o RAW antes de encerrar.
10. Dizer que não consegue revisar assets do Drive quando existe acesso/pipeline Drive: se os arquivos estão em `MGS-AGENTS/CRIATIVOS`, inventarie, gere evidência visual e revise. Só reporte bloqueio real de permissão/credencial.
11. Fechar `00_REVIEW` agindo no original: decisões finais usam a cópia limpa (`dest_drive_id`). O original sai de `UPLOAD MANUAL` somente após READY validado e vai para `99_LEGACY`, preservando ID/nome.
12. Tratar um lote inteiro como moto ou carro sem revisar cada asset: a classificação veicular é por conteúdo real. Em `CAR`, `MOTO` só entra depois de `FORMAT` quando motocicletas dominam visualmente; assets de carro permanecem no padrão anterior.

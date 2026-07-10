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

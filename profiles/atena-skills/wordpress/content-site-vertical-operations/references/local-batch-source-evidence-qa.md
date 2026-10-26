# QA de fontes em lotes editoriais exclusivamente locais

- Persista batches pequenos de artigos completos antes de escalar, e valide o JSON final relido do disco. O gerador em memória não prova que o artefato entregue é o mesmo.
- Crie um arquivo de evidência por local_id com URL citada, método, resultado substantivo, caminho do registro bruto e limitações. Separe web_search, web_extract e GET direto; um método recuperado não transforma uma falha anterior em HTTP200.
- Ao receber HTTP200 sem texto editorial, procure shell, consentimento de cookies ou PDF escaneado antes de aceitar a coleta. Um parser HTML direto pode recuperar uma FAQ que o extrator reduziu a cookies; preserve ambos os resultados.
- Em PDF, diferencie transporte bem-sucedido de extração textual. Salve o original e seu hash quando útil. NeedsOcrError não comprova leitura do PDF; identifique explicitamente se o texto substantivo veio de OCR, busca ou outro transporte real.
- Confira o idioma do conteúdo entregue após redirects. Uma rota espanhola pode entregar inglês; use a URL final, sinalize o idioma no corpo e registre a tentativa de equivalente, sem inventar rotas localizadas.
- Revalide os limites após qualquer reparo pontual. Além do contrato de campos e palavras alfabéticas, confira HTML balanceado e allowlist, frase inicial/excerpt idênticos, fontes inseridas no parágrafo pertinente e parágrafos exatamente duplicados entre artigos.
- Compare assuntos próximos por mecanismo e problema resolvido, não só por títulos. Registre por que uma pauta sobre caña de bota não é uma tradução de uma pauta sobre barra para tênis baixos, por exemplo.
- Feche a lista exata por igualdade de conjuntos de local_id e informe separadamente texto local, imagem apenas conceituada, QA independente, Yoast e publicação. Validação local não autoriza declarar etapas não executadas.

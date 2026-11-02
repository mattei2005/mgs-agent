# Limpeza técnica do arquivo criativo — escopo 1566643959458168864

## Autoridade e estado

- Pedido: Rodolfo Mattei (`344196393512075265`), mensagem `1566643959458168864`, thread `1562078493498540042`.
- Zeus é responsável pela preparação e execução segura, sem writer paralelo.
- Estado: **limpeza concluída e validada após confirmação crítica de Rodolfo em `1566800073071788244`, respondendo à pergunta de alvos `1566646147366264864`**. O estado anterior de espera abaixo é histórico supersedido somente para esse manifesto; não há autorização destrutiva genérica.
- Plano: `data/ares/creative-ops/30tb-archive/legacy-cleanup-1566643959458168864/cleanup-plan.json`. Digest canônico SHA-256: `3835baf8f8af312267ad2a4c3e9856544278b92479f55857152dca60c73a7a0b`.

## Inventário e classificação

A SA canônica enumerou integralmente as duas subárvores técnicas `_ESTRUTURAS_ANTIGAS` e `_TESTES`, com todas as páginas: 89 descendentes, sendo 46 pastas e 43 arquivos, além das duas raízes consultadas. Não confundir esse escopo técnico com o acervo completo em `_ARQUIVO_FISICO`.

**Alvos exatos propostos: 30 objetos — 29 pastas e uma cópia-piloto.**

- 28 pastas da árvore vazia `_ARQUIVO_FISICO/_ESTRUTURAS_ANTIGAS/PROVEDORES`, incluindo a pasta histórica homônima `UPLOAD MANUAL` e seus descendentes vazios. Ela NÃO é a entrada ativa.
- Uma cópia-piloto `SHEIN_US_ES_VID_CUATRIMOTO_GRATIS_NV_002.mp4`, ID `1wz1Lm5l8a-UnbQnm5xFsO1Om0LqAQTkR`, em `_ARQUIVO_FISICO/_TESTES`.
- A própria pasta `_TESTES`, ID `17NmrZhIocyGGpsWIF2hT4pCfyXzX0hhg`, somente depois de retirar a cópia-piloto e confirmar que não recebeu nenhum outro conteúdo.

A cópia-piloto possui 5.375.929 bytes. O download integral dela e do provider permanente `1eiPtnza8L27Qd9KoQUOO28ZN-CwWR3zx` produziu tamanho, MD5 e SHA-256 idênticos; o leitor lógico permanente também passou. A referência remanescente no índice é evidência de job `kind=canary`, não mapeamento produtivo. Preservar esse histórico; não apagar ou fabricar recibos para eliminar a referência.

## Proteções obrigatórias

- Preservar a entrada ativa `UPLOAD MANUAL`, ID `1ARBvLammWUHuAclNmcriwkkgeedKryBd`, e todas as suas fontes.
- Preservar os 42 arquivos restantes dessas subárvores, incluindo os 12 RAW e três materiais de referência já conciliados, e os demais arquivos históricos da pasta Geizian.
- Preservar nove pastas legadas vazias registradas no namespace de compatibilidade. Elas ainda podem ser consultadas por validações de pedidos/recibos antigos; vazio não significa descartável. A pasta legada Nicolas é aceita por `ares_manager_delivery.exact_folder` via `ares_archive_namespace.legacy_manager_folder`.
- Preservar originais, providers, controles, backups, pastas operacionais e quaisquer IDs fora do manifesto.
- Não mudar status de campanha, reservas, elegibilidade, ownership funcional, credenciais, permissões ou agendas.

## Execução e recuperação

A SA tem `canTrash=false` e `canDelete=false` nos alvos consultados. Isso é uma fronteira de autoridade nativa, não falha de autenticação. O conector owner existente também bloqueia métodos genéricos PATCH/DELETE; não contornar esse guard, não selecionar identidade pessoal para agentes e não ampliar genericamente o transporte. Após a confirmação crítica, implementar/testar uma operação de limpeza confinada ao manifesto e à identidade owner já isolada e aprovada, com gate de autoridade rastreável, locks canônicos, intent/CAS e reconciliação antes de replay.

A ação proposta é **lixeira, sem exclusão permanente**. Revalidar IDs/versões/bytes/owner/parents e todos os filhos imediatamente antes da ação. Qualquer objeto novo fora do manifesto bloqueia a pasta correspondente. Registrar cada efeito e comprovar `trashed=true` em cada alvo, permanência dos não alvos e leitura íntegra da cópia produtiva. Preservar metadata anterior, journals e prova integral do piloto/duplicata para restauração.

Nenhuma ação destrutiva foi executada na preparação. Esse estado foi supersedido exclusivamente pela execução confirmada abaixo.

## Execução confirmada e aceite final — `1566800073071788244`

- Confirmação nativa de Rodolfo (`344196393512075265`) relida na thread, vinculada à pergunta `1566646147366264864` e ao mesmo digest do plano. Evidência `confirmation.json`.
- Gate dedicado `scripts/mgs_archive_technical_cleanup.py`, sem habilitar PATCH/DELETE genérico no owner nem trocar a SA. Locks queue → inventory, snapshot original, comparação nativa de IDs/versões/parent/owner/ACL, filhos paginados, ordem de baixo para cima e intents persistidos antes de cada RPC. Resultado ambíguo só admite reconciliação, nunca replay cego.
- **30/30 IDs exatos na lixeira: 29 pastas e uma cópia-piloto. Exclusões permanentes: zero.** Leitura independente de todos os alvos e dos **63 objetos protegidos** do escopo ampliado confirmou nomes/parent/owner/ACL/conteúdo preservados onde aplicável. As nove pastas de compatibilidade, os 42 arquivos restantes e a entrada ativa ficaram intocados. Não é uma auditoria nova de todo o acervo.
- Cópia permanente baixada integralmente após a lixeira e conferida por tamanho/MD5/SHA-256; leitor lógico produtivo passou. Catálogo, índice e padrão de gestores conservaram seus hashes durante a operação. Prova `final-verification.json`, aceite `2026-11-02T13:10:03.225490+00:00`.
- A auditoria posterior do piloto técnico antigo reproduziu `UNEXPLAINED_SOURCE_404_WITHOUT_RETIREMENT_RECEIPT`: sua fonte lógica antiga já não estava disponível ao verificador. A limpeza atual não excluiu essa fonte e não atribui sua ausência. O caminho antigo também exigiria tratar a cópia-piloto como mídia ativa. Recuperação confinada: `ares_archive_automation.py` reconhece somente esse job canário como **validação técnica aposentada**, mediante request/receipt/ACK nativos imutáveis, manifesto/confirmação/journal/lixeira exatos e leitor permanente íntegro. Não forja recibo de retirada da fonte, não altera ACK ou fingerprint antigo e não admite jobs produtivos/outros canários. Conferência real do job e reconciliação: sem bloqueios, zero cópias/reverificações produtivas; `pilot-monitor-disposition-verification.json`.
- **113 testes focados passaram**, em seis módulos/interpretes separados, incluindo 26 do gate novo. Não é a suíte inteira do repositório. Ciclo produtivo de leitura: worker saudável, estado `ok`, dois jobs de 196 examinados e nenhum bloqueio nessa amostra; o piloto aposentado foi validado separadamente. Esperas de intake de outros pedidos mantidas, fora desta limpeza.
- Metadata original, journal, recibos e provas de bytes permanecem para restauração. Nenhuma alteração em credencial, permissão, agenda, campanha, reserva ou elegibilidade.

## Primeiro uso produtivo — obrigação separada

O padrão Exclusivos → Usados está ativo e tecnicamente testado. O recibo `manager-standard/first-production-use.json` ainda não existe: não ocorreu aceite observado de campanha nova pela nova rota. No próximo pedido normal, Zeus verifica entrega exclusiva, atribuição Meta real e movimento apenas das peças efetivamente usadas. Não pedir upload/campanha artificial a Rodolfo, não criar cron ou campanha para produzir prova e não confundir o remanejamento dos 172 históricos com essa observação produtiva.

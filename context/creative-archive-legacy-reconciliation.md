# Conciliação do legado criativo: disponibilidade e uso

## Autoridade e fonte vigente

- Pedido de continuidade: Rodolfo Mattei, mensagem `1566533058130088158`, thread `1562078493498540042`.
- Esta etapa sucede a reorganização física de `1566510979838255326`, sem repeti-la ou ampliar para exclusões, permissões, credenciais, campanhas ou liberação de reservas.
- Estado técnico: concluído e validado. A disposição de uso dos 172 tratados ainda exige evidência/declaração operacional; não foi inventada.
- Fontes operacionais: `data/ares/creative-ops/30tb-archive/legacy-reconciliation-1566533058130088158/` (`provider-metadata.json`, `native-verification.json`, `object-role-ledger.json`, `retired-source-ledger.json`, `acceptance.json`).

## 1. Os 44 registros inacessíveis foram explicados

Todos os 44 IDs e SHA-256 correspondem exatamente ao manifesto da purga de lixeira confirmada em `1563588372872699927`, executada e validada em 24/10/2026. Cada ID tem recibo HTTP 204 e ausência nativa novamente conferida. A pergunta crítica em `1563587313966120991` avisava explicitamente que a exclusão seria definitiva mesmo sem cópia comprovada; Rodolfo respondeu Sim. Autor e mensagens foram relidos no Discord.

Isto fecha a dúvida sobre o destino desses IDs específicos: não são desaparecimentos desta reorganização. Não prova uma cópia alternativa dos vídeos, nem autoriza recriá-los ou repetir exclusões. O estado correto é **fonte descartada por confirmação anterior; cópia de arquivo não comprovada**.

Os 44 vínculos conta/anúncio/campanha/creative/vídeo continuam conferidos na Meta. Foram preservados status de campanha, IDs lógicos, SHA-256 e histórico. O catálogo recebeu apenas `storage_availability=source_retired_archive_unproven` e a referência ao recibo de disposição; não foi convertido para um falso arquivo disponível nem excluído como histórico.

## 2. Os 187 objetos atuais continuam íntegros e legíveis

- 172 são tratados com registro de catálogo e reserva existente.
- 12 são originais RAW identificados por ID de origem e checksum original, ligados a 12 linhagens; cinco têm o tratado dentro do próprio conjunto de 172. Portanto objetos e linhagens não são totais somáveis.
- Três são arquivos com marcador de referência e sem cadastro de criativo final. Dois têm origem LIBRARY META confirmada por bytes idênticos em outras cópias; o terceiro permanece referência rotulada/não final, sem promover seu nome a prova de origem ou autorização produtiva.

Cada um dos 187 passou por ACK nativo, acesso, owner, privacidade, checksum e download integral do provider: **1.207.887.551 bytes**. Todos foram depois relidos pelo consumidor lógico real, preservando source/provider/stock IDs.

A auditoria encontrou **102 paths históricos incompatíveis com os nomes atuais das pastas**, como `Usados Nicolas` → `NICOLAS - Usados`. Os bytes e parents nativos continuavam corretos; o leitor ainda exigia o path textual congelado. A correção é uma extensão delimitada do namespace: somente os 187 objetos da coorte antiga, com novo aceite/digest, parents exatos e prova integral. Requests, receipts, ACKs e backfill index não foram reescritos. Nenhuma mídia foi movida, recopiada ou reprocessada nesta etapa.

O namespace original e a extensão somam 284 registros de metadata. A implantação usou candidato testado, canário de leitura real, locks intake → queue, barreira temporária e rollback preparado. O pin do owner transport permaneceu inalterado e compatível, pois seu executável não mudou.

## 3. O uso dos 172 tratados não foi fabricado

A consulta paginada leu as 36 contas registradas da operação, 14.597 anúncios únicos e 1.670 vídeos retornados pelas bibliotecas de vídeo das contas. A cobertura de anúncios exclui os DELETED não disponibilizados nessa consulta; vídeos de Page/referência podem existir fora do edge advideos. Esses limites impedem interpretar ausência de match como prova de nunca usado.

Cem dos 172 tratados têm candidatos por título original em vídeos vinculados a anúncios atuais. Isso não é prova determinística da linhagem do tratado: o catálogo e o registro de uploads não contêm o vínculo de mídia desses 172, e um download-canário Meta retornou payload transcodificado diferente tanto do original quanto do tratado. Não confundir título, posição numa pasta Usados ou esse payload derivado com igualdade de bytes.

Os 172 permanecem no legado, reservados e fora do pool automático. O catálogo recebeu `storage_availability=verified_archive_legacy_hold` e uma anotação de uso não verificado; nenhum `used_by`, ad ID ou manager foi inferido. Os 12 RAW e três não finais são descritos no ledger de objetos, não adicionados como novos candidatos produtivos.

## Aceite e decisão restante

- 217 testes focados passaram (211 regressões e seis guards novos persistidos em `tests/test_ares_archive_historical_reconciliation.py`), além das provas reais de todos os 187 leitores.
- Ciclo canônico: worker pronto, sem bloqueios na fatia executada; owner agendado e heartbeat nativo relidos. A verificação específica dos 187 não foi substituída por esse green slice.
- 216 linhas de catálogo receberam somente disponibilidade/anotação de conciliação. IDs, hashes, status, reservas, elegibilidade, ownership funcional e referências de campanha permaneceram iguais.
- Zero nova exclusão, movimento/cópia de mídia, mudança de ACL/credencial ou criação de campanha.

**Próximo passo decisório:** validar com os gestores/Ares a destinação dos 172 tratados antes de reclassificar em Usados/Exclusivos ou liberar qualquer reserva. Recomendação: manter o hold e obter confirmação operacional por lote/gestor, usando os candidatos Meta apenas como auxílio. Esta investigação não autoriza contato/handoff novo, liberação ao estoque comum, novo uso em campanha ou mudança da política de confiança por iniciativa própria.

A primeira campanha nova pelo padrão Exclusivos → Usados continua um aceite separado, acompanhado pelo recibo real, não pela remarcação de históricos.

## Evidências

`/root/.hermes/profiles/zeus/artifacts/drive-legacy-reconciliation-1566533058130088158/`: baseline, provas exatas de purga, readback Meta, cobertura paginada, joins de RAW/referências, provas de bytes/leitor, candidato/deploy/rollback, diff de catálogo e testes. Não armazenar URLs de paginação/Source Meta ou credenciais nesses documentos.

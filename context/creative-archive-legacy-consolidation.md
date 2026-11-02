# Consolidação do acervo criativo legado

## Autoridade e limites

- Responsável: Zeus; dono: Rodolfo Mattei.
- Aprovação: mensagem `1566510979838255326`, thread `1562078493498540042`, continuidade do padrão aprovado em `1566497527719661640`.
- Fonte operacional: `data/ares/creative-ops/30tb-archive/legacy-consolidation/` (`plan.json`, `binding.json`, `execution.json`, bindings nativos de parent/source).
- Estado: reorganização física aplicada e validada; classificação histórica ambígua e primeiro uso do novo fluxo são camadas separadas. A recorrência é registrada no fechamento, sem promover um tick manual a evento agendado.
- Sem exclusão de criativos, recópia, reprocessamento, mudança de ACL/credenciais, criação de campanhas ou liberação de reservas. O owner executor existente permanece isolado; agentes/verificadores continuam na SA canônica.

## Topologia vigente

- A raiz `MGS-ARQUIVO` conserva `CRIATIVOS` e `_MGS_CONTROLE`. Este último é o controle técnico protegido e não foi deslocado.
- Entrada única permanece `UPLOAD MANUAL` do Drive MGS, ID `1ARBvLammWUHuAclNmcriwkkgeedKryBd`; não houve mudança em suas pastas ou fontes pendentes.
- A árvore operacional é `CRIATIVOS/<OP>/<IMG|VID>/01_READY`, `<NOME> - Exclusivos` e `<NOME> - Usados`, conforme `context/creative-manager-storage-standard.md`.
- Providers, originais, cópias de implantação e estruturas antigas ficam em `CRIATIVOS/_ARQUIVO_FISICO`. A pasta homônima histórica UPLOAD MANUAL e a cópia-piloto solta foram preservadas em estruturas técnicas, não excluídas nem apresentadas como entrada/peça produtiva nova.
- O namespace físico é explícito em `ares_archive_namespace.py`. O futuro produtor usa o root nativo verificado, não cria outra árvore na raiz antiga. Os caminhos lógicos congelados continuam evidência histórica e não são reescritos.

## Resultado comprovado

- 122 reparentings exatos com intent/CAS e readback: 25 branches, 85 objetos de mídia/estoque e 12 pastas legadas. Dez pastas técnicas novas, criadas pelo owner e verificadas pela SA.
- Todos os 15.107 objetos do inventário anterior continuam presentes, com os mesmos IDs, nomes, bytes/checksums nativos, targets e acesso. Apenas os parents explicitamente planejados mudaram. O inventário posterior contém 15.117 objetos; a diferença são as dez pastas técnicas.
- 85 peças com classificação comprovada: 25 Exclusivos e 60 Usados. As 60 associações conta/anúncio/campanha/creative foram relidas na Meta. Os 25 exclusivos preservam sua entrega/reserva anterior; ausência de anúncio não é a única prova.
- Em 26 casos, o antigo stock ID já era inacessível, mas a cópia histórica exata e seu ACK existiam: o mesmo provider ID foi exposto como view de estoque; nenhuma cópia nova nem ID lógico substituto foi criado.
- 257 registros de catálogo receberam somente localização/histórico de localização. Checksums, IDs lógicos, reservas, elegibilidade, ownership funcional e referências de campanha foram preservados.
- 97 providers afetados tiveram leitura real pelo consumidor, prova de ancestralidade/owner/stock e download integral com MD5/SHA-256: 482.556.056 bytes. Canário não vazio de 14 objetos/quatro streams passou e foi restaurado antes do lote.
- Os 22 jobs dos incidentes COPIED_PATH/COPIED_METADATA originais foram novamente verificados pelo reconciliador real, com as fontes/cópias integrais quando presentes, sem alterar requests/receipts/ACKs.

## Reconciliação explícita, não falsificação de metadata

`binding.json` é vinculado ao digest do plano. Parents nativos aceitos e metadata de fonte têm documentos auxiliares com digest/autoridade/membership exatos. Nome de exibição humano pode divergir do nome canônico lógico somente na lista aprovada com os mesmos IDs e bytes. A resposta nativa é preservada em `provider_metadata`/`stock_metadata`; não se fabrica resposta de API.

Uma projeção histórica mantinha o parent congelado apesar da localização autorizada: corrigida com pin nativo independente, preservando o ACK original. A comparação inicial do owner da raiz também continha uma diferença de projeção: o snapshot antigo omitira permissionId; email e permissionId atuais foram confrontados com o pin canônico, sem mudança real de owner.

Duas fontes clean dos jobs antigos permanecem no intake `SHEIN_US_ES/Ícaro`, com os mesmos IDs e bytes. O reconciliador de leitura aceita somente suas localizações e snapshots exatos; fontes não foram movidas/reprocessadas. O guard destrutivo de retirada continua exigindo a origem original e não foi relaxado para apagar arquivos dessa entrada.

## Exceções no fechamento inicial — histórico supersedido

- 187 objetos das antigas pastas rotuladas Usados não possuem prova suficiente de uso no catálogo. Foram preservados com os mesmos IDs nas estruturas legadas, sem promovê-los a Usados/Exclusivos nem liberá-los ao pool. Desses, 172 têm reserva de gestor no catálogo, mantida inalterada; quinze não têm esse join de catálogo.
- 44 registros históricos distintos apontam a IDs retornando 404 para a SA e não têm provider correspondente comprovado no acervo enumerado. São registros preexistentes, não objetos desaparecidos nesta migração. Não afirmar exclusão, perda ou existência global apenas pelo 404; rastrear evidência/backup/origem antes de qualquer recuperação.
- A autoria dos movimentos anteriores continua sem prova nativa; Drive Activity API desativada não foi substituída por inferência de owner/last modifier.
- Próximo trabalho: conciliar uso/disposição dos legados ambíguos e os 44 registros; depois fechar comunicação/deduplicação do cron mantendo incidentes reais. Não alterar cron funcional, apagar fontes/legados ou inventar recibos para silenciar alertas.
- Primeiro uso real do fluxo novo continua sob acompanhamento interno do Zeus, pelo recibo `manager-standard/first-production-use.json`. Mover peças já utilizadas nesta consolidação não equivale a criar uma campanha nova nem concluir esse gate.

## Estado vigente após a conciliação

O pedido `1566533058130088158` supersede a classificação de exceções acima, conforme `context/creative-archive-legacy-reconciliation.md`: os 44 IDs foram vinculados por ID/hash/recibo à purga explicitamente confirmada em `1563588372872699927`, sem nova exclusão. Nos 187 objetos, há 172 tratados com uso ainda não comprovado, 12 originais RAW e três materiais de referência/não finais. Todos os 187 tiveram bytes/ACK e leitura lógica validados; 102 incompatibilidades de path histórico foram corrigidas por uma extensão exata e testada do namespace. Reservas e elegibilidade não mudaram. Naquele fechamento, a pendência era a confirmação operacional do uso/destinação dos 172. Rodolfo a resolveu explicitamente em `1566639091007758458`: os 172 tratados foram movidos com os mesmos stock IDs aos nove destinos Usados dos gestores das pastas históricas e relidos integralmente, conforme a seção final de `context/creative-archive-legacy-reconciliation.md`. Reservas, elegibilidade, ownership funcional, providers e referências Meta foram preservados. Não reabrir a confirmação dessa coorte nem confundir a declaração humana com um vínculo Meta que não foi fornecido.

## Limpeza técnica posterior — 1566643959458168864

O pedido para terminar a limpeza está em `context/creative-archive-technical-cleanup.md`. Inventário nativo e manifesto exato preparados: proposta de lixeira para 29 pastas técnicas e uma cópia-piloto comprovadamente duplicada, sem purga permanente. A confirmação crítica específica ainda não foi fornecida. Nove pastas vazias de compatibilidade e todos os arquivos não alvos ficam protegidos; não confundir o acervo ativo de providers em `_ARQUIVO_FISICO` com resíduo descartável. A observação do primeiro pedido novo é uma aceitação produtiva separada, não obrigação de Rodolfo fabricar uma campanha de teste.

## Evidências e rollback

Evidências independentes: `/root/.hermes/profiles/zeus/artifacts/drive-legacy-consolidation-1566510979838255326/`, em especial `whole-tree-identity-integrity-final.json`, `migrated-consumer-full-byte-validation.json`, `original-drift-jobs-revalidation-final.json` e `closure-tests-final.json`.

Plano, journal e `inventory-before-finalization.jsonl` preservam os IDs/parents originais e os snapshots anteriores. Rollback exige CAS e reaplicação reversa dos mesmos IDs sob os locks intake → queue → inventário; não executar restauração cega ou novas cópias. Pins de código do executor são atualizados apenas após validação, preservando seu histórico e sem restart.

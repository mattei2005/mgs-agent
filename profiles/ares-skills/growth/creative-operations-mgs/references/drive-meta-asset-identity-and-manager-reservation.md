# Identidade Drive × Meta e reserva de uploads de gestores

Use esta referência quando for necessário decidir se um criativo tratado no Drive já está sendo usado por um gestor ou pode entrar no pool de testes do Ares.

## Invariante

Original e tratado são uma única linhagem criativa. Nome de arquivo, pasta `01_READY` ou nome do anúncio não provam ineditismo.

Todo asset enviado por gestor começa como:

```text
reservation_status = RESERVADO_PELO_GESTOR
ares_eligible = false
```

Silêncio não libera. A liberação exige declaração expressa ou conciliação suficiente com a plataforma real.

## Quando o gestor baixa do Drive e envia à Meta

O download normal preserva o conteúdo do arquivo, mas não transporta o `drive_id` para a Meta. Ao fazer upload, a Meta cria identificadores próprios e pode processar/recomprimir a mídia.

Não assumir que MD5/checksum do Drive será diretamente comparável ao identificador da Meta.

Relacionar, quando disponíveis:

```text
Drive/inventário                  Meta
--------------------------------  ---------------------------------
asset_drive_id                    ad_id
canonical_filename                creative_id
original_checksum/clean_checksum  image_hash ou video_id
perceptual_fingerprint            effective_object_story_id
dimensões/duração/aspect ratio    conta/campanha/adset/anúncio
original → tratado                thumbnail/frames/conteúdo visual
```

O nome do anúncio é apenas rótulo operacional. O filename pode aparecer na biblioteca da Meta, mas é sinal auxiliar, não chave de identidade.

Depois do primeiro match, persistir o vínculo Drive → Meta no inventário.

## Ordem segura de conciliação

1. Consultar anúncios e creatives no runtime/API real, incluindo ativos, pausados e histórico relevante.
2. Usar `ad_id` para localizar o anúncio e `creative_id` para o objeto criativo.
3. Cruzar `image_hash`/`video_id`/`effective_object_story_id` quando expostos.
4. Cruzar nome canônico, dimensões, duração e proporção como sinais auxiliares.
5. Se houve reexportação ou tratamento, usar fingerprint/comparação visual; hash binário pode mudar.
6. Marcar match como reservado/usado e inelegível, salvo decisão explícita de reteste.
7. Repetir a conciliação imediatamente antes de campaign write para evitar corrida com gestores.

## Fluxo humano recomendado

Para reduzir ambiguidade, o gestor usa preferencialmente a versão tratada do Drive e informa:

```text
nome canônico
conta de anúncio
campanha ou nome do anúncio
```

O gestor não precisa descobrir IDs técnicos; Ares os obtém em read-only e registra o relacionamento.

Se o gestor subir o original antes do tratamento, o tratado correspondente continua reservado e inelegível. Estratégias diferentes (bot e tráfego direto) não tornam original e tratado candidatos independentes.

## Preflight de arquivos nomeados pelo gestor

1. Liste e pagine somente a pasta exata autorizada; resolva cada nome humano para um único Drive ID, preservando a ordem dos grupos e a grafia live. Não envie nomes informais diretamente a um preparador que exige `canonical_filename`.
2. Antes de baixar ou reservar, faça GET dos IDs selecionados com `id,name,parents,trashed,size,md5Checksum,owners,capabilities,properties,appProperties`. Os helpers compactos podem omitir `appProperties`; solicite o campo explicitamente para não perder a marcação de proveniência.
3. Confira `reference_only`, os vínculos de Library quando presentes e o inventário canônico por ID. `reference_only=true` é evidência de classificação como referência, não prova de direitos de uso; ausência da chave também não comprova aprovação final. Owner corporativo, nome de produto e presença na pasta do gestor não substituem a linhagem.
4. Havendo referência sem prova de transformação/aprovação final, pare antes de upload Meta ou campaign write. Preserve request, grupos, copy e início solicitado; registre os IDs e o motivo e peça somente as versões finais ou autorização para produzir adaptações reais. Não remova propriedades, renomeie ou invente registros para liberar o preparador.
5. Para arquivos finais com identidade ainda não resolvida, baixe e confirme tamanho/MD5 live; procure o SHA256 nos campos de checksum da linhagem existente. Hash idêntico conserva a linhagem mesmo com nome ou Drive ID diferente; ausência de match não autoriza criar um candidato final automaticamente. Verifique metadata separadamente: `clean=true` prova sanitização técnica, não aprovação de conteúdo nem ineditismo.
6. Resolva o mapa completo `nome informado → Drive ID → asset_id → canonical_filename` antes da preparação. Se houver drift comprovado, siga a reconciliação abaixo; se o arquivo realmente não estiver registrado, conclua o intake autorizado antes de retomar o preparador central.

### Estoque permanente existente e confirmação de versão final

- Para uma origem já existente em `MGS-ARQUIVO/CRIATIVOS/<gestor>`, teste primeiro `ares_archive_storage.resolve_media` e o `drive_file_readback` canônico por ID. Um registro histórico verificado com `stock_representation=retained_source` pode fornecer leitura/download direto; `canMoveItemIntoTeamDrive=false` não bloqueia esse consumo e não justifica pedir transferência para UPLOAD MANUAL quando nenhum movimento é necessário.
- Vincule a confirmação explícita de versão final do gestor elegível aos IDs/checksums e ao request original. Não repita a pergunta já respondida; preserve a proveniência e a marcação histórica de referência, sem alegar transformação, direitos ou ineditismo. Ausência dessa aprovação continua fail-closed; a confirmação não cria elegibilidade global nem dispensa classificação, metadata, reserva, reconciliação e QA.
- Na importação autorizada de uma linhagem histórica existente, preserve o primeiro registro somente quando comprovado pelo manifesto histórico e pela correspondência exata de Drive ID + SHA256; registre separadamente o horário atual da importação/aprovação. Nunca substitua `first_seen_at` por uma data antiga inferida do nome ou da criação do arquivo para contornar um gate. Sem a prova histórica, aplique o intake/arquivo corrente ou mantenha a pendência real.
- Normalize a taxonomia apenas no conjunto final autorizado e com plano reversível, colisões verificadas e GET após cada alteração; mantenha ID, bytes, pasta, cópia histórica e mapa do nome humano. Não invente uma segunda linhagem para o mesmo conteúdo nem altere mappings/ACKs para satisfazer o preparador.
- Se o pre-stage fizer uploads e depois falhar no guard de proveniência de objetos, reconcilie primeiro os títulos determinísticos por `act_<conta-autorizada>/advideos`, com paginação e readiness. Essa resposta account-scoped comprova os IDs; retome o mesmo preparador para adotar os uploads confirmados, sem repetir POST, editar o guard ou ampliar escopo. A aceitação final exige o runner central, QA renderizado e igualdade dos IDs do checkpoint com as árvores ativas.

## Recuperar drift de nomes e reposições na pasta do gestor

- Se o preparador rejeitar nome ausente/ambíguo, liste por API a pasta exata inteira antes de pedir outro arquivo: o Drive pode conter todos os nomes literais enquanto o inventário mantém nomes anteriores. Compare também os IDs dos registros cujo nome já coincide; coincidência de nome não garante o arquivo certo.
- Para renomeação no mesmo ID, exija igualdade de MD5/tamanho live com o registro. Para reposição com ID novo, baixe a cópia selecionada, confira MD5/tamanho do Drive, SHA256 contra a linhagem existente e metadata clean; preserve os IDs anteriores e histórico Meta. Checksum idêntico é a mesma linhagem, não um asset novo.
- Trate trocas de nomes como um mapa completo antes de editar: um nome solicitado pode apontar no cache a outra linhagem cujo tratado está na lixeira. Confirme cada ID antigo por GET, preserve backup e histórico, reconcilie apenas registros comprovados sob lock e valide unicidade de todos os nomes solicitados contra seus IDs live. Não renomeie o Drive, apague histórico ou descarte uma colisão apenas para satisfazer o lookup; registro histórico retirado do lookup precisa conservar nome anterior e evidência da retirada. Registre manutenção de dados em REPORT-INFRA.
- Uma reserva de request anterior concluído não prova execução ainda em andamento nem libera uso global. Para reuso explicitamente solicitado pelo mesmo gestor, valide o estado terminal anterior e os anúncios na conta exata; mantenha bindings/test_history e anexe a transferência de reserva ao histórico. Request anterior ainda resumível permanece conflitante; não roube a reserva.
- Retome o mesmo pedido pelo preparador central, dry-run e Engine v3. Antes de concluir, exija igualdade de campaign/adset/ad IDs do checkpoint com as árvores finais, cobertura exata de ad/creative IDs pelas provas renderizadas e conferência literal dos grupos/copy. Essa conferência real testa o reparo; metadados reconciliados sozinhos não comprovam campanha concluída.

## Pitfalls

- Não considerar `01_READY` sinônimo de “nunca usado”.
- Não liberar asset porque não houve resposta do gestor.
- Não confiar somente no nome do arquivo ou anúncio.
- Não confiar somente no `creative_id`: duplicações/reuploads podem criar outro creative.
- Não confiar somente em checksum binário após reexportação ou processamento da Meta.
- Não tratar original e tratado como dois testes distintos sem autorização expressa.

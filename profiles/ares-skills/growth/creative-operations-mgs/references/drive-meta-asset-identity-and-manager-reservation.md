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

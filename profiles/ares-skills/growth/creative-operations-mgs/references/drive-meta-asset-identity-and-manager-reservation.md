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

## Pitfalls

- Não considerar `01_READY` sinônimo de “nunca usado”.
- Não liberar asset porque não houve resposta do gestor.
- Não confiar somente no nome do arquivo ou anúncio.
- Não confiar somente no `creative_id`: duplicações/reuploads podem criar outro creative.
- Não confiar somente em checksum binário após reexportação ou processamento da Meta.
- Não tratar original e tratado como dois testes distintos sem autorização expressa.

## Entrada operacional unificada no Ares

Rodolfo, Geizian, Kelly e gestores autorizados enviam criativos diretamente ao Ares. Não existe handoff agente legado → Ares.

Ares trabalha com pedido natural. País, vertical e idioma devem ser inferidos quando houver evidência segura; se faltarem e alterarem destino/naming, perguntar somente o bloqueio mínimo. Nunca inventar esses campos.

Entrada recomendada:

```text
País: US
Vertical: CC
Língua: ES
Estratégia: bot | tráfego direto | desconhecida
Conta: quando conhecida
[anexo]
```

Formato curto aceito:

```text
US | CC | ES | bot
[anexo]
```

### Operação SHEIN — tráfego direto

Para criativos de tráfego direto da SHEIN nos Estados Unidos, aceitar e registrar:

```text
US | SHEIN | EN | tráfego direto
[anexo]
```

SHEIN_US_EN segue a ordem `<VERTICAL>_<COUNTRY>_<LANG>`. Resolver a operação e o destino pelo catálogo/binding ativos, `ares_archive_locations` e `ares_archive_storage`: o estoque permanente fica nos 30 TB, não fisicamente no Shared Drive. O path legado MGS-AGENTS/CRIATIVOS/SHEIN_US_EN e o ID histórico `1yV7Uge_KFN_Sih-iuVd7FY68cpfCUrxi` são evidência anterior, não instrução para recriar pastas ou substituir IDs. vertical=SHEIN é o valor informado pelo gestor; país, idioma, estratégia, reserva e elegibilidade permanecem campos separados. Não confundir o exemplo EN com o contrato de outra operação ES.

## Reserva padrão de upload humano

Todo upload de gestor começa fail-closed:

```text
reservation_status = RESERVADO_PELO_GESTOR
ares_eligible = false
```

O original e a cópia tratada compartilham a mesma linhagem. Se o gestor usar o original, a tratada também fica inelegível. Silêncio nunca libera o asset.

## Arquivo permanente e binding vivo

Fonte vigente: `context/drive-flat-intake-cutover.md`, confirmações1566814476626563115 e1566825959645253764, e `flat-intake-binding.json`. O estado anterior de integração em validação foi supersedido pelo cutover aceito; não usá-lo como bloqueio atual. Agentes usam SA canônica, Shared Drive somente para entrada/staging e componente owner isolado para transporte autorizado aos 30 TB. Preservar IDs, linhagens, status, reservas e ares_eligible=false. Pedido de upload/registro não autoriza campanha nem DELETE/trash. Receita `creative-operations-mgs/references/flat-upload-intake.md` e contrato `shared-drive-30tb-archive-queue.md`.

## Estrutura Drive canônica

A raiz real e o backend devem ser validados por API. No flat ativo, entrada simples e stock permanente são separados:

```text
MGS-AGENTS/
└── UPLOAD MANUAL  [arquivos diretamente; contexto vem do pedido]
    └── _PROCESSAMENTO  [staging técnico temporário]

30 TB / MGS-ARQUIVO / CRIATIVOS /
└── <VERTICAL>_<COUNTRY>_<LANG>/
    ├── IMG/
    │   ├── 01_READY
    │   ├── 02_TESTING
    │   ├── 03_TESTED
    │   ├── 04_WINNERS
    │   ├── 05_REJECTED
    │   └── 99_LEGACY
    └── VID/
        ├── 01_READY
        ├── 02_TESTING
        ├── 03_TESTED
        ├── 04_WINNERS
        ├── 05_REJECTED
        └── 99_LEGACY
```

Não criar subpastas intermediárias de placement/idioma no destino final sem aprovação. Placement fica no inventário; status fica na pasta. O exemplo de status é estoque permanente, não árvore a criar no intake. Resolver também os destinos registrados `<NOME> - Exclusivos` / `<NOME> - Usados`; common não libera reserva, e usado só é confirmado pelo uso real. Paths MGS-AGENTS/CRIATIVOS podem permanecer namespace lógico de inventário, sem reescrita em massa.

Quando o pedido autorizado for tratar/mover:

1. registrar o pedido humano e IDs exatos no binding flat, usando o mesmo job/claim; só então inventariar/classificar o lote, sem segundo writer;
2. criar cópia limpa;
3. validar `clean=true`;
4. validar a cópia no staging e concluir transporte/receipt/ACK/stock;
5. validar por readback a entrega permanente em 01_READY ou `<NOME> - Exclusivos`, conforme o pedido;
6. preservar o original por mesmo ID e provas de bytes/ACL, sem delete; READY/LEGACY do staging não são acervo permanente;
7. reconciliar o conjunto e o saldo exatos; arquivos de outros pedidos ou sem contexto na entrada são contados separadamente, não exigidos como zero global.

Se o pedido disser copiar/manter original na entrada, preservar conforme solicitado.

## Inventário mínimo unificado

```text
asset_id
original_filename
canonical_filename
source_manager
requested_by
created_by
vertical
country
language
strategy
ad_account_id
source_drive_id
asset_drive_id
original_checksum
clean_checksum
perceptual_fingerprint
format
angle
person
orientation
p_orient
variant
status
reservation_status
ares_eligible
used_by
campaign_owner
meta_ad_id
meta_creative_id
meta_image_hash
meta_video_id
effective_object_story_id
width
height
aspect_ratio
placement_fit
metadata_clean
first_seen_at
last_reconciled_at
performance_label
notes
```

Fonte local canônica:

```text
/root/mgs-agent/data/ares/creative-ops/inventory/assets.jsonl
```

## Antes de campanha

`01_READY` significa pronto tecnicamente. Campaign Ops deve conciliar Meta × Drive antes da seleção, atualizar reserva/elegibilidade e repetir a conferência imediatamente antes do write.

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

## Reserva padrão de upload humano

Todo upload de gestor começa fail-closed:

```text
reservation_status = RESERVADO_PELO_GESTOR
ares_eligible = false
```

O original e a cópia tratada compartilham a mesma linhagem. Se o gestor usar o original, a tratada também fica inelegível. Silêncio nunca libera o asset.

## Estrutura Drive canônica

A raiz real deve ser validada por API antes do write. Estrutura atual:

```text
MGS-AGENTS/CRIATIVOS/
├── UPLOAD MANUAL
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

Não criar subpastas intermediárias de placement/idioma no destino final sem aprovação. Placement fica no inventário; status fica na pasta.

Quando o pedido autorizado for tratar/mover:

1. inventariar e classificar;
2. criar cópia limpa;
3. validar `clean=true`;
4. colocar a cópia em `01_READY` correto;
5. validar Drive readback;
6. mover o original para `99_LEGACY`, sem deletar;
7. confirmar que a entrada contém apenas pendências.

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

# Manifest and commands

## Manifest modes

```text
pure_clone              source campaign copied deeply; no replacement ads
clone_prestaged         campaign/adset/ad copy lineage + exactly 3 ready replacement media assets
from_zero_prestaged     new campaign + adset + creatives + ads; exactly 3 ready media assets; no clone IDs
```

O alcance do registry é específico ao modo: `pure_clone` reutiliza os creatives/mídias já existentes e pode executar com registry vazio. Os dois modos prestageados exigem exatamente três registros `ready` por campanha. `clone_prestaged` exige IDs fonte e usa `/copies`; `from_zero_prestaged` proíbe `source_campaign_id`, `source_adset_id` e `source_ad_id`, exige objetos `campaign_create` e `adset_create` completos e usa somente os edges diretos da conta. Não é necessário prepopular o registry sem pedido: quando houver mídia crua, o próprio pedido autorizado executa pre-stage/upload/readback antes de materializar e selar o manifest.

Every campaign requires:

```text
idempotency_key
app_key
account_id
mode
name
start_time with timezone
status PAUSED or future ACTIVE
```

`pure_clone` exige `source_campaign_id`. `clone_prestaged` exige `source_campaign_id`, `source_adset_id`, exatamente três ads e `source_ad_id` não zero em cada ad. `from_zero_prestaged` exige `campaign_create`, `adset_create`, exatamente três ads e ausência total de IDs fonte. Para cada mídia prestageada: asset ID, checksum, vertical video ID, square video ID, `ready=true`, `upload_edge=ad_account_advideos` e `association_verified=true`.

Payloads containing `standard_enhancements` or external `https://fb.com/messenger_doc/` are rejected before transport.

## Commands

```text
python3 /root/mgs-agent/scripts/ares-campaign-engine-v3.py validate --manifest <path>
python3 /root/mgs-agent/scripts/ares-campaign-engine-v3.py plan --manifest <path>
python3 /root/mgs-agent/scripts/ares-campaign-engine-v3.py media-summary
```

Register media only after real Meta readback. Manual registration is for importing already-confirmed IDs; the v3 pre-stage uploader is separately gated by `media_upload_enabled=true` and `--confirm-upload`:

```text
python3 /root/mgs-agent/scripts/ares-campaign-engine-v3.py media-register \
  --account-id <id> --asset-id <id> --checksum <sha256> \
  --vertical-video-id <id> --square-video-id <id> --ready --confirm-readback

python3 /root/mgs-agent/scripts/ares-campaign-engine-v3.py prestage-upload \
  --account-id <id> --page-id <id> --asset-id <id> --checksum <sha256> \
  --vertical-file <file> --square-file <file> --confirm-upload
```

The v3 pre-stage uploader is active but still requires `--confirm-upload`, advertiser User Access Token, Page `ADVERTISE` identity, exact checksum, both Meta videos reaching ready and exact ID membership readback in `act_{AD_ACCOUNT_ID}/advideos` before registry commit. It never uploads campaign media to `/{PAGE_ID}/videos`. Manual registration requires `--confirm-readback` and the same ad-account association proof.

Build CPV manifests only when every campaign has three ready media records and the source creative templates are current. `--campaign-numbers` accepts 1–100 values; the planner chunks them into bundles of two automatically:

```text
# Clone com mídia prestageada
python3 /root/mgs-agent/scripts/ares-campaign-engine-v3.py build-cpv \
  --assets-json <assets.json> \
  --source-snapshot-json <source-selection.json> \
  --mode clone_prestaged \
  --campaign-numbers 14,15 --operational-date YYYY-MM-DD \
  --request-id <unique-id> --status ACTIVE --output <manifest.json>

# Criação do zero com mídia prestageada
python3 /root/mgs-agent/scripts/ares-campaign-engine-v3.py build-cpv \
  --assets-json <assets.json> \
  --source-snapshot-json <reference-selection.json> \
  --mode from_zero_prestaged \
  --from-zero-specs-json <explicit-create-specs.json> \
  --campaign-numbers 31 --operational-date YYYY-MM-DD \
  --request-id <unique-id> --status PAUSED --output <manifest.json>
```

No modo do zero, `source-snapshot-json` fornece somente templates/campos de referência já lidos; seus IDs fonte ficam fora das campanhas do manifest e nunca entram no executor. `from-zero-specs-json` contém `from_zero_specs[]`, cada item com `campaign_create` e `adset_create` completos.

Use `--status PAUSED` only for an explicitly requested technical canary; normal production uses `ACTIVE` with the future `start_time` sealed in the manifest.

The builder emits `prevalidated=false`. Promote only through the deterministic prevalidator, which rechecks the media registry and seals a tamper-evident content digest:

```text
python3 /root/mgs-agent/scripts/ares-campaign-engine-v3.py prevalidate \
  --manifest <draft.json> --registry <media-registry.json> --output <sealed.json>
```

Any post-prevalidation change invalidates execute. Source, templates, media, budget, UTMs, names and future start must be final before sealing.

## Execute gate

Real execute requires all four:

```text
manifest.prevalidated = true
config.enabled = true
config.write_enabled = true
--confirm-execute
```

O config instalado está ativo sob guards de `development_access`: `enabled=true`, `write_enabled=true` e `media_upload_enabled=true`. Isso não remove os gates independentes de manifest selado, `--confirm-execute` ou `--confirm-upload`; `--offline-fake` é somente teste e nunca contata a Meta.

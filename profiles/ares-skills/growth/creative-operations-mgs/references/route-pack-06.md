## Transição Creative Ops → Campaign Ops

Ares é dono das duas etapas. Não existe handoff entre agentes: a passagem ocorre quando o inventário compartilhado recebe evidência suficiente para Campaign Ops avaliar o asset.

## Gate de entrada em Campaign Ops

Campos mínimos:

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
format
angle
p_orient
source_drive_id
asset_drive_id
metadata_clean
status
reservation_status
ares_eligible
used_by
campaign_owner
notes
```

Para upload de gestor, o padrão inicial é:

```text
reservation_status = RESERVADO_PELO_GESTOR
ares_eligible = false
```

O asset só pode ficar elegível quando:

- o gestor informar que não utilizou e não utilizará;
- Rodolfo/Geizian/operação liberar expressamente;
- a conciliação Meta × Drive não encontrar uso e houver evidência suficiente;
- houver decisão expressa de reteste.

Silêncio do gestor nunca libera. `01_READY` não significa “nunca utilizado”.

## Conciliação antes da seleção

Antes de selecionar o asset para teste/campanha:

1. Ler candidatos tecnicamente prontos.
2. Consultar a conta Meta real e o histórico relevante.
3. Cruzar, quando disponíveis:
   - `ad_id`;
   - `creative_id`;
   - `image_hash` ou `video_id`;
   - `effective_object_story_id`;
   - original → tratado;
   - checksums e fingerprint perceptual/visual;
   - conta, campanha, gestor e estratégia.
4. Marcar como inelegível tudo que estiver reservado, rodando, `TESTING`, `WINNER` ou bloqueado. `TESTED` permanece inelegível por padrão; só retorna ao pool com decisão expressa de reteste, `retest_eligible=true`, histórico de tentativas preservado e conciliação confirmando ausência de uso ativo.
5. Reservar os escolhidos antes do write.
6. Repetir a conferência imediatamente antes de publicar, pois gestores podem agir entre análise e execução.

Renomeação, reexportação ou limpeza de metadata pode mudar hash/ID. Por isso, nome do anúncio/arquivo é auxiliar; a decisão usa IDs/hashes/linhagem/comparação visual.

## Transição para uso humano

Kelly, Geizian ou gestor podem usar o asset diretamente. Nesse caso, registrar:

```text
used_by = HUMAN
campaign_owner = <humano>
reservation_status = RESERVADO_PELO_GESTOR | UTILIZADO
ares_eligible = false
```

Se o original for utilizado, a versão tratada correspondente também fica inelegível, salvo decisão expressa de reteste.

## Limites e escalonamento

- Creative Ops pode criar/tratar/inventariar sem executar campaign write automaticamente.
- Campaign write carrega skill/guardrails de campanha e valida autoridade atual.
- Budget/billing/credencial seguem gates próprios.
- Conteúdo editorial pertence à Atena.
- Permissão/infra/incidente escala para Zeus.

## Hard gate de referência/backend

Se criação depender de referência externa ou provider específico:

1. validar referência/asset/backend real;
2. tentar rotas técnicas permitidas;
3. se bloqueado, parar e reportar evidência curta;
4. só usar fallback após autorização explícita;
5. nunca rotular output de um backend como se viesse de outro.

## Checklist

- [ ] Referência e provider essenciais validados.
- [ ] Asset final real validado visual e tecnicamente.
- [ ] Metadata `clean=true`.
- [ ] Original → tratado registrado.
- [ ] Drive readback confirmado.
- [ ] Reserva e `ares_eligible` definidos.
- [ ] Meta × Drive conciliado antes de seleção/write.
- [ ] Campaign write executado somente com skill e autoridade correspondentes.
- [ ] Estado final confirmado por readback.

# Sourcing GenAI reordenado sob review tipado

Use quando uma duplicação estática herdada continuar falhando em `flexible media/copy/tracking readback mismatch` após o aceite de diferenças de público ter sido validado.

## Procedimento

1. Preserve o mesmo request, ambos manifests selados e os campaign/adset/ad/creative IDs. Faça GET completo dos mesmos anúncios, incluindo `object_story_spec`, `asset_feed_spec`, `media_sourcing_spec`, `url_tags` e recursos individuais; uma leitura compacta não distingue campo omitido de drift real.
2. Compare separadamente story/imagem primária, feed textual, tracking, recursos e sourcing. Normalize `url_tags` ausente e vazio conforme o comparador canônico, sem mover UTMs. Se somente a ordem das variantes GenAI diferir, confira o multiconjunto das entradas completas, incluindo multiplicidade, hash, origem, enrollment e quaisquer outras chaves; comparar apenas hashes ou converter para set perde diferenças materiais.
3. Use `reviewed_copy_targeting.preserved_sourcing` somente no contexto obtido por `shein_continuation.validate_descriptor` do descriptor real. Exija slot/creative/digest selados, imagem primária e story idênticos, AFS exclusivamente textual integralmente igual e tracking literal. Não fabrique `APPROVED_RESUME` nem considere um aceite de público como autorização de diferenças de mídia.
4. Se o runtime ainda comparar sourcing por posição ou excluir AFS textual, separe manutenção da transação: preserve a primeira falha, fixture protegida, backup/inventário e CAS. Reproduza vermelho→verde e negativos de imagem extra/ausente/duplicada, hash, origem, enrollment, crop, imagem primária, Page, texto, tracking, payload e contexto antes de instalar e emitir REPORT-INFRA. Fora do review tipado válido, preserve o gate estrito de mídia nova.
5. Retome exclusivamente o mesmo descriptor pelo runner central:

   ```text
   python3 /root/mgs-agent/scripts/ares-shein-recovery.py --continuation <descriptor.json> --confirm-execute
   ```

   Preserve o início comercial futuro em `preserved_start_time`; o `start_now=true` técnico da continuação não antecipa a campanha. Não edite manifests, repita criação ou renderize novamente provas ainda válidas.
6. Após o retorno terminal, faça readback fresco no mesmo contexto validado. Exija QA semântico, `proof_covers`, conjuntos não vazios de IDs iguais ao checkpoint e campanha/conjuntos/anúncios ACTIVE, com início, budget e tracking do alvo. `engine_replayed=false` complementa, mas não substitui a igualdade de IDs. Somente então conclua na origem com as ressalvas aceitas e o bloco AdOps.

## Verificação

Exercite os comparadores com o binding real validado e as suites de sourcing, review de público e AFS textual presentes na instalação. Confira previamente os arquivos e o total executado: `unittest discover` com zero testes não é cobertura. Igualdade semântica offline não comprova QA renderizado, ativação ou serving.

# Chromium — readiness antes do attach

## Resultado

Manutenção t_8426333c iniciada somente após conclusão de t_8f7a90a8. Publicação atômica limitada a `scripts/ares_campaign_v3/preview_renderer.py`; novo teste em `tests/test_preview_renderer_readiness.py`. Nenhum restart de gateway, write Meta/Drive, canário, alteração de credencial, budget, manifest ou gate.

## Diagnóstico e correção

A presença de `DevToolsActivePort` não garantia conteúdo pronto. O fluxo original lia a primeira linha de arquivo vazio e levantava IndexError. Reproduzido deterministicamente no original, sem browser/rede/API; recibo `original-race-reproduced.json`. Isso não atribui falha à campanha nem explica sufixos adimages. Evidência anterior preservada em t_8364ae25.

O launcher aguarda arquivo completo com porta ASCII 1–65535 e caminho do browser, `/json/version` disponível em loopback e WebSocket correspondente ao mesmo host/porta/browser. Um deadline monotônico cobre os retries de startup e limita o timeout do probe HTTP ao tempo restante. Processo morto e prazo vencido falham fechado. A lógica de renderização, os gates URL/mídia/activation e o timeout contratado não foram relaxados.

O cleanup existente foi preservado: somente process group próprio criado com start_new_session, TERM/KILL e wait/reap antes de limpar o perfil temporário. Testes com Chromium real local, child morto, sentinel de diretório protegido e hashes do runtime confirmam preservação. Nenhum perfil persistente foi usado.

## Verificação executada

- Focados: 18 testes +29 subtests PASS.
- Regressão completa staging: 583 testes +484 subtests, 46 arquivos, sem exclusões/skips/falhas.
- Regressão completa instalada: 583 testes +484 subtests, 46 arquivos, sem exclusões/skips/falhas.
- Inclui IMG estático e VID local renderizados em Chromium real, rejeição de tipo errado/link-only e barreiras semânticas/activation simuladas.
- Testes determinísticos cobrem arquivo ausente/vazio→válido, escrita parcial, portas inválidas/limites, arquivo desaparecido/encoding inválido, endpoint indisponível/malformado/divergente, processo morto antes/durante probe, timeout/deadline e limpeza/reap.
- Zero tentativas de rede externa detectadas pelo guard socket da regressão; os testes renderizados usam HTTP local. Module-origin checks confirmam staging/installed conforme cada bateria.
- 31 arquivos protegidos (estado operacional, configuração e executáveis QA/Chromium) mantêm hashes do baseline; outros 59 módulos Python centrais inalterados.

## Publicação e recuperação

Backup original com SHA256; publicação por CAS e locks task/account/request, sem central writer ativo observado. O primeiro guard de publicação parou antes de substituir o original porque o candidato temporário `.py` entrou no próprio glob CAS. Readback comprovou nenhum módulo original alterado; o mesmo candidato foi hash-validado e renomeado `.tmp`, depois publicado atomicamente, sem excluir nem restaurar estado operacional. Recibo final em `deployment-receipt.json`.

Rollback, se necessário: reconciliar estado atual, adquirir coordenação, conferir hashes esperados e substituir somente o launcher pelo backup. Nunca restaurar snapshots operacionais antigos, apagar runtime/perfis persistentes ou fazer replay de campanha.

## Conhecimento e governança

Aprendizado salvo somente na skill própria Ares `meta-campaign-engine-v3/references/architecture-and-runtime.md`, seção Readiness do Chromium de QA. Readback, mirror e testes verificados. Registro `PROC-ARES-CHROMIUM-READINESS`, checkpoint `ARES-CHROMIUM-t_8426333c`, inventário `chromium-preview-readiness-t_8426333c` e audit local. REPORT-INFRA usa embed silencioso, content vazio e GET do alvo exato; recibo separado.

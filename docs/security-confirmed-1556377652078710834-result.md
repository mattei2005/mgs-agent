# Confirmação de segurança — instalada e validada

## Estado e autoridade

Rodolfo344196393512075265 confirmou1556377652078710834 e1556377669082419264 na thread1555572634228490283. A entrega adicional está concluída; supersede somente os bloqueios de três helpers, transporte e publicação da fila registrados em `docs/security-followup-1556332890743115850-status.md`. Não declara toda a lista de18itens corrigida. Item2campanhas,5downloads e7CTAs permanecem fora desta intervenção; chaves, dadosfinanceiros e política destrutiva não foram alterados.

## Entrega real

1. **Cache Atena** — `skills/content-generate-rec-p1/scripts/card-cache-lookup.sh`: SQL parametrizado, transação, logs escapados; contrato real `card-cache.db/card_cache` preservado, incluindo TTL, todoscampos, incremento somenteemhit e exit0/1. A candidata antiga referia outro schema e NÃO foi promovida.
2. **Imagem Gemini** — mesmo diretório, `generate-featured-image.sh`: APIkey fora daURL/argv, header porfd, erro remoto semeco debody, temporários/outputs únicos, base64shell comhashreverso. Prompts/compositor/identidadecartão/compressão1280×720preservados. Nenhuma geração paga foi feita nesta validação.
3. **Busca de imagem** — `search-card-image.sh`: Bravekey porfd separado, fora deargv; nomes únicos em candidatos/saída oficial eBrave. Ranking/fontes, fallbackBing, normalização e política de downloads preservados. O helper separadoBingnão foi alterado nem certificado por associação.
4. **Controlador financeiro** — `apps/finance-system/finance_release.py`: somente encode/decode transporte; base64gerado porcomando ehashreverso obrigatório. Bootstrap explícito sobleaseexclusiva+lockslegados, CAS, backup e readback. AST de `production_policy`, `publish`, `recover`, `restore_locked`, `legacy_locks`, `validate_plan` idêntica. Bloqueio de selfupdate no manifesto normal permanece. Native20controller+4transporteshell passam; remoteReadreal também validou novoencoder.
5. **Fila financeira publicada** — release `queue-four-confirmed-1556377652078710834`, journal`committed`. Quatroprodutores existentes `meta-lookup.mjs`, `google-lookup.mjs`, `manual-quotes.mjs`, `history-refresh.mjs` nos dois destinoslocal/remoto, sob controladorcanônico. Lock compartilhado de admissão, limiteglobal16semrace, sem eliminar histórico. Pendingnão termina sóporqueTTLvisualvenceu; workerterminal continua fonte. Nenhum banco/ledger/entradafinanceira ou importador foi reprocessado.

## Verificação

- **15testes dos helpers**: Bash/SQL/PIL/ImageMagick reais; só rede/op e paths delog/cache substituídos por fixtures declaradas. Doismesmoslug simultâneos geram arquivosdistintos; contratoTTL/injeção/logs e transporteFD exercidos. ZerochamadasreaisGemini/Brave ezeromutaçãocacheprodutivo durante testes.
- **Gatesfinanceiros integrais atuais:249Node+203Python=452**, semfail/skip. Reciboscanônicos porfase commanifestoexato, nãocombinaçãomanual deexecuçõesparciais. npm auditomitdev:zerovulnerabilidadesreportadas.
- Concorrência4processos/4produtores/filesystem/flockreais:25/25. HTTPExpressreal emloopback9/9, comidentidades/papéis explicitamentefixture; não chamar issologinprodutivo.
- Navegadorprodutivo autenticado comMFAowner:28checksantes+28depois, desktop/mobile, incluindo cinco visõesmanager, persistência/reabertura, zeroerrosJS ezeroPOSTfinanceiro. Não alegar7loginsprodutivosdistintos. Sessões técnicas desta validaçãoencerradas, sessõehumanaspreservadas.
- Hasheslocal/remoto dos4produtores idênticos ao candidato; serviçoapp/socket/PostgreSQLativos. Filaantes/depois37registros(32ready5error),nenhumpending/malformed e nenhuma submissãoprodutiva para testar.
- Fingerprints porcenário/revisão/result/overrides/additions,ledger,históricoeauditfinanceiro idênticosantes/depoiscutover eapósbrowser. Apenas serviçoappfinanceirorecarregado; nenhumgateway/VPS/DBreiniciado.

## Falhas e recuperação

- Um teste de imagem esperava1920×1080intermediário; ocompressorcanônico já produz1280×720. Corrigida sóassertion do teste e repetidas15verificações; não mudou design.
- Um lookup deartefato presumiu nomefinal-existing-plan inexistente; resolvido pelo arquivo real `release-plan-four-existing-final.json`. Nenhuma nova publicação nessa falha.
- RotaCLIastra de revisão excedeu180s apósassertionKeyErrorstatus: duas verificaçõesreopencontextnãotêmHTTPstatus. Assertioncorrigida por tipo e28checksrevalidados;20controller+4shellreexecutados. ReciboAstrareal confirmouprovideropenai-codex/subscription_included epublication_readytrue; semalegarjanela872kvalidadaemcatálogofresco. Rótulodoprompt eDBDiscordSoldivergiam; rota finance foi revalidadaemsessãoAstraexplícita antesdecutover, não pelo rótulo. Sessão `20261004_115514_341c85`.
- Alteração simultâneaCSSreconciliada no audit `FINANCE_COMPOSITION_BLOCK_STYLING_PUBLISHED`, autoridade1556369322782232598. Não era anomalia. Gateemcursofoi interrompido; linkpublicantigopreservado eassetscopiados emsnapshotpequeno427539bytes/30arquivos, testes/helpersstageatualizados. Gatesintegrais reexecutados no snapshotestável. Nenhumprivatefullclone.
- Consulta de metadadosSQLite usoucreated_at inexistente; descoberta porPRAGMA econsulta porIDcorrigida, semescritanaDBdeestado.

## Fontes, rollback e limites

Evidências em `backups/security-confirmed-1556377652078710834/`: `installed-four.json`, `helper-tests.json`, `astra-finance-review.json`, `published.json`, `remote-before.json`, `remote-after.json`, `financial-before.json`, `financial-after.json`, `financial-post-browser.json`, `{before,after}-browser.json`, `verification-summary.json`.

Originais dos3helpers/controlador em`before/`. O journal/backups exatos dos8destinos estão em `apps/finance-system/private/releases/queue-four-confirmed-1556377652078710834/`; não usar `recover` para uma releasejácommitted. Reversão do códigoaplicado requer novo manifestobounded com baselines atuais; jamais restaurarbanco sobreatividadesposteriores. Dump adicional remoto em`/home/zeus/mgs-finance-backups/queue-confirmed-1556377652078710834/finance-before.dump`, SHAe catálogopg_restoreverificados; nãofoifeito restorematerializado.

A fila ainda percorreJSONshistóricos: correçãoderace não é política de retenção ou promessa de zero recorrência. Os18diretóriosanteriores continuam preservados. Item5downloads, comprovação depropriedade/consentimentotelefone e assinaturadecliquesSMS continuam pendências separadasdearquitetura; novascredenciais/OTP/links/limpeza não foram impostos. ContadorOrigin continua mitigação de navegador,nãoprova devisitaúnica.

Aprendizado próprioZeus persistido em `hermes-agent-operations/references/security-guard-native-validation.md`, commirrorverificado: respeitarschemareal de cache, transportar segredo porfd, contratoimagem final1280×720 e snapshotestáveldeassets antesdegates. Nenhuma skilldeoutroagente fora dos3helpersautorizados foi alterada. Inventário, audit, registry/checkpoint eREPORT-INFRA devem apontar conclusão deste escopo, semfecharlacunasnãoautorizadas.

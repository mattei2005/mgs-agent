# Item 5 — downloads instalados e validados

## Autoridade e escopo vigente

Rodolfo `344196393512075265`, thread `1555572634228490283`: continuação `1556448396171022478`, confirmação crítica específica `1556452175473803376`. Esta entrega supersede somente o estado pendente do item 5 nos relatórios anteriores. Não reexecuta o pacote financeiro já concluído nem altera campanhas/Ares, CTAs, credenciais, SMS ou política de exclusão.

## Instalado

- `scripts/mgs_public_fetch.py`: transporte dedicado, sem promover o módulo piloto que continha políticas de campanhas/CTAs. HTTP(S)/portas80/443, todas as respostas DNS públicas, conexão em IP validado, certificado/SNI do hostname original, gate em cada redirect, limite20MiB e limite8redirects. Sem cookies/auth/proxy do ambiente. Descompressão também limitada. GET/HEAD apenas.
- `scripts/mgs-rec-runner.py`: consultas públicas, verificação pública, overrides de imagem e imagem de WP usam a fronteira. Fallback de navegador intercepta recursos pelo transporte, bloqueia service workers e WebSockets upstream.
- `scripts/mgs-p1-runner.py`: consultas públicas, rendering aid, download de imagem e verificação pública usam a fronteira; APIs autenticadas WordPress ficam intactas.
- `skills/content-generate-rec-p1/scripts/search-card-image.sh`: URL inicial validada antes de credenciais/providers, downloads oficiais/Brave protegidos. Ranking, composição, normalização e fontes preservados. Bing invocado por wrapper que vincula seu download e contexto ao transporte sem editar `search-card-image-bing.py`.
- `tests/test_p1_dry_run_safety.py`: mock atualizado para a nova fronteira; não usa a rede real para produzir a fixture.

## Provas reais

Evidência em `backups/download-protection-1556452175473803376/`:

- `native-tests.json`:29testes,0falhas/erros/skips; HTTP/stream/redirect/tamanho/descompressão em servidor loopback explicitamente fixture; validação de DNS e callers reais, CLI privada negativa.
- `p1-safety-tests.json`:2regressões,0falhas/erros/skips. Reexecutadas no código instalado. CLI P1 Eggbev real:preflight_only,content_generated=false,publication_ready=false e0writes/providers.
- `browser-tests.json`:6checks no módulo instalado, Chromium1243 existente somente leitura, ambienteQA isolado:documento/imagem fixture, GET privado rejeitado, listener WebSocket privado com0conexões; navegação Bing real200 e seletores de candidatos presentes. Não é prova de instalação de Playwright no interpretador padrão; nenhum browser/perfil do Ares alterado.
- `post-install-smoke.json`:8checks:bloqueios nos2runners e shell, fonte Bank of America pública real pelos2runners, PNG público baixado pelaCLI/validadoPIL e18diretóriosfinanceiros preservados.
- `public-smoke.json`:GETs reais200 em Eggbev, Bank of America, Bing ePNGWordPress, sem provider pago.
- `preservation-check.json`:57funções/classesREC e65P1 têmAST idêntica após inverter exclusivamente a fronteira de downloads/browser; regras, prompts, composição e CTAs não mudaram.
- `installed.json`:hashes e readback exato dos5alvos; fontes atuais iguais ao backup antes da instalação; nenhum produtor selecionado em execução no preflight. CLI/help eBashsyntax reais positivos. Sem restart de gateway/VPS.

## Falhas recuperadas antes da publicação

- Primeiro patchV4A rejeitado por correspondências múltiplas; nenhuma escrita. Correção por substituições exatas/repetidas na stage, depois preservaçãoAST.
- Ensaio de navegador interrompido aos150s/90s/45s. Stack real isolou deadlock de `ws.close()` síncrono no callbackWebSocket. Corrigido para interceptação sem conexão upstream; fixture eBing real reexecutados com6checksverdes, depois novamente no código instalado. Sem processos de ensaio mantidos para execução futura.
- TesteP1 antigo ainda mockava `requests.get`, deixando escapar a nova chamada para `example.com/card.png`404. Atualizado mock para `public_response`;2regressões verdes sem rede.

## Rollback, limites e pendências

Originais em `before/`. Reversão:restaurar somente os4arquivos existentes com conferência do baseline atual; manter o novo transporte sem referências em vez de excluir por associação. Não houve exclusão de diretórios financeiros, publicação editorial, geração paga, envioSMS ou alteração de chaves.

Certificação restrita aos callers integrados. Execução direta do helperBing sem wrapper e APIs autenticadas não recebem certificação global por associação. Browser probado emQA não resolve presença de dependência no interpretador operacional; a dependênciaPlaywright estava ausente no interpretador do tool shell e não foi instalada nele. A proteção falha fechada se faltar uma capacidade necessária do navegador. Não houve scan novo pago.

Restam decisões separadas de propriedade/consentimento de telefone e integridade dos linksSMS, e política de retenção/manifesto final de exclusão. Os18diretórios continuam não elegíveis no manifesto anterior; nenhuma exclusão aprovada nesta confirmação.

Aprendizado salvo no subsistema de skillZeus, `hermes-agent-operations/references/security-guard-native-validation.md`, com mirror/readback:transporte dedicado, interceptação de browser sem deadlock, mocks da fronteira correta e importlib. Inventário/audit/checkpoints eREPORT-INFRA vinculam esta fonte.

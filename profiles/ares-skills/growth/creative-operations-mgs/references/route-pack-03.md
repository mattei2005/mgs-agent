## Sanitização obrigatória de metadados

Todo criativo gerado, baixado do Canva, recebido de Kelly/Geizian/gestor ou preparado para Drive/handoff deve passar pelo gate server-side de limpeza antes de virar asset final.

Comandos canônicos:

```bash
/root/mgs-agent/scripts/clean-creative-metadata.sh clean /path/to/creative.png --agent ares
/root/mgs-agent/scripts/clean-creative-metadata.sh verify /path/to/creative.metadata-clean.png
```

Regras operacionais:

```text
Origem/etapa                     Regra
───────────────────────────────  ─────────────────────────────────────────────
Criativo criado pelo Ares         Limpar antes de handoff/Drive/entrega final.
Criativo baixado do Canva         Tratar como bruto; limpar antes de organizar.
Criativo recebido de humano       Limpar antes de virar entregável final.
Transição para Campaign Ops ou humano       Usar sempre o arquivo `.metadata-clean.*`.
```

Reporte apenas status curto, sem despejar metadata bruta no Discord:

```text
clean: true
harmful_tags_before: N
harmful_tags_after: 0
clean_path: /path/to/creative.metadata-clean.png
```

Pitfalls operacionais:

- Anexos do Discord podem retornar `403 Forbidden` no download direto se a requisição não tiver `User-Agent`; ao importar thread/anexo, tente novamente com header simples antes de declarar bloqueio.
- Em vídeos `.mov/.mp4`, ExifTool pode manter descritores estruturais QuickTime/TrackN após `-all=`; isso não deve virar recusa automática se o sanitizer oficial já tratar como allowlist estrutural e `verify` retornar `clean=true`.
- OAuth Drive: se o helper de escrita retornar HTTP 400 enquanto o watchdog do Ares indicar `token_ok`, pode haver um `refresh_token` antigo no arquivo de token sobrescrevendo o refresh válido do arquivo OAuth client. Validar cada fonte separadamente reportando apenas HTTP/erro redigido; usar a fonte válida para concluir a operação, sem cair para service account em writes de My Drive. Alterar/sincronizar credencial permanente exige escopo/autorização de infra.
- Se o sanitizer oficial precisar de ajuste de script/allowlist para validar corretamente um criativo, isso deixa de ser tarefa puramente criativa: enviar `REPORT-INFRA` ao Zeus com arquivo alterado e evidência curta.

Referências da skill:

```text
/root/mgs-agent/docs/CREATIVE_METADATA_SANITIZER.md
/root/mgs-agent/scripts/clean-creative-metadata.sh
Referências da skill:

```text
references/drive-ready-destination-correction.md — correção canônica: READY fica em pasta de status; STORY/FEED/REELS ficam no inventário/handoff, não em subpasta final.
references/human-upload-ready-drive-handoff.md — fluxo validado para upload humano via Discord → import/read attachment quando `.mov` não entra no gateway → detecção de formato/ângulo → limpeza de metadata → upload verificado em READY → inventário/handoff Ares.
references/upload-folder-live-verification.md — verificação forte quando originais continuam em UPLOAD MANUAL: cruzar `source_drive_id` com relatório, validar `dest_drive_id`/ancestralidade live, tamanho, SHA-256 limpo e sanitizer em todos os destinos; não confundir preservação do bruto com pendência.
references/car-br-pt-multi-image-ready-handoff.md — fluxo validado para lote de imagens CAR Brasil/Português: Ares aplica classificação/naming/metadata/READY diretamente; Ares só aplica regras de campanha/teste depois do handoff verificado.
references/spain-cc-human-upload-handoff.md — fluxo para uploads CC Espanha/ES: Ares aplica classificação/naming/metadata/READY; Ares aplica apenas regras de campanha após handoff verificado; inclui mapping `CC_ES_ES`, naming e blocker de OAuth Drive sem mencionar Ares antes do upload verificado.
references/video-variation-gpt-grok-workflow.md — workflow para comparar variação de vídeo com GPT/OpenAI e Grok/xAI a partir de anexo Discord, incluindo import read-only, contact sheet, geração e sanitização.
references/car-video-reference-recreation-lessons.md — aprendizados de correção Rodolfo/Geizian para variação de vídeo CAR: recriar linguagem audiovisual da referência, evitar legenda/zoom/slideshow como final, usar prompt editável e respeitar precedente GPT preview + Grok preview.
references/car-pt-financing-video-recreation.md — playbook BR/PT para recriar vídeos de financiamento de veículo com vendedor/concessionária, carro branco, cenas/narrativa, voz integrada e QA contra zoom/slideshow/TTS robótico.
references/video-gpt-grok-precedent.md — precedente operacional: GPT preview + Grok preview; não negar capacidade sem checar histórico/thread citada pelo usuário.
references/video-provider-default-and-oauth-pitfalls.md — correções de sessão: GPT/OpenAI como provider padrão quando não especificado; variação real de vídeo não é overlay; OAuth Grok/xAI em Discord/headless sem vazamento de Callback URL; wrapper Grok usando venv Hermes.
references/video-copy-variation-from-existing-asset.md — workflow para criar variação rápida de copy em vídeo existente mantendo o mesmo carro/produto, validando contact sheet, valores/oferta e metadata limpa.
references/safari-invitation-video-reference-workflow.md — workflow validado para convite animado com referência YouTube/anexo, incluindo regra de não produzir antes de validar a referência, fallback por anexo Discord, YouTube cookies/proxy persistente, Grok real via wrapper e dados fixos legíveis.
references/meta-ad-library-creative-intake.md — fluxo para analisar/baixar referências da Meta/Facebook Ad Library com Playwright/API, validar token sem expor segredo e interpretar erros comuns.
references/meta-ad-library-playwright-browser-download.md — workflow de prova de vida e download via Chromium/Playwright quando `curl` recebe challenge/403 mas o browser consegue renderizar Library, IDs, imagens e vídeos.
```
```
references/meta-ad-library-creative-intake.md — fluxo para analisar/baixar referências da Meta/Facebook Ad Library com Playwright/API, validar token sem expor segredo e interpretar erros comuns.
references/meta-ad-library-playwright-download-packaging.md — workflow validado para baixar imagens/vídeos da Meta Ad Library via Playwright, sanitizar e entregar ZIP com inventário.
```
## Origem e uso dos assets

Classifique a origem e o consumidor antes de montar o plano.

```text
Origem                         Tratamento
─────────────────────────────  ─────────────────────────────────────────────
LEGACY_AGENT_GENERATED                 Nomear e colocar direto no fluxo organizado.
HUMAN_UPLOAD                   Validar, inventariar e propor organização.
CANVA                          Tratar como bruto/original antes de organizar.
KELLY / GEIZIAN / GESTOR       Registrar como `created_by` quando conhecido.
```

```text
Uso final                      Tratamento
─────────────────────────────  ─────────────────────────────────────────────
ARES                           Incluir handoff completo para campanha vio Ares.
HUMAN                          Organizar para uso direto por humano/campanha manual.
UNKNOWN                        Manter em revisão até contexto suficiente.
```

Nunca assuma que todo criativo precisa passar pelo Ares. Ares é consumidor opcional; Creative Ops continua responsável pelo padrão mesmo quando a campanha é humana.

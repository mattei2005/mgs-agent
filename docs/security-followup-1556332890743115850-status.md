# Segurança: fechamento parcial após decisões de Rodolfo

## Autoridade e preservações

- Thread `1555572634228490283`; decisões `1556332890743115850` e `1556336633480089792` de Rodolfo `344196393512075265`.
- Item2 excluído: regras de campanhas/Ares não alteradas. Item5 explicado por exemplo, não autorizado para instalação. Item6 autorizado e instalado no helper Grok. Item7/CTAs excluído, inclusive links/copy/arquivos estáticos preservados.
- Itens9/10/12/13/16/18 autorizados; autorização não elimina Critical Subset ou autoriza expandir o conjunto de publicação financeira para seu controlador protegido.

## Aplicado e verificado

- **6 / Grok**: `scripts/mgs-grok-generate.py`, raízes operacionais de mídia fixas, conteúdo válido de imagem, path/fd/symlink/arquivo regular e profile validados; rejeição antes de credenciais; base64 por shell com hash reverso. Nove testes nativos e CLI negativa real. URLs/data-URIs não são abrangidos pela contenção local; nenhuma geração ou chamada paga realizada.
- **9 / Reações**: `scripts/monitor-sb-messenger-token-invalid.py` autentica o reactor não-bot, Rodolfo ou os papéis atuais de destinatários Gestor/Admin, com paginação e falha fechada. Oito testes específicos + suíte existente; GET nativo de membro Discord200 confirmou a dependência, sem fechar incidente real ou modificar usuários/papéis.
- **9 / Dry-run e concorrência P1**: `scripts/mgs-p1-runner.py` retorna apenas preflight local, `publication_ready=false`/`content_generated=false`, antes de providers, WP e taxonomy. Nomes de arquivos exclusivos por execução. Dois testes e CLI nativa Eggbev positiva; nenhum artigo ou criativo produzido. Não certificar dry-run de todo o ecossistema por esse resultado.
- **9 / CSV**: backend `class-mgs-chat-sms.php` do MGS Chat Funnels em Zuout neutraliza fórmulas no CSV e preserva valores no banco, telefones literais e envio SMS. Dez casos PHP nativos, validação da classe carregada no WordPress e hash remoto exato. Opções e outros arquivos preservados. Plugin0.4.5; mudança somente no backend, não no pacote/frontend.
- **10 / Login Router**: cache de tentativas continua limitado a10k; limite por origem preservado, sem bloqueio global pela cardinalidade. SuíteGo/race/vet, binário/processo do serviço exatos, health/login/favicon públicos200, routes hash inalterado. Primeiro smoke urllib apresentou403 antes/depois, provocou rollback; diagnóstico curl/browserUA200 e origem403 esperada; nova implantação validada. Reinício somente do aplicativo Router, nenhum gateway/VPS.
- **10 / Contador**: backend do Dicas Finanças restringe POST de navegador por Origin canônico, compatível com homeHTTP atrás de edgeHTTPS. Dez casos PHP, próprio Origin aceito e externo rejeitado no WordPress; HTTP403 real com código próprio para Origin externo, HTTP400 de slug inválido com Origin próprio. Seis arquivos estáticos/opções/CTAs e fórmula/base1892 inalterados. Origin não autentica visitantes únicos; request HTTP forjado/bots continuam como risco residual.
- **12 / Prevenção de cópias**: entrada reutilizável `apps/finance-system/deploy/prepare_release.py` usa `source_stage.py` com allowlist limitada, hashes, fixtures explícitas e `test_output_dirs` vazios separados; sem recursão deprivate/evidências/dumps/oldstages. Usada em preparação real e seis testes nativos do helper. Closure nativa de concorrência:45arquivos de código,302642bytes; não é cópia completa do financeiro. Nenhum cron de exclusão, prazo temporal de retenção arbitrário ou mudança dos importadores.
- **13 / Manifesto**:18diretórios históricos inventariados em `backups/security-round-1556332890743115850/finance/preservation-manifest.json`, com dependências/preservações. Não excluir nenhum deles nesta tarefa nem tratá-los como órfãos por idade/tamanho.
- **16 / Cobertura**: matriz dos27achados históricos em `backups/security-round-1556332890743115850/finding-matrix-current.json`, classificando instalado/mitigação parcial/candidato/exclusão/bloqueio e limitações. Nenhum novo scan pago/reset.
- **18 / Verificação**: componentes instalados revalidados e rollback preservado. Fechamento consolidado é PARCIAL, não uma certificação global ou declaração de todos18itens corrigidos.

## Fila financeira — candidata, não instalada

- Rota privadaAstra900k/OAuth da sessão `20261004_115514_341c85`. Cache872000não é prova de nova medição autenticada da janela. Modelo global não foi alterado por comando de configuração.
- Quatro produtores existentes:meta-lookup,google-lookup,manual-quotes,history-refresh. Função compartilhada exportada pelo módulo existente, sem bootstrap de novo arquivo em produção.
- Concorrência nativa com imports exatos,filesystem/flock reais e quatro processos:25/25. Ensaio HTTP Express/loopback:9/9; identidades/papéis são fixtures declaradas, não logins produtivos. Sem invocar banco financeiro ou provedores. Prova/planos preservados, não usar como canário de autenticação produtiva.
- Gate completo Node:249/249. Suíte Python completa:167testes,13erros por openpyxl ausente no intérprete do gate e fixture PNGomitida. Diagnóstico corrigido com overlay QA isolado openpyxl3.1.5/et-xmlfile2.0.0, PNGoriginal copiado com hash exato e testes focados24+31+3+7positivos. A nova suíte Python integral e receipts por fase ainda estão pendentes; não inventar/compor recibos canônicos verdes.
- Falhas intermediárias de closure:20fixturesreferenciadas ausentes, depois diretório vazio de output ausente; ambos corrigidos na origem/preparação, históricos RED/timeouts preservados. Timeouts artificiais70s/180s não são regressão de negócio nem validação. Um comando de teste apontou erroneamente para pathlocal de runtime financeiro; foi corrigido para candidata local, mantendo runtime real RunCloud separado. Teste de arquivo isolado semcwd correto também foi reexecutado no candidato.
- **Bloqueio de escopo/política**: `finance_release.py` usa `base64.b64encode` no transporte de publicação e leitura. Isso conflita com o invarianteMGS de base64 produzido por shell e hash reverso antes de uso. O controlador é protegido e não pertence ao plano dos quatro payloads autorizados. Não alterar/adaptar/contornar o controlador ou publicar enquanto falta a autorização específica para corrigir seu transporte e as validações finais. Saldo/histórico/importadores/produção permaneceram intactos.

## Confirmação adicional solicitada na thread

Ação recomendada, ainda NÃO autorizada:
- Skill compartilhada da Atena `content-generate-rec-p1/scripts/card-cache-lookup.sh`: SQLinterpolado → parâmetros; candidata passou quatro testes SQLite, não promovida.
- Mesma skill `generate-featured-image.sh` e `search-card-image.sh`: remover chaves de argv/URLdeprocesso e temporários compartilhados; preservar providers, composição, downloads e contratos, sem implantar o item5 por associação.
- Controlador `apps/finance-system/finance_release.py`: corrigir exclusivamente transporte de empacotamento para shell+hashreverso, preservando locks/fences/CAS/backup/rollback/gates. Não muda chaves ou regras financeiras; exige escopo próprio, não payload de self-update.
- Estado atual acima; estado novo será corrigido/testado/canário/reversível. Pós-ação: Rodolfo não precisa configurar ou trocar credencial. Nenhuma exclusão, mudança deAGENT/permissões/budget, produção de campanha ou alteração deCTA incluída.

Outras lacunas registradas: comprovar propriedade/consentimento de telefone no intake público e integridade de cliquesSMS exige decisão de arquitetura (eventual verificação do telefone/assinatura do provedor), não imposição deOTP, dedup ou mudança de links/campanhas nesta autorização. O template da skillAres não foi alterado.

## Fontes de execução

- `backups/security-round-1556332890743115850/`: receipts nativos, deploy Router/WP, matriz, candidata cache, provas Finance e originais protegidos.
- Decisão ativa: `docs/security-followup-1556014718810853448-scope.md`.
- Procedimento reutilizável próprioZeus: `hermes-agent-operations/references/security-guard-native-validation.md`, com routing e mirror próprios.
- REPORT-INFRA e checkpoint precisam refletir fechamento bloqueado/parcial, não sucesso integral. Nenhum processo de teste/continuação pode permanecer ativo após entrega.

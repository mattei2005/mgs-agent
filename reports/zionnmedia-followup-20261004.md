# Zionn Media — formulários e performance: bloqueio de transporte

Autorização: Rodolfo `1556448165153210379`, thread `1556015743831646349`.
Escopo: comprovar entrega dos formulários e melhorar mobile, preservando Elementor/base/Pro/PowerPack.

## Resultado confirmado

- Dois envios sintéticos pelos formulários públicos nativos: home Elementor e Contact CF7. Marcador `MGS-TEST-ZIONN-1791156902611322134`; nome identifica teste técnico, não cliente. Destinatários foram os já configurados: contact@zionnmedia.com e admin mattei2005@gmail.com; sem alteração de destinatários/configurações.
- Ambos retornaram HTTP200 e mensagem de sucesso (`success=true` / `mail_sent`). Isso comprova o processamento do formulário e entrega ao transporte local, não recebimento na caixa.
- Os dois novos envios da janela de teste aparecem no Postfix como `A8F3D21022A1` (23:35:06, 1022 bytes, Google Workspace) e `A81AB21022A1` (23:35:14, 948 bytes, Gmail). Ambos terminaram `dsn=5.7.28`, `status=bounced`: Google bloqueia o IP do servidor por reputação/taxa de mensagens não solicitadas. O log também possui rejeições históricas; não foram contadas como testes deste turno.
- Transporte atual: WordPress → `/usr/sbin/sendmail -t -i` → Postfix direto, sem relayhost e sem SMTP SASL. O MX de zionnmedia.com é Google e seu SPF inclui somente `_spf.google.com`; não foi mudado DNS nem transporte.
- Nenhum novo envio após comprovar a rejeição. Nenhuma limpeza/reenvio da fila compartilhada (171 mensagens preexistentes no preflight, zero destinatários Zionn naquele momento). Não atribuir a origem dessa fila ao Zionn; causa/reputação global não investigada neste escopo.
- Cofre `MGS Conteúdo`: busca por títulos Zionn/SMTP/provedores comuns encontrou somente itens WordPress Zionn. Isso não certifica ausência de um serviço corporativo em outros cofres/títulos; não criar credenciais nem contratar serviço por inferência.

## Preservação

Readback depois dos testes: árvores/hash manifests Elementor/base+Pro+PowerPack, hashes do builder das cinco páginas, controles MU e configurações CF7/Elementor forms iguais ao preflight. Não foram modificados arquivos/plugins/dados de layout ou configurações do servidor.
O Elementor gravou um registro técnico de submissão `200`, campo `message` contém o marcador do teste. Registro mantido e claramente sintético; sua exclusão exige gate destrutivo separado. Não houve exclusão de arquivo/dado nem ocultação desse efeito.

## Performance

Baseline novo em duas execuções Lighthouse mobile: 72/100 e 72/100; LCP 5270.543ms e 6022.520ms; CLS0 em ambas; transferências 945810 e 945843 bytes. Não alegar melhora neste turno.
DOM renderizado mobile/desktop usa Montserrat. O CSS de Google Open Sans do GeneratePress continua no caminho bloqueante; a imagem do hero mobile e do rodapé somam transferências relevantes. Estes são candidatos, não otimizações aplicadas ou canários aprovados.
Nenhuma otimização em produção foi aplicada antes do bloqueio decisório de envio. Performance permanece pendente e independente de renovar o Elementor.

## Decisão

Recomendação: transporte SMTP/API corporativo autenticado, restrito ao Zionn, com remetente autorizado e readback remoto/inbox. Não mudar Postfix compartilhado nem contornar reputação repetindo pelo mesmo IP. Antes de instalação/configuração, resolver provedor existente, credencial via1Password e obter confirmação específica da integração de produção; cobrança/contratação e credenciais permanecem Critical Subset. Não propor rota pessoal Gmail/OAuth como fallback.

## Recuperações e aprendizado

Pré-requisito 1Password inicialmente ausente no subprocesso: carregado ambiente canônico `/root/mgs-agent/.env` sem expor valores; acesso SSH/WordPress confirmado. Subcomando de checkpoint corrigido para `checkpoint-upsert`. Browser/Lighthouse usam o interpreter e Chromium já validados, sem instalação de pacotes.
Regra de validação de entrega (handler/MTA/SMTP/inbox separados e parada diante de rejeição) salva em `wordpress-plugin-integrity-audits/references/complete-wordpress-site-reaudit.md`.
Evidências privadas: `/root/.hermes/profiles/zeus/workspace/zionn-followup-20261004/` (`form-test.json`, `mail-delivery-log.json`, `runtime-before/after.json`, `preservation-readback.json`, `test-record-readback.json`, `lighthouse-baseline-0/1.json`).

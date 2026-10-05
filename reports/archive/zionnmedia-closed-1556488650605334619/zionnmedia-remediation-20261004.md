# Zionn Media — remediação e gates restantes

Atualizado: 2026-10-04T18:41:40.375092+00:00.
Autorização: mensagem 1556336762215989379, thread 1556015743831646349.
Estado: **correções seguras aplicadas e validadas; não encerrado como remediação integral**.

## Aplicado em produção

- Backup integral de banco/webroot e clone privado em `/var/backups/mgs-zionnmedia-remediation-20261004`; rollback preservado. Não removido no encerramento.
- Removidas as 16 âncoras ocultas conhecidas da home e suas cópias contaminadas nas revisões; os 54 rascunhos classificados foram preservados em quarentena reversível com manifesto privado, não apagados.
- Leitura posterior: 54 rascunhos marcados; 1620 registros de posts preservados; zero ocorrências do marcador conhecido em post_content e _elementor_data. Isso é evidência delimitada, não garantia de ausência universal de malware.
- Atualizados 7 plugins públicos a partir de downloads.wordpress.org: akismet 5.7.2, all-in-one-wp-migration 7.111, elementskit-lite 4.0.7, sticky-header-effects-for-elementor 2.2.3, wordfence 9.0.2, wps-hide-login 1.9.19, wordpress-seo 28.6. Verificação nativa final: todos os 7 solicitados aprovados.
- Defesa da rota ElementsKit /elementskit/v1/dynamic-content para requisições sem privilégio de edição, mantendo os controles de segurança anteriores.
- Corrigidas fontes geradas com host HTTP legado, imagens/background, metadescriptions das cinco páginas, headings, ARIA/contraste e resíduos legais/copyright. Correção legal editorial não equivale a parecer jurídico.
- MU plugin `/home/runcloud/webapps/zionnmedia/wp-content/mu-plugins/mgs-zionn-site-repairs.php`: SHA-256 `8e86b7651d95c4d183b003b9657221a24dc7985110bd5fd572cf1f762021d5b2`, payload exato conferido, instalado como runcloud e comportamento frontend validado.
- Assets ElementsKit não usados deixam de carregar somente nas cinco páginas conhecidas e com árvore de widgets reconhecida; widget desconhecido restaura o stack completo. Um glyph do menu foi substituído por fa-bars da biblioteca já suportada, eliminando a fonte addon de aproximadamente 465 KB. Nenhum outro widget foi alterado nesse cutover; hash da home igual ao canário.

## Validação final

- Produção: cinco rotas × dois viewports (390/1440), 10 casos aprovados, zero violações axe, overflow, imagens quebradas, spam conhecido, mixed content, erros JS/HTTP relevantes. Menu mobile/desktop e logo→home testados.
- Paridade: 15 verificações canonical público/cache-busted/origem aprovadas; quatro requests de segurança com 403 esperado aprovados.
- PHP 8.3.33: candidato final reaprovado em 10 casos no clone. Dois formulários testados pelo handler nativo exclusivamente no clone, com interceptação de e-mail; nenhum envio externo real e nenhuma certificação da entrega SMTP de produção.
- Screenshots e geometria desktop/mobile preservam o layout recuperado. O ícone novo permaneceu reconhecível, sem fallback vazio; diferenças de altura das seções no gate de ícone foram zero.
- Lighthouse da home, amostra laboratorial: mobile performance 72, accessibility 100, best-practices 100, SEO 100; desktop performance 97, accessibility 100, best-practices 100, SEO 100.
- LCP lab: mobile 5.20s; desktop 1.09s. Baseline auditado: performance 55 mobile / 58 desktop. Mobile melhorou, mas continua aquém do ideal; scores 100 de outras categorias não certificam segurança, WCAG, conformidade legal ou Core Web Vitals reais.
- Sem arquivo de manutenção no último gate privilegiado; servidor canário encerrado ao fim dos testes.

## Bloqueios e risco residual

1. Elementor Pro 3.21.0 e PowerPack 2.9.9 permanecem na unidade compatível instalada. A origem oficial do pacote Pro recusou o download (HTTP 401); fonte/pacote comercial PowerPack não está certificado. Não usados ZIPs de terceiros, não modificadas licenças, contas ou cobrança. Precisam de download oficial autorizado ou nova decisão para migração dos widgets. Contenção não substitui atualização nem certificação integral dos componentes comerciais.
2. Produção mantém PHP 8.1.34 da linha 8.1 fora do suporte. PHP 8.3.33 passou no clone final, mas não houve mudança de runtime de produção. Próximo cutover proposto: somente aplicação zionnmedia.com no MatteiInc01, PHP 8.1→8.3, sem outros sites; backup e retorno a 8.1 caso qualquer gate regresse. Exige confirmação específica antes de modificar a configuração/runtime do servidor.
3. Performance mobile ainda 72/100 e LCP de laboratório acima do alvo bom. Não classificar como otimização completa ou CWV aprovado; o stack comercial legado ainda permanece.

## Falhas intermediárias recuperadas

- Importação recursiva do helper: corrigida para importlib explícito; backup/clone reexecutados com sucesso.
- Guard de conteúdo/transferência longa/UTF-8: corrigidos e retestados antes dos gates.
- CSS antigo no CDN e MU criado em contexto root sem legibilidade frontend: diagnóstico de cache/identidade, CSS versionado e reimplantação como runcloud; payload e browser revalidados.
- Janela de manutenção concorrente: readback de locks/versões, manutenção encerrada e gate integral repetido; não atribuída a invasão nem a outro agente sem evidência.
- Parser do recibo de lint+JSON e verificação WP-CLI: mensagens nativas não-JSON reconhecidas explicitamente, contagem exata conferida e validação reexecutada. Stat inicial sem privilégio produziu Permission denied; repetido no contexto sudo autorizado, com encadeamento fail-fast.
- Nenhuma falha remanescente omitida: o 401 comercial e os gates de runtime/performance continuam abertos.

## Evidência e continuidade

Workspace: `/root/.hermes/profiles/zeus/workspace/zionn-remediation-20261004`. Artefatos finais: closure-receipt.json, production-readback.json, production-browser.json, updated-plugin-checksums-final.json, final-integrity.json, canary-final-php83.json, production-native-menu-icon.json, lighthouse-mobile-final.json, lighthouse-desktop-final.json e font-cdn-exact-readback.json.
Checkpoint: zionnmedia-remediation-20261004. Não promover este estado a concluído antes de resolver/aceitar explicitamente os gates restantes.
Skill wordpress-plugin-integrity-audits: aprendizados incorporados no SKILL.md e references/complete-wordpress-site-reaudit.md, com readback textual.

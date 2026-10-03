# Zionn Media — auditoria e correções seguras

## Estado

**Parcial, bloqueado por licenças e compatibilidade do conjunto visual. Não é fechamento integral do site.**

- Solicitante: Rodolfo Mattei, thread `1556015743831646349`, mensagem `1556020992411967559`.
- Alvo confirmado: `https://zionnmedia.com/`, webroot `/home/runcloud/webapps/zionnmedia`, MatteiInc01 `162.55.28.178`.
- Evidências: `/root/.hermes/profiles/zeus/workspace/zionnmedia-audit-20261003/`.
- Checkpoint: `zionnmedia-audit-20261003`.

## Causa confirmada e cache

A captura do proprietário coincide com o frontend atual: tema GeneratePress genérico, sem o runtime do Elementor e com widgets padrão. As cinco páginas publicadas preservam `elementor_canvas` e os dados do builder, mas todos os plugins normais estavam inativos. Um snapshot de 22/09 já registrava essa inatividade; não se atribui sua autoria nem se classifica como mudança nova desta conversa.

A hipótese de cache exagerado não foi corroborada: homepage pública, cache-busted e origem mostram o mesmo defeito de renderização; edge `CF-Cache-Status: DYNAMIC`, sem Age, e zero arquivos no cache local inventariado. Nenhum purge global foi aplicado.

## Correções realizadas

1. Recalculados os contadores de 20 categorias: 14 contadores positivos obsoletos passaram a zero, coerentes com zero posts publicados. Nenhum termo ou relacionamento foi excluído. Os links das categorias de spam desapareceram do HTML público.
2. Seis widgets de `sidebar-1` foram movidos para inativos preservando as configurações. O tema pode mostrar fallback de sidebar enquanto o canvas original não for recuperado; não se afirma remoção visual integral da sidebar.
3. `generatepress/footer.php` foi comparado ao ZIP oficial da mesma versão, 3.4.0. A diferença era exclusivamente um prefixo com dois parágrafos ocultos e links relativos para `2`. O original foi preservado fora do webroot e o arquivo oficial restaurado atomicamente, com PHP lint, modes e owner preservados. Mapa completo posterior: 142/142 arquivos do tema idênticos ao pacote oficial. Autoria da modificação não foi provada.
4. Contact Form 7 6.1.7 foi reativado; o formulário 6514 existe, aparece em `/contact/`, tem labels e campos obrigatórios e não deixa shortcode cru. Não foi enviado lead nem certificado recebimento de email.
5. A correção anterior do logo permanece: URL própria tanto no post_content quanto no link Elementor. O hash dos dados Elementor da home segue o da correção anterior.

## Preservação e provas

- 144 registros de posts/páginas/mídias tiveram status e SHA-256 de post_content comparados e preservados nesta auditoria.
- Cinco páginas publicadas continuam HTTP 200, sem o link errado do logo, sem os dois links ocultos e sem links das categorias suspeitas.
- Nove assets internos da população inicial: 9/9 HTTP 200.
- Desktop e mobile: zero imagens quebradas nas sondagens, sem overflow horizontal no mobile observado. O layout original permanece não recuperado.
- Core WordPress 7.1.2: checksums PASS. Elementor 4.3.3: checksums PASS.
- Verificação de 16 plugins: dez passaram, All-in-One Migration teve somente três arquivos adicionais no storage; cinco comerciais não têm checksum público disponível. Isso não certifica os cinco comerciais nem equivale a malware.
- Zero executável PHP/phtml/phar/php5 encontrado em uploads na coleta dirigida.
- Banco posts/options: CHECK TABLE coletado; conteúdo suspeito conhecido permanece em rascunhos históricos, não em posts publicados.
- PHP observado: 8.1.34; migração de runtime não foi aplicada e permanece separada, sujeita ao gate de sistema.

## Canário isolado e bloqueio

Foi criada uma cópia restrita em `/var/backups/mgs-zionnmedia-audit-20261003/canary`, com banco separado `mgs_zionnmedia_canary_20261003`, sem endpoint público e com WP Cron desabilitado. Nenhuma credencial, binding de licença ou cobrança foi criado/alterado.

Ativar Elementor 4.3.3 + Pro 3.21.0 + PowerPack 2.9.9 no clone passou no comando de ativação, mas renderizar o frontend produziu fatal: `Elementor\\Core\\Schemes\\Typography` ausente em `powerpack-elements/extensions/tooltips.php:365`. A falha ocorreu somente no clone. Desativar PowerPack no clone eliminou o fatal na home, mas deixa o widget de menu dependente ausente; não satisfaz o layout completo.

O updater do Elementor informou versão Pro 4.3.1 e campo package preenchido. O download genérico retornou HTTP 401 `Your site is not active`; a resolução nativa para `plugin-downloads.elementor.com` também retornou 401. Nenhum desses corpos é ZIP válido e nenhum pacote foi instalado. O vendor PowerPack respondeu `license=invalid`, apesar de o banco local conservar `pp_license_status=valid`. Não há autorização efetiva comprovada para os pacotes necessários.

Não foi ativado o conjunto visual incompatível em produção. Não houve downgrade, redesenho inferido nem edição de código comercial para contornar a falha.

## Backup e recuperação

- Snapshot SQL: `/var/backups/mgs-zionnmedia-audit-20261003/before.sql`.
- Bytes: 58809583.
- SHA-256: `6daa4f4aed0e45430891994d3f4797643dcd117ac8e386f6a636d6b7d0f3f6e9`.
- Importação no banco isolado e bootstrap da cópia: sucesso real.
- Footer anterior e candidato oficial preservados em diretório restrito, com hashes em `footer-restoration.json`.
- Opções/widgets e contagens anteriores preservados em JSONs restritos da evidência.
- Nenhum servidor/daemon de teste ou túnel foi iniciado. Clone e banco diagnóstico ficam inventariados para continuidade; exclusão exigirá o gate aplicável.

## Limitações e decisão necessária

Permanecem: layout original, menu PowerPack, formulário Pro da home, metadados/SEO do conjunto desativado, compatibilidade e integridade dos comerciais, PHP 8.1, auditoria axe/Lighthouse e aceitação visual do proprietário. Não existe certificação integral de segurança, envio de email, consentimento ou performance.

Recomendação: liberar o domínio nas licenças existentes e obter pacotes oficiais atuais para recuperar o conjunto original com canário; isso pode exigir regularização do proprietário, mas nenhum pagamento foi autorizado ou feito. Alternativa: nova autorização explícita para substituir dependências comerciais e reconstruir o layout preservando conteúdo/identidade; não executada.

## Recuperação de coletores e aprendizado

O subcomando `wp theme verify-checksums` não existe neste runtime; a alternativa foi a comparação integral com o ZIP oficial. Um coletor teve import ausente, corrigido antes de completar a evidência; o crawl tentou decodificar um PNG como UTF-8, foi corrigido e voltou a validar 9/9 assets. Esses defeitos de coleta não foram tratados como defeitos de produção.

Aprendizado salvo e conferido em `wp-plugin-mass-operation/references/wordpress-irrelevant-posts-incident-audit.md` (recontagem de termos após rascunho) e `wordpress-plugin-integrity-audits/SKILL.md` (campo package/banner local não substituem licença válida e ZIP autenticado). Não contém credenciais.

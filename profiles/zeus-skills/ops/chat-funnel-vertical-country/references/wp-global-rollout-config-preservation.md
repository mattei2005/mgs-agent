# MGS Chat Funnels — Rollout WP global sem contaminar configs

## Quando usar

Use esta referência em operações de rollout do `MGS Chat Funnels` quando Rodolfo pedir para abrir rotas `/chat/...` para o WordPress global (`wp_head`, `wp_body_open`, `wp_footer`) em vários sites.

## Lição operacional

Abrir a rota para WordPress global muda o ambiente da página. O chat deixa de ser HTML isolado e passa a carregar GTM, Yoast, WPCode, scripts/plugins globais, tema e footer. Isso é necessário quando Rodolfo quer que alterações globais do site reflitam no chat, mas cria dois riscos:

1. **UTM frágil:** se o link só recebe UTM no momento em que o card é renderizado, scripts globais podem ler/interferir no anchor antes da navegação final.
2. **Config contaminada:** subir ZIP completo do plugin pode sobrescrever `configs/*.json` do site vivo com configs locais de outro domínio, trocando URLs de oferta — ex.: OpenZed recebendo targets de Eggbev.

## Regra de deploy

Para rollout técnico de código/template/CSS/JS:

- Não subir pacote completo que contenha `configs/*.json`, salvo se o escopo for explicitamente alterar configs.
- `configs/*.json` são dados ambientais por instalação/site/chat. Mesmo nome lógico (`car-br-01.json`) em sites diferentes não significa config global compartilhada.
- Preservar configs vivas antes de qualquer alteração técnica.
- Aplicar abertura WordPress global e UTM hardening juntos; nunca abrir WP global sozinho.

## UTM hardening obrigatório

O renderer deve:

```js
card.dataset.mgsTargetUrl = offer.url || offer.target || "#";
card.href = mergeSourceParams(card.dataset.mgsTargetUrl);
```

E reaplicar antes da navegação:

```js
function refreshTrackedLinkHref(e) {
  const link = e.target && e.target.closest
    ? e.target.closest("a[data-mgs-target-url], a.offer-card, #call-btn")
    : null;
  if (!link) return;
  const targetUrl = link.dataset.mgsTargetUrl || link.getAttribute("href") || "";
  if (!targetUrl || targetUrl === "#") return;
  link.href = mergeSourceParams(targetUrl);
}

["pointerdown", "touchstart", "mousedown", "focus", "click"].forEach((eventName) => {
  document.addEventListener(eventName, refreshTrackedLinkHref, true);
});
```

## Validação mínima por domínio

Após deploy, validar publicamente em cada domínio:

- `/chat/car/br1?...utm_source=...` retorna HTTP 200.
- Sinais de WordPress global aparecem: GTM/Yoast/wp-json/wp-includes/wp-content.
- Sinais de hardening aparecem: `data-mgs-target-url`, `refreshTrackedLinkHref`, `pointerdown`, `touchstart`.
- Cards CAR apontam para o domínio correto do próprio site.
- Domínio errado não aparece nos P1 targets; especialmente não aceitar `eggbev.com/p1-` dentro de outro domínio.
- Clique real ou DOM `href` final contém UTMs.

## Sequência segura

1. Identificar sites alvo e domínio canônico de cada rota.
2. Fazer leitura pública inicial: WP global atual, hardening atual, targets atuais.
3. Preparar pacote/code-only sem `configs/` ou copiar somente arquivos de código/template. Quando usar WP Admin sem SSH, montar um plugin temporário baseado em `templates/mgs-chat-code-updater.php` com payload em `payload/` e ativá-lo uma vez para copiar os arquivos; depois desativar/remover o updater.
4. Se usar WP Admin, confirmar que o updater foi ativado; instalar sem ativar não altera o plugin principal.
5. Se usar SSH/SFTP/RunCloud, copiar apenas arquivos necessários (`mgs-chat-funnels.php`, templates/assets relevantes), não configs.
6. Rodar `php -l` no arquivo PHP alterado.
7. Validar publicamente cada site com query UTM.
8. Registrar audit/inventário.
9. Reportar bloqueios separadamente; não declarar rollout completo se algum domínio ficou sem aplicar.

## Pitfalls

- Instalar plugin updater via WP Admin não basta; ele precisa ser ativado para executar `register_activation_hook`.
- Após ativar updater por WP Admin, não confiar só no status do redirect final: se o GET de ativação retornar `302` para `plugins.php?activate=true`, valide o efeito real na rota pública antes de declarar falha. Em Cliquet, o follow do redirect chegou a retornar 500, mas a ativação havia executado e o chat público já estava atualizado.
- Se credencial WP falhar e o host SFTP for `publickey-only`, parar e reportar bloqueio; não forçar gambiarra. Para itens SFTP Bitnami/AWS, teste explicitamente usuário/senha e permissão de escrita. No caso Cliquet, o item `SFTP cliquet servers` aceitava login SFTP com usuário literal `wpfiles` e senha do campo `wpfiles`, mas não tinha permissão de escrita em `wp-content/plugins`, então não servia para deploy.
- Em itens 1Password com campos concealed extras, não assumir que todo campo oculto é senha de WP. No caso `cliquet wordpress zeus`, o campo correto para login WP Admin era `password`; campos como `zeus`, `role` e `login_ur` eram dados auxiliares/APP password/URL e falhavam como senha de login. Sempre testar combinações sem expor segredo e confirmar entrada em `wp-admin/plugins.php`.
- Se Rodolfo disser “só este site até eu validar”, tratar como canário single-site. Não consultar snapshot/config de outro domínio como base para sobrescrever o alvo.
- Correção de UTM deve ser validada no clique final ou `href` real no DOM, não só por presença da função `mergeSourceParams`.

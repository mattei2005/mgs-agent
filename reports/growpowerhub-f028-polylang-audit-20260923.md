# F028 — Auditoria do patch Polylang em growpowerhub.com

**Estado:** MAPEADO — DECISÃO PENDENTE  
**Data:** 2026-09-23 UTC  
**Domínio:** `growpowerhub.com`  
**Aplicação:** `growpowerhub` / MatteiInc03JBF  
**Modo:** somente leitura; nenhum arquivo, plugin, banco, cache ou configuração foi alterado.

## Resposta executiva

A divergência é real, pequena e funcional. O Polylang 3.6.7 possui exatamente um arquivo diferente do pacote oficial:

`wp-content/plugins/polylang/frontend/canonical.php`

Foram comentadas somente duas linhas oficiais:

- `wp_safe_redirect( $redirect_url, 301, POLYLANG );`
- `exit;`

Isso desliga os redirecionamentos canônicos 301 feitos pelo Polylang, mas mantém o cálculo e a emissão das URLs canônicas no HTML.

Não há código adicional, arquivo extra, arquivo faltante ou evidência de malware. É um patch manual deliberado ou workaround funcional, com autoria não atribuída.

## Integridade

- Polylang ativo: `3.6.7`;
- pacote oficial comparado: `https://downloads.wordpress.org/plugin/polylang.3.6.7.zip`;
- SHA-256 do ZIP oficial: `cb31936543fa540a7140651923d998d1544026320ead564e02b00f108c350a23`;
- arquivo oficial `canonical.php`: `df26e260cf810fc0bb8e5105fee247d7140f19ca026445b45d32939f2e5eba16`;
- arquivo ao vivo: `78ac41fa55141528e3cc7292be08e1885c65f24757ee94155e29d6507de58906`;
- 468 arquivos ao vivo e 468 no pacote oficial;
- somente `frontend/canonical.php` diverge;
- zero arquivo extra;
- zero arquivo faltante;
- `wp plugin verify-checksums polylang`: falha exclusivamente nesse arquivo.

## Evidência temporal

- mtime do arquivo modificado: `2025-03-13T01:24:13Z`;
- mtime padrão dos demais arquivos do pacote: aproximadamente `2025-03-13T01:23:12Z`;
- owner: `runcloud:runcloud`;
- modo: `0644`.

O intervalo de aproximadamente um minuto após a instalação/extração do pacote reforça que foi uma alteração pontual e deliberada. O histórico de shell preservado não contém comando de edição atribuível; foram encontrados somente comandos `find` relacionados a Polylang. Não é possível identificar o autor.

## Configuração multilíngue

- idioma padrão: alemão (`de`);
- alemão: URL raiz, 253 conteúdos;
- inglês (`en`): `/en/`, 84 conteúdos;
- espanhol (`es`): `/es/`, 34 conteúdos;
- francês (`fr`): `/fr/`, 17 conteúdos;
- `hide_default=1`;
- `force_lang=0`;
- `redirect_lang=0`.

Tema ativo: `jbf-wp-theme-main` 2.4.2.  
WordPress: 7.1.2.

## Efeito observado ao vivo

Home e páginas de amostra responderam HTTP 200 tanto no público quanto na origem.

Com o patch atual:

- `https://growpowerhub.com/?lang=en` responde 200, sem redirecionar, e declara canonical `https://growpowerhub.com/en/`;
- `?lang=fr` responde 200 e declara canonical `/fr/`;
- `?lang=es` responde 200 e declara canonical `/es/`;
- uma URL de post sem barra final responde 200 e declara canonical com barra final, sem fazer 301.

Portanto, a alteração reduz redirecionamentos, mas permite que múltiplas URLs respondam 200 para o mesmo conteúdo. O canonical HTML reduz o risco de indexação duplicada, mas não elimina crawl duplicado, cache fragmentado ou inconsistências de atribuição.

## Erros e saúde

- home pública: HTTP 200;
- home na origem: HTTP 200;
- nenhuma ocorrência de Polylang/canonical.php nos tails dos logs de erro;
- nenhuma evidência textual de redirect loop;
- nenhuma evidência de que o patch seja backdoor ou injeção.

A ausência de erro atual não prova que o workaround nunca tenha sido necessário; somente mostra que não há evidência operacional preservada justificando-o hoje.

## Atualização pendente

- versão instalada: 3.6.7;
- versão disponível: 3.8.9;
- auto-update: desligado.

Uma atualização normal do Polylang substituirá o arquivo modificado e reativará os 301. Atualizar sem decisão pode alterar rotas de idioma, campanhas, UTMs, cache e comportamento percebido pelo usuário.

## Riscos

### Manter como está

- checksum do plugin continua inválido;
- updates futuros podem apagar o workaround sem aviso;
- URLs alternativas continuam respondendo 200;
- manutenção e auditoria ficam ambíguas.

### Restaurar diretamente o arquivo oficial

- reativa os 301 canônicos;
- pode alterar URLs de entrada, UTMs e cache;
- pode reintroduzir eventual loop ou incompatibilidade que motivou o patch em 2025;
- não existe evidência suficiente para afirmar que a restauração é segura sem canário.

### Atualizar diretamente para 3.8.9

- mistura duas mudanças: remoção do patch e upgrade de versão;
- amplia o escopo e dificulta rollback/atribuição de regressão;
- não recomendado nesta etapa.

## Recomendação de Zeus

Não atualizar nem restaurar em lote agora.

Plano recomendado:

1. Backup independente do plugin 3.6.7 e do arquivo atual.
2. Canário pequeno restaurando somente as duas linhas oficiais.
3. Testar público e origem para:
   - `/`, `/en/`, `/es/`, `/fr/`;
   - `?lang=...`;
   - URLs de posts dos quatro idiomas;
   - UTMs/fbclid/gclid;
   - cadeia e destino dos 301;
   - cache e ausência de loops.
4. Se passar, manter o arquivo oficial e planejar o upgrade 3.8.9 separadamente.
5. Se o comportamento sem 301 for necessário, não continuar editando o plugin. Migrar a exceção para um mu-plugin suportado, usando o filtro `pll_check_canonical_url`, restaurar o pacote oficial e validar o checksum.

Essa abordagem preserva o comportamento quando necessário e impede que atualizações silenciosamente apaguem a exceção.

## Decisão necessária

A mudança afeta roteamento público/SEO e exige confirmação antes de canário em produção.

Recomendação: autorizar um canário reversível que restaure apenas as duas linhas oficiais, sem atualizar o plugin.

## Evidências

Workspace:

`/root/.hermes/profiles/zeus/workspace/growpowerhub-f028-audit-20260923/`

Artefatos principais:

- `audit-live.json`;
- `behavior-live.json`;
- `update-attribution-live.json`.

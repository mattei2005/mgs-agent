# Apoio técnico ContentOps por renderer existente

## Autoridade e ownership

- Resolver `data/atena/editorial-manager-authority.json` e autenticar o pedido humano na origem antes do write. Uma dependência técnica já autorizada de Raquel não precisa de outra aprovação editorial genérica do CEO.
- Manter Atena como coordenadora, dona do QA final e da planilha. Usar um executor por alvo, sem replay de publicação ou de caches concluídos.
- Não interpretar a capacidade limitada da conta Editor como falta de acesso técnico de toda a instalação. Investigar as referências técnicas canonicamente permitidas ao executor escolhido e validar suas capacidades reais; não elevar usuários, trocar credenciais, usar identidade alheia ou contornar `current_user_can`.
- Antes de concluir que não há caminho de manutenção em Bitnami, confrontar a credencial editorial com o item canônico `Wordpress - <domínio exato>` no 1Password: confirmar por GET autenticado o papel e as capacidades e ler a URL de login cadastrada. Um 404 em `/wp-admin/` ou `/wp-login.php` não elimina uma entrada administrativa explicitamente cadastrada. Comprovar a rota no runtime/perfil do próprio executor, sem transformar Zeus em intermediário obrigatório; acesso administrativo confirmado ainda não certifica transporte de reparo nem autoriza deploy/remoção de ferramenta temporária.

## Certificar origem e mecanismo

- Confrontar domínio, host, webroot real, owner, `home`, post ID/permalink e conteúdo nativo. Um registro com `home` correto isoladamente não prova que o HTML público vem daquele servidor.
- Quando o hash do HTML público coincidir exatamente com o cache WPFC daquele alvo na origem certificada, essa igualdade é evidência forte de binding e camada. `DYNAMIC`, `Caddy` e `Last-Modified` isolados não identificam nem excluem cache na origem.
- Separar renderer instalado, ativo e efetivamente ligado ao callback. Arquivo SFTP presente não prova ativação: consultar a lista autenticada de plugins. Um author-box inativo não pode ser tratado como cache; ativação plugin-wide pode afetar todo o acervo e não é inferida de um reparo localizado.
- Para Yoast home-page, preservar o escopo do objeto derivado existente. A ausência de execução nativa não autoriza general indexing, mudanças de options para disparar watcher, SQL cego ou deployment de endpoint novo.
- Antes de propor transporte temporário porque uma conta SFTP rejeitou shell, aplicar a sequência de diagnóstico de acesso do SKILL.md: procurar referências de servidor com usuário/senha e chaves vinculadas à instalação exata, não apenas títulos SSH ou arquivos `.pem`. A restrição observada é da conta testada, não prova de ausência de outro SSH. O executor de origem faz descoberta, testes somente leitura e preparação local sem aprovação rotineira de Zeus; reparo remoto exige binding, backup/recuperação/canário e autoridade vigente, e operações protegidas mantêm sua confirmação específica.
- Em Bitnami, manter a proibição de WPCode executável sem chave `.pem` certificada para recuperação. Administrador REST e SFTP read-only não substituem esse transporte.

## Preflight compartilhado para o executor ContentOps

O executor Atena pode usar `python3 /root/mgs-agent/scripts/mgs-contentops-preflight.py --domain DOMINIO_EXATO` para gate de domínio, resolução canônica 1Password e GETs de identidade/plugins sem segredos ou writes. O procedimento compartilhado é `context/contentops-technical-execution.md`; ele não depende de instalar/copiar a skill Zeus no perfil Atena. Testar pelo handler terminal nativo carregado com o perfil de destino antes de declarar paridade: o resultado de Zeus não prova capacidade do outro agente, e capacidade administrativa não equivale a liberação irrestrita nem entrega do reparo.

## Inspeção nativa e revisão do pacote candidato

1. Antes de instalar ferramenta para descobrir o ambiente, consultar o registry nativo de abilities e seus metadados. Para ambiente remoto, usar `core/get-environment-info` somente quando anunciado e confirmado como leitura/não destrutivo; a versão PHP do terminal local não comprova a versão servida pelo WordPress remoto. Não presumir essas propriedades para qualquer outra ability.
2. Vincular lint, testes, revisão e hashes ao pacote final exato. Se um candidato for retirado, tratar seus recibos como históricos; não somar suites antigas ao total final nem usar a revisão de outra versão como liberação.
3. Se a revisão detectar lacunas de concorrência, snapshot ou recuperação, manter a escrita desabilitada e delimitar o que o artefato remanescente realmente faz. Uma ferramenta de inspeção pode obter evidência, mas testes locais com doubles não certificam backup/restauração nem execução segura em produção.
4. Ao propor uma fase somente de inspeção, indicar o dado que falta, a alteração administrativa causada pela instalação, os componentes próprios exatos e o aceite de exportação/limpeza. Explicar que essa decisão não conclui o reparo nem autoriza automaticamente uma fase posterior de escrita; qualquer mudança de escopo permanece sujeita à autoridade vigente.

## WPCode existente: preservar efeitos laterais

1. Inspecionar a versão instalada, `WPCode_Snippet::save`, activation checks, localizações e todos os hooks acionados pelo save. Não presumir ausência de purge por não chamar uma API de cache explicitamente.
2. Congelar posts completos, corpos, taxonomias, indexables/scores, metadados autorais, perfis e opções protegidas. Incluir opções derivadas que callbacks possam tocar, como `__uagb_asset_version`, além dos dados do snippet/cache WPCode.
3. Certificar um diretório privado de backup gravável pelo owner, fora do webroot; não presumir que `/home/<owner>/backups` é gravável e não mudar suas permissões. Um subdiretório novo `0700` em `mgs-backups` gravável é preferível a alterar uma pasta existente.
4. Para a operação localizada, suspender **somente no request de manutenção** os callbacks comprovados que ampliariam invalidação: `WpFastestCache::on_all_status_transitions` pode purgar todo o cache; `UAGB_Helper::delete_page_assets` avança a versão global de assets mesmo no save de um CPT `wpcode`; `UAGB_Front_Assets::trigger_regeneration_event` pode agendar regeneração posterior. Preservar a configuração persistente dos plugins e suas capacidades. Se os hooks não puderem ser confinados com segurança, não executar o save.
5. Salvar pelo objeto/API nativo, com identidade técnica e capacidades reais. Usar allowlist exata ID+permalink e sem alteração de locale global. Executar canário e expandir o mesmo objeto somente após validação pública real.
6. Persistir ID e recibo antes da validação posterior. Se o wrapper falhar, reler o mesmo ID/backup antes de retry; não criar um segundo snippet.
7. Usar processo independente para readback nativo e comparar os campos protegidos antes de requests públicos. Após navegação, diferenciar contadores de views e `_uag_page_assets` regenerados de metadados autorais; reportar diferenças derivadas e seus efeitos, não afirmar igualdade integral falsa nem restaurar dados corretos para esconder a diferença.

## Transporte PHP e validação pública

- JSON não é um literal PHP seguro se simplesmente inserido em string PHP com aspas duplas: `$` e índices no payload podem interpolar ou causar parse error antes do bootstrap. Codificar o JSON num literal PHP de aspas simples, escapando barras e apóstrofos, ou usar outro transporte canônico seguro. Validar a sintaxe do PHP **montado completo** antes de enviá-lo; validar somente a string do snippet não testa o envelope.
- Não incluir snapshots completos no argv remoto quando um digest nativo do mesmo snapshot resolve o gate. Guardar o snapshot privado e comparar o digest com serialização canônica explicitamente igual dos dois lados.
- Arquivar só os arquivos-cache exatos comprovados: path/realpath, owner, ausência de symlink inclusive nos pais, hash e backup verificável. Não remover diretórios, incluir URLs adicionais ou purgar host/prefixo/global. Cache já ausente é no-op certificado, não erro para repetir o write.
- Validar a URL normal, nunca promover apenas a variante diagnóstica. Se a origem foi corrigida mas o edge permanece HIT antigo, purgar somente as URLs literais aprovadas. Resolver o token por zona exata; token ativo com zero zonas visíveis exige consultar o outro token aprovado, não rotacionar credenciais.
- Yoast pode normalizar `es_US` para o fallback OG suportado `es_ES`. Não forçar um locale Open Graph não suportado para satisfazer um teste; registrar separadamente HTML/Article/WebPage em `es-US` e o fallback nativo OG em espanhol.
- Conferir a página de autor no template real: um archive customizado pode não percorrer o main loop. Um callback limitado em hook existente adequado, como `get_footer`, pode apresentar a bio sem reescrever o tema; validar localização e visibilidade reais.
- Aplicar CDP metrics depois de selecionar/navegar a aba correta e persistir as observações antes de asserts. `innerWidth` mede o layout; `screen.width` desktop pode ser o hardware padrão e não o viewport. Fixar `screenWidth` explicitamente quando necessário. Overflow preexistente deve ser reconciliado com o baseline, não corrigido como nova CSS dentro de um reparo de autoria.

## Entrega

Entregar recibo por objeto, URLs normais, hashes, provas nativas/públicas, comparações protegidas, efeitos laterais e bloqueios específicos. Distinguir gates técnicos reparados de aceite final do artigo; Atena consolida o QA e a planilha. Não prometer recuperação integral quando ainda falta transporte certificado ou operação estrutural expressamente excluída.

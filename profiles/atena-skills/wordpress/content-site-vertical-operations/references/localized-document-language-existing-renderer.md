# Idioma de documento por renderer nativo existente

## Escopo e autoridade

Use somente quando a fonte canônica autorizar corrigir a apresentação localizada de artigos já aprovados e existir renderer instalado compatível. Capacidade Administrator, SSH ou WPCode disponível não concede autoridade para código arbitrário, segurança, locale global ou outros objetos. Resolva domínio/site_key/mercado/idioma, identidade dedicada e escopo humano antes do write; uma dependência de hardening continua separada da localização editorial.

## Contrato por documento

- Vincule IDs, URLs/permalinks e caminhos literais, tipo/status e tag linguística. Faça o callback falhar fechado fora desse conjunto, consulta principal, host e métodos admitidos. Declare explicitamente o tratamento de query, tracking, feeds, embed, preview, arquivos, REST/admin/CLI e paginação; não amplie variantes por inferência.
- Use os hooks nativos de atributos HTML, locale OG, grafo schema e data exibida; não faça substituição ampla no HTML nem altere locale/idioma padrão. Localize apenas os nós do documento por @id/tipo, preservando WebSite/logo institucionais e datas ISO.
- Derive a data principal do post real e traduza somente o componente linguístico solicitado. Não regrave timestamps nem localize datas de relateds de outro ID como efeito lateral.

## Inspeção e preparação

1. Leia as classes/métodos e a árvore de efeitos realmente instalados, inclusive hooks genéricos, termos privados, erros, caches internos e integrações SEO. Registre hashes, callbacks, flags e transporte real; não invente REST para CPT privado. Antes de criar qualquer canário WPCode, confirme na identidade dedicada `wpcode_edit_snippets` e `wpcode_activate_snippets`, incluindo o segundo check com a instância real do snippet/tipo. Renderer instalado e SSH disponível não substituem a capacidade: `WPCode_Snippet::save()` pode recusar ativação e ainda persistir outros campos. Não invoque o save como teste de permissão nem use SQL, troca de identidade ou filtros de capacidades para contorná-lo. Confira separadamente `edit_css` para um renderer CSS nativo já existente; essa capacidade não libera PHP/WPCode nem dispensa escopo, efeitos indiretos e canário de layout.
2. Teste o código local com grafos capturados e contextos positivos/negativos. Faça lint no PHP do aplicativo por stdin sem salvar arquivo remoto. Testes com stubs não provam persistência WordPress ou apresentação pública.
3. Fotografe posts, todas as postmetas, termos, indexables e opções globais protegidas, além dos snippets/erros/opções de cache existentes. Se houver outro snippet ativo ou erro alheio incompatível com a inspeção, reconcilie antes de executar.
4. Inspecione também os callbacks indiretos do Spectra/UAGB antes de salvar WPCode: `UAGB_Helper::delete_page_assets` pode invalidar derivados e avançar a versão global dos assets, mesmo sem editar CSS autoral. Capture o marcador real de versão e os derivados `_uag_page_assets`, `_uag_css_file_name` e `_uag_js_file_name` antes do primeiro canário. Quando o escopo permitir, contenha somente os callbacks comprovados de invalidação ampla durante a requisição e restaure-os em `finally`; não desative controles de segurança nem aplique mudança permanente de hooks. Registre deltas de cache separadamente dos inputs autorais. Se o marcador inicial não foi capturado, não prometa rollback exato ou igualdade integral de metadata; não restaure derivados por inferência. Teste sintético do guard não comprova contenção em produção: a próxima execução autorizada ainda exige comparação nativa e QA público reais.

## Particularidades do WPCode inspecionado

- Trate `WPCode_Snippet::save()` como mutador: pode criar termos privados, reconstruir `wpcode_snippets` e apagar/reconstruir o índice derivado `wpcode_snippets_errors`, mesmo vazio. Preserve baseline/autoload e reporte deltas reais; não prometa banco byte-idêntico.
- Na implementação verificada, construa propriedades por array no construtor; métodos `set_location()`/`set_code_type()` são loaders e `set_attribute()` não é setter de configuração. Reinspecione versões diferentes.
- Para criar/atualizar corpo PHP inativo via API, envie o corpo sem `<?php` com `wp_slash`. Faça readback do hash do corpo nativo. Ative em outro processo com instância nova pelo ID, sem reatribuir o corpo slashed: a ativação em CLI não usa o mesmo unslash do formulário.
- Use um save por processo. O save inspecionado remove `content_save_pre` do processo e sua restauração pode não ocorrer em versões recentes do core; não salve artigos ou outros objetos na mesma requisição.
- Confirme que a localização de execução roda depois da query e antes dos hooks renderizadores necessários. Um callback que exige `is_singular()` não pode ser avaliado prematuramente e retornar antes de registrar seus filtros.

## Canário, expansão e fechamento

1. Crie um único snippet exclusivo, inicialmente inativo, com intenção local e título rastreável. Capture o ID real; resposta ambígua exige consulta por ID/título e reconciliação, nunca criação repetida.
2. Ative apenas o canário. Exija hash/status/cache compilado/ausência de erro por novo processo, URL pública normal e desktop/mobile. Compare profundamente o grafo: somente os campos linguísticos contratados devem mudar; preserve corpo, mídia, canonical, robots, datas ISO e controles fora do alvo.
3. Expanda o mesmo ID somente após o canário passar: desative, atualize o corpo completo inativo, releia e reative com instância nova. Use intenções/recibos separados por etapa; não crie um segundo snippet.
4. Valide cada URL normal e controles negativos, além de todos os campos nativos protegidos. Se já mostrar a alteração, não limpe cache novamente; se estiver antiga, diagnostique e renove somente cópias seletivas cobertas pela autoridade vigente.
5. Faça rollback pela desativação nativa do mesmo snippet, sem apagar arquivo/post/termo nem sobrescrever opções globais antigas. Comprove o efeito público; draft ou código correto isolado não encerra rollback.

## Tipos e proveniência de coletores

- Reflection pode retornar `file=false` para função interna/closure sem arquivo; valide que é string antes de operações de caminho. Compare somente callbacks com fonte conhecida, sem relaxar guard porque um tipo local falhou.
- Resultados diretos de SELECT podem representar IDs como strings; valide formato e normalize apenas o tipo numérico para comparações internas, preservando identificadores literais de origem e evidências. Não diagnostique alteração de outro objeto por uma comparação string/int.
- Guarde erro e correção do coletor sem sobrescrever provas aceitas nem reverter produção correta para satisfazer um assert defeituoso.

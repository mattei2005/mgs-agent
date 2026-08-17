# Equivalência JBF Preloader ↔ LoftLoader

Use quando Rodolfo pedir para auditar, comparar ou padronizar o preloader integrado do tema SB/JBF em sites sem o tema, usando LoftLoader.

## Fontes reais e precedência

1. WordPress options e código implantado vencem para configuração persistida.
2. Navegador em URL bare vence para experiência real do usuário.
3. Comparar URL bare e cache-busted antes de concluir que uma alteração não foi aplicada.
4. Código do builder externo JBF vence para o fechamento real do overlay; a tela admin do tema não expõe o timing.

## JBF integrado — contrato observado no Helixenit

Validação de referência: `helixenit.net`, tema `jbf-wp-theme-main` 2.4.2, 2026-08-17.

Option: `jbf_preloader_option_name`.

Campos:

- `enable_0`: habilita o preloader em todas as páginas.
- `image_1_1`: imagem/logo central.
- `image_2_2`: segunda imagem opcional no rodapé.
- `bgcolor_3_3`: cor de fundo.

Frontend do tema:

- elemento `#jbf-preloader` em `wp_body_open`;
- `position: fixed; inset: 0; z-index: 100000; display: flex`;
- imagem 1 com altura fixa de 40 px;
- imagem 2 com altura 70 px, posicionada no rodapé;
- o módulo local bloqueia scroll com `body.style.overflow = "hidden"`.

O timing não vem da tela admin. O builder externo JBF possui duas rotas de fechamento:

- `onWindowLoad`: remove `#jbf-preloader` após 1000 ms;
- `dismissLoader`: remove `.Preloader` e `#jbf-preloader` após 300 ms quando o slot/ad permite.

No canário Helixenit cache-busted, o overlay ficou visível aproximadamente de 0,61 s até 2,01 s; `window.load` ocorreu em 1,67 s. A chamada real de `Element.remove()` veio do builder externo `digital-trust_helixenit.builder.js`, não do JS local do módulo.

## LoftLoader — contrato observado no Gamezonead

Validação de referência: `gamezonead.com`, plugin `loftloader` 2.5.3, 2026-08-17.

Options persistidas após o ajuste canário:

- `loftloader_main_switch`: `on`;
- `loftloader_show_range`: `sitewide`;
- `loftloader_bg_color`: `#ffffff`;
- `loftloader_bg_opacity`: `100`;
- `loftloader_bg_animation`: `no-animation`;
- `loftloader_loader_type`: `frame`;
- `loftloader_loader_color`: `#164201` (a moldura é ocultada pelo CSS canônico);
- `loftloader_custom_img`: logo completo 792×289 do próprio site;
- `loftloader_img_width`: `76` (não governa o `frame`; o CSS canônico fixa o logo em 40 px de altura);
- `loftloader_max_load_time`: `2.0`.

CSS canônico do canário oculta as quatro bordas animadas do `frame`, mantém o logo completo central com 40 px de altura e não altera as demais opções do plugin.

Comportamento:

- fecha ao receber `window.load` adicionando `body.loaded`;
- `max_load_time` é fallback máximo, também adicionando `body.loaded`;
- `no-animation` remove visualmente o fundo de imediato e o logo termina seu fade em cerca de 0,3 s;
- o wrapper técnico permanece transparente no DOM por aproximadamente 1 s adicional e pode continuar com dimensão de viewport, mas isso não representa tempo visual para o usuário.

Medição corrigida após o preset novo, em cinco cargas frias e cinco quentes:

- duração visual fria mediana: ~1,52 s (0,94–1,86 s);
- duração visual quente mediana: ~1,03 s (0,99–1,26 s);
- desaparecimento visual absoluto desde o início da navegação: mediana ~2,19 s fria e ~1,39 s quente;
- 10/10 respostas HTTP 200.

Não reportar o instante em que `#loftloader-wrapper` fica transparente ou sai do DOM como duração do preloader. Medir o fundo (`.loader-section`) e o logo (`#loader`) visíveis. O valor anterior de ~2,65 s representava o wrapper/fade técnico sob a configuração antiga e não o tempo percebido no computador do usuário.

## Preset LoftLoader para reproduzir a experiência JBF

Para equivalência funcional/visual aproximada em site sem tema JBF:

- Enabled: ON;
- Display: Sitewide;
- Background: `#ffffff`;
- Opacity: `100`;
- Maximum Load Time: `2.0` segundos;
- Ending Animation: `No Animation` para imitar a remoção instantânea do JBF;
- imagem: logo do próprio site, não favicon genérico;
- alvo visual: logo central com ~40 px de altura;
- close button: desativado.

LoftLoader Lite não possui um modo nativo perfeitamente estático igual ao JBF:

- `frame` desenha uma moldura animada;
- `imgloading` deixa a imagem a 30% e aplica animação de preenchimento.

Para igualdade visual real, manter `frame` e adicionar CSS restrito ao LoftLoader para ocultar as quatro bordas animadas e renderizar apenas o logo central com 40 px de altura. Fazer isso somente após canário e screenshot/runtime readback.

## Auditoria obrigatória

1. Ler options reais via WP-CLI/REST.
2. Ler código do tema/plugin implantado.
3. Testar home bare em contexto novo de navegador.
4. Instrumentar desde o primeiro frame e registrar:
   - primeiro momento visível;
   - cobertura da viewport;
   - `DOMContentLoaded`;
   - `window.load`;
   - início/fim do fade ou remoção;
   - estado final e overflow do body.
5. Repetir com cachebuster quando a opção estiver ativa, mas a home bare não mostrar overlay.
6. Se cache-busted tiver preloader e bare não, confirmar marcador/cache da home antes de propor purge.
7. Não declarar equivalência apenas pela tela do Customizer; exigir option readback e navegador.

## Pitfall WP Fastest Cache

Após habilitar o JBF preloader, a home bare pode continuar servindo HTML anterior sem `#jbf-preloader`, enquanto cache-busted já mostra o novo overlay. Exemplo Helixenit: home bare carregou arquivo do WP Fastest Cache criado antes da habilitação; cache-busted continha node, CSS e JS do JBF. Tratar como purge pendente, não falha de configuração.

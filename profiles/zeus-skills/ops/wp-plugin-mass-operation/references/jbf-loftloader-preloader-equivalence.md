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

Options persistidas:

- `loftloader_main_switch`: `on`;
- `loftloader_show_range`: `sitewide`;
- `loftloader_bg_color`: `#ffffff`;
- `loftloader_bg_opacity`: `95`;
- `loftloader_bg_animation`: `fade`;
- `loftloader_loader_type`: `frame`;
- `loftloader_loader_color`: `#164201`;
- `loftloader_custom_img`: favicon do site;
- `loftloader_img_width`: `76`;
- `loftloader_max_load_time`: `2.0`.

Comportamento:

- fecha ao receber `window.load` adicionando `body.loaded`;
- `max_load_time` é fallback máximo, também adicionando `body.loaded`;
- `fade` inicia após 0,3 s e dura 0,7 s;
- no canário Gamezonead, o overlay ficou visível de ~0,66 s a ~2,65 s; `window.load` ocorreu em ~1,60 s.

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

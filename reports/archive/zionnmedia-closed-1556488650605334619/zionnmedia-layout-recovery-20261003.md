# Zionn Media — recuperação do layout existente

## Autoridade e resultado

- Rodolfo: mensagem `1556096703344676935`, thread `1556015743831646349`.
- Alvo exclusivo de escrita: `zionnmedia.com`, `/home/runcloud/webapps/zionnmedia`, servidor `162.55.28.178`.
- `marketingdigitalad.com` usado somente como referência pública/live read-only.
- Resultado: renderização original recuperada em produção sem renovação, cobrança, upgrade/downgrade ou alteração de arquivo vendor. Aceite visual do proprietário ainda pendente; não equivale a certificação integral de segurança de componentes antigos.

## Causa e correção

O site tinha Elementor, Pro e complementos inativos. O PowerPack antigo referenciava classes `Elementor\Core\Schemes\Typography`/`Color` retiradas pelo Elementor atual. A recuperação anterior havia tratado a recusa de download oficial como bloqueio de layout; isso foi reclassificado: é bloqueio de atualização, não da renderização existente.

Adicionado MU `mgs-zionn-elementor-compat.php`: constantes/API de esquema mínimas, PowerPack restrito ao widget Advanced Menu utilizado, extensões não usadas desabilitadas, bypass reversível de HTML antigo do Elementor e bloqueio dos handlers PP/ppe anônimos que o menu não utiliza. O fonte instalado usa `elementor_element_cache_ttl=disable`, não o antigo switch experimental. O widget estava registrado, mas o HTML em cache ainda o omitia até o bypass correto.

Reativados somente componentes existentes: Elementor 4.3.3, Pro 3.21.0, PowerPack 2.9.9, ElementsKit Lite 3.1.3 e Sticky Header Effects 2.1.3. CF7 preservado ativo. Não foram copiados plugins comerciais da referência nem modificadas licenças.

## Evidência verificada

- Cinco páginas, em 390×900 e 1440×900: dez casos; HTTP 200, nenhum erro JavaScript, imagem quebrada, overflow ou request interno falho.
- Quinze probes: URL canônica, URL fresca e origem com resolução direta, cinco páginas; estrutura Elementor presente em todos.
- Menu abre/fecha; cinco links corretos; clique real no logo permanece no domínio.
- Formulário home e Contact presentes; validação nativa de campos obrigatórios exercitada, sem envio real de email.
- Sete actions efetivamente registradas (`pp_get_section_data`, `ppe_lf_process_login`, `pp_lf_process_social_login`, `pp_lf_process_lost_pass`, `pp_lf_process_reset_pass`, `pp_get_post`, `ppe_register_user`) devolvem 403 a POST anônimo.
- Árvores dos cinco plugins: zero arquivos alterados contra a cópia imediatamente prévia; hashes de conteúdo e builder, slugs/status/template, contagem de registros, sidebar e footer preservados.
- Categorias sem contagem positiva obsoleta; widgets seguem inativos; footer oficial permanece com o hash validado; cache local contém zero arquivos.
- REST e login retornam 200. Servidores PHP e túnel temporários encerrados; clone privado e snapshots retidos como rollback.
- Referência tem as mesmas quatro seções, alturas e copyright no hero. Uma captura fullPage após interação incorporou o painel fechado fora da viewport; diagnóstico corrigido por geometria fresh/open/closed/logo e screenshots de viewport real: scrollX=0, scrollWidth=viewport e painel fechado com x=viewport. Nenhuma alteração CSS especulativa aplicada.

## Backup e rollback

- Snapshot: `/var/backups/mgs-zionnmedia-recovery-20261003/cutover-before.sql`.
- SHA-256: `114fa502e9df56105988e6131d79179466a305a942b1fa7b4da66fc5ce7bf45c`.
- MU SHA-256: `74f75bcfb361726c13435f5fe207f823e28f374c9a948dd250bfd51612fe6629`.
- Executor: workspace `recovery-rollback.py`, restaura active_plugins do manifesto e move MU para quarentena privada; não apaga arquivos. Não acionado: gates de produção passaram.
- Clone/database: `/var/backups/mgs-zionnmedia-recovery-20261003/canary`, `mgs_zionnmedia_recovery_20261003`; nenhum endpoint público.

## Falhas recuperadas e limites

Foram corrigidos em foreground: nome errado de subcomando do helper de checkpoint; intérpretes sem Playwright (reuso do venv já existente, sem instalação); API inexistente `remove_all_listeners` no harness; formato inicial inadequado do filtro de widgets; cache HTML obsoleto; erro de aspas no SELECT de validação. Nenhuma dessas falhas alterou os arquivos vendor ou os dados das páginas. As execuções reais subsequentes passaram.

Continuam separados: aceite visual de Rodolfo; autenticidade/entitlement e manutenção de Pro/PowerPack legados; PHP 8.1; entrega real de email não testada. Não houve cobrança, renovação, credencial nova, redesign nem atualização de plugins. A proteção narrow dos handlers não substitui atualizações oficiais.

## Artefatos

Workspace: `/root/.hermes/profiles/zeus/workspace/zionnmedia-audit-20261003`.
Readbacks principais: `recovery-live-browser.json`, `recovery-live-http.json`, `recovery-live-guard.json`, `recovery-final-tree-validation.json`, `recovery-production-before.json`, `recovery-production-after.json`, `recovery-prior-fix-regression.json`, `recovery-live-menu-geometry.json`, `recovery-test-runtime-cleanup.json`.

Aprendizado registrado na skill `wordpress-plugin-integrity-audits`, referência `visual-compatibility-stack-recovery.md`; inventário inclui `zionnmedia-layout-recovery-20261003` e supersessão explícita do bloqueio anterior.

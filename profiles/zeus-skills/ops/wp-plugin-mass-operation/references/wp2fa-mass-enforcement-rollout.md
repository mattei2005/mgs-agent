# Rollout massivo WP 2FA com enforcement imediato

Use quando Rodolfo pedir instalação/configuração de `WP 2FA – Two-factor authentication for WordPress` em todo o portfólio.

## Segurança e autorização

- Operação em mais de 40 sites pertence ao Critical Subset: sempre obter a confirmação crítica adicional após o preflight.
- `all-users` + `no-grace-period` exige configuração no próximo login e pode bloquear acesso administrativo até o usuário cadastrar TOTP.
- Nunca gerar, ler ou expor segredo TOTP/QR. Validar somente presença dos metadados necessários ou comportamento da tela.
- Instalação/política sitewide não configura o autenticador individual; cada usuário precisa escanear o QR e guardar backup codes.

## Preset canônico MGS

Versão validada em 2026-08-17: `4.1.0`.

- `enable_totp = enable_totp`
- `enable_email = false`
- `enable_passkeys = false`
- `backup_codes_enabled = yes`
- `enable-email-backup = false`
- `enforcement-policy = all-users`
- `enforced_users = []`
- `enforced_roles = []`
- `excluded_users = []`
- `excluded_roles = []`
- `grace-policy = no-grace-period`
- `grace-policy-after-expire-action = configure-right-away`
- wizard administrativo finalizado; usuário configura 2FA depois/no próximo login.

Requisitos oficiais da versão validada: WordPress 5.5+, PHP 7.4+; API WordPress.org informou tested até 7.0.4. Fixar o pacote e validar SHA-256 antes do rollout. Pacote 4.1.0 usado no caso de referência: `a3a0fd5a0fdb28c84d7c5c837ddb0ea5194efddd92cca7c84918f487eb45c779`.

## RunCloud — WP-CLI

1. Fazer backup por site:
   - options `wp_2fa_%`;
   - usermeta `wp_2fa_%`;
   - `active_plugins`;
   - diretório `wp-content/plugins/wp-2fa` se já existir;
   - hashes do backup.
2. Instalar ZIP validado com `wp plugin install ZIP --activate --force`.
3. Não gravar `wp_2fa_policy` cru sem hash. Carregar o plugin e usar `WP2FA\WP2FA::update_plugin_settings()` sobre defaults + settings existentes + preset desejado.
4. Remover `wp_2fa_default_settings_applied`, `wp_2fa_wizard_not_finished` e `wp_2fa_redirect_on_activate` via `Settings_Utils`.
5. Atualizar o estado dos usuários com `WP2FA\Admin\Helpers\User_Helper::update_user_state()` para cada ID.
6. Readback obrigatório:
   - plugin ativo e versão exata;
   - cada opção do preset;
   - settings hash presente;
   - wizard finalizado;
   - `wp_2fa_enforcement_state=enforced` igual ao total de usuários;
   - home HTTP 200.
7. Em falha, restaurar options/usermeta/active plugins e arquivos do backup individual antes de continuar.

Metadado `wp_2fa_enabled_methods` sozinho não prova cadastro completo. Para TOTP, confirmar apenas se `wp_2fa_totp_key` está presente e classificar como `ready`/`incomplete`, sem imprimir valor.

## Sites externos — backend autenticado

1. Application Passwords podem ler usuários, mas podem retornar `401 rest_cannot_install_plugin` e até `404` no controller de plugins mesmo quando WP 2FA está ativo. Não usar esse endpoint como único readback.
2. Fallback validado:
   - login autenticado;
   - upload do ZIP em `plugin-install.php?tab=upload`;
   - o link `Activate Plugin` pode estar em iframe/invisível: extrair o `href` e navegar diretamente, em vez de clicar;
   - validar a linha `tr[data-plugin="wp-2fa/wp-2fa.php"]` como `active` e procurar `4.1.0`, sem depender de `Version`/`Versión`.
3. Configurar sem wizard visual pelo endpoint oficial:
   - carregar `index.php?page=wp-2fa-setup` para obter `wp2faWizardNew.nonce`;
   - POST `admin-ajax.php` com `action=wp2fa_wizard_save` e todas as chaves do preset;
   - exigir HTTP 200, `success:true`, `message: Setup complete` e `isCurrentUserExcluded:false`.
4. O enforcement imediato é testado em sessão nova, não na sessão que salvou a política. No próximo login, exigir:
   - redirect para `profile.php?show=wp-2fa-setup`;
   - botão `button.wp2fa-profile__btn.wp2fa-profile__btn--primary` presente;
   - zero inputs de método email;
   - home HTTP 200.
5. O `readme.txt` do pacote 4.1.0 ainda declara `Stable tag: 4.0`; não usar esse campo para versão. A versão exata deve vir da linha autenticada do plugin antes do enforcement.
6. Depois do enforcement, `plugins.php` é redirecionado até a conta configurar TOTP. Um rollback que conta “linha do plugin ausente” após esse redirect é falso positivo. Sempre reconciliar URL atual, asset público e nova sessão antes de declarar remoção.

## Aceitação do portfólio

- contagem de sites confere com o escopo;
- todos os plugins ativos/versão correta;
- policy exata nos sites com WP-CLI;
- fresh-login enforcement em todos os externos;
- homes e asset WP 2FA HTTP 200;
- Application Passwords externas continuam funcionais;
- falhas, rollbacks e warnings preexistentes são reportados honestamente;
- checkpoint, inventário e REPORT-INFRA atualizados.

## Caso de referência

Rollout 2026-08-17: 54 sites, 447 contas locais, 49 RunCloud + 5 externos. Readback RunCloud 49/49, fresh-login externos 5/5, homes/assets 54/54. Sete vínculos TOTP preexistentes foram reconhecidos como `ready`; nenhum segredo foi exposto.

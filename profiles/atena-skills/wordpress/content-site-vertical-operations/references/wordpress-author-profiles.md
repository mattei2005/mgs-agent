# Perfis de autor WordPress em sites MGS

## Objetivo

Padronizar nome de exibição e biografia de autores sem alterar identidade de login, função, e-mail ou credenciais, com suporte a um site ou a um lote de domínios MGS.

## Contrato editorial

- Nome de exibição da Atena: `Atena`.
- Nome de exibição da Raquel: `Raquel Oliveira`.
- Biografias compartilhadas entre vários sites devem ser corporativas e genéricas. Não mencione vertical, país, idioma, produto ou campanha salvo pedido explícito de perfil nichado.
- Atena: use primeira pessoa e o idioma editorial real do portal, conforme correção de Raquel `discord:1560295338257023118#1562273124030873610`. Esta regra supersede, para Atena, o texto único em inglês/terceira pessoa abaixo; não altera o perfil de Raquel nem autoriza expandir automaticamente o lote aos demais portais.
  - PT-BR: `Sou Atena, redatora da MGS Digital Corp. Produzo conteúdo claro, envolvente e bem pesquisado para leitores de diferentes temas e mercados.`
  - ES: `Soy Atena, redactora de MGS Digital Corp. Creo contenido claro, atractivo y bien investigado para lectores de distintos temas y mercados.`
  - EN: `I'm Atena, a writer at MGS Digital Corp. I create clear, engaging, well-researched content for readers across different topics and markets.`
- Histórico supersedido de Atena (não usar como texto ativo): `Atena is a creative writer at MGS Digital Corp, focused on producing clear, engaging, and well-researched content for readers across different topics and markets.`
- Perfil de Raquel, sem alteração nesta decisão: `Raquel Oliveira is a writer and content editor at MGS Digital Corp, focused on editorial quality, clear communication, and useful content for readers across different topics and markets.`
- Quando houver texto existente, o preflight deve registrar que ele será substituído; biografia não vazia é estado editorial, não campo descartável.

## 1. Resolver o escopo

1. Para pedido genérico sobre todos os sites MGS, obtenha os alvos somente pelo gate canônico `mgs-domain-scope.py list --agent atena`.
2. Não derive alvos enumerando RunCloud, 1Password ou inventário global.
3. Confirme que cada domínio é WordPress e possui uma rota de operação validada.
4. Operação acima do limite crítico só prossegue após a confirmação correspondente; o preflight permanece somente leitura.

## 2. Inventariar antes do write

Para cada domínio, registre separadamente Atena e Raquel:

- user ID;
- username/slug;
- nome de exibição;
- descrição atual;
- role;
- rota disponível (`REST próprio`, `REST admin` ou `WP-CLI`);
- HTTP/readback.

A credencial dedicada `Atena WordPress - <domínio>` permite ler e editar o próprio perfil quando `/wp/v2/users/<id>` está exposto. Para outro usuário, não assuma que a função Editor possui `edit_users`.

Pitfall: busca pública em `/wp/v2/users?search=...` retorna apenas autores expostos pelo site e pode omitir contas sem posts publicados. Resultado vazio exige rota administrativa/WP-CLI; nunca crie uma segunda conta nem escolha um usuário parecido.

Pitfall: autenticação editorial comprovada por `/posts?context=edit` não prova que as rotas de usuários existem. Alguns sites removem todo `/wp/v2/users`; trate `rest_no_route` como necessidade de rota alternativa, não como credencial inválida.

## 3. Atualizar o menor campo possível

Via REST, envie somente:

```json
{
  "name": "Nome aprovado",
  "description": "Biografia aprovada"
}
```

Endpoint:

```text
POST /wp-json/wp/v2/users/<id>
```

Use o wrapper seguro de autenticação; senha ou Application Password não pode aparecer em argv, logs ou artefatos.

Via WP-CLI, resolva o usuário pelo login/ID confirmado e atualize somente `display_name` e `description`. Não altere `user_login`, `user_email`, roles, password ou Application Passwords.

Para WP-CLI remoto, envie um script curto pela entrada padrão e passe somente webroot/owner como argumentos:

```bash
sshpass -f "$password_file" ssh <opções> "zeus@$host" \
  "sudo -n bash -s -- '$wp_path' '$owner'" < remote-author-update.sh
```

Dentro do script remoto, execute o menor write e depois releia os campos preservados:

```bash
runuser -u "$owner" -- wp --path="$wp_path" user update "$login" \
  --display_name="$name" --description="$bio" --skip-plugins --skip-themes
```

Não coloque PHP longo ou `wp eval` com arrays diretamente no argv do SSH: o shell remoto reinterpreta parênteses e aspas, podendo falhar antes do write. Prefira `bash -s` com script em stdin, estado por domínio e readback separado.

## 4. Executar lote com estado resumível

- Faça um domínio por vez ou lotes pequenos por host.
- Grave após cada alvo: domínio, IDs, antes/depois sanitizados, rota, HTTP/rc e readback.
- Em falha, pare apenas o alvo afetado, reconcilie efeitos e continue somente quando o contrato do lote autorizar parcialidade.
- Identidade ambígua, rota administrativa desconhecida ou mismatch de username/role bloqueia o domínio; não amplie privilégios e não improvise credencial.

## 5. Readback obrigatório

Após cada write, confirme:

- ID e username idênticos ao pre-read;
- role, e-mail e slug preservados;
- `name` e `description` exatamente iguais ao aprovado;
- página pública `/author/<slug>/` sem o nome antigo e com a biografia nova quando o tema exibir o perfil.

A página pública complementa, mas não substitui, o readback autenticado: tema/cache pode ocultar ou transformar campos. Quando houver cache, use cache-buster/no-cache apenas como diagnóstico; variante nova não aprova a representação canônica antiga.

No QA da bio pública, capture o componente completo de autoria, não só o pai imediato do link: o texto pode estar em um parágrafo irmão dentro de `.jd-box .info`. Exija a frase canônica em elemento realmente renderizado (geometria e estilos visíveis), separadamente em mobile e desktop; não use apenas schema, campo de cadastro ou a concatenação dos dois viewports. Diferencie erro local de seletor, cache antigo e ausência real de renderização antes de propor qualquer mudança em produção.

Em retomadas de autoria, revalide cada artigo: páginas do mesmo autor podem misturar bio antiga e bio correta enquanto o perfil nativo já está conforme. Não regrave o usuário nem invalide os irmãos corretos; quando a URL normal antiga for HIT de APO, a variante diagnóstica mostrar o texto atual e a zona exata estiver validada, renove somente esse URL pela API seletiva autorizada e comprove MISS atualizado → HIT atualizado. Conte bio apenas no DOM visível do artigo ou perfil realmente acessível: frase em JSON-LD não prova bio renderizada. Se o HTML normal e diagnóstico continuarem errados sob DYNAMIC/via Caddy, preserve a incerteza da camada e resolva o transporte de origem, sem purge de borda por tentativa.

Ao trocar perfis de navegador, configure viewport/screen, UA e touch coerentes em cada navegação. Aguarde fontes e várias leituras estáveis de `innerWidth/clientWidth/scrollWidth` antes de classificar overflow; preserve uma medição transitória anterior e só superseda com observação real estável, sem esconder excesso por CSS ou desconsiderar overflow persistente.

## Diagnóstico de biografia em portal multilíngue

Quando houver autorização editorial para executar a rota nativa comprovada, siga também `references/minimal-native-multilingual-own-bio-write.md`: intenção anti-replay, sanitização stock, apenas chaves próprias aprovadas, preservação privada dos demais dados e readback independente. O diagnóstico abaixo não concede essa autorização nem garante a apresentação pública.

- Comprove suporte e mapeamento no código instalado antes de propor chaves localizadas; inspecione somente usermeta de descrição da identidade própria autorizada e capture Reflection/linhas/SHA-256 dos métodos pertinentes e callbacks de `get_user_metadata`/`get_the_author_description`.
- Diferencie campo de formulário e chave persistida: o idioma padrão pode usar `description` mesmo quando o formulário usa um sufixo. Mudar a bio desse idioma pode ser inseparável de mudar a bio global; preservar configuração de idioma/locale não significa preservar o valor da bio padrão.
- Inspecione o save nativo antes de usá-lo como transporte parcial: um handler que percorre todos os idiomas e trata campos omitidos como vazio pode apagar outra bio ou criar linhas vazias. Não invoque hooks artificialmente nem use esse save para prometer zero escrita em idiomas preservados.
- Registre separadamente campo nativo implementado, linha de usermeta existente e registro REST. Linha ausente não exige necessariamente plugin/registro novo, mas suporte nativo também não comprova endpoint REST localizado nem concede autorização de write.
- Em probes guardados, registre o idioma efetivamente resolvido por `pll_current_language()`. Alterar apenas REQUEST_URI e continuar no idioma padrão não valida o frontend localizado; mantenha essa limitação explícita, sem forçar runtime/locale para fabricar aprovação.
- Preserve diagnóstico como somente leitura: nenhum save de teste, novo registro de strings, plugin/hook/config/role/runtime. Se faltar rota comprovada ou se o pedido exigir separar armazenamentos que o código nativo compartilha, encaminhe somente essa dependência a Tech.

## 6. Relatório

Separe:

- atualizados e validados;
- já conformes/no-op;
- bloqueados por identidade/rota;
- falhas com efeito parcial reconciliado.

Não declare “todos” quando a contagem validada for menor que o escopo. Informe que credenciais, roles e usernames permaneceram inalterados.
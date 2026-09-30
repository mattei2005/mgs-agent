# Perfis de autor WordPress em sites MGS

## Objetivo

Padronizar nome de exibição e biografia de autores sem alterar identidade de login, função, e-mail ou credenciais, com suporte a um site ou a um lote de domínios MGS.

## Contrato editorial

- Nome de exibição da Atena: `Atena`.
- Nome de exibição da Raquel: `Raquel Oliveira`.
- Biografias compartilhadas entre vários sites devem ser corporativas e genéricas. Não mencione vertical, país, idioma, produto ou campanha salvo pedido explícito de perfil nichado.
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

A página pública complementa, mas não substitui, o readback autenticado: tema/cache pode ocultar ou transformar campos. Quando houver cache, use cache-buster/no-cache antes de concluir.

## 6. Relatório

Separe:

- atualizados e validados;
- já conformes/no-op;
- bloqueados por identidade/rota;
- falhas com efeito parcial reconciliado.

Não declare “todos” quando a contagem validada for menor que o escopo. Informe que credenciais, roles e usernames permaneceram inalterados.
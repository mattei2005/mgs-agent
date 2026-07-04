# Discord mobile grouped-list alert layout — Meta App Roles (2026-06-30)

## Contexto

Rodolfo estava revisando alertas reais do monitor Meta App Roles nos canais B001–B010. O alerta precisava mostrar usuários do app com:
- bot email vindo da planilha `Migracao 22/06`, coluna A;
- segurador/nome do perfil;
- perfil ID vindo da coluna K (`USUARIO`);
- role.

A primeira tentativa em tabela monoespaçada com 4 colunas (`BOT EMAIL | SEGURADOR | PERFIL ID | ROLE`) ficou aceitável no desktop, mas ruim no Discord mobile: emails e nomes longos truncavam com `…`, e a lista ficava visualmente pesada.

## Correção validada

Para listas de pessoas/itens com um campo agrupador longo (email, domínio, site, bot user, conta), preferir layout agrupado por chave, sem tabela de 4 colunas:

```text
Usuários do app - B002
Ordenado por BOT EMAIL

disparosconecta@gmail.com
• Adalberto Vilela Oliveira — adalbertovilelaoliveira — Admin
• Afonso Araujo — fernandadossanto678 — Admin
• Sabrina Pereira — 100035572880779 — Admin

disparosfinanceadx@gmail.com
• Fernando Narciso Acosta — 100009006839947 — Admin
• Jaqueline Dagostin — clemer.silva.564 — Admin

sem email
• Lola Lilliana — owner do app — Admin
```

Estrutura:
1. título curto;
2. linha de ordenação (`Ordenado por BOT EMAIL`);
3. email completo em linha própria;
4. bullets dos registros daquele email: `• Nome — perfil_id — role`;
5. linha em branco entre grupos.

## Por que funciona melhor

- Evita truncar o email, que era a principal chave de leitura.
- Mantém agrupamento natural por site/bot user.
- Elimina colunas fixas largas no mobile.
- Continua legível no desktop.
- Reduz ruído visual sem criar legenda artificial (`D1`, `D2`), que Rodolfo rejeitou como horrível.

## Pitfalls

- Não tentar resolver com “modo desktop”: Discord renderiza pela largura do client do usuário; a mensagem não controla isso.
- Não criar legenda de aliases para email (`D1 = ...`) salvo pedido explícito. O usuário rejeitou esse formato.
- Não usar tabela Markdown crua nem tabela monoespaçada larga quando houver 3+ campos longos.
- Se o alerta precisa ser reenviado para validação visual, primeiro enviar real em apenas um canal/app canário (ex. B001), depois replicar B001–B010 após aprovação.

## Validação usada

- Dry-run do script com B001 confirmou 3 mensagens e payloads abaixo do limite Discord.
- Envio real canário B001 retornou `errors_count=0`, `alerts_sent=1`.
- Depois da aprovação, o formato pode ser aplicado ao monitor e reenviado para todos os canais.

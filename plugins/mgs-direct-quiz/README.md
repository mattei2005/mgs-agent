# MGS Direct Quiz

Plugin WordPress simples para criar e duplicar landing pages de uma pergunta usadas em tráfego direto.

O WordPress é apenas o painel de controle. Cada landing ativa é publicada como um `index.html` físico na própria rota; o servidor entrega esse arquivo sem inicializar WordPress/PHP. Criar, editar, ativar ou desativar sincroniza a entrega estática automaticamente e valida o conteúdo por readback.

## Contrato

- LP2: `/quiz/{pais}/sh2-gNNN/`, por exemplo `sh2-g002`.
- LP1: `/quiz/{pais}/sh1-gNNN/`, por exemplo `sh1-g002`.
- O número após `sh` deve corresponder ao modelo visual selecionado.
- Modelos visíveis no painel: V1 (minimal escura) e V2 (branded verde).
- Configuração por gestor no WordPress Admin, no menu `Landing SHEIN`.
- Interface visual em cards para criar, editar, ativar/desativar e duplicar landings.
- O logo pode ser informado por URL ou escolhido diretamente na Biblioteca de Mídia do WordPress, com preview e remoção.
- Cada opção pode ter um destino HTTPS; o segundo pode reutilizar o primeiro.
- Todos os parâmetros recebidos são preservados nos CTAs, incluindo `utm_source`, `utm_medium`, `utm_campaign`, `utm_adgroup`, `fbclid` e parâmetros personalizados.
- Parâmetros já definidos no destino vencem e não são duplicados.
- `page_id` e `p` não são encaminhados.
- Não coleta dados, não chama APIs externas e não implementa tracking de campanha.
- Duplicação copia somente a configuração, deixa a cópia inativa e exige novo gestor/slug.
- Cópias inativas não geram arquivo público; a ativação publica o `index.html`.
- Edições regeneram o `index.html` de forma atômica.
- Para trocar país, gestor, modelo ou slug de uma landing ativa, desative primeiro; isso impede duas rotas públicas concorrentes.
- O JavaScript do arquivo estático preserva UTMs, `fbclid` e parâmetros personalizados nos CTAs.
- Não implementa exclusão; desative a landing quando ela não deve mais responder.

## Rollback

Desativar o plugin retira os diretórios estáticos das rotas públicas de forma reversível e não apaga a option `mgs_direct_quiz_landings`.

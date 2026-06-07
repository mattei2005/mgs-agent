# Hera Creative Agent Bootstrap — PT-BR padrão MGS

## Quando esta referência é útil

Use ao criar ou revisar um novo agente operacional MGS com equipe brasileira envolvida, especialmente agentes de Creative Operations/marketing que terão SOUL, documento canônico, skills e templates próprios.

## Aprendizado capturado

Durante a criação da Hera, os primeiros documentos operacionais foram escritos em português, mas a primeira skill e seus templates nasceram em inglês. Rodolfo corrigiu a direção: para agentes internos MGS, o conteúdo operacional deve ser padronizado em Português do Brasil antes da revisão/liberação.

## Regra prática de idioma

```text
Camada                                      Idioma recomendado
───────────────────────────────────────────  ─────────────────────────────
SOUL do agente                              Português do Brasil
Documento operacional/contexto canônico      Português do Brasil
Conteúdo de SKILL.md operacional MGS         Português do Brasil
Templates usados por equipe                  Português do Brasil
Exemplos/checklists/status                   Português do Brasil
Nome de skill/pasta/arquivo                  Inglês curto ou slug técnico ok
Frontmatter técnico YAML                     Inglês/misto ok
Tags técnicas                                Inglês ou slugs sem acento ok
Jargões já usados na operação                brief, handoff, CTA, assets ok
```

## Sequência recomendada para novo agente MGS

1. Criar profile Hermes sem gateway/token ativo.
2. Criar SOUL inicial com missão, limites, relação com Zeus/Ares/Atena e escopo proibido.
3. Registrar usuário/agente em `authorized-users.json` e audit log.
4. Sincronizar SOUL/config para o repo.
5. Criar bot/canal/token e validar acesso Discord antes de systemd.
6. Criar documento operacional canônico em `/root/mgs-agent/context/<agent>.md`.
7. Enviar arquivos longos como `MEDIA:/path`, não colar conteúdo gigante no chat.
8. Alinhar SOUL ao documento canônico.
9. Criar skills/templates próprios do agente em PT-BR quando forem operacionais para MGS.
10. Sincronizar apenas skills customizadas necessárias; não versionar categorias inteiras com skills bundled/vendor.
11. Validar frontmatter, templates, sync e gateway.
12. Só depois rodar teste controlado no Discord.

## Pitfall

Não misturar idioma por camada: se SOUL/documento estão em PT-BR e a skill operacional está em inglês, o agente tende a responder de forma inconsistente e parecer genérico. Padronize antes da revisão do Rodolfo.

## Validação mínima

- `SKILL.md` começa com frontmatter válido.
- Conteúdo principal está em PT-BR.
- Templates estão em PT-BR.
- Cópia versionada é idêntica ao source do profile.
- Gateway foi reiniciado quando a skill precisa entrar no runtime/autocomplete.
- Logs confirmam bot conectado após restart.

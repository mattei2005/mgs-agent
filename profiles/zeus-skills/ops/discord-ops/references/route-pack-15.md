### Diagnóstico rápido: symlink vs arquivo real no git

```bash
# mode 120000 = symlink (errado), 100644 = arquivo real (correto)
git ls-files -s profiles/

# Ver o que git armazenou como conteúdo
git show HEAD:profiles/zeus-soul.md

# Teste definitivo
echo "x" >> /root/.hermes/profiles/zeus/SOUL.md
git -C /root/mgs-agent diff  # vazio se symlink, diff real se arquivo
```

### Adicionar novo agente ao sync

1. Adicionar no loop `for agent in zeus atena NOVO_AGENTE` para SOUL.md.
2. Adicionar o agente no loop de `config.yaml` quando o profile tiver config versionada.
3. Adicionar bloco `rsync -a --delete` só para categorias MGS-específicas do novo agente; não sincronizar a árvore inteira de skills bundled/hub.
4. Rodar manualmente uma vez para criar os arquivos iniciais.
5. Confirmar cron: `crontab -l | grep sync-souls`.
6. Se a categoria virar política MGS-wide em `/root/mgs-agent/AGENT.md`, fazer double-confirm antes de editar, porque AGENT.md é Critical Subset.

Categorias seletivas conhecidas:
- Zeus: `ops/`
- Atena: `wordpress/`, `devops/`, e `autonomous-ai-agents/openhands` como exceção pontual
- Ares: `growth/`

### Política de extensão de skills

Se nova skill MGS-específica for criada em categoria não coberta (ex: `zeus/skills/data-science/`), adicionar ao bloco rsync do script E reportar via `[REPORT-INFRA]`. Skill fora do sync = não versionada = sem rastreabilidade.

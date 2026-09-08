# Zeus: transcrição de áudio em português

Rodolfo pediu transcrição em português durante a thread1545426987756298340 em2026-09-08. Respostas continuam texto, sem TTS.

Diagnóstico confirmado: STT local/faster-whisper `base`, linguagem automática vazia; log do áudio apontou idioma `en` embora Rodolfo falasse português. Não era tradução voluntária do assistente. Consultadas documentação oficial Hermes e implementação `tools/transcription_tools.py` do runtime ativo. Skill genérica hermes-agent estava desabilitada; foi lida diretamente em disco, sem habilitar ou modificar outro perfil.

Correção delimitada: `stt.local.language: pt` no config ativo Zeus e mirror `/root/mgs-agent/profiles/zeus-config.yaml`. Usado `atomic_config_write` nativo, backup de ambos, comparação semântica verificando nenhuma outra chave alterada. `_resolve_stt_language('local', _load_stt_config()) == 'pt'`. Mesmo áudio retranscrito com sucesso em português. Não mudou provider/modelo/credenciais e não houve restart. Próximo áudio novo chegou transcrito em português na própria execução.

Evidência: `/root/mgs-agent/work/stt-portuguese-1546894693135028234/{apply-and-test.py,readback.json,retranscription.txt}`; backups0600. Não publicar áudio/transcrição como anexos nem imprimir config inteira. Referências `op://` não são valores de segredos.

Para recorrência: conferir provider/modelo/idioma efetivamente resolvidos e idioma detectado no log específico; não atribuir a causa ao LLM sem prova. Repetir o mesmo áudio no caminho real após correção. Idioma é lido pela rotina de transcrição; não reiniciar o gateway por reflexo. Alterações em outros perfis precisam de autorização própria. Configuração pt é preferência do Zeus/Rodolfo, não default universal de todos os agentes.

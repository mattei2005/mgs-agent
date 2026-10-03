# Zeus: transcrição de áudio em português

Rodolfo pediu transcrição em português durante a thread1545426987756298340 em2026-09-08. Respostas continuam texto, sem TTS.

Diagnóstico confirmado: STT local/faster-whisper `base`, linguagem automática vazia; log do áudio apontou idioma `en` embora Rodolfo falasse português. Não era tradução voluntária do assistente. Consultadas documentação oficial Hermes e implementação `tools/transcription_tools.py` do runtime ativo. Skill genérica hermes-agent estava desabilitada; foi lida diretamente em disco, sem habilitar ou modificar outro perfil.

Correção delimitada: `stt.local.language: pt` no config ativo Zeus e mirror `/root/mgs-agent/profiles/zeus-config.yaml`. Usado `atomic_config_write` nativo, backup de ambos, comparação semântica verificando nenhuma outra chave alterada. `_resolve_stt_language('local', _load_stt_config()) == 'pt'`. Mesmo áudio retranscrito com sucesso em português. Não mudou provider/modelo/credenciais e não houve restart. Próximo áudio novo chegou transcrito em português na própria execução.

Evidência: `/root/mgs-agent/work/stt-portuguese-1546894693135028234/{apply-and-test.py,readback.json,retranscription.txt}`; backups0600. Não publicar áudio/transcrição como anexos nem imprimir config inteira. Referências `op://` não são valores de segredos.

Se o runtime vivo não tiver backend local instalado, `transcribe_audio_local_fallback` pode retornar `No installed local STT backend is available`: não tratar o áudio como vazio nem instalar pacotes no gateway por reflexo. Recuperar o áudio pontual em ambiente efêmero via `uv run --python 3.12 --with faster-whisper`, com português explícito e CPU/int8; preservar o config/runtime de produção. Se o PyAV disponível rejeitar `metadata_errors`, decodificar o áudio com `ffmpeg -f f32le -ac 1 -ar 16000 pipe:1`, converter os bytes em `numpy.float32` e passar o array a `WhisperModel.transcribe`, evitando o decoder incompatível. Validar pelo transcript real; recuperação pontual não prova reparo do STT automático do gateway.

Para recorrência: conferir provider/modelo/idioma efetivamente resolvidos e idioma detectado no log específico; não atribuir a causa ao LLM sem prova. Repetir o mesmo áudio no caminho real após correção. Idioma é lido pela rotina de transcrição; não reiniciar o gateway por reflexo. Alterações em outros perfis precisam de autorização própria. Configuração pt é preferência do Zeus/Rodolfo, não default universal de todos os agentes.

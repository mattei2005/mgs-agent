import os
import sys
from honcho import Honcho

WORKSPACE = os.getenv("HONCHO_WORKSPACE", "mgs-honcho-spike")
API_KEY = os.getenv("HONCHO_API_KEY")

if not API_KEY:
    print("BLOCKED: HONCHO_API_KEY não está definido. Crie a key no app.honcho.dev e exporte como variável de ambiente.")
    sys.exit(2)

honcho = Honcho(workspace_id=WORKSPACE, api_key=API_KEY, environment="production")

rodolfo = honcho.peer("rodolfo-synthetic")
zeus = honcho.peer("zeus-synthetic")
atena = honcho.peer("atena-synthetic")

session = honcho.session("synthetic-agent-ops-001")
session.add_messages([
    rodolfo.message("A Raquel pediu dois RECs hoje e um deles travou na imagem."),
    atena.message("O REC do cartão Alpha falhou na busca de imagem, mas o REC Beta publicou em draft."),
    zeus.message("Conclusão operacional preliminar: investigar fallback de imagem antes de escalar produção."),
    rodolfo.message("Atena está respondendo, mas quero saber se o problema é recorrente ou pontual."),
    zeus.message("Vou comparar eventos recentes e validar contra logs antes de reportar como incidente."),
])

question = "Com base nesse histórico sintético, qual conclusão operacional você tiraria sobre Atena? Responda curto e indique incertezas."
response = zeus.chat(question, target=atena)
print("workspace=", WORKSPACE)
print("question=", question)
print("response=", response)

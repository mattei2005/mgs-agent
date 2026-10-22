"""Read-only semantic-check canary for the Node security reload."""

def node_security_marker() -> str:
    return "NODE22_SECURITY_RELOAD_CANARY"

assert node_security_marker() == "NODE22_SECURITY_RELOAD_CANARY"

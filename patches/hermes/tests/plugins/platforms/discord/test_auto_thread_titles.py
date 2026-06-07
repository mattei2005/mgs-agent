from plugins.platforms.discord.adapter import DiscordAdapter


def title_for(message: str) -> str:
    adapter = DiscordAdapter.__new__(DiscordAdapter)
    return adapter._auto_thread_name_from_message(message)


def test_auto_thread_title_classifies_table_question_not_raw_prefix():
    message = """duvidas sobre isso:

1 - nao da pra melhorar essa tabela em relacao a colunas e quebras de linha ?

2 - por que voce manda 1/3 se cada mensagem aceita 4000 caracteres ?"""

    title = title_for(message)

    assert title == "Formatação de Tabelas"
    assert "Duvidas" not in title
    assert "nao da pra" not in title.casefold()
    assert len(title.split()) <= 6


def test_auto_thread_title_uses_semantic_examples_not_first_phrase():
    examples = {
        "me ajuda com esse erro do cronus": "Erro no Cronus Zen",
        "como converter esses horarios da espanha": "Conversão Horários Espanha",
        "preciso criar uma invoice": "Geração de Invoices",
        "me ajuda com o código do lazy blocks": "Código Lazy Blocks",
        "claude baniu minha conta": "Banimento Conta Claude",
    }

    for message, expected in examples.items():
        assert title_for(message) == expected


def test_auto_thread_fallback_strips_generic_scaffolding():
    title = title_for("duvida sobre isso: isso aqui ficou estranho no layout mobile")

    assert title == "Estranho Layout Mobile"
    assert "duvida" not in title.casefold()
    assert "isso" not in title.casefold()
    assert len(title.split()) <= 6

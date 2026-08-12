from app.config import Settings


def test_long_persona_can_be_loaded_from_file(tmp_path):
    persona = tmp_path / "persona.md"
    expected = "# 성격\n\n" + "길고 구체적인 페르소나 설명입니다.\n" * 100
    persona.write_text(expected, encoding="utf-8")
    settings = Settings(_env_file=None, bot_persona_file=str(persona), bot_persona="fallback")
    assert settings.persona_text() == expected.strip()


def test_persona_string_is_used_when_file_is_missing(tmp_path):
    settings = Settings(
        _env_file=None,
        bot_persona_file=str(tmp_path / "missing.md"),
        bot_persona="문자열 페르소나",
    )
    assert settings.persona_text() == "문자열 페르소나"


def test_blank_optional_discord_application_id_is_allowed():
    settings = Settings(_env_file=None, discord_application_id="")
    assert settings.discord_application_id is None

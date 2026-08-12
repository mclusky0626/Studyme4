from scripts.local_launcher import quote_env, render_local_env


def local_values():
    return {
        "DISCORD_TOKEN": "discord-secret",
        "LLM_PROVIDER": "openai",
        "OPENAI_API_KEY": "api-secret",
        "GEMINI_API_KEY": "",
        "GROK_API_KEY": "",
        "CHAT_MODEL": "gpt-4.1-mini",
        "PARTICIPATION_JUDGE_PROVIDER": "llm",
        "OLLAMA_PARTICIPATION_MODEL": "qwen2.5:3b",
    }


def test_local_launcher_uses_sqlite_and_no_redis():
    rendered = render_local_env(local_values())
    assert "sqlite+aiosqlite" in rendered
    assert 'REDIS_URL=""' in rendered
    assert 'BOT_NAME="미유"' in rendered


def test_env_values_are_safely_quoted():
    assert quote_env('value with "quotes"') == '"value with \\"quotes\\""'

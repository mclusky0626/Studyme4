#!/usr/bin/env python3
"""Zero-service macOS launcher for Miyu.

This file intentionally uses only the Python standard library because it also performs
the first-time virtual environment and dependency installation.
"""

from __future__ import annotations

import getpass
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / ".env"
VENV_DIR = ROOT / ".venv"
DATA_DIR = ROOT / "data"
LOG_DIR = ROOT / "logs"
DEPENDENCY_MARKER = VENV_DIR / ".studyme-dependencies"

PROVIDERS = {
    "1": ("openai", "OPENAI_API_KEY", "gpt-4.1-mini"),
    "2": ("gemini", "GEMINI_API_KEY", "gemini-2.5-flash-lite"),
    "3": ("grok", "GROK_API_KEY", "grok-3-mini"),
}


def heading(message: str) -> None:
    print(f"\n=== {message} ===")


def fail(message: str) -> None:
    print(f"\n오류: {message}", file=sys.stderr)
    if sys.stdin.isatty():
        input("Enter를 누르면 창이 닫혀.")
    raise SystemExit(1)


def read_env(path: Path = ENV_FILE) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, raw_value = line.split("=", 1)
        value = raw_value.strip()
        if value.startswith(('"', "'")):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                value = value.strip("\"'")
        values[key.strip()] = value
    return values


def quote_env(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def render_local_env(values: dict[str, str]) -> str:
    database_path = (DATA_DIR / "studyme.db").resolve().as_posix()
    provider = values["LLM_PROVIDER"]
    model_keys = {
        "openai": "OPENAI_CHAT_MODEL",
        "gemini": "GEMINI_CHAT_MODEL",
        "grok": "GROK_CHAT_MODEL",
    }
    lines = [
        "# 미유 로컬 구동기가 만든 설정 파일입니다. Git에 포함되지 않습니다.",
        f"DISCORD_TOKEN={quote_env(values['DISCORD_TOKEN'])}",
        'DISCORD_APPLICATION_ID=""',
        'WAKE_WORD="미유야"',
        "",
        f'DATABASE_URL="sqlite+aiosqlite:///{database_path}"',
        'REDIS_URL=""',
        "",
        f"LLM_PROVIDER={quote_env(provider)}",
        f"OPENAI_API_KEY={quote_env(values.get('OPENAI_API_KEY', ''))}",
        f"GEMINI_API_KEY={quote_env(values.get('GEMINI_API_KEY', ''))}",
        f"GROK_API_KEY={quote_env(values.get('GROK_API_KEY', ''))}",
        f"{model_keys[provider]}={quote_env(values['CHAT_MODEL'])}",
        "",
        'BOT_NAME="미유"',
        'BOT_PERSONA_FILE="persona.md"',
        "MEMORY_EXTRACTION_ENABLED=true",
        "AUTO_PARTICIPATION_ENABLED=true",
        f"PARTICIPATION_JUDGE_PROVIDER={quote_env(values['PARTICIPATION_JUDGE_PROVIDER'])}",
        'OLLAMA_BASE_URL="http://localhost:11434"',
        f"OLLAMA_PARTICIPATION_MODEL={quote_env(values['OLLAMA_PARTICIPATION_MODEL'])}",
        "RESPONSE_MAX_BUBBLES=4",
        "RESPONSE_BUBBLE_MAX_CHARS=700",
        "RUN_BOT=true",
        "HEALTH_HOST=127.0.0.1",
        "PORT=8080",
        "LOG_LEVEL=INFO",
        "",
    ]
    return "\n".join(lines)


def choose(prompt: str, choices: dict[str, str], default: str) -> str:
    for key, label in choices.items():
        suffix = " (기본)" if key == default else ""
        print(f"  {key}. {label}{suffix}")
    while True:
        answer = input(f"{prompt} [{default}]: ").strip() or default
        if answer in choices:
            return answer
        print("목록에 있는 번호를 골라줘.")


def secret_prompt(label: str, current: str = "") -> str:
    suffix = " (Enter면 기존 값 유지)" if current else ""
    while True:
        value = getpass.getpass(f"{label}{suffix}: ").strip()
        if value:
            return value
        if current:
            return current
        print("빈 값으로는 실행할 수 없어.")


def configure() -> None:
    heading("미유 최초 설정")
    current = read_env()
    print("토큰과 API 키는 화면에 표시되지 않고 이 Mac의 .env에만 저장돼.")

    discord_token = secret_prompt("Discord 봇 토큰", current.get("DISCORD_TOKEN", ""))
    provider_by_name = {value[0]: key for key, value in PROVIDERS.items()}
    provider_choice = choose(
        "대화 모델 제공자",
        {"1": "OpenAI", "2": "Gemini", "3": "Grok"},
        provider_by_name.get(current.get("LLM_PROVIDER", "openai"), "1"),
    )
    provider, api_key_name, default_model = PROVIDERS[provider_choice]
    api_key = secret_prompt(f"{provider.upper()} API 키", current.get(api_key_name, ""))

    model_env_name = {
        "openai": "OPENAI_CHAT_MODEL",
        "gemini": "GEMINI_CHAT_MODEL",
        "grok": "GROK_CHAT_MODEL",
    }[provider]
    current_model = current.get(model_env_name, default_model)
    chat_model = input(f"채팅 모델 [{current_model}]: ").strip() or current_model

    judge_choice = choose(
        "접두사 없는 대화 감지",
        {
            "1": "같은 대화 모델 사용 (설치 없이 가장 간단)",
            "2": "로컬 Ollama 사용",
            "3": "끄기",
        },
        {"llm": "1", "ollama": "2", "off": "3"}.get(
            current.get("PARTICIPATION_JUDGE_PROVIDER", "llm"), "1"
        ),
    )
    judge = {"1": "llm", "2": "ollama", "3": "off"}[judge_choice]
    ollama_model = current.get("OLLAMA_PARTICIPATION_MODEL", "qwen2.5:3b")
    if judge == "ollama":
        ollama_model = input(f"Ollama 판단 모델 [{ollama_model}]: ").strip() or ollama_model
        print("Ollama가 아직 없다면 나중에 `ollama pull " + ollama_model + "`을 실행해줘.")

    values = {
        "DISCORD_TOKEN": discord_token,
        "LLM_PROVIDER": provider,
        api_key_name: api_key,
        "OPENAI_API_KEY": current.get("OPENAI_API_KEY", ""),
        "GEMINI_API_KEY": current.get("GEMINI_API_KEY", ""),
        "GROK_API_KEY": current.get("GROK_API_KEY", ""),
        "CHAT_MODEL": chat_model,
        "PARTICIPATION_JUDGE_PROVIDER": judge,
        "OLLAMA_PARTICIPATION_MODEL": ollama_model,
    }
    values[api_key_name] = api_key
    ENV_FILE.write_text(render_local_env(values), encoding="utf-8")
    ENV_FILE.chmod(0o600)
    print("설정을 저장했어. 다음부터는 '미유 실행.command'만 더블클릭하면 돼.")


def python_version(executable: str) -> tuple[int, int] | None:
    try:
        output = subprocess.check_output(
            [executable, "-c", "import sys; print(sys.version_info[0], sys.version_info[1])"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
        major, minor = output.strip().split()
        return int(major), int(minor)
    except (OSError, subprocess.SubprocessError, ValueError):
        return None


def find_python() -> str:
    candidates = [
        sys.executable,
        "/opt/homebrew/bin/python3.13",
        "/opt/homebrew/bin/python3.12",
        "/usr/local/bin/python3.13",
        "/usr/local/bin/python3.12",
        shutil.which("python3.13"),
        shutil.which("python3.12"),
        shutil.which("python3"),
    ]
    for candidate in candidates:
        if candidate:
            version = python_version(candidate)
            if version is not None and version >= (3, 12):
                return candidate
    fail("Python 3.12 이상이 필요해. 터미널에서 `brew install python@3.12`를 실행해줘.")
    raise AssertionError("unreachable")


def dependency_fingerprint() -> str:
    return hashlib.sha256((ROOT / "pyproject.toml").read_bytes()).hexdigest()


def prepare_runtime(force_update: bool = False) -> Path:
    DATA_DIR.mkdir(exist_ok=True)
    LOG_DIR.mkdir(exist_ok=True)
    venv_python = VENV_DIR / "bin" / "python"
    if not venv_python.exists():
        heading("처음 한 번만 실행 환경 만드는 중")
        subprocess.run([find_python(), "-m", "venv", str(VENV_DIR)], check=True)

    fingerprint = dependency_fingerprint()
    installed = DEPENDENCY_MARKER.read_text().strip() if DEPENDENCY_MARKER.exists() else ""
    if force_update or installed != fingerprint:
        heading("필요한 패키지 설치 중")
        subprocess.run(
            [str(venv_python), "-m", "pip", "install", "--upgrade", "pip"],
            cwd=ROOT,
            check=True,
        )
        subprocess.run(
            [str(venv_python), "-m", "pip", "install", "-e", "."],
            cwd=ROOT,
            check=True,
        )
        DEPENDENCY_MARKER.write_text(fingerprint + "\n")
    return venv_python


def validate_configuration() -> None:
    values = read_env()
    if not values.get("DISCORD_TOKEN"):
        fail("Discord 봇 토큰이 없어. '미유 설정.command'를 먼저 실행해줘.")
    provider = values.get("LLM_PROVIDER", "openai")
    required_key = {
        "openai": "OPENAI_API_KEY",
        "gemini": "GEMINI_API_KEY",
        "grok": "GROK_API_KEY",
    }.get(provider)
    if not required_key or not values.get(required_key):
        fail(f"{provider} API 키가 없어. '미유 설정.command'를 다시 실행해줘.")


def migrate(venv_python: Path) -> None:
    heading("데이터 준비 중")
    subprocess.run([str(venv_python), "-m", "alembic", "upgrade", "head"], cwd=ROOT, check=True)


def run_bot(force_update: bool = False) -> None:
    if not ENV_FILE.exists():
        configure()
    validate_configuration()
    try:
        venv_python = prepare_runtime(force_update=force_update)
        migrate(venv_python)
    except subprocess.CalledProcessError:
        fail("설치 또는 데이터 준비에 실패했어. 위 오류 내용을 확인해줘.")

    heading("미유 실행 중")
    print("이 창을 닫거나 Ctrl+C를 누르면 미유가 종료돼.")
    run_environment = os.environ.copy()
    try:
        ca_bundle = subprocess.check_output(
            [str(venv_python), "-c", "import certifi; print(certifi.where())"], text=True
        ).strip()
        run_environment["SSL_CERT_FILE"] = ca_bundle
        run_environment["REQUESTS_CA_BUNDLE"] = ca_bundle
    except subprocess.SubprocessError:
        pass
    try:
        completed = subprocess.run(
            [str(venv_python), "-m", "app.main"], cwd=ROOT, env=run_environment
        )
    except KeyboardInterrupt:
        print("\n미유를 종료했어.")
        return
    if completed.returncode:
        fail(f"미유가 오류 코드 {completed.returncode}로 종료됐어.")


def main() -> None:
    os.chdir(ROOT)
    action = sys.argv[1] if len(sys.argv) > 1 else "run"
    if action == "configure":
        configure()
    elif action == "update":
        run_bot(force_update=True)
    elif action == "run":
        run_bot()
    else:
        fail(f"알 수 없는 실행 모드: {action}")


if __name__ == "__main__":
    main()

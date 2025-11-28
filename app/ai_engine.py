import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# Default model can be overridden via the OPENAI_MODEL environment variable
MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1")

_client: Optional[OpenAI] = None


def _load_api_key() -> str:
    """Return the OpenAI API key from env or a gitignored file."""
    env_key = os.getenv("OPENAI_API_KEY")
    if env_key:
        return env_key.strip()

    key_file_env = os.getenv("OPENAI_API_KEY_FILE")
    default_key_path = Path(__file__).resolve().parent.parent / "openai_api_key.txt"
    key_path = Path(key_file_env).expanduser() if key_file_env else default_key_path

    if key_path.is_file():
        key = key_path.read_text(encoding="utf-8").strip()
        if key:
            return key

    raise RuntimeError(
        "OpenAI API key not found. Set OPENAI_API_KEY or place it in "
        f"{key_path} (configurable via OPENAI_API_KEY_FILE)."
    )


def _get_client() -> OpenAI:
    """Lazily instantiate the OpenAI client so tests can monkeypatch ask_gpt."""
    global _client
    if _client is None:
        _client = OpenAI(api_key=_load_api_key())
    return _client


def ask_gpt(prompt: str) -> str:
    """Send a prompt to OpenAI ChatCompletion API and return the reply."""
    response = _get_client().chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4
    )
    return response.choices[0].message.content

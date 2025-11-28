import logging
import os
import time
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from openai import OpenAI
from openai import APIStatusError

load_dotenv()

# Model defaults (override via env)
ANALYSIS_MODEL = os.getenv("OPENAI_ANALYSIS_MODEL", os.getenv("OPENAI_MODEL", "gpt-4.1"))
SUMMARY_MODEL = os.getenv("OPENAI_SUMMARY_MODEL", "gpt-4.1-mini")

_client: Optional[OpenAI] = None
logger = logging.getLogger(__name__)


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


def ask_gpt(prompt: str, *, model: Optional[str] = None, temperature: float = 0.4, retries: int = 3) -> str:
    """Send a prompt to OpenAI ChatCompletion API and return the reply with retries and rate-limit handling."""
    model_to_use = model or ANALYSIS_MODEL
    backoff = 1.0
    last_exc: Optional[Exception] = None

    for attempt in range(1, retries + 1):
        try:
            response = _get_client().chat.completions.create(
                model=model_to_use,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature
            )
            return response.choices[0].message.content
        except Exception as exc:  # Broad to capture rate limits/network issues
            last_exc = exc
            status = getattr(exc, "status_code", None)
            is_rate_limit = status == 429 or isinstance(exc, APIStatusError) and getattr(exc, "status_code", None) == 429
            logger.warning("OpenAI call failed (attempt %s/%s, model=%s, rate_limit=%s): %s", attempt, retries, model_to_use, is_rate_limit, exc)
            if attempt == retries:
                break
            sleep_for = backoff * (2 if is_rate_limit else 1)
            time.sleep(sleep_for)
            backoff *= 2

    raise RuntimeError(f"OpenAI call failed after {retries} attempts: {last_exc}")

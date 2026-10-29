"""Settings: which AI provider and model Stevie talks to.

Read from ~/.config/krel-assistant/config.toml (or $XDG_CONFIG_HOME). Every
setting is optional; with no file at all Stevie uses a local Ollama.
"""

import os
import stat
import tomllib
from dataclasses import dataclass

# Providers that speak the OpenAI chat-completions API, so one client covers them all.
PROVIDERS = {
    "ollama": {"base_url": "http://localhost:11434/v1", "key_env": None},
    "openrouter": {"base_url": "https://openrouter.ai/api/v1", "key_env": "OPENROUTER_API_KEY"},
    "gemini": {"base_url": "https://generativelanguage.googleapis.com/v1beta/openai", "key_env": "GEMINI_API_KEY"},
    "openai": {"base_url": "https://api.openai.com/v1", "key_env": "OPENAI_API_KEY"},
}

DEFAULT_PROVIDER = "ollama"
# Picked by testing on a CPU-only laptop (i7-1185G7): answers in 10-50 s and calls tools reliably.
# qwen3:4b (thinking) took minutes; llama3.2:3b was faster but garbled tool calls.
DEFAULT_MODEL = "qwen3:4b-instruct"
DEFAULT_TIMEOUT = 120


class ConfigError(Exception):
    pass


@dataclass
class Config:
    provider: str = DEFAULT_PROVIDER
    model: str = DEFAULT_MODEL
    base_url: str = PROVIDERS[DEFAULT_PROVIDER]["base_url"]
    api_key: str | None = None
    timeout: int = DEFAULT_TIMEOUT


def config_dir():
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(base, "krel-assistant")


def config_path():
    return os.path.join(config_dir(), "config.toml")


def load(provider=None, model=None):
    """Build the config from the file, then apply command-line overrides."""
    data = {}
    path = config_path()
    if os.path.exists(path):
        try:
            with open(path, "rb") as f:
                data = tomllib.load(f)
        except tomllib.TOMLDecodeError as e:
            raise ConfigError(f"{path}: {e}") from None
        if data.get("api_key") and os.stat(path).st_mode & (stat.S_IRWXG | stat.S_IRWXO):
            raise ConfigError(f"{path} holds an API key but other users can read it. Fix with: chmod 600 {path}")

    name = provider or data.get("provider", DEFAULT_PROVIDER)
    if name not in PROVIDERS and "base_url" not in data:
        raise ConfigError(f"Unknown provider '{name}'. Known: {', '.join(PROVIDERS)}, or set base_url yourself.")
    preset = PROVIDERS.get(name, {"base_url": None, "key_env": None})

    # The file's model belongs to the file's provider; switching provider on the command line drops it.
    file_model = data.get("model") if not provider or provider == data.get("provider") else None
    key = data.get("api_key") or (os.environ.get(preset["key_env"]) if preset["key_env"] else None)
    return Config(
        provider=name,
        model=model or file_model or DEFAULT_MODEL,
        base_url=data.get("base_url") or preset["base_url"],
        api_key=key,
        timeout=int(data.get("timeout", DEFAULT_TIMEOUT)),
    )

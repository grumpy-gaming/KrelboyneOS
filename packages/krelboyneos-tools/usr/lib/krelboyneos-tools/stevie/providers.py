"""Talking to the AI: one client for every OpenAI-compatible chat API."""

import json
import socket
import urllib.error
import urllib.request


class ProviderError(Exception):
    pass


class OpenAICompatible:
    def __init__(self, config):
        self.config = config

    def chat(self, messages, tools):
        """Send the conversation; return the assistant's reply message (a dict)."""
        body = {"model": self.config.model, "messages": messages}
        if tools:
            body["tools"] = tools
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        request = urllib.request.Request(
            self.config.base_url.rstrip("/") + "/chat/completions",
            data=json.dumps(body).encode(), headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout) as response:
                data = json.load(response)
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")[:500]
            raise ProviderError(f"{self.config.provider} answered {e.code}: {detail}") from None
        except (urllib.error.URLError, ConnectionError) as e:
            if self.config.provider == "ollama":
                raise ProviderError("Cannot reach Ollama at " + self.config.base_url + ". On KrelboyneOS, install it from "
                                    "KOS Software > AI > Stevie's AI; if it is installed, check: systemctl status ollama") from None
            raise ProviderError(f"Cannot reach {self.config.provider}: {getattr(e, 'reason', e)}") from None
        except (TimeoutError, socket.timeout):
            raise ProviderError(f"{self.config.provider} did not answer within {self.config.timeout} seconds") from None
        try:
            return data["choices"][0]["message"]
        except (KeyError, IndexError, TypeError):
            raise ProviderError(f"Unexpected answer from {self.config.provider}: {str(data)[:300]}") from None

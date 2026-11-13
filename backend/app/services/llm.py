"""Thin wrapper around the Anthropic SDK.

The rest of the app calls `create_message` and never imports the SDK, so tests can
replace this one function and a deployment without an API key degrades cleanly.
"""
from __future__ import annotations

import logging
import threading

from ..config import settings

log = logging.getLogger("summa.llm")

# Models that support the server-side refusal fallback parameter.
_FALLBACK_MODELS = ("claude-opus-5", "claude-fable-5", "claude-sonnet-5-5")
_FALLBACK_BETA = "server-side-fallback-2026-07-01"

_client = None
_lock = threading.Lock()


class LLMUnavailable(RuntimeError):
    """No key is configured, or the provider could not complete the request."""

    def __init__(self, message: str, status_code: int = 503) -> None:
        super().__init__(message)
        self.status_code = status_code


def is_enabled() -> bool:
    return settings.llm_enabled


def status() -> dict:
    return {
        "enabled": is_enabled(),
        "provider": "Anthropic Claude",
        "model": settings.llm_model if is_enabled() else None,
        "setup_hint": None if is_enabled() else "Set ANTHROPIC_API_KEY in the .env file and restart the server.",
    }


def _get_client():
    global _client
    if not is_enabled():
        raise LLMUnavailable("The AI assistant is not configured. Set ANTHROPIC_API_KEY to enable it.")
    if _client is None:
        with _lock:
            if _client is None:
                import anthropic

                _client = anthropic.Anthropic(api_key=settings.llm_api_key, timeout=90.0, max_retries=2)
    return _client


def create_message(
    *,
    system: str,
    messages: list,
    tools: list | None = None,
    output_schema: dict | None = None,
    max_tokens: int = 16000,
):
    """Send one request and return the SDK message. Raises LLMUnavailable on any failure."""
    import anthropic

    client = _get_client()
    output_config: dict = {"effort": settings.llm_effort}
    if output_schema is not None:
        output_config["format"] = {"type": "json_schema", "schema": output_schema}
    params: dict = {
        "model": settings.llm_model,
        "max_tokens": max_tokens,
        "system": system,
        "messages": messages,
        "output_config": output_config,
    }
    if tools:
        params["tools"] = tools
    try:
        if settings.llm_model.startswith(_FALLBACK_MODELS):
            # If a safety classifier declines the request, the API retries it on a fallback model.
            return client.beta.messages.create(betas=[_FALLBACK_BETA], fallbacks="default", **params)
        return client.messages.create(**params)
    except anthropic.AuthenticationError as exc:
        raise LLMUnavailable("The configured ANTHROPIC_API_KEY was rejected.", 503) from exc
    except anthropic.PermissionDeniedError as exc:
        raise LLMUnavailable("The API key does not have access to the configured model.", 503) from exc
    except anthropic.NotFoundError as exc:
        raise LLMUnavailable(f"The model '{settings.llm_model}' was not found. Check SUMMA_LLM_MODEL.", 503) from exc
    except anthropic.RateLimitError as exc:
        raise LLMUnavailable("The AI provider is rate limiting requests. Try again in a minute.", 429) from exc
    except anthropic.BadRequestError as exc:
        log.warning("LLM bad request: %s", exc)
        raise LLMUnavailable("The AI provider rejected the request.", 502) from exc
    except anthropic.APIStatusError as exc:
        log.warning("LLM status error %s", exc.status_code)
        raise LLMUnavailable("The AI provider returned an error. Try again shortly.", 502) from exc
    except anthropic.APIConnectionError as exc:
        raise LLMUnavailable("Could not reach the AI provider. Check the network connection.", 503) from exc


def text_of(message) -> str:
    return "\n".join(block.text for block in message.content if getattr(block, "type", None) == "text").strip()

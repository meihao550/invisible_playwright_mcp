"""OpenRouter (OpenAI-compatible) client config. Key from arg or env only."""
from __future__ import annotations

from typing import Mapping

from . import env as environment

BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "z-ai/glm-5.3-flash"

#: App attribution for the public rankings at https://openrouter.ai/apps.
#: OpenRouter groups usage by these two headers and by nothing else: without
#: them every request is anonymous traffic on the key, so the app appears
#: nowhere however much it is used. They are constants rather than settings
#: because they name THIS package, not the person running it.
APP_URL = "https://github.com/feder-cr/invisible_playwright_mcp"
APP_TITLE = "invisible_playwright_mcp"


def resolve_key(explicit: str | None, env: Mapping[str, str]) -> str:
    key = explicit or env.get("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError(
            "no OpenRouter key: pass --openrouter-key or set OPENROUTER_API_KEY"
        )
    # ⛔ STRIPPED, SO A COPY-PASTE OR `$(cat keyfile)` DOES NOT FAIL FAR FROM
    # ITS CAUSE. A trailing newline reaches the openai SDK and goes into the
    # `Authorization: Bearer <key>\n` header, which httpx then rejects with
    # `APIConnectionError: Connection error.` - a sentence that names neither
    # the key nor the whitespace, so the user looks for a network problem
    # that is not there. Rejecting an empty-after-strip key with the usual
    # message keeps the "a key is required" error one place rather than two.
    key = key.strip()
    if not key:
        raise RuntimeError(
            "no OpenRouter key: pass --openrouter-key or set OPENROUTER_API_KEY"
        )
    return key


def resolve_model(explicit: str | None, env: Mapping[str, str]) -> str:
    return explicit or environment.read(environment.MODEL, env) or DEFAULT_MODEL


def make_client(key: str):
    from openai import OpenAI
    try:
        # openai>=1.68 exports Omit at package top level.
        from openai import Omit  # type: ignore[attr-defined]
    except ImportError:  # pragma: no cover - older SDKs
        from openai._types import Omit  # type: ignore[no-redef]

    # ⛔ `default_headers` CARRIES THE AUTHORIZATION ITSELF, AND THAT IS WHAT
    # MAKES THE ENVIRONMENT STOP WINNING. The SDK composes outgoing headers
    # as (api_key-derived defaults) <- (OPENAI_CUSTOM_HEADERS from env) <-
    # (default_headers from this call), left to right. Until this line
    # existed, a shell with
    #   export OPENAI_CUSTOM_HEADERS='Authorization: Bearer sk-hijacked'
    # replaced the key the caller passed, so the request went out
    # authenticated as somebody else - silently, with `client.api_key` still
    # reading the right value and only the bytes on the wire disagreeing.
    # Writing Authorization in default_headers puts the caller's key in the
    # last layer and the env's copy is overwritten rather than overwriting.
    #
    # ⛔ `OpenAI-Organization` AND `OpenAI-Project` ARE DROPPED, NOT PASSED
    # EMPTY. The SDK reads OPENAI_ORG_ID / OPENAI_PROJECT_ID from the
    # environment and sends them as headers to WHATEVER host it is talking
    # to, which here is openrouter.ai - a third party that has no business
    # seeing an unrelated OpenAI account's identifiers. `Omit()` is the SDK's
    # sentinel for "do not send this header at all", distinct from the empty
    # string (which sends an empty header) and from `None` (which would mean
    # the api_key route is used, defeating the fix above).
    return OpenAI(
        base_url=BASE_URL,
        api_key=key,
        default_headers={
            "Authorization": f"Bearer {key}",
            "OpenAI-Organization": Omit(),
            "OpenAI-Project": Omit(),
            "HTTP-Referer": APP_URL,
            "X-Title": APP_TITLE,
        },
    )

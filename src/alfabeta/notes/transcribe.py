"""A photo of class notes becomes Markdown, literally (spec 005 FR-005, research R5).

One Claude Messages API call per photo, through spec 004's `HttpTransport`, the one module allowed
to open a socket. The key is the place's own (constitution II): the Mac's in its keychain, the
cloud's in its secret store. The same client answers the report's one text question per changed
topic, "what it adds" (research R8), under the same budget.
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol, cast

from alfabeta.google.transport import TransportError
from alfabeta.notes.model import MAX_PHOTO_BYTES, TRANSCRIBABLE, PhotoState, Usage

if TYPE_CHECKING:
    from alfabeta.google.keychain import TokenStore
    from alfabeta.google.transport import HttpTransport

API = "https://api.anthropic.com/v1/messages"
# The newest API version (2026-10-21): no sampling parameters are sent, which it rejects.
API_VERSION = "2026-10-21"
MAX_TOKENS = 16000
# A "what it adds" answer is a few lines of Spanish (research R8).
ANSWER_TOKENS = 1500
# Reading handwriting is not a reasoning task; quickstart step 2 measures quality and cost at this level.
EFFORT = "low"
# A 10 MB photo and a page of Markdown take longer than spec 004's 30 s default.
TIMEOUT_SECONDS = 120.0
UNREADABLE = "[ilegible: página completa]"
# The 400 a spend limit returns has no documented message (Claude API errors page, read 2026-10-27).
_BUDGET_WORDS = ("spend limit", "usage limit", "credit balance")

INSTRUCTIONS = """\
Transcribe literally the handwritten class notes in the photo, in Markdown.

- Keep the language of the notes; write nothing that is not on the page.
- Keep the page's structure: headings, lists and their indentation, arrows (→, ↓, └).
- Text written between lines: ^(text). Crossed-out text: ~~text~~.
- A word you are not sure of: write your best reading followed by [?].
- A part you cannot read: [ilegible]. A drawing: [dibujo: what it shows, in Spanish]. A boxed part: [recuadro] before it.
- If nothing on the photo can be read, answer only the single line: [ilegible: página completa]
- Answer with the transcription only, no introduction and no comment."""


def claude_key_name(student: str) -> str:
    """Keychain account of the place's Claude key; `#` cannot occur in an account alias."""
    return f"{student}#claude"


@dataclass(frozen=True)
class Transcription:
    """What one photo became."""

    state: PhotoState  # transcribed, unsupported, unreadable, budget_wait or failed
    markdown: str = ""
    usage: Usage | None = None


class Transcriber(Protocol):
    """Turns a photo into Markdown."""

    def transcribe(self, image: bytes, mime_type: str) -> Transcription:
        """One photo, one call at most."""
        ...


class Answerer(Protocol):
    """Answers one text question; the report's "what it adds" (research R8)."""

    def answer(self, prompt: str) -> Transcription:
        """One question, one call; `transcribed` means answered, the text in `markdown`."""
        ...


def _budget_refused(status: int, error: dict[str, Any], headers: dict[str, str]) -> bool:
    """A credit or spend-limit refusal (research R5): waits for a day, not a retry.

    Documented: 402 `billing_error`; 400 `invalid_request_error` for an organization or workspace spend
    limit, message not given; 429 with no `retry-after` for the tier's monthly cap. The message words are
    unobserved; quickstart step 3 records the real answer when the workspace cap is reached.
    """
    if status == 402 or error.get("type") == "billing_error":
        return True
    message = str(error.get("message", "")).lower()
    if status == 400 and any(word in message for word in _BUDGET_WORDS):
        return True
    return status == 429 and "retry-after" not in {k.lower() for k in headers}


class ClaudeTranscriber:
    """`Transcriber` over the Messages API."""

    def __init__(self, transport: HttpTransport, key: str, model: str) -> None:
        self._transport = transport
        self._key = key
        self._model = model

    @classmethod
    def from_store(
        cls, transport: HttpTransport, store: TokenStore, student: str, model: str
    ) -> ClaudeTranscriber | None:
        """The place's transcriber, or None when it holds no key."""
        key = store.get(claude_key_name(student))
        return cls(transport, key, model) if key else None

    def transcribe(self, image: bytes, mime_type: str) -> Transcription:
        """JPEG, PNG or WebP up to 10 MB only; anything else is `unsupported` without a call."""
        if mime_type not in TRANSCRIBABLE or len(image) > MAX_PHOTO_BYTES:
            return Transcription(PhotoState.UNSUPPORTED)
        content: list[dict[str, Any]] = [
            {
                "type": "image",
                "source": {"type": "base64", "media_type": mime_type, "data": base64.b64encode(image).decode()},
            },
            {"type": "text", "text": INSTRUCTIONS},
        ]
        done = self._ask(content, MAX_TOKENS)
        if done.state == PhotoState.TRANSCRIBED and done.markdown.strip() == UNREADABLE:
            return Transcription(PhotoState.UNREADABLE, usage=done.usage)
        return done

    def answer(self, prompt: str) -> Transcription:
        """One text question, one call; the same refusals as a photo's (research R5)."""
        return self._ask([{"type": "text", "text": prompt}], ANSWER_TOKENS)

    def _ask(self, content: list[dict[str, Any]], max_tokens: int) -> Transcription:
        """One Messages API call; `transcribed` with the text, or why there is none."""
        body = {
            "model": self._model,
            "max_tokens": max_tokens,
            "output_config": {"effort": EFFORT},
            "messages": [{"role": "user", "content": content}],
        }
        headers = {"x-api-key": self._key, "anthropic-version": API_VERSION, "content-type": "application/json"}
        try:
            resp = self._transport.request("POST", API, headers=headers, body=json.dumps(body).encode())
        except TransportError:
            return Transcription(PhotoState.FAILED)
        data = cast("dict[str, Any]", json.loads(resp.body)) if resp.body else {}
        if resp.status >= 400:
            error = cast("dict[str, Any]", data.get("error", {}))
            refused = _budget_refused(resp.status, error, resp.headers)
            return Transcription(PhotoState.BUDGET_WAIT if refused else PhotoState.FAILED)
        raw_usage = cast("dict[str, int]", data.get("usage", {}))
        usage = Usage(int(raw_usage.get("input_tokens", 0)), int(raw_usage.get("output_tokens", 0)))
        if data.get("stop_reason") != "end_turn":
            return Transcription(PhotoState.FAILED, usage=usage)  # cut short or refused: never a page
        blocks = cast("list[dict[str, Any]]", data.get("content", []))
        markdown = "\n".join(str(b.get("text", "")) for b in blocks if b.get("type") == "text").strip()
        if not markdown:
            return Transcription(PhotoState.FAILED, usage=usage)
        return Transcription(PhotoState.TRANSCRIBED, markdown + "\n", usage)

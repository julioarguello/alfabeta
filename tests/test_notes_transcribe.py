"""A photo becomes Markdown through one Messages API call (spec 005 T013, T014). Invented values."""

from __future__ import annotations

import base64
import json
import logging
from pathlib import Path
from typing import Any

import pytest

from alfabeta.google.transport import Response, TransportError
from alfabeta.notes.model import MAX_PHOTO_BYTES, PhotoState, Usage
from alfabeta.notes.transcribe import API_VERSION, ClaudeTranscriber, claude_key_name
from tests.conftest import FakeTransport, MemoryStore

FIXTURES = Path(__file__).parent / "fixtures" / "notes"
KEY = "sk-ant-clave-inventada"
PHOTO = b"\x89PNG\r\n\x1a\nfoto inventada"


def answer(name: str, status: int = 200, headers: dict[str, str] | None = None) -> Response:
    return Response(status, (FIXTURES / name).read_bytes(), headers or {})


def transcriber(*responses: Response) -> tuple[ClaudeTranscriber, FakeTransport]:
    t = FakeTransport(list(responses))
    return ClaudeTranscriber(t, KEY, "claude-sonnet-5-5"), t


def test_the_request_sends_the_image_before_the_instructions():
    tr, t = transcriber(answer("claude-answer.json"))
    result = tr.transcribe(PHOTO, "image/png")
    method, url, headers, body = t.calls[0]
    sent: dict[str, Any] = json.loads(body or b"{}")
    content = sent["messages"][0]["content"]
    assert (method, url) == ("POST", "https://api.anthropic.com/v1/messages")
    assert [c["type"] for c in content] == ["image", "text"]
    assert content[0]["source"] == {
        "type": "base64",
        "media_type": "image/png",
        "data": base64.b64encode(PHOTO).decode(),
    }
    assert headers["anthropic-version"] == API_VERSION and headers["x-api-key"] == KEY
    assert not {"temperature", "top_p", "top_k", "thinking"} & set(sent)
    assert sent["model"] == "claude-sonnet-5-5"
    assert result.state == PhotoState.TRANSCRIBED
    assert result.markdown.startswith("## Las sustancias inventadas") and "ZORONGO" in result.markdown
    assert result.usage == Usage(3712, 845)


@pytest.mark.parametrize(
    ("mime", "size"), [("image/heic", 10), ("application/pdf", 10), ("image/jpeg", MAX_PHOTO_BYTES + 1)]
)
def test_an_unsupported_photo_makes_no_call(mime: str, size: int):
    tr, t = transcriber()
    assert tr.transcribe(b"x" * size, mime).state == PhotoState.UNSUPPORTED
    assert t.calls == []


def test_the_unreadable_answer_is_unreadable():
    tr, _ = transcriber(answer("claude-unreadable.json"))
    result = tr.transcribe(PHOTO, "image/png")
    assert (result.state, result.markdown) == (PhotoState.UNREADABLE, "")


@pytest.mark.parametrize(
    ("name", "status", "headers"),
    [
        ("claude-billing-402.json", 402, {}),
        ("claude-spend-limit-400.json", 400, {}),
        ("claude-spend-limit-400.json", 429, {}),  # the tier's monthly cap: no retry-after
    ],
)
def test_a_budget_refusal_waits(name: str, status: int, headers: dict[str, str]):
    tr, _ = transcriber(answer(name, status, headers))
    assert tr.transcribe(PHOTO, "image/png").state == PhotoState.BUDGET_WAIT


@pytest.mark.parametrize(
    "reply",
    [
        Response(429, b'{"type":"error","error":{"type":"rate_limit_error","message":"x"}}', {"retry-after": "30"}),
        Response(529, b'{"type":"error","error":{"type":"overloaded_error","message":"x"}}'),
        Response(400, b'{"type":"error","error":{"type":"invalid_request_error","message":"bad image"}}'),
        Response(
            200, json.dumps({"content": [{"type": "text", "text": "a medias"}], "stop_reason": "max_tokens"}).encode()
        ),
        Response(200, json.dumps({"content": [], "stop_reason": "refusal"}).encode()),
    ],
)
def test_any_other_error_or_a_cut_answer_fails(reply: Response):
    tr, _ = transcriber(reply)
    result = tr.transcribe(PHOTO, "image/png")
    assert (result.state, result.markdown) == (PhotoState.FAILED, "")


def test_no_connection_fails():
    class Down:
        def request(
            self, method: str, url: str, *, headers: dict[str, str] | None = None, body: bytes | None = None
        ) -> Response:
            raise TransportError("URLError")

    assert ClaudeTranscriber(Down(), KEY, "m").transcribe(PHOTO, "image/png").state == PhotoState.FAILED


def test_the_key_is_in_no_log_line_and_comes_from_the_places_store(caplog: pytest.LogCaptureFixture):
    store = MemoryStore()
    assert ClaudeTranscriber.from_store(FakeTransport(), store, "s9", "m") is None
    store.set(claude_key_name("s9"), KEY)
    t = FakeTransport([answer("claude-billing-402.json", 402)])
    tr = ClaudeTranscriber.from_store(t, store, "s9", "m")
    assert tr is not None
    with caplog.at_level(logging.DEBUG):
        logging.getLogger("alfabeta.notes.transcribe").debug("control")
        tr.transcribe(PHOTO, "image/png")
    assert "control" in caplog.text and KEY not in caplog.text
    assert "#" in claude_key_name("s9")  # never an account alias, which unlink could reach

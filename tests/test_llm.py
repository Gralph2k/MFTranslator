"""DeepSeekLLM: ретраи, пустой content в JSON-режиме, исчерпание попыток.

Единственный горячий error path прода без тестов: сбой сети или капризы
DeepSeek не должны молча съедать реплику или разбор.
"""

import asyncio
import json

import httpx
import pytest

from bot.llm import DeepSeekLLM, LLMError


def _message(content: str) -> dict:
    return httpx.Response(
        200, json={"choices": [{"message": {"content": content}}]}
    )


@pytest.fixture
def no_sleep(monkeypatch):
    """Бэкофф между ретраями не ждём — тесты и так детерминированы."""

    async def _instant(_seconds: float) -> None:
        return None

    monkeypatch.setattr(asyncio, "sleep", _instant)


def _llm(handler) -> DeepSeekLLM:
    llm = DeepSeekLLM(api_key="test")
    # Подменяем клиент целиком: _get_client вернёт его и не пойдёт в сеть.
    llm._client = httpx.AsyncClient(
        base_url=llm.base_url, transport=httpx.MockTransport(handler)
    )
    return llm


async def test_retries_429_and_succeeds(no_sleep):
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if len(requests) == 1:
            return httpx.Response(429)
        return _message("Привет.")

    llm = _llm(handler)
    try:
        assert await llm.complete([{"role": "user", "content": "hi"}]) == "Привет."
    finally:
        await llm.aclose()

    assert len(requests) == 2


async def test_gives_up_after_max_retries(no_sleep):
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(500)

    llm = _llm(handler)
    try:
        with pytest.raises(LLMError, match="3 попыток"):
            await llm.complete([{"role": "user", "content": "hi"}])
    finally:
        await llm.aclose()

    assert len(requests) == 3


async def test_empty_json_answer_falls_back_in_two_steps(no_sleep):
    """Пустой content в JSON-режиме: без response_format, потом с напоминанием.

    Известная особенность DeepSeek: json_mode иногда отвечает пустотой.
    """
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if len(requests) <= 2:
            return _message("")
        return _message('{"mood": "спокойно"}')

    llm = _llm(handler)
    try:
        raw = await llm.complete(
            [{"role": "user", "content": "дай JSON"}], json_mode=True
        )
    finally:
        await llm.aclose()

    assert json.loads(raw) == {"mood": "спокойно"}
    bodies = [json.loads(r.read()) for r in requests]
    # Шаг 1: с response_format; шаг 2: без него; шаг 3: с напоминанием в конце.
    assert "response_format" in bodies[0]
    assert "response_format" not in bodies[1]
    assert bodies[2]["messages"][-1]["role"] == "user"
    assert "JSON-объектом" in bodies[2]["messages"][-1]["content"]


async def test_plain_answer_is_returned_as_is():
    def handler(request: httpx.Request) -> httpx.Response:
        return _message("Просто текст, без JSON.")

    llm = _llm(handler)
    try:
        assert await llm.complete([{"role": "user", "content": "hi"}]) == (
            "Просто текст, без JSON."
        )
    finally:
        await llm.aclose()

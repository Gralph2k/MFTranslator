"""Клиент модели: DeepSeek для работы, фейк для тестов."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from typing import Any, Protocol

import httpx

from .tls import httpx_verify


class LLMError(RuntimeError):
    """Модель недоступна или ответила не то."""


class LLM(Protocol):
    async def complete(
        self,
        messages: list[dict[str, str]],
        *,
        json_mode: bool = False,
        temperature: float = 0.8,
    ) -> str: ...

    async def aclose(self) -> None: ...


@dataclass
class DeepSeekLLM:
    """OpenAI-совместимый клиент DeepSeek с повторами на сбоях."""

    api_key: str
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-chat"
    timeout: float = 60.0
    max_retries: int = 3
    _client: httpx.AsyncClient | None = field(default=None, init=False, repr=False)

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                verify=httpx_verify(),
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
            )
        return self._client

    async def complete(
        self,
        messages: list[dict[str, str]],
        *,
        json_mode: bool = False,
        temperature: float = 0.8,
    ) -> str:
        client = await self._get_client()
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "stream": False,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        last_error: str = "неизвестная ошибка"
        for attempt in range(1, self.max_retries + 1):
            try:
                response = await client.post("/chat/completions", json=payload)
                if response.status_code == 429 or response.status_code >= 500:
                    last_error = f"HTTP {response.status_code}"
                    raise LLMError(last_error)
                response.raise_for_status()
                data = response.json()
                choice = (data.get("choices") or [{}])[0]
                message = choice.get("message") or {}
                content = message.get("content")
                if not content or not content.strip():
                    # Пустой content в JSON-режиме — известная особенность DeepSeek.
                    # Сначала пробуем без response_format (модель отвечает охотнее),
                    # потом добавляем прямое требование вернуть объект.
                    last_error = (
                        f"пустой ответ (finish={choice.get('finish_reason')}, "
                        f"fields={sorted(message)})"
                    )
                    empty_retries = payload.setdefault("_empty_retries", 0)
                    payload["_empty_retries"] = empty_retries + 1
                    if empty_retries == 0 and "response_format" in payload:
                        payload.pop("response_format")
                    elif empty_retries == 1:
                        payload["messages"] = list(payload["messages"]) + [
                            {
                                "role": "user",
                                "content": (
                                    "Ответь только JSON-объектом по схеме выше. "
                                    "Поле reply не может быть пустым."
                                ),
                            }
                        ]
                    raise LLMError(last_error)
                return content
            except (httpx.HTTPError, LLMError, KeyError, IndexError) as exc:
                last_error = str(exc) or type(exc).__name__
                if attempt >= self.max_retries:
                    break
                await asyncio.sleep(min(8.0, 0.5 * 2 ** (attempt - 1)))

        raise LLMError(f"DeepSeek не ответил за {self.max_retries} попыток: {last_error}")

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None


@dataclass
class FakeLLM:
    """Заранее заданные ответы: так тесты не ходят в сеть."""

    replies: list[str]
    calls: list[dict[str, Any]] = field(default_factory=list)

    async def complete(
        self,
        messages: list[dict[str, str]],
        *,
        json_mode: bool = False,
        temperature: float = 0.8,
    ) -> str:
        self.calls.append(
            {"messages": messages, "json_mode": json_mode, "temperature": temperature}
        )
        if not self.replies:
            raise LLMError("FakeLLM: ответы закончились")
        return self.replies.pop(0)

    async def aclose(self) -> None:
        return None


def parse_json_object(text: str) -> dict[str, Any]:
    """Достаёт JSON-объект из ответа модели.

    Модели любят оборачивать JSON в ```json ... ``` или добавлять фразу до него,
    поэтому сначала пробуем как есть, потом ищем первую { и последнюю }.
    """
    text = text.strip()
    if text.startswith("```"):
        lines = [line for line in text.splitlines() if not line.strip().startswith("```")]
        text = "\n".join(lines).strip()

    try:
        value = json.loads(text)
        if isinstance(value, dict):
            return value
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        try:
            value = json.loads(text[start : end + 1])
            if isinstance(value, dict):
                return value
        except json.JSONDecodeError as exc:
            raise LLMError(f"не разобрал JSON от модели: {exc}") from exc

    raise LLMError("в ответе модели нет JSON-объекта")

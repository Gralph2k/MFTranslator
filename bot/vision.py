"""Vision-клиент для оценки фото анкеты: OpenRouter, дешёвая модель с глазами.

Отдельный класс, а не ветка DeepSeekLLM: протокол `LLM.complete` умеет только
текстовые сообщения, DemoLLM в CLI падает на content-частях, а DeepSeek
изображения не принимает вообще. Здесь messages собираются с image_url-частями
(data URL base64), ответ ждём текстом и парсим как JSON.
"""

from __future__ import annotations

import asyncio
import base64
from dataclasses import dataclass, field
from typing import Any

import httpx

from .llm import LLMError, parse_json_object
from .tls import httpx_verify


@dataclass
class VisionLLM:
    """OpenAI-совместимый клиент OpenRouter с повторами на сбоях."""

    api_key: str
    base_url: str = "https://openrouter.ai/api/v1"
    model: str = "google/gemini-2.5-flash-lite"
    timeout: float = 90.0
    max_retries: int = 3
    # У Gemini-моделей на OpenRouter дефолтный лимит выхода бывает мал:
    # разбор четырёх фото с флагами в него не помещается и обрезается.
    max_tokens: int = 3000
    _client: httpx.AsyncClient | None = field(default=None, init=False, repr=False)

    def _extra_body(self) -> dict[str, Any]:
        """Z.AI (glm-4.5+) - рейтинговые модели: без отключения размышлений
        токены уходят в reasoning_content и content приходит пустым."""
        if "z.ai" in self.base_url or "bigmodel" in self.base_url:
            return {"thinking": {"type": "disabled"}}
        return {}

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

    async def review_photos(
        self,
        system_prompt: str,
        user_prompt: str,
        images: list[bytes],
    ) -> dict[str, Any]:
        """Один вызов на весь набор фото: так дешевле и набор виден целиком."""
        content: list[dict[str, Any]] = [{"type": "text", "text": user_prompt}]
        for image in images:
            encoded = base64.b64encode(image).decode("ascii")
            content.append(
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded}"}}
            )
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content},
            ],
            "max_tokens": self.max_tokens,
            "temperature": 0.2,
            "stream": False,
            **self._extra_body(),
        }

        client = await self._get_client()
        last_error = "неизвестная ошибка"
        for attempt in range(1, self.max_retries + 1):
            try:
                response = await client.post("/chat/completions", json=payload)
                if response.status_code == 429 or response.status_code >= 500:
                    last_error = f"HTTP {response.status_code}"
                    raise LLMError(last_error)
                response.raise_for_status()
                data = response.json()
                choice = (data.get("choices") or [{}])[0]
                text = (choice.get("message") or {}).get("content")
                if not text or not text.strip():
                    last_error = f"пустой ответ (finish={choice.get('finish_reason')})"
                    raise LLMError(last_error)
                return parse_json_object(text)
            except (httpx.HTTPError, LLMError, KeyError, IndexError) as exc:
                last_error = str(exc) or type(exc).__name__
                if attempt >= self.max_retries:
                    break
                await asyncio.sleep(min(8.0, 0.5 * 2 ** (attempt - 1)))

        raise LLMError(f"vision-модель не ответила за {self.max_retries} попыток: {last_error}")

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

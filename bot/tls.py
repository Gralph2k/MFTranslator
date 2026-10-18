"""TLS-доверие: используем хранилище Windows, а не только certifi.

На машинах с антивирусом или VPN, которые проверяют HTTPS, соединение
подписывается их корневым сертификатом. Windows ему доверяет, а httpx по
умолчанию смотрит в certifi и падает с CERTIFICATE_VERIFY_FAILED.
"""

from __future__ import annotations

import ssl
from typing import Any


def make_ssl_context() -> Any | None:
    """Контекст из системного хранилища или None, если truststore недоступен."""
    try:
        import truststore
    except ImportError:
        return None

    try:
        return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    except Exception:
        return None


def httpx_verify() -> Any:
    """Значение для httpx.AsyncClient(verify=...)."""
    context = make_ssl_context()
    return context if context is not None else True


def is_certificate_error(exc: BaseException) -> bool:
    text = str(exc).lower()
    return "certificate" in text or "ssl" in text

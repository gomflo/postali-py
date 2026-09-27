from __future__ import annotations

from typing import Optional

DOCS_URL = "https://postali.app/api/docs#errors"

#: Códigos que devuelve la API en ``{"error": {"code": ...}}``.
API_ERROR_CODES = frozenset(
    {"invalid_cp", "invalid_query", "not_found", "rate_limited", "internal_error"}
)


class PostaliError(Exception):
    """Error de la API de Postali o del transporte.

    ``code`` es uno de:

    - ``invalid_cp``, ``invalid_query``, ``not_found``, ``rate_limited``,
      ``internal_error``: los devuelve la API.
    - ``timeout``: se superó el timeout.
    - ``network_error``: no se pudo conectar (DNS, TLS, conexión rechazada…).
    - ``http_error``: respuesta no exitosa sin cuerpo de error reconocible.

    ``status`` es el status HTTP, o ``0`` si no hubo respuesta.
    """

    def __init__(
        self,
        code: str,
        message: str,
        *,
        status: int = 0,
        docs_url: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status
        self.docs_url = docs_url or DOCS_URL

    def __repr__(self) -> str:
        return f"PostaliError(code={self.code!r}, status={self.status}, message={self.message!r})"

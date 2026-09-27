from __future__ import annotations

import json
import socket
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from ._errors import API_ERROR_CODES, PostaliError
from ._models import (
    BulkItem,
    BulkResult,
    CpResult,
    Estado,
    EstadosResult,
    MunicipioResult,
    MunicipiosResult,
    SearchResult,
    ValidateResult,
)
from ._normalize import COUNTRIES, normalize_cp
from ._version import __version__

DEFAULT_BASE_URL = "https://postali.app"
DEFAULT_TIMEOUT = 10.0
#: Máximo de códigos que acepta ``POST /bulk`` por petición.
BULK_MAX = 100
#: Longitud máxima de ``q`` en ``search``.
SEARCH_MAX_LENGTH = 100
# Cloudflare rechaza (403) el User-Agent por defecto de urllib ("Python-urllib/x.y").
DEFAULT_USER_AGENT = f"postali-py/{__version__} (+https://postali.app)"

_Timeout = Union[float, None]


class Postali:
    """Cliente síncrono de la API de Postali.

    >>> from postali import Postali
    >>> postali = Postali(country="mx")
    >>> postali.cp("06700").municipio
    'Cuauhtémoc'

    :param country: ``"mx"`` (por defecto), ``"co"`` o ``"es"``.
    :param base_url: URL base de la API. Por defecto ``https://postali.app``.
    :param timeout: segundos por petición (``None`` = sin límite). Por defecto 10.
    :param user_agent: cabecera ``User-Agent`` a enviar.
    """

    def __init__(
        self,
        country: str = "mx",
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: _Timeout = DEFAULT_TIMEOUT,
        user_agent: str = DEFAULT_USER_AGENT,
    ) -> None:
        if country not in COUNTRIES:
            raise ValueError(f"País no soportado: {country!r}. Usa 'mx', 'co' o 'es'.")
        self.country = country
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.user_agent = user_agent
        self._root = f"{self.base_url}/api/v1/{country}"

    def __repr__(self) -> str:
        return f"Postali(country={self.country!r}, base_url={self.base_url!r})"

    # ------------------------------------------------------------------ lookup

    def cp(self, codigo: Union[str, int]) -> CpResult:
        """Estado, municipio y asentamientos de un código postal.

        Lanza ``PostaliError`` con ``code="not_found"`` si el CP no existe.
        """
        return CpResult.from_dict(self._get(f"/cp/{self._cp(codigo)}"))

    def validate(self, codigo: Union[str, int]) -> ValidateResult:
        """Comprueba si un CP existe. El resultado es *truthy* si es válido."""
        return ValidateResult.from_dict(self._get(f"/validate/{self._cp(codigo)}"))

    # ------------------------------------------------------------------ search

    def search(self, q: str, *, limit: Optional[int] = None) -> SearchResult:
        """Búsqueda difusa por colonia, municipio o CP (para autocompletar)."""
        query = q.strip() if isinstance(q, str) else ""
        if not query:
            raise PostaliError("invalid_query", "La búsqueda está vacía.", status=400)
        if len(query) > SEARCH_MAX_LENGTH:
            raise PostaliError(
                "invalid_query", f"La búsqueda excede {SEARCH_MAX_LENGTH} caracteres.", status=400
            )
        params: List[Tuple[str, str]] = [("q", query)]
        if limit is not None:
            params.append(("limit", str(int(limit))))
        return SearchResult.from_dict(self._get(f"/search?{urllib.parse.urlencode(params)}"))

    # --------------------------------------------------------------- geografía

    def estados(self) -> EstadosResult:
        """Regiones de nivel 1 (estados / departamentos / provincias)."""
        return EstadosResult.from_dict(self._get("/estados"))

    def estado(self, slug: str) -> Estado:
        """Detalle de una región."""
        return Estado.from_dict(self._get(f"/estado/{_slug(slug, 'estado')}"))

    def municipios(self, estado_slug: str) -> MunicipiosResult:
        """Municipios de una región, ordenados por nombre."""
        return MunicipiosResult.from_dict(
            self._get(f"/estado/{_slug(estado_slug, 'estado')}/municipios")
        )

    def municipio(self, estado_slug: str, municipio_slug: str) -> MunicipioResult:
        """Asentamientos de un municipio (máx. 1000; ver ``truncated``)."""
        return MunicipioResult.from_dict(
            self._get(
                f"/municipio/{_slug(estado_slug, 'estado')}/{_slug(municipio_slug, 'municipio')}"
            )
        )

    # -------------------------------------------------------------------- bulk

    def bulk(self, codigos: Sequence[Union[str, int]]) -> BulkResult:
        """Resuelve muchos CPs a la vez.

        Normaliza cada código, marca como ``valid=False`` los que no tienen
        formato válido (sin enviarlos) y parte la lista en lotes de 100.
        Los resultados conservan el orden de entrada.
        """
        if isinstance(codigos, (str, bytes)) or not codigos:
            raise PostaliError("invalid_query", "`codigos` debe ser una lista no vacía.", status=400)
        results: List[Optional[BulkItem]] = [None] * len(codigos)
        pending: List[Tuple[int, str]] = []
        for i, raw in enumerate(codigos):
            cp = normalize_cp(raw, self.country)
            if cp is None:
                results[i] = BulkItem(cp=str(raw), valid=False)
            else:
                pending.append((i, cp))
        for start in range(0, len(pending), BULK_MAX):
            chunk = pending[start : start + BULK_MAX]
            data = self._request("POST", "/bulk", {"cps": [cp for _, cp in chunk]})
            items = data.get("results", []) if isinstance(data, dict) else []
            for j, (i, cp) in enumerate(chunk):
                results[i] = BulkItem.from_dict(items[j]) if j < len(items) else BulkItem(cp=cp, valid=False)
        final = [r if r is not None else BulkItem(cp="", valid=False) for r in results]
        return BulkResult(total=len(final), results=final)

    # ---------------------------------------------------------------- internos

    def _cp(self, codigo: Union[str, int]) -> str:
        cp = normalize_cp(codigo, self.country)
        if cp is None:
            raise PostaliError(
                "invalid_cp",
                f"{codigo!r} no tiene el formato de CP de {self.country.upper()}.",
                status=400,
            )
        return cp

    def _get(self, path: str) -> Dict[str, Any]:
        return self._request("GET", path)

    def _request(self, method: str, path: str, body: Any = None) -> Dict[str, Any]:
        headers = {"User-Agent": self.user_agent, "Accept": "application/json"}
        data: Optional[bytes] = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(self._root + path, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                status = resp.status
                raw = resp.read()
        except urllib.error.HTTPError as e:
            try:
                raw_err = e.read()
            except Exception:
                raw_err = b""
            raise _to_error(e.code, raw_err) from None
        except urllib.error.URLError as e:
            if isinstance(e.reason, (socket.timeout, TimeoutError)):
                raise self._timeout_error() from e
            raise PostaliError(
                "network_error", f"No se pudo contactar con Postali: {e.reason}"
            ) from e
        except (socket.timeout, TimeoutError) as e:
            raise self._timeout_error() from e
        except OSError as e:
            raise PostaliError("network_error", f"No se pudo contactar con Postali: {e}") from e

        parsed = _parse_json(raw)
        if not isinstance(parsed, dict):
            raise PostaliError("http_error", "Respuesta de Postali vacía o no es JSON.", status=status)
        return parsed

    def _timeout_error(self) -> PostaliError:
        return PostaliError("timeout", f"La petición a Postali superó {self.timeout} s.")


def _slug(value: str, name: str) -> str:
    s = value.strip() if isinstance(value, str) else ""
    if not s:
        raise PostaliError("invalid_query", f"Falta `{name}`.", status=400)
    return urllib.parse.quote(s, safe="")


def _parse_json(raw: bytes) -> Any:
    try:
        return json.loads(raw.decode("utf-8")) if raw else None
    except (ValueError, UnicodeDecodeError):
        return None


def _to_error(status: int, raw: bytes) -> PostaliError:
    data = _parse_json(raw)
    err = data.get("error") if isinstance(data, dict) else None
    if isinstance(err, dict) and isinstance(err.get("code"), str):
        code = err["code"] if err["code"] in API_ERROR_CODES else "http_error"
        raw_msg, raw_docs = err.get("message"), err.get("docs_url")
        message = raw_msg if isinstance(raw_msg, str) else f"HTTP {status}"
        docs = raw_docs if isinstance(raw_docs, str) else None
        return PostaliError(code, message, status=status, docs_url=docs)
    if status == 404:
        code = "not_found"
    elif status == 429:
        code = "rate_limited"
    elif status >= 500:
        code = "internal_error"
    else:
        code = "http_error"
    snippet = raw[:200].decode("utf-8", "replace").strip()
    msg = f"HTTP {status}" + (f": {snippet}" if snippet and not snippet.startswith("<") else "")
    return PostaliError(code, msg, status=status)

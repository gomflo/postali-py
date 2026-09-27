from __future__ import annotations

import io
import json
import socket
import urllib.error
import urllib.request
from typing import Any, Callable, List, Optional

import pytest

import postali
from postali import (
    BulkItem,
    CpResult,
    Postali,
    PostaliError,
    ValidateResult,
    normalize_cp,
)

CP_06700 = {
    "cp": "06700",
    "estado": "Ciudad de México",
    "estado_slug": "ciudad-de-mexico",
    "municipio": "Cuauhtémoc",
    "municipio_slug": "cuauhtemoc",
    "asentamientos": [
        {
            "nombre": "Roma Norte",
            "tipo": "Colonia",
            "ciudad": "Ciudad de México",
            "zona": "Urbano",
            "asenta_slug": "roma-norte",
        }
    ],
}


def api_error(code: str, message: str = "msg") -> dict:
    return {"error": {"code": code, "message": message, "docs_url": "https://postali.app/api/docs#errors"}}


class FakeResponse(io.BytesIO):
    def __init__(self, body: bytes, status: int = 200) -> None:
        super().__init__(body)
        self.status = status


class Recorder:
    """Sustituye a urllib.request.urlopen y guarda cada petición."""

    def __init__(self, handler: Callable[[urllib.request.Request], Any]) -> None:
        self.handler = handler
        self.requests: List[urllib.request.Request] = []
        self.timeouts: List[Optional[float]] = []

    def __call__(self, req: urllib.request.Request, timeout: Optional[float] = None) -> FakeResponse:
        self.requests.append(req)
        self.timeouts.append(timeout)
        result = self.handler(req)
        if isinstance(result, BaseException):
            raise result
        if isinstance(result, FakeResponse):
            return result
        return FakeResponse(json.dumps(result).encode("utf-8"))

    @property
    def urls(self) -> List[str]:
        return [r.full_url for r in self.requests]


def http_error(status: int, body: bytes) -> urllib.error.HTTPError:
    return urllib.error.HTTPError("https://postali.app/x", status, "err", {}, io.BytesIO(body))  # type: ignore[arg-type]


@pytest.fixture
def mock(monkeypatch: pytest.MonkeyPatch) -> Callable[[Callable[[urllib.request.Request], Any]], Recorder]:
    def install(handler: Callable[[urllib.request.Request], Any]) -> Recorder:
        rec = Recorder(handler)
        monkeypatch.setattr(urllib.request, "urlopen", rec)
        return rec

    return install


# --------------------------------------------------------------- normalize_cp


def test_normalize_restaura_cero_inicial() -> None:
    assert normalize_cp("6700") == "06700"
    assert normalize_cp(6700) == "06700"
    assert normalize_cp("8001", "es") == "08001"
    assert normalize_cp("50001", "co") == "050001"


def test_normalize_espacios_y_completos() -> None:
    assert normalize_cp(" 76 148 ") == "76148"
    assert normalize_cp("050001", "co") == "050001"


@pytest.mark.parametrize("value", ["670", "abcde", "067000", "0670", "", "-6700", "０６７００", True, None, 6.7])
def test_normalize_rechaza(value: Any) -> None:
    assert normalize_cp(value) is None


def test_normalize_no_fabrica_doble_cero() -> None:
    assert normalize_cp("06700", "co") is None


def test_normalize_pais_invalido() -> None:
    with pytest.raises(ValueError):
        normalize_cp("06700", "ar")


# --------------------------------------------------------------------- client


def test_defaults_y_user_agent(mock: Any) -> None:
    rec = mock(lambda req: CP_06700)
    r = Postali().cp("06700")
    assert isinstance(r, CpResult)
    assert r.municipio == "Cuauhtémoc"
    assert r.asentamientos[0].nombre == "Roma Norte"
    assert r.asentamientos[0].zona == "Urbano"
    assert rec.urls == ["https://postali.app/api/v1/mx/cp/06700"]
    req = rec.requests[0]
    assert req.get_method() == "GET"
    # Cloudflare bloquea "Python-urllib/x.y": siempre mandamos un UA propio.
    assert req.get_header("User-agent") == f"postali-py/{postali.__version__} (+https://postali.app)"
    assert rec.timeouts == [10.0]


def test_country_base_url_timeout(mock: Any) -> None:
    rec = mock(lambda req: {"cp": "050001", "valid": True, "asentamientos": 1})
    client = Postali("co", base_url="http://localhost:3000/", timeout=2.5)
    v = client.validate("50001")
    assert isinstance(v, ValidateResult) and v.valid and bool(v)
    assert rec.urls == ["http://localhost:3000/api/v1/co/validate/050001"]
    assert rec.timeouts == [2.5]


def test_pais_no_soportado() -> None:
    with pytest.raises(ValueError):
        Postali("ar")


def test_cp_normaliza(mock: Any) -> None:
    rec = mock(lambda req: CP_06700)
    Postali().cp(6700)
    assert rec.urls == ["https://postali.app/api/v1/mx/cp/06700"]


def test_cp_invalido_no_toca_red(mock: Any) -> None:
    rec = mock(lambda req: CP_06700)
    with pytest.raises(PostaliError) as exc:
        Postali().cp("abc")
    assert exc.value.code == "invalid_cp"
    assert exc.value.status == 400
    assert rec.requests == []


def test_error_de_api(mock: Any) -> None:
    body = json.dumps(api_error("not_found", "No se encontró el recurso solicitado.")).encode()
    mock(lambda req: http_error(404, body))
    with pytest.raises(PostaliError) as exc:
        Postali().cp("00000")
    e = exc.value
    assert (e.code, e.status, e.message) == ("not_found", 404, "No se encontró el recurso solicitado.")
    assert e.docs_url == "https://postali.app/api/docs#errors"
    assert str(e) == "No se encontró el recurso solicitado."


def test_validate_falso_es_falsy(mock: Any) -> None:
    mock(lambda req: {"cp": "00000", "valid": False, "asentamientos": 0})
    v = Postali().validate("00000")
    assert not v
    assert v.asentamientos == 0


def test_search(mock: Any) -> None:
    hit = {k: "x" for k in ("cp", "nombre", "tipo", "municipio", "estado", "estado_slug", "municipio_slug", "asenta_slug")}
    rec = mock(lambda req: {"query": "roma norte", "results": [hit]})
    r = Postali().search("  roma norte ", limit=5)
    assert r.query == "roma norte" and len(r.results) == 1 and r.results[0].cp == "x"
    assert rec.urls == ["https://postali.app/api/v1/mx/search?q=roma+norte&limit=5"]


@pytest.mark.parametrize("q", ["", "   ", "x" * 101])
def test_search_invalida(mock: Any, q: str) -> None:
    rec = mock(lambda req: {})
    with pytest.raises(PostaliError) as exc:
        Postali().search(q)
    assert exc.value.code == "invalid_query"
    assert rec.requests == []


def test_geografia(mock: Any) -> None:
    def handler(req: urllib.request.Request) -> Any:
        url = req.full_url
        if url.endswith("/estados"):
            return {"total": 1, "estados": [{"nombre": "Madrid", "slug": "madrid", "total_asentamientos": 9, "total_municipios": 3}]}
        if url.endswith("/municipios"):
            return {"estado": "A Coruña", "estado_slug": "a-coruna", "total": 1, "municipios": [{"nombre": "A", "slug": "a", "total_asentamientos": 2}]}
        if "/municipio/" in url:
            return {
                "estado": "Madrid", "estado_slug": "madrid", "municipio": "M", "municipio_slug": "m",
                "total_asentamientos": 1, "truncated": False,
                "colonias": [{"cp": "28013", "nombre": "Madrid", "tipo": "Zona Postal", "ciudad": None, "zona": None, "asenta_slug": "madrid-28013"}],
            }
        return {"nombre": "Madrid", "slug": "madrid", "total_asentamientos": 9, "total_municipios": 3}

    rec = mock(handler)
    es = Postali("es")
    assert es.estados().estados[0].slug == "madrid"
    assert es.estado("madrid").total_municipios == 3
    assert es.municipios("a-coruna").municipios[0].total_asentamientos == 2
    m = es.municipio("madrid", "san lorenzo/x")
    assert m.truncated is False and m.colonias[0].ciudad is None
    assert rec.urls == [
        "https://postali.app/api/v1/es/estados",
        "https://postali.app/api/v1/es/estado/madrid",
        "https://postali.app/api/v1/es/estado/a-coruna/municipios",
        "https://postali.app/api/v1/es/municipio/madrid/san%20lorenzo%2Fx",
    ]


def test_slug_vacio(mock: Any) -> None:
    mock(lambda req: {})
    with pytest.raises(PostaliError) as exc:
        Postali().estado(" ")
    assert exc.value.code == "invalid_query"


def test_ignora_campos_desconocidos(mock: Any) -> None:
    mock(lambda req: {**CP_06700, "nuevo_campo": 1})
    assert Postali().cp("06700").cp == "06700"


# ----------------------------------------------------------------------- bulk


def _bulk_echo(req: urllib.request.Request) -> Any:
    cps = json.loads(req.data)["cps"]  # type: ignore[arg-type]
    return {
        "total": len(cps),
        "results": [
            {"cp": cp, "valid": cp != "00000", "estado": None, "estado_slug": None,
             "municipio": None, "municipio_slug": None, "asentamientos": 0 if cp == "00000" else 1}
            for cp in cps
        ],
    }


def test_bulk_normaliza_y_conserva_orden(mock: Any) -> None:
    rec = mock(_bulk_echo)
    r = Postali().bulk(["6700", "abc", 44100, "00000"])
    req = rec.requests[0]
    assert req.get_method() == "POST"
    assert req.get_header("Content-type") == "application/json"
    assert json.loads(req.data) == {"cps": ["06700", "44100", "00000"]}  # type: ignore[arg-type]
    assert r.total == 4
    assert [(i.cp, i.valid) for i in r.results] == [("06700", True), ("abc", False), ("44100", True), ("00000", False)]
    assert r.results[1] == BulkItem(cp="abc", valid=False)


def test_bulk_lotes_de_100(mock: Any) -> None:
    rec = mock(_bulk_echo)
    codes = [str(10000 + i) for i in range(250)]
    r = Postali().bulk(codes)
    assert len(rec.requests) == 3
    assert [i.cp for i in r.results] == codes


def test_bulk_todos_invalidos_no_toca_red(mock: Any) -> None:
    rec = mock(_bulk_echo)
    r = Postali().bulk(["x", "1"])
    assert rec.requests == []
    assert not any(i.valid for i in r.results)


@pytest.mark.parametrize("value", [[], "06700"])
def test_bulk_entrada_invalida(mock: Any, value: Any) -> None:
    mock(_bulk_echo)
    with pytest.raises(PostaliError) as exc:
        Postali().bulk(value)
    assert exc.value.code == "invalid_query"


# -------------------------------------------------------- errores transporte


@pytest.mark.parametrize(
    "status,code",
    [(403, "http_error"), (404, "not_found"), (429, "rate_limited"), (502, "internal_error")],
)
def test_respuesta_html(mock: Any, status: int, code: str) -> None:
    mock(lambda req: http_error(status, b"<html>nope</html>"))
    with pytest.raises(PostaliError) as exc:
        Postali().estados()
    assert exc.value.code == code
    assert exc.value.status == status
    assert exc.value.message == f"HTTP {status}"


def test_texto_plano_en_error(mock: Any) -> None:
    mock(lambda req: http_error(422, b"Failed to deserialize the JSON body"))
    with pytest.raises(PostaliError) as exc:
        Postali().estados()
    assert exc.value.message == "HTTP 422: Failed to deserialize the JSON body"


def test_200_no_json(mock: Any) -> None:
    mock(lambda req: FakeResponse(b"ok"))
    with pytest.raises(PostaliError) as exc:
        Postali().estados()
    assert exc.value.code == "http_error"


@pytest.mark.parametrize(
    "exc_in",
    [socket.timeout("timed out"), TimeoutError(), urllib.error.URLError(socket.timeout("timed out"))],
)
def test_timeout(mock: Any, exc_in: BaseException) -> None:
    mock(lambda req: exc_in)
    with pytest.raises(PostaliError) as exc:
        Postali(timeout=1).estados()
    assert exc.value.code == "timeout"


@pytest.mark.parametrize(
    "exc_in",
    [urllib.error.URLError("nodename nor servname provided"), ConnectionResetError("reset")],
)
def test_network_error(mock: Any, exc_in: BaseException) -> None:
    mock(lambda req: exc_in)
    with pytest.raises(PostaliError) as exc:
        Postali().estados()
    assert exc.value.code == "network_error"
    assert exc.value.status == 0
    assert exc.value.__cause__ is exc_in

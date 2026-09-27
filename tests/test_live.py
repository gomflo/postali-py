"""Pruebas contra la API real. Desactivadas por defecto; actívalas con:

    POSTALI_LIVE=1 pytest -m live
"""

from __future__ import annotations

import os

import pytest

from postali import Postali, PostaliError

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(os.environ.get("POSTALI_LIVE") != "1", reason="define POSTALI_LIVE=1"),
]

BASE_URL = os.environ.get("POSTALI_BASE_URL", "https://postali.app")


@pytest.fixture(scope="module")
def mx() -> Postali:
    return Postali("mx", base_url=BASE_URL)


def test_mx_cp_con_cero_perdido(mx: Postali) -> None:
    r = mx.cp(6700)
    assert r.cp == "06700"
    assert r.municipio == "Cuauhtémoc"
    assert any(a.nombre == "Roma Norte" for a in r.asentamientos)


def test_mx_cp_varias_colonias(mx: Postali) -> None:
    r = mx.cp("76148")
    assert r.estado_slug == "queretaro"
    assert len(r.asentamientos) > 1


def test_co_y_es() -> None:
    assert Postali("co", base_url=BASE_URL).cp("050001").estado == "Antioquia"
    assert Postali("es", base_url=BASE_URL).cp("28013").municipio == "Madrid"


def test_resto_de_endpoints(mx: Postali) -> None:
    assert not mx.validate("00000")
    assert mx.search("roma norte", limit=3).results[0].cp == "06700"
    assert mx.estados().total == 32
    assert mx.estado("jalisco").slug == "jalisco"
    assert mx.municipios("jalisco").total > 100
    assert mx.municipio("jalisco", "guadalajara").colonias
    assert [i.valid for i in mx.bulk(["06700", "abc", "00000"]).results] == [True, False, False]


def test_not_found(mx: Postali) -> None:
    with pytest.raises(PostaliError) as exc:
        mx.cp("00000")
    assert exc.value.code == "not_found"
    assert exc.value.status == 404

"""Modelos de respuesta.

Son ``dataclasses`` inmutables con los mismos nombres de campo que el JSON de
la API, así que ``r.asentamientos[0].nombre`` funciona igual que en la
documentación. ``from_dict`` ignora campos desconocidos para que una versión
nueva de la API no rompa clientes antiguos.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Mapping, Optional


def _opt_str(d: Mapping[str, Any], key: str) -> Optional[str]:
    v = d.get(key)
    return v if isinstance(v, str) else None


@dataclass(frozen=True)
class Asentamiento:
    """Colonia, fraccionamiento, barrio o zona postal dentro de un CP."""

    nombre: str
    tipo: str
    asenta_slug: str
    ciudad: Optional[str] = None  #: ``None`` en CO y ES.
    zona: Optional[str] = None  #: ``"Urbano"`` / ``"Rural"``; ``None`` en CO y ES.

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "Asentamiento":
        return cls(
            nombre=d["nombre"],
            tipo=d["tipo"],
            asenta_slug=d["asenta_slug"],
            ciudad=_opt_str(d, "ciudad"),
            zona=_opt_str(d, "zona"),
        )


@dataclass(frozen=True)
class CpResult:
    """Respuesta de ``GET /api/v1/{country}/cp/{codigo}``."""

    cp: str
    estado: str
    estado_slug: str
    municipio: str
    municipio_slug: str
    asentamientos: List[Asentamiento] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "CpResult":
        return cls(
            cp=d["cp"],
            estado=d["estado"],
            estado_slug=d["estado_slug"],
            municipio=d["municipio"],
            municipio_slug=d["municipio_slug"],
            asentamientos=[Asentamiento.from_dict(a) for a in d.get("asentamientos", [])],
        )


@dataclass(frozen=True)
class ValidateResult:
    """Respuesta de ``GET /api/v1/{country}/validate/{codigo}``."""

    cp: str
    valid: bool
    asentamientos: int  #: Número de asentamientos que cubre el CP.

    def __bool__(self) -> bool:
        return self.valid

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "ValidateResult":
        return cls(cp=d["cp"], valid=bool(d["valid"]), asentamientos=int(d["asentamientos"]))


@dataclass(frozen=True)
class SearchHit:
    cp: str
    nombre: str
    tipo: str
    municipio: str
    estado: str
    estado_slug: str
    municipio_slug: str
    asenta_slug: str

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "SearchHit":
        return cls(
            cp=d["cp"],
            nombre=d["nombre"],
            tipo=d["tipo"],
            municipio=d["municipio"],
            estado=d["estado"],
            estado_slug=d["estado_slug"],
            municipio_slug=d["municipio_slug"],
            asenta_slug=d["asenta_slug"],
        )


@dataclass(frozen=True)
class SearchResult:
    """Respuesta de ``GET /api/v1/{country}/search``."""

    query: str
    results: List[SearchHit] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "SearchResult":
        return cls(query=d["query"], results=[SearchHit.from_dict(h) for h in d.get("results", [])])


@dataclass(frozen=True)
class Estado:
    """Región de nivel 1: estado (MX), departamento (CO) o provincia (ES)."""

    nombre: str
    slug: str
    total_asentamientos: int
    total_municipios: int

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "Estado":
        return cls(
            nombre=d["nombre"],
            slug=d["slug"],
            total_asentamientos=int(d["total_asentamientos"]),
            total_municipios=int(d["total_municipios"]),
        )


@dataclass(frozen=True)
class EstadosResult:
    """Respuesta de ``GET /api/v1/{country}/estados``."""

    total: int
    estados: List[Estado] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "EstadosResult":
        return cls(total=int(d["total"]), estados=[Estado.from_dict(e) for e in d.get("estados", [])])


@dataclass(frozen=True)
class MunicipioItem:
    nombre: str
    slug: str
    total_asentamientos: int

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "MunicipioItem":
        return cls(nombre=d["nombre"], slug=d["slug"], total_asentamientos=int(d["total_asentamientos"]))


@dataclass(frozen=True)
class MunicipiosResult:
    """Respuesta de ``GET /api/v1/{country}/estado/{slug}/municipios``."""

    estado: str
    estado_slug: str
    total: int
    municipios: List[MunicipioItem] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "MunicipiosResult":
        return cls(
            estado=d["estado"],
            estado_slug=d["estado_slug"],
            total=int(d["total"]),
            municipios=[MunicipioItem.from_dict(m) for m in d.get("municipios", [])],
        )


@dataclass(frozen=True)
class Colonia:
    """Asentamiento dentro de un municipio (incluye su CP)."""

    cp: str
    nombre: str
    tipo: str
    asenta_slug: str
    ciudad: Optional[str] = None
    zona: Optional[str] = None

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "Colonia":
        return cls(
            cp=d["cp"],
            nombre=d["nombre"],
            tipo=d["tipo"],
            asenta_slug=d["asenta_slug"],
            ciudad=_opt_str(d, "ciudad"),
            zona=_opt_str(d, "zona"),
        )


@dataclass(frozen=True)
class MunicipioResult:
    """Respuesta de ``GET /api/v1/{country}/municipio/{estado}/{municipio}``."""

    estado: str
    estado_slug: str
    municipio: str
    municipio_slug: str
    total_asentamientos: int
    truncated: bool  #: ``True`` si hay más de 1000 asentamientos y la lista se recortó.
    colonias: List[Colonia] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "MunicipioResult":
        return cls(
            estado=d["estado"],
            estado_slug=d["estado_slug"],
            municipio=d["municipio"],
            municipio_slug=d["municipio_slug"],
            total_asentamientos=int(d["total_asentamientos"]),
            truncated=bool(d["truncated"]),
            colonias=[Colonia.from_dict(c) for c in d.get("colonias", [])],
        )


@dataclass(frozen=True)
class BulkItem:
    """Resultado individual de ``bulk``."""

    cp: str
    valid: bool
    asentamientos: int = 0
    estado: Optional[str] = None
    estado_slug: Optional[str] = None
    municipio: Optional[str] = None
    municipio_slug: Optional[str] = None

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "BulkItem":
        return cls(
            cp=d["cp"],
            valid=bool(d["valid"]),
            asentamientos=int(d.get("asentamientos") or 0),
            estado=_opt_str(d, "estado"),
            estado_slug=_opt_str(d, "estado_slug"),
            municipio=_opt_str(d, "municipio"),
            municipio_slug=_opt_str(d, "municipio_slug"),
        )


@dataclass(frozen=True)
class BulkResult:
    """Respuesta de ``POST /api/v1/{country}/bulk`` (mismo orden que la entrada)."""

    total: int
    results: List[BulkItem] = field(default_factory=list)

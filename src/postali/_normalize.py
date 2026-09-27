from __future__ import annotations

import re
from typing import Dict, Optional, Tuple, Union

#: Países soportados (ISO 3166-1 alfa-2, minúsculas).
COUNTRIES: Tuple[str, ...] = ("mx", "co", "es")

#: Longitud del código postal por país.
CP_LENGTH: Dict[str, int] = {"mx": 5, "co": 6, "es": 5}

_WS = re.compile(r"\s+")


def normalize_cp(value: Union[str, int], country: str = "mx") -> Optional[str]:
    """Normaliza un código postal.

    - Acepta ``str`` o ``int``.
    - Quita espacios.
    - Restaura el cero inicial que Excel, un CSV o ``int()`` suelen comerse:
      ``"6700"`` → ``"06700"`` (MX), ``"8001"`` → ``"08001"`` (ES),
      ``"50001"`` → ``"050001"`` (CO).

    Se añade como máximo **un** cero y nunca delante de otro cero: en los tres
    países ningún CP empieza por ``00``, así que una entrada más corta es un CP
    incompleto, no uno recortado.

    Devuelve ``None`` si el resultado no tiene el formato del país.
    """
    if country not in CP_LENGTH:
        raise ValueError(f"País no soportado: {country!r}. Usa 'mx', 'co' o 'es'.")
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        return None
    length = CP_LENGTH[country]
    cp = _WS.sub("", str(value))
    if not cp.isascii() or not cp.isdigit():
        return None
    if len(cp) == length - 1 and not cp.startswith("0"):
        cp = "0" + cp
    return cp if len(cp) == length else None

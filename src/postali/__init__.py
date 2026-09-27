"""Cliente oficial de la API gratuita de códigos postales de Postali.

México, Colombia y España. Sin API key, sin dependencias.

    >>> from postali import Postali
    >>> Postali("mx").cp("06700").asentamientos[0].nombre
    'Roma Norte'

Documentación de la API: https://postali.app/api/docs
"""

from ._client import (
    BULK_MAX,
    DEFAULT_BASE_URL,
    DEFAULT_TIMEOUT,
    DEFAULT_USER_AGENT,
    SEARCH_MAX_LENGTH,
    Postali,
)
from ._errors import DOCS_URL, PostaliError
from ._models import (
    Asentamiento,
    BulkItem,
    BulkResult,
    Colonia,
    CpResult,
    Estado,
    EstadosResult,
    MunicipioItem,
    MunicipioResult,
    MunicipiosResult,
    SearchHit,
    SearchResult,
    ValidateResult,
)
from ._normalize import COUNTRIES, CP_LENGTH, normalize_cp
from ._version import __version__

__all__ = [
    "Postali",
    "PostaliError",
    "normalize_cp",
    "COUNTRIES",
    "CP_LENGTH",
    "BULK_MAX",
    "SEARCH_MAX_LENGTH",
    "DEFAULT_BASE_URL",
    "DEFAULT_TIMEOUT",
    "DEFAULT_USER_AGENT",
    "DOCS_URL",
    "Asentamiento",
    "BulkItem",
    "BulkResult",
    "Colonia",
    "CpResult",
    "Estado",
    "EstadosResult",
    "MunicipioItem",
    "MunicipioResult",
    "MunicipiosResult",
    "SearchHit",
    "SearchResult",
    "ValidateResult",
    "__version__",
]

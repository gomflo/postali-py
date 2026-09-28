# postali

Cliente oficial para Python de la **API gratuita de códigos postales de [Postali](https://postali.app)**: México, Colombia y España.

- Sin API key, sin registro, sin cuota mensual.
- Cero dependencias: sólo la biblioteca estándar (`urllib`). Python 3.9+.
- Respuestas tipadas como `dataclasses` inmutables (`py.typed` incluido).
- Restaura el cero inicial que se pierde en Excel, un CSV o `int()` (`6700` → `"06700"`).

**Documentación de la API:** https://postali.app/api/docs · **Sitio:** https://postali.app

## Instalación

```bash
pip install postali-api
```

El paquete se instala como `postali-api` y se importa como `postali`.

## Uso rápido

```python
from postali import Postali

postali = Postali("mx")
print(postali.cp("06700").asentamientos[0].nombre)  # Roma Norte
```

## Ejemplos

### Autocompletar la colonia en un formulario de dirección

Un endpoint de tu backend (aquí con Flask) que el formulario llama cuando el usuario termina de escribir el CP:

```python
from flask import Flask, jsonify
from postali import Postali, PostaliError

app = Flask(__name__)
postali = Postali("mx")

@app.get("/direccion/<cp>")
def direccion(cp: str):
    try:
        r = postali.cp(cp)  # "6700" también funciona
    except PostaliError as e:
        if e.code in ("not_found", "invalid_cp"):
            return jsonify(error="CP no encontrado"), 404
        raise
    return jsonify(
        estado=r.estado,
        municipio=r.municipio,
        colonias=[a.nombre for a in r.asentamientos],
    )
```

¿Buscas por nombre de colonia en lugar de CP?

```python
for hit in postali.search("roma norte", limit=5).results:
    print(hit.cp, hit.nombre, hit.municipio, hit.estado)
```

### Validar un CP

```python
if not postali.validate("06700"):   # ValidateResult es truthy si el CP existe
    raise ValueError("Ese código postal no existe.")
```

`validate` lanza `PostaliError` con `code == "invalid_cp"` si el texto ni siquiera tiene formato de CP (p. ej. `"abc"`), sin hacer la petición.

### Limpiar una columna de CPs (CSV / pandas)

```python
r = postali.bulk(["06700", "44100", 6700, "abc"])
for item in r.results:           # mismo orden que la entrada
    print(item.cp, item.valid, item.municipio)
# 06700 True Cuauhtémoc · 44100 True Guadalajara · 06700 True Cuauhtémoc · abc False None
```

`bulk` normaliza cada código, marca los que no tienen formato válido como `valid=False` y parte la lista en lotes de 100.

### Colombia y España

```python
Postali("co").cp("050001").municipio   # 'Medellín'
Postali("es").cp(8001).municipio       # "08001" → 'Barcelona'
```

## API

`Postali(country="mx", *, base_url="https://postali.app", timeout=10.0, user_agent=...)`

| Método | Endpoint | Devuelve |
|---|---|---|
| `cp(codigo)` | `GET /api/v1/{country}/cp/{codigo}` | `CpResult` |
| `validate(codigo)` | `GET /api/v1/{country}/validate/{codigo}` | `ValidateResult` |
| `search(q, limit=None)` | `GET /api/v1/{country}/search?q=` | `SearchResult` |
| `estados()` | `GET /api/v1/{country}/estados` | `EstadosResult` |
| `estado(slug)` | `GET /api/v1/{country}/estado/{slug}` | `Estado` |
| `municipios(estado_slug)` | `GET /api/v1/{country}/estado/{slug}/municipios` | `MunicipiosResult` |
| `municipio(estado_slug, municipio_slug)` | `GET /api/v1/{country}/municipio/{estado}/{municipio}` | `MunicipioResult` |
| `bulk(codigos)` | `POST /api/v1/{country}/bulk` | `BulkResult` |

"Estado" es el nivel 1 de cada país: estado en México, departamento en Colombia, provincia en España. Los campos de cada resultado se llaman igual que en el JSON de la API.

### Errores

Todo error de la API o de red se lanza como `PostaliError`, con `code`, `status`, `message` y `docs_url`:

```python
from postali import PostaliError

try:
    postali.cp("00000")
except PostaliError as e:
    print(e.code, e.status, e.message)  # not_found 404 No se encontró el recurso solicitado.
```

| `code` | Cuándo |
|---|---|
| `invalid_cp` | El CP no tiene el formato del país |
| `invalid_query` | Falta `q`, está vacía o hay un parámetro inválido |
| `not_found` | El CP, estado o municipio no existe |
| `rate_limited` | Demasiadas peticiones desde tu IP |
| `internal_error` | Error del servidor (5xx) |
| `timeout` | Se superó el `timeout` |
| `network_error` | No se pudo conectar |
| `http_error` | Otra respuesta no exitosa |

### Normalización de CPs

```python
from postali import normalize_cp

normalize_cp("6700")          # '06700'
normalize_cp(" 76 148 ")      # '76148'
normalize_cp("50001", "co")   # '050001'
normalize_cp("670")           # None (incompleto)
```

Se añade como máximo un cero, y nunca delante de otro cero: ningún CP de México, Colombia o España empieza por `00`.

## Datos y atribución

Datos: Sepomex vía [Postali](https://postali.app) / GeoNames ([CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)) para CO y ES.

## English

`postali` is the official zero-dependency Python client (stdlib `urllib`, Python 3.9+) for the free [Postali](https://postali.app) postal-code API covering Mexico, Colombia and Spain. No API key required.

```python
from postali import Postali
r = Postali("mx").cp("06700")          # "mx" | "co" | "es"
print(r.estado, r.municipio, [a.nombre for a in r.asentamientos])
```

Responses are typed frozen dataclasses; errors raise `PostaliError` with `code` (`invalid_cp`, `not_found`, `rate_limited`, `timeout`…), `status` and `docs_url`. Postal codes that lost their leading zero (`6700`) are restored automatically. API reference: https://postali.app/api/docs

Data: Sepomex via Postali / GeoNames (CC BY 4.0) for CO and ES.

## Licencia

MIT © Postali

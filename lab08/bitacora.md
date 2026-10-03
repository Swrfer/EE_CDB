# Bitácora del Laboratorio 08

## Entorno de trabajo

- Fecha de inicio: 3 de octubre de 2026.
- Sistema: macOS sobre arquitectura ARM64.
- Entorno Conda: `cdb`.
- Python: 3.12.14.
- Rama de trabajo: `lab08-api-client`.
- Condición clínica elegida: cáncer gástrico.

El laboratorio se desarrolló con `requests`, `requests-cache`, Pydantic,
pandas, PyArrow, pytest y `responses`. El proyecto se instaló en modo editable
mediante su archivo `pyproject.toml`.

La condición clínica se eligió por su relación directa con el proyecto de tesis.
Aunque la primera implementación utiliza cáncer gástrico, las consultas y el
cliente se diseñarán para aceptar otros términos, incluidos genes, fármacos y
condiciones clínicas.

## 1. Exploración previa de las APIs

Antes de implementar el cliente se revisaron la documentación y las respuestas
JSON de tres servicios biomédicos públicos:

- NCBI E-utilities para PubMed.
- ClinicalTrials.gov API v2.
- openFDA Drug Adverse Events.

Las consultas exploratorias se realizaron el 3 de octubre de 2026,
aproximadamente a las 12:42, hora de la Ciudad de México. Los encabezados de las
tres respuestas registraron las 18:42 UTC.

### Estrategia de búsqueda

Para PubMed se utilizó una consulta que combina el término MeSH de neoplasias
gástricas con la expresión `gastric cancer` en título o resumen:

```text
("stomach neoplasms"[MeSH Terms] OR "gastric cancer"[Title/Abstract])
```

ClinicalTrials.gov se consultó mediante la condición `gastric cancer`.

openFDA se consultó mediante el campo de indicación terapéutica:

```text
patient.drug.drugindication:"GASTRIC CANCER"
```

Esta última consulta recupera reportes en los que algún medicamento fue
registrado con cáncer gástrico como indicación. No implica que el medicamento
haya causado el evento adverso ni que fuera necesariamente el único tratamiento
del paciente.

### Endpoints, parámetros y paginación

| Fuente | Endpoint | Parámetros principales | Paginación | Límite de tasa |
|---|---|---|---|---|
| NCBI E-utilities | `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi` y posteriormente `esummary.fcgi` | `db=pubmed`, `term`, `retmode=json`, `retmax`, `retstart` | Desplazamiento con `retstart` y tamaño de lote con `retmax` | 3 solicitudes por segundo sin llave y 10 por segundo con llave |
| ClinicalTrials.gov v2 | `https://clinicaltrials.gov/api/v2/studies` | `query.cond`, `pageSize`, `pageToken`, `countTotal`, `format=json` | La respuesta proporciona `nextPageToken`, que se envía como `pageToken` en la solicitud siguiente | La documentación pública consultada no declara un límite numérico; se aplicará una política conservadora |
| openFDA Drug Event | `https://api.fda.gov/drug/event.json` | `search`, `limit`, `skip` y `count` | Desplazamiento con `skip` y tamaño de lote con `limit` | La documentación informa 240 solicitudes por minuto y 1,000 por día y dirección IP sin llave |

La documentación de openFDA presentaba una inconsistencia al momento de la
consulta. Su página de autenticación indicaba que la llave era requerida, pero
también describía límites para llamadas sin llave, mientras que la guía del
endpoint señalaba que la llave no era indispensable. La petición anónima
realizada en este laboratorio respondió correctamente con código HTTP 200.

### Solicitudes exploratorias

#### PubMed

```bash
curl \
  --silent \
  --show-error \
  --get \
  --max-time 30 \
  'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi' \
  --data-urlencode 'db=pubmed' \
  --data-urlencode 'term=("stomach neoplasms"[MeSH Terms] OR "gastric cancer"[Title/Abstract])' \
  --data-urlencode 'retmode=json' \
  --data-urlencode 'retmax=3'
```

#### ClinicalTrials.gov

```bash
curl \
  --silent \
  --show-error \
  --get \
  --max-time 30 \
  'https://clinicaltrials.gov/api/v2/studies' \
  --data-urlencode 'query.cond=gastric cancer' \
  --data-urlencode 'pageSize=3' \
  --data-urlencode 'countTotal=true' \
  --data-urlencode 'format=json'
```

#### openFDA

```bash
curl \
  --silent \
  --show-error \
  --get \
  --max-time 30 \
  'https://api.fda.gov/drug/event.json' \
  --data-urlencode 'search=patient.drug.drugindication:"GASTRIC CANCER"' \
  --data-urlencode 'limit=3'
```

En las tres llamadas se utilizó un tiempo máximo de 30 segundos y los parámetros
se codificaron de manera independiente mediante `--data-urlencode`, en lugar de
concatenarlos manualmente a la URL.

### Resultados observados

#### PubMed

La petición respondió con HTTP 200 y un cuerpo de 266 bytes. ESearch informó
155,153 registros y devolvió tres PMID:

```text
42826542
42826439
42826294
```

La API interpretó la búsqueda como:

```text
"stomach neoplasms"[MeSH Terms] OR "gastric cancer"[Title/Abstract]
```

ESearch devuelve identificadores y metadatos de la búsqueda, pero no proporciona
por sí solo todos los datos bibliográficos. Por ello, el cliente combinará
ESearch con ESummary para recuperar títulos, revistas y fechas de publicación.

#### ClinicalTrials.gov

La petición respondió con HTTP 200 y un cuerpo aproximado de 121 KB. Se
informaron 4,336 estudios, se recibieron los tres solicitados y la respuesta
incluyó `nextPageToken`.

El primer registro fue `NCT00911820`, un estudio completado sobre cáncer
esofágico y gástrico, con una inscripción real de 88 participantes.

El gran tamaño de solo tres registros confirmó que la respuesta contiene módulos
anidados y que la paginación debe procesarse gradualmente. El generador de la
Actividad 3 recorrerá `studies` uno a uno y utilizará `nextPageToken` únicamente
cuando necesite otra página.

#### openFDA

La petición respondió con HTTP 200 y un cuerpo aproximado de 46 KB. Se
informaron 20,730 reportes coincidentes y se recibieron los tres solicitados.

El primer reporte tenía el identificador `10004141`. Incluía Gleevec, cuyo
nombre genérico se registró como imatinib mesilato, y cáncer gástrico como
indicación. Entre las reacciones aparecieron lesión hepática, progresión de
neoplasia maligna, cáncer gástrico y problema de uso del producto.

Un reporte puede contener varios medicamentos, indicaciones y reacciones. Por
tanto, la normalización posterior deberá conservar las relaciones entre el
reporte, los medicamentos y las reacciones, en lugar de asumir una fila simple
por paciente.

### Encabezados y control de tasa

Las tres respuestas declararon contenido JSON, pero ninguna incluyó
`Retry-After` ni encabezados explícitos de límite de tasa. La ausencia de esos
encabezados en una respuesta exitosa no implica que el servicio carezca de
límites.

El cliente utilizará:

- Caché persistente en disco.
- Una sesión HTTP reutilizable.
- Tiempo límite en todas las solicitudes.
- Reintentos solo para métodos idempotentes.
- Backoff exponencial para HTTP 429 y errores 5xx.
- Respeto de `Retry-After` cuando el servidor lo proporcione.
- Una frecuencia conservadora aunque el servidor no publique encabezados.

### Precauciones de interpretación

Los conteos son una fotografía de las APIs en la fecha de descarga y pueden
cambiar cuando se agreguen o actualicen registros.

La presencia de un artículo, ensayo o reporte no demuestra por sí sola
relevancia causal. En particular, openFDA contiene notificaciones espontáneas y
no permite calcular incidencia, riesgo relativo ni causalidad sin denominadores
y análisis adicionales.

La recuperación automatizada reducirá el trabajo manual, pero la evidencia
utilizada posteriormente en la discusión de genes deberá revisarse de forma
crítica y trazable.

### Conteo inicial de solicitudes

La exploración produjo tres solicitudes reales sin caché:

| Origen | Solicitudes reales | Resueltas desde caché |
|---|---:|---:|
| Exploración manual con `curl` | 3 | 0 |

Estas llamadas se registran por separado porque ocurrieron antes de instrumentar
el cliente. El informe final sumará las solicitudes exploratorias y las
realizadas posteriormente por el módulo.

## 2. Una petición HTTP decente

Se implementó una petición mínima a ClinicalTrials.gov que conserva tres
prácticas obligatorias:

```python
response = http.get(
    STUDIES_URL,
    params=params,
    timeout=DEFAULT_TIMEOUT,
)
response.raise_for_status()
payload = response.json()
```

La implementación completa quedó en
`clientes/clinical_trials.py`. La función `buscar_estudios_simple()` también
comprueba que la condición no esté vacía, que el tamaño de página sea positivo y
que la respuesta JSON sea un objeto.

El tiempo límite se definió como una tupla:

```python
DEFAULT_TIMEOUT = (3.05, 20.0)
```

El primer valor limita el tiempo para establecer la conexión y el segundo limita
la espera de lectura. De esta manera, el programa no puede permanecer bloqueado
indefinidamente en ninguna de las dos etapas.

### Petición correcta

Se consultó `gastric cancer` mediante un diccionario de parámetros:

```python
params = {
    "query.cond": "gastric cancer",
    "pageSize": 1,
    "countTotal": "true",
    "format": "json",
}
```

La petición respondió con HTTP 200. Informó 4,336 estudios, devolvió un registro
y el primer identificador fue `NCT00911820`.

La URL preparada por `requests` fue equivalente a:

```text
https://clinicaltrials.gov/api/v2/studies?query.cond=gastric+cancer&pageSize=1&countTotal=true&format=json
```

### Fallo provocado 1: identificador inexistente sin `raise_for_status()`

Se solicitó el identificador sintácticamente válido pero inexistente
`NCT99999999`:

```python
missing_response = requests.get(
    f"{STUDIES_URL}/NCT99999999",
    timeout=DEFAULT_TIMEOUT,
)
```

Como no se llamó a `raise_for_status()`, `requests.get()` no lanzó una excepción
y el programa continuó normalmente, aunque la respuesta tenía:

```text
Código HTTP: 404
response.ok: False
Content-Type: text/plain; charset=UTF-8
```

El cuerpo recibido fue:

```text
NCT number NCT99999999 not found
```

Al intentar ejecutar `missing_response.json()`, se obtuvo:

```text
JSONDecodeError: Expecting value: line 1 column 1 (char 0)
```

El error visible apareció durante el parseo de JSON y no durante la petición.
Esto puede ocultar el problema original: el servidor no devolvió un registro
válido, sino un error HTTP en texto plano.

Con `raise_for_status()`, la ejecución se habría detenido antes del parseo con
un `HTTPError` que identifica directamente el código 404.

### Fallo provocado 2: concatenación manual de parámetros

Se construyó manualmente una URL con el término:

```text
cáncer gástrico & HER2
```

La URL se formó de manera incorrecta mediante concatenación:

```python
manual_url = (
    f"{STUDIES_URL}"
    f"?query.cond={search_term}"
    f"&pageSize=1"
    f"&countTotal=true"
    f"&format=json"
)
```

`requests` codificó los espacios y los caracteres acentuados, pero el carácter
`&` permaneció como un separador reservado de parámetros. La URL enviada
contenía este fragmento:

```text
query.cond=c%C3%A1ncer%20g%C3%A1strico%20&%20HER2
```

El servidor interpretó `HER2` como si fuera otro parámetro y respondió con HTTP
400:

```text
` HER2` is unknown parameter
```

Cuando la misma consulta se preparó correctamente mediante `params=`, el
carácter `&` se codificó como `%26`:

```text
query.cond=c%C3%A1ncer+g%C3%A1strico+%26+HER2
```

En este caso, todo el texto se conserva como el valor de `query.cond`.

El experimento mostró una diferencia importante: `requests` puede corregir
automáticamente algunos caracteres de una URL concatenada, como espacios y
acentos, pero no puede saber si un carácter reservado forma parte del término o
de la estructura de la consulta. `params=` evita esa ambigüedad y permite que la
biblioteca realice la codificación de forma consistente.

### Validación estática

La función permanente se comprobó sin realizar nuevas peticiones:

```text
compileall: código 0
Ruff: All checks passed
mypy: Success: no issues found
```

### Conteo acumulado de solicitudes

La preparación offline de una URL con `requests.Request.prepare()` no hizo
ninguna llamada de red.

| Actividad | Solicitudes reales | Resueltas desde caché |
|---|---:|---:|
| Exploración manual de las tres APIs | 3 | 0 |
| Petición correcta de ClinicalTrials.gov | 1 | 0 |
| Identificador inexistente | 1 | 0 |
| URL concatenada manualmente | 1 | 0 |
| **Total acumulado** | **6** | **0** |

## 3. Paginación sin agotar la memoria

Se implementó `iterar_estudios()` en `clientes/paginacion.py`. La función es un
generador de Python y entrega cada estudio mediante `yield`, en lugar de
acumular todos los resultados en una lista.

La comprobación estructural mostró:

```text
Nombre: iterar_estudios
¿Es función generadora?: True
```

### Estrategia de paginación

El generador solicita una página de ClinicalTrials.gov y procesa el arreglo
`studies` un elemento a la vez. Cuando termina una página, recupera
`nextPageToken` y lo envía como `pageToken` en la solicitud siguiente.

El proceso termina cuando ocurre alguna de estas condiciones:

- Se alcanza `max_records`.
- La respuesta ya no contiene `nextPageToken`.
- La API devuelve un error HTTP.
- El servidor devuelve una estructura inesperada.
- Se detecta un token repetido.

La detección de tokens repetidos evita que un comportamiento anómalo de la API
produzca un ciclo infinito.

Para el experimento se configuraron:

```text
Condición: gastric cancer
Tamaño de página: 100
Registros totales: 300
```

### Diseño de la comparación de memoria

La comparación se implementó en `scripts/medir_paginacion.py` y utilizó
`tracemalloc`.

Para comparar las dos estrategias con los mismos datos y sin repetir descargas
innecesarias se siguieron tres pasos:

1. Se vació una caché exclusiva de la Actividad 3.
2. El generador recorrió 300 estudios una vez para almacenar tres páginas en
   caché.
3. Las mediciones del generador y de la lista reutilizaron esas mismas páginas.

El calentamiento produjo tres peticiones reales. Las dos mediciones posteriores
se resolvieron completamente desde la caché.

### Procesamiento uno a uno

Durante el recorrido del generador se imprimió la memoria en cuatro puntos:

| Registro procesado | Memoria actual | Pico observado |
|---:|---:|---:|
| 1 | 10.01 MiB | 14.71 MiB |
| 100 | 10.01 MiB | 14.71 MiB |
| 200 | 13.99 MiB | 27.66 MiB |
| 300 | 8.80 MiB | 27.66 MiB |

La memoria actual disminuyó después de terminar la última página porque los
estudios ya procesados dejaron de ser necesarios. El valor pico conserva el
máximo observado durante toda la ejecución y, por definición, no disminuye.

### Comparación contra la lista

| Estrategia | Registros | Pico de memoria |
|---|---:|---:|
| Generador | 300 | 27.66 MiB |
| Lista | 300 | 31.39 MiB |

La lista consumió 3.73 MiB adicionales. El generador redujo el pico de memoria
en 11.89% respecto a la versión que acumuló todos los estudios.

El primer y el último NCT fueron idénticos en ambas estrategias, lo que confirmó
que la comparación utilizó el mismo conjunto y orden de registros.

La diferencia fue moderada porque cada respuesta de ClinicalTrials.gov contiene
estructuras JSON extensas y la decodificación de una página de 100 estudios
produce un costo temporal considerable. Sin embargo, existe una diferencia de
escalabilidad:

- La lista conserva todos los registros y crece con el total recuperado.
- El generador conserva principalmente la página activa y su consumo se
  relaciona con `page_size`.

Por esta razón, la ventaja del generador aumenta cuando se procesan conjuntos
más grandes o se reduce el tamaño de cada página.

### Uso de la caché

La caché SQLite ocupó aproximadamente 7.5 MB y se guardó en:

```text
lab08/.cache/activity03.sqlite
```

El directorio `.cache/` está excluido mediante `.gitignore`. La caché reduce
peticiones repetidas, pero no sustituye a los datos crudos reproducibles de la
Actividad 5.

La salida exacta del experimento quedó registrada en:

```text
evidencias/lab08_03_memory.txt
```

### Conteo acumulado de solicitudes

| Actividad | Solicitudes reales | Resueltas desde caché |
|---|---:|---:|
| Actividades 1 y 2 | 6 | 0 |
| Calentamiento de la caché para 300 estudios | 3 | 0 |
| Medición con generador | 0 | 3 |
| Medición con lista | 0 | 3 |
| **Total acumulado** | **9** | **6** |

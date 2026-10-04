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

## 4. Cliente HTTP robusto

Se implementó `RobustAPIClient` en `clientes/base.py` como componente común para
PubMed, ClinicalTrials.gov y openFDA.

El cliente incorpora:

- Tiempo límite de conexión y lectura en todas las peticiones.
- Una `CachedSession` reutilizable.
- Caché persistente en SQLite para el uso real.
- Reintentos restringidos a métodos idempotentes.
- Backoff exponencial.
- Respeto del encabezado `Retry-After`.
- Contadores de peticiones reales, caché y reintentos.
- Cierre explícito de la sesión.
- Uso como administrador de contexto mediante `with`.

### Sesión y caché

La sesión conserva conexiones HTTP entre solicitudes y evita crear una conexión
nueva para cada página. En la configuración real, la caché se almacena en disco
con una vigencia predeterminada de siete días.

Solo se almacenan respuestas HTTP 200. Los errores 429 y 5xx no se guardan, ya
que hacerlo podría convertir un fallo transitorio en una respuesta persistente
de caché.

Los métodos permitidos en la caché son:

```text
GET
HEAD
OPTIONS
```

Estos métodos se consideran idempotentes: repetirlos no debería crear ni
modificar recursos en el servidor.

### Política de reintentos

El cliente utiliza tres intentos totales. Esto significa una petición inicial y,
como máximo, dos repeticiones.

| Código o situación | ¿Reintenta? | Justificación |
|---|---|---|
| 400 Bad Request | No | La solicitud está mal formada; repetirla sin cambios produciría el mismo resultado |
| 401 Unauthorized | No | Requiere corregir autenticación o permisos |
| 404 Not Found | No | El recurso solicitado no existe |
| 429 Too Many Requests | Sí | Es una limitación temporal de tasa y puede resolverse esperando |
| 500 Internal Server Error | Sí | Puede representar un fallo transitorio del servidor |
| 503 Service Unavailable | Sí | El servicio puede recuperarse después de una espera |
| Otros códigos 5xx | Sí | Representan errores del lado del servidor potencialmente temporales |
| Timeout | Sí | Puede deberse a una interrupción transitoria |
| ConnectionError | Sí | La conexión puede recuperarse en un intento posterior |
| Método no idempotente | No | Repetirlo podría duplicar una operación con efectos laterales |

Las excepciones de red solo se reintentan cuando el método es idempotente.

### Backoff exponencial

Con el factor predeterminado de 0.5 segundos, las esperas después de los intentos
fallidos son:

```text
Primer fallo: 0.5 segundos
Segundo fallo: 1.0 segundos
```

Si se configuraran más intentos, la siguiente espera sería de 2.0 segundos.

Cuando la respuesta incluye `Retry-After`, este valor tiene prioridad sobre el
backoff calculado. El cliente acepta tanto segundos numéricos como una fecha
HTTP.

### Métricas

Cada instancia mantiene tres contadores:

| Métrica | Significado |
|---|---|
| `real_requests` | Intentos que llegaron a la red o fallaron durante la conexión |
| `cache_hits` | Respuestas recuperadas sin consultar nuevamente al servidor |
| `retries` | Repeticiones posteriores a un fallo |

La propiedad `total_attempts` suma peticiones reales y respuestas desde caché.

### Pruebas simuladas

La política se verificó con `responses` y el dominio reservado `example.test`.
No se realizaron llamadas externas.

Se comprobaron los siguientes escenarios:

1. Respuesta 200 con JSON válido.
2. Respuesta 429 seguida de 200, respetando `Retry-After: 2`.
3. Error 500 persistente, abandonado después de tres intentos.
4. Error 503 seguido de recuperación mediante backoff.
5. Errores 400, 401 y 404 sin reintento.
6. Método POST sin reintento ante 503.
7. Segunda petición GET idéntica resuelta desde caché.

El resultado fue:

```text
9 passed in 0.19s
```

La prueba de 500 persistente confirmó dos esperas simuladas de 0.5 y 1.0
segundos. La prueba de 429 confirmó una espera simulada de 2.0 segundos, tomada
de `Retry-After`.

La prueba de caché confirmó una petición real y una respuesta desde caché para
dos GET idénticos.

La evidencia quedó guardada en:

```text
evidencias/lab08_04_client_tests.txt
```

Estas pruebas se ejecutaron con respuestas interceptadas, pero la verificación
definitiva con el wifi apagado se realizará en la Actividad 8.

### Conteo acumulado de solicitudes públicas

Las pruebas de esta actividad no consultaron ninguna API real. Por tanto, el
conteo acumulado del laboratorio permanece en:

| Origen | Solicitudes reales | Resueltas desde caché |
|---|---:|---:|
| Actividades 1–3 | 9 | 6 |
| Pruebas simuladas de la Actividad 4 | 0 | 0 |
| **Total acumulado** | **9** | **6** |

## 5. Conservación de las respuestas crudas

Se implementó `RawResponseStore` en `clientes/raw_storage.py` para guardar cada
respuesta antes de transformarla.

El orden de trabajo quedó centralizado en `fetch_json_and_store()`:

```text
petición HTTP
→ guardado del cuerpo crudo
→ guardado de metadatos
→ interpretación del JSON
```

De esta manera, un error durante el parseo o la validación no destruye la
respuesta original.

### Formato de almacenamiento

El cuerpo se escribe directamente desde `response.content`. No se utiliza
`response.json()` ni se vuelve a serializar el contenido antes de guardarlo.

Cada descarga produce dos archivos:

1. El cuerpo crudo con extensión `.json`, `.xml` o `.bin`, según
   `Content-Type`.
2. Un archivo lateral `.metadata.json`.

El nombre contiene:

- Fuente.
- Fecha y hora UTC con microsegundos.
- Los primeros 12 caracteres del SHA-256 del cuerpo.

Por ejemplo:

```text
pubmed_20261004T173459737582Z_7d470623a896.json
```

### Metadatos reproducibles

El archivo lateral registra:

- Fuente.
- Fecha y hora de descarga en UTC.
- Método HTTP.
- Código de estado.
- URL solicitada.
- Parámetros utilizados.
- Tipo de contenido.
- Tamaño en bytes.
- SHA-256 completo.
- Procedencia de red o caché.
- Encabezados de la respuesta.

Los parámetros con nombres como `api_key`, `token`, `access_token` o `key` se
sustituyen por:

```text
***REDACTED***
```

La misma censura se aplica si una credencial aparece dentro de la URL.

### Prueba del orden de operaciones

Se simuló una respuesta HTTP 200 cuyo encabezado declaraba JSON, pero cuyo cuerpo
contenía HTML inválido:

```text
<html>temporary error</html>
```

El parseo produjo el `JSONDecodeError` esperado. Sin embargo, antes de la
excepción ya se habían escrito:

- El cuerpo exacto.
- Su archivo de metadatos.

La prueba confirmó que el archivo guardado era idéntico byte por byte a la
respuesta simulada.

### Descarga real de las tres fuentes

El script `scripts/descargar_crudos.py` realizó una solicitud controlada a cada
API.

#### PubMed

```text
Cuerpo: data/raw/pubmed/pubmed_20261004T173459737582Z_7d470623a896.json
Tamaño: 266 bytes
Claves: esearchresult, header
```

#### ClinicalTrials.gov

```text
Cuerpo: data/raw/clinicaltrials/clinicaltrials_20261004T173459918362Z_7d31ac3182e4.json
Tamaño: 123,424 bytes
Claves: nextPageToken, studies, totalCount
```

#### openFDA

```text
Cuerpo: data/raw/openfda/openfda_20261004T173507410629Z_2d6b0efb69be.json
Tamaño: 47,483 bytes
Claves: meta, results
```

Las tres respuestas provinieron de la red. No hubo reintentos ni respuestas
desde caché.

### Importancia para la reproducibilidad de la tesis

1. El archivo crudo conserva exactamente la evidencia disponible en la fecha de descarga, aunque la API cambie posteriormente.
2. Los parámetros y el hash permiten auditar qué se solicitó y comprobar que el insumo no fue modificado.
3. La transformación puede repetirse con código nuevo sin volver a consultar el servicio ni depender de su estado futuro.

### Exclusión de datos

Se generaron seis archivos dentro de `data/raw/`: tres cuerpos y tres archivos
de metadatos.

El directorio completo está excluido mediante `.gitignore`:

```text
/lab08/data/
```

Por tanto, el repositorio documenta cómo regenerar los datos, pero no versiona
las respuestas descargadas.

La salida resumida y versionable se guardó en:

```text
evidencias/lab08_05_raw_downloads.txt
```

### Conteo acumulado de solicitudes

| Actividad | Solicitudes reales | Resueltas desde caché |
|---|---:|---:|
| Actividades 1–4 | 9 | 6 |
| Descarga cruda de PubMed | 1 | 0 |
| Descarga cruda de ClinicalTrials.gov | 1 | 0 |
| Descarga cruda de openFDA | 1 | 0 |
| **Total acumulado** | **12** | **6** |


## 6. Validar en la frontera

Se definieron modelos de Pydantic para ClinicalTrials.gov, PubMed y openFDA. La
validación se ejecuta después de adaptar el JSON original y antes de construir
los DataFrames, para impedir que registros incompletos o clínicamente
incoherentes continúen hacia el análisis.

### Modelos y reglas aplicadas

| Fuente | Modelo | Validaciones principales |
|---|---|---|
| ClinicalTrials.gov | `ClinicalTrialRecord` | NCT válido, título no vacío, estado conocido, inscripción >= 0 y fechas coherentes |
| PubMed | `PubMedRecord` | PMID numérico, título no vacío, año plausible y autores |
| openFDA | `OpenFDAEvent` | Identificador numérico, fechas coherentes, medicamentos y reacciones no vacíos, edad entre 0 y 130 años |

Cada registro se procesa de manera independiente. Los válidos continúan; los
malformados se registran con su fuente, identificador y motivo, y después se
omiten sin detener el lote completo.

### Resultados de los registros reales

| Fuente | Recibidos | Válidos | Descartados |
|---|---:|---:|---:|
| ClinicalTrials.gov | 3 | 3 | 0 |
| PubMed | 3 | 3 | 0 |
| openFDA | 3 | 3 | 0 |
| **Total** | **9** | **9** | **0** |

Los nueve registros reales pasaron la validación. Esto demuestra la
compatibilidad inicial de los adaptadores con las respuestas descargadas, pero
no garantiza que todos los registros futuros de las APIs sean válidos.

### Muestra de tres registros rechazados

Se introdujeron defectos controlados en copias de registros reales. Estos
controles no proceden directamente de las APIs ni se mezclaron con los datos
válidos.

| Fuente | Identificador | Defecto controlado | Motivo del rechazo |
|---|---|---|---|
| ClinicalTrials.gov | NCT00911820 | Conteo de inscripción ausente | `enrollmentInfo.count` debe ser un entero |
| PubMed | 42829718 | Título vacío | `title` debe ser texto no vacío |
| openFDA | 10004141 | Lista de reacciones vacía | `reactions` debe contener al menos un elemento |

Los tres controles malformados fueron rechazados:

```text
Controles recibidos: 3
Controles válidos: 0
Controles rechazados: 3
```

El informe completo se guardó localmente en
`data/processed/validation_report.json`, ruta excluida mediante `.gitignore`.
La evidencia de ejecución se conserva en
`evidencias/lab08_06_validation.txt`.

### Conteo acumulado de solicitudes

La validación utilizó archivos locales y realizó cero solicitudes nuevas. La
consulta ESummary necesaria para completar los registros de PubMed realizó una
solicitud real.

| Actividad | Solicitudes reales | Resueltas desde caché |
|---|---:|---:|
| Actividades 1–5 | 12 | 6 |
| Resumen ESummary de PubMed | 1 | 0 |
| Validación local | 0 | 0 |
| **Total acumulado** | **13** | **6** |


## 7. Consolidar y analizar

Los nueve registros que superaron la validación se normalizaron con
`pandas.json_normalize` y se organizaron en tres DataFrames. Las columnas con
valores múltiples, como países, autores, medicamentos y reacciones, se
conservaron como listas para no perder información.

### Archivos Parquet

| Fuente | Filas | Columnas | Archivo local |
|---|---:|---:|---|
| ClinicalTrials.gov | 3 | 8 | `data/processed/clinicaltrials.parquet` |
| PubMed | 3 | 5 | `data/processed/pubmed.parquet` |
| openFDA | 3 | 7 | `data/processed/openfda.parquet` |

Los tres archivos se volvieron a leer con pandas después de escribirlos. Las
dimensiones y las filas esperadas se conservaron, por lo que se comprobó el
ciclo de escritura y lectura de Parquet. Todo `data/processed/` permanece
excluido mediante `.gitignore`.

### Pregunta 1: ensayos activos y ubicación

Se consideraron activos los estados `RECRUITING`, `NOT_YET_RECRUITING`,
`ENROLLING_BY_INVITATION` y `ACTIVE_NOT_RECRUITING`. Ninguno de los tres
ensayos de la muestra tenía uno de esos estados: dos estaban completados y uno
tenía estado desconocido.

Por tanto, la muestra validada contenía **0 ensayos activos** y no fue posible
asignar ensayos activos a algún país. Esto describe únicamente la muestra de
tres registros y no el universo completo de ClinicalTrials.gov.

### Pregunta 2: reacciones notificadas en openFDA

Después de expandir la lista de reacciones, `Pyrexia` apareció en dos reportes.
Las otras ocho reacciones aparecieron una vez cada una. Estos datos son
notificaciones de farmacovigilancia y no demuestran causalidad entre un
medicamento y un evento.

### Pregunta 3: publicaciones por año

Los tres artículos recuperados de PubMed correspondieron a 2026. Esta
concentración se debe a que se utilizaron los primeros resultados de la consulta
y no representa la evolución histórica completa de la literatura sobre cáncer
gástrico.

### Notebook reproducible

El análisis quedó implementado en `notebooks/consolidado.ipynb`. El notebook
contiene 15 celdas, de las cuales 5 son de código. Todas se ejecutaron con
`nbconvert`: no quedaron celdas sin ejecutar y no se registraron errores.

La advertencia del kernel sobre comunicación TCP corresponde al funcionamiento
local de Jupyter. El notebook leyó exclusivamente los archivos Parquet locales
y no realizó solicitudes de red.

Las evidencias de esta actividad se guardaron en
`evidencias/lab08_07_consolidation.txt` y
`evidencias/lab08_07_notebook_execution.txt`.

### Conteo acumulado de solicitudes

La consolidación, la lectura de Parquet y la ejecución del notebook fueron
operaciones locales. El conteo acumulado se mantiene en **13 solicitudes
reales**, **6 respuestas desde caché** y ninguna solicitud adicional durante
esta actividad.


## 8. Pruebas completamente offline

La suite utiliza `responses` para simular las respuestas HTTP y evitar la
dependencia de los servicios públicos durante las pruebas. Además, una fixture
global reemplaza `socket.socket.connect`; cualquier intento accidental de abrir
una conexión real provoca un fallo inmediato.

### Casos obligatorios

| Caso | Comportamiento comprobado |
|---|---|
| 200 con JSON válido | El cliente devuelve el contenido esperado |
| 429 seguido de 200 | Reintenta, respeta `Retry-After` y termina correctamente |
| 500 persistente | Se detiene después de tres intentos |
| 404 | Propaga el error sin reintentar |
| Campo obligatorio ausente | Pydantic produce un `ValidationError` |

La suite también cubre un 503 con backoff exponencial, los códigos 400 y 401 sin
reintento, métodos no idempotentes, respuestas desde caché, conservación de
bytes crudos y rechazo de valores clínicamente inválidos.

### Verificación con el Wi-Fi apagado

La prueba final se ejecutó el 4 de octubre de 2026 con la interfaz `en0`
desactivada. El sistema informó explícitamente:

```text
Wi-Fi Power (en0): Off
```

Pytest recolectó y ejecutó 24 pruebas:

```text
24 passed in 0.28s
```

No quedaron pruebas omitidas ni errores. La evidencia completa, incluidos los
nombres individuales de los casos, se guardó en
`evidencias/lab08_08_pytest_offline.txt`.

La combinación de mocks, bloqueo de sockets y ejecución física sin Wi-Fi
demuestra que la suite no depende de PubMed, ClinicalTrials.gov, openFDA ni de
otro servicio externo.

### Conteo de solicitudes

Las pruebas offline realizaron **0 solicitudes reales**. Las respuestas 200,
429, 500, 503, 400, 401 y 404 observadas durante pytest fueron simuladas y no
incrementan las métricas de uso de las APIs públicas.


## 9. Medir la cortesía

El cliente robusto utiliza `RequestMetrics` para distinguir intentos reales,
respuestas obtenidas desde caché y reintentos. Para el resumen final se
combinaron esas métricas instrumentadas con las seis solicitudes exploratorias
realizadas antes de construir el cliente.

| Actividad | Solicitudes reales | Respuestas desde caché |
|---|---:|---:|
| Exploración y fallos controlados, actividades 1–2 | 6 | 0 |
| Paginación de ClinicalTrials.gov, actividad 3 | 3 | 6 |
| Descarga cruda de las tres APIs, actividad 5 | 3 | 0 |
| Resumen ESummary de PubMed, actividad 6 | 1 | 0 |
| Validación, consolidación y pruebas, actividades 6–8 | 0 | 0 |
| **Total** | **13** | **6** |

En total se resolvieron 19 solicitudes lógicas. Seis fueron atendidas desde la
caché, equivalentes al **31.58%**. Las respuestas simuladas por `responses`
durante pytest no se contabilizaron como tráfico real ni como caché de las APIs
públicas.

### Reflexión

Mil primeras ejecuciones simultáneas podrían generar 13,000 solicitudes reales
y ejercer presión innecesaria sobre servicios públicos gratuitos.
La caché reduce las repeticiones, pero también se requieren límites de tasa,
pausas y ejecuciones escalonadas.

El desglose reproducible se guardó en
`evidencias/lab08_09_metrics.txt` y
`evidencias/lab08_09_metrics.json`.

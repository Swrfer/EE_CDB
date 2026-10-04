# Laboratorio 08 — Cliente para APIs biomédicas públicas

Cliente reproducible en Python para consultar PubMed, ClinicalTrials.gov v2 y
openFDA, conservar las respuestas crudas, validar los registros y consolidarlos
en archivos Parquet.

El ejemplo utiliza **cáncer gástrico**. La arquitectura está preparada para
extender posteriormente las búsquedas a genes de interés, capacidad pronóstica
y regulación epigenética.

## Objetivos cumplidos

- Todas las solicitudes usan `timeout`, `params=` y `raise_for_status()`.
- Se reutiliza una sesión HTTP con caché en disco.
- Solo se reintentan métodos idempotentes.
- Se reintentan 429 y 5xx con backoff exponencial.
- Se respeta el encabezado `Retry-After`.
- La paginación de ClinicalTrials.gov utiliza un generador.
- Las respuestas crudas se guardan antes de interpretar el JSON.
- Los registros se validan mediante modelos de Pydantic.
- Los datos válidos se normalizan y guardan en Parquet.
- Las pruebas funcionan con el Wi-Fi apagado.
- Se contabilizan solicitudes reales, caché y reintentos.

## Fuentes consultadas

Fecha de la exploración y descarga de ejemplo: **4 de octubre de 2026**.

| Fuente | Endpoint | Parámetros principales | Paginación |
|---|---|---|---|
| PubMed ESearch | `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi` | `db`, `term`, `retmode`, `retstart`, `retmax` | `retstart` y `retmax` |
| PubMed ESummary | `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi` | `db`, `id`, `retmode` | Los PMID se procesan por lotes |
| ClinicalTrials.gov v2 | `https://clinicaltrials.gov/api/v2/studies` | `query.cond`, `pageSize`, `pageToken`, `countTotal`, `format` | `nextPageToken` |
| openFDA Drug Event | `https://api.fda.gov/drug/event.json` | `search`, `limit`, `skip` | `skip` y `limit` |

Consultas principales:

```text
PubMed:
"stomach neoplasms"[MeSH Terms] OR "gastric cancer"[Title/Abstract]

ClinicalTrials.gov:
query.cond=gastric cancer

openFDA:
patient.drug.drugindication:"GASTRIC CANCER"
```

NCBI permite normalmente 3 solicitudes por segundo sin llave y 10 por segundo
con una llave registrada. Para las demás fuentes no se dependió de encabezados
de tasa: el cliente aplica caché, reintentos selectivos y pausas indicadas por
`Retry-After`. Los límites oficiales deben revisarse antes de ejecutar consultas
masivas porque pueden cambiar.

## Estructura principal

```text
lab08/
├── clientes/
├── evidencias/
├── notebooks/
│   └── consolidado.ipynb
├── scripts/
├── tests/
├── bitacora.md
├── pyproject.toml
└── README.md
```

## Instalación

Desde la raíz del repositorio:

```bash
conda activate cdb

python -m pip install \
  -e './lab08[dev,notebooks]'

python -m pip check
```

El proyecto requiere Python 3.12 o posterior.

## Obtener los datos

Los datos crudos y procesados no se incluyen en Git. Para regenerarlos:

```bash
cd ~/EE_CDB/lab08

python scripts/descargar_crudos.py
python scripts/descargar_pubmed_resumen.py
python scripts/validar_registros.py
python scripts/consolidar_datos.py
```

Las respuestas se guardan primero en `data/raw/<fuente>/`. Cada respuesta
genera un archivo con los bytes recibidos y un `.metadata.json` con fecha UTC,
URL, parámetros, código HTTP, encabezados, tamaño, hash SHA-256 e indicador de
caché. Los parámetros sensibles se redactan antes de guardar los metadatos.

Los resultados validados y normalizados se escriben en `data/processed/`:

```text
validation_report.json
analysis_summary.json
clinicaltrials.parquet
pubmed.parquet
openfda.parquet
```

Todo `data/` está excluido mediante `.gitignore`.

## Política de reintentos

| Código | ¿Reintentar? | Justificación |
|---:|:---:|---|
| 400 | No | La solicitud está mal formada y repetirla no la corrige |
| 401 | No | Requiere corregir autenticación o credenciales |
| 404 | No | El recurso no existe |
| 429 | Sí | Es una limitación temporal; se respeta `Retry-After` |
| 500 | Sí | Puede representar un fallo transitorio del servidor |
| 503 | Sí | El servicio puede estar temporalmente no disponible |

La política solo se aplica a `GET`, `HEAD` y `OPTIONS`. Los métodos no
idempotentes no se reintentan automáticamente.

## Paginación y memoria

La función `iterar_estudios()` recuperó 300 registros de ClinicalTrials.gov sin
acumular todas las páginas simultáneamente.

| Implementación | Pico de memoria |
|---|---:|
| Generador | 27.66 MiB |
| Lista | 31.39 MiB |

El generador redujo el pico en 3.73 MiB, equivalente a 11.89% en esta ejecución.

## Validación

Se definieron `ClinicalTrialRecord`, `PubMedRecord` y `OpenFDAEvent`. Las reglas
incluyen inscripción mayor o igual a cero, fechas coherentes, estados conocidos,
identificadores válidos, textos y listas obligatorias no vacíos, y edad entre 0
y 130 años.

| Fuente | Recibidos | Válidos | Descartados |
|---|---:|---:|---:|
| ClinicalTrials.gov | 3 | 3 | 0 |
| PubMed | 3 | 3 | 0 |
| openFDA | 3 | 3 | 0 |
| **Total** | **9** | **9** | **0** |

Tres controles malformados fueron rechazados correctamente por inscripción
ausente, título vacío y lista de reacciones vacía.

## Consolidación y análisis

Los nueve registros válidos se normalizaron con `pd.json_normalize` y se
guardaron en tres archivos Parquet. En la muestra no hubo ensayos activos,
`Pyrexia` apareció en dos reportes de openFDA y los tres artículos de PubMed
correspondieron a 2026.

Estos resultados demuestran el funcionamiento del pipeline. La muestra es
demasiado pequeña para realizar inferencias clínicas, epidemiológicas o de
farmacovigilancia.

El análisis reproducible está en `notebooks/consolidado.ipynb`. Para regenerarlo:

```bash
python scripts/crear_notebook.py

jupyter nbconvert \
  --to notebook \
  --execute \
  --inplace \
  notebooks/consolidado.ipynb
```

## Pruebas sin conexión

La suite utiliza `responses` para simular las respuestas HTTP. Una fixture
global bloquea además cualquier llamada a `socket.socket.connect`.

```bash
cd ~/EE_CDB/lab08
python -m pytest -q tests
```

Se cubren 200, 429 seguido de 200, 500 persistente, 503, 400, 401 y 404 sin
reintento, caché, conservación del crudo y campos obligatorios ausentes.

Evidencia obtenida con el Wi-Fi apagado:

```text
Wi-Fi Power (en0): Off
24 passed in 0.28s
```

## Métricas de cortesía

| Métrica | Total |
|---|---:|
| Solicitudes reales | 13 |
| Respuestas desde caché | 6 |
| Solicitudes lógicas resueltas | 19 |
| Proporción resuelta desde caché | 31.58% |

Mil primeras ejecuciones simultáneas podrían generar 13,000 solicitudes reales
y ejercer presión innecesaria. La caché reduce repeticiones, pero también se
necesitan límites de tasa, pausas y ejecuciones escalonadas.

## Llaves y secretos

Las consultas del ejemplo funcionan sin llave. No deben añadirse al repositorio
llaves, tokens, archivos `.env`, datos crudos ni bases de caché.

```bash
git grep -n -I \
  -E '(api[_-]?key|access[_-]?token|secret)[[:space:]]*='
```

## Extensión prevista: genes de interés

La siguiente ampliación parametrizará consultas como:

```text
GENE AND gastric cancer
GENE AND gastric cancer AND prognosis
GENE AND gastric cancer AND survival
GENE AND gastric cancer AND methylation
GENE AND gastric cancer AND epigenetic regulation
GENE AND gastric cancer AND H3K27ac
GENE AND gastric cancer AND H3K4me3
```

Los resultados conservarán la estrategia del laboratorio: respuesta cruda,
fecha y parámetros, validación, deduplicación por identificador y tablas
normalizadas. La presencia de un artículo no demuestra por sí misma capacidad
pronóstica ni regulación epigenética; esas afirmaciones requieren revisión y
evaluación crítica de la evidencia.

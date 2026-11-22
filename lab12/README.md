# Laboratorio 12 — Primeros pasos en OMOP CDM

## Objetivo

Conversión de una cohorte sintética de Synthea a OMOP CDM 5.4, evaluación de
la calidad del mapeo y exploración de conceptos estándar, códigos de origen y
periodos de observación.

La base DuckDB y los vocabularios no se incluyen en Git debido a su tamaño. El
proceso de construcción y las consultas están documentados en esta entrega.

## Ruta seleccionada

Se utilizó **ETL-Synthea de OHDSI** porque proporciona reglas de transformación
reproducibles y conserva el modelo OMOP CDM, en lugar de construir manualmente
cada tabla.

Los datos se generaron con Synthea `v3.4.0-18-ga07a65555`. Se comprobó la
compatibilidad estructural de las 18 tablas CSV con la implementación para
Synthea 3.3.0.

## Software

- OMOP CDM 5.4
- ETLSyntheaBuilder 2.1
- CommonDataModel 1.1.0
- DatabaseConnector 7.1.0
- SqlRender 1.19.4
- DuckDB para R 1.5.0
- DuckDB para Python 2.0.0
- R 4.4.0
- Java 17.0.18
- Python 3.12

## Estructura

```text
lab12/
├── README.md
├── consultas_omop.sql
├── diagrama_er.md
├── reporte_calidad.md
├── scripts/
│   ├── 01_convertir_omop.R
│   ├── 01_ejecutar_etl.sh
│   ├── 02_reparar_vocabulario_eventos.R
│   ├── 03_corregir_datetime_eventos.R
│   ├── 04_cargar_eventos_compatibles.R
│   ├── 04_cargar_eventos_compatibles.sh
│   ├── 05_generar_analisis.py
│   ├── 06_comparar_eunomia.py
│   └── 07_validar_publicar.sh
└── evidencias/
    ├── analisis/
    ├── sql_eventos_compatibles/
    └── registros de ejecución
```

## Flujo reproducible

Desde la raíz del repositorio:

```bash
conda activate cdb
export JAVA_HOME="/opt/anaconda3/envs/cdb/lib/jvm"

./lab12/scripts/01_ejecutar_etl.sh
./lab12/scripts/02_reparar_vocabulario_eventos.sh
./lab12/scripts/04_cargar_eventos_compatibles.sh
python lab12/scripts/05_generar_analisis.py
python lab12/scripts/06_comparar_eunomia.py
```

Los CSV de Synthea deben estar en `lab10/data/raw/synthea_5000/csv/` y los
vocabularios de ATHENA en `lab12/data/raw/athena/`.

## Resultados principales

- Personas: 5,745
- Periodos de observación: 5,745
- Visitas: 320,853
- Condiciones: 92,084
- Exposiciones a medicamentos: 280,617
- Mediciones: 3,111,032
- Observaciones: 1,596,434
- Procedimientos: 385,657
- Conceptos cargados: 2,026,160
- Conceptos estándar: 846,202

El porcentaje de `concept_id = 0` fue 0% en Condition, Drug, Measurement,
Observation, Procedure y Visit.

La mediana de observación fue de 11,516 días. Al aplicar
`OBSERVATION_PERIOD`, 699 condiciones quedaron fuera de la ventana, equivalentes
al 0.7591%.

## Estándar frente a origen

La condición más frecuente fue Gingivitis (`concept_id = 4281516`), con 10,343
eventos. El código de origen más frecuente fue `66383009` y produjo el mismo
conteo porque esta condición apareció con un solo código fuente en la cohorte.

## Comparación con Eunomia

| Métrica | Synthea propio | Eunomia |
|---|---:|---:|
| Personas | 5,745 | 2,694 |
| Mediana de observación, días | 11,516 | 13,868 |
| Visitas | 320,853 | 1,037 |
| Media de visitas por persona | 55.8491 | 0.3849 |
| Diagnóstico más frecuente | Gingivitis | Viral sinusitis |

La base propia respeta la estructura OMOP, pero presenta una utilización de
servicios y una distribución clínica diferentes de GiBleed.

## Simplificaciones documentadas

- Los campos `*_datetime` afectados quedaron nulos porque la fuente proporciona
  fechas sin una hora clínicamente verificable.
- `condition_era`, `drug_era`, `device_exposure`, `death`,
  `payer_plan_period` y `cost` no se materializaron por incompatibilidades
  específicas con DuckDB y porque no se requieren para las consultas.
- La base DuckDB, los CSV de Synthea, los vocabularios y la copia local de
  Eunomia permanecen fuera de Git.

## Entregables

- `consultas_omop.sql`: consultas comentadas.
- `diagrama_er.md`: modelo entidad-relación y comparación con OMOP 5.4.
- `reporte_calidad.md`: resultados e interpretación.
- `evidencias/analisis/`: tablas CSV resultantes.
- `scripts/`: construcción y reproducción del análisis.

# Laboratorio 10 — SQL Fundamentals

Base clínica local generada con Synthea y consultada con DuckDB.

## Elección del motor

Se eligió **DuckDB** porque el análisis se realiza localmente y no
requiere conexiones simultáneas de otros usuarios.

DuckDB permite consultar tablas analíticas grandes sin instalar ni
administrar un servidor, lo que simplifica la reproducción.

PostgreSQL se aproxima más a una infraestructura institucional como
OHDSI, pero DuckDB es suficiente para este volumen y para Jupyter.

## Generación reproducible

La cohorte se generó con una semilla fija mediante:

```bash
java \
  -jar tools/synthea/synthea-with-dependencies.jar \
  -s 20261102 \
  -p 5000 \
  --exporter.baseDirectory=lab10/data/raw/synthea_5000 \
  --exporter.csv.export=true \
  --exporter.fhir.export=false \
  Massachusetts
```

Synthea produjo 5,745 pacientes: 5,000 vivos y 745 fallecidos.

## Conteos

| Tabla | Filas |
|---|---:|
| patients | 5,745 |
| encounters | 353,175 |
| conditions | 204,995 |
| medications | 280,594 |
| observations | 4,534,043 |

## Carga reproducible

La carga está definida en `sql/carga.sql` y se ejecuta mediante
`scripts/cargar_duckdb.py`.

Las fechas se almacenan como `DATE` o `TIMESTAMPTZ`, no como texto.
Los CSV y la base `clinical.duckdb` están excluidos de Git.

## Esquema de la base

La base contiene cinco tablas relacionadas mediante `patient_id` y
`encounter_id`.

El diagrama entidad-relación y las llaves están documentados en:

- `docs/diagrama_er.md`
- `docs/llaves.md`

## Reproducción

1. Generar los CSV de Synthea con el comando documentado anteriormente.
2. Ejecutar `python scripts/cargar_duckdb.py`.
3. Ejecutar `python scripts/ejecutar_consultas.py`.
4. Abrir o ejecutar `notebooks/laboratorio10.ipynb`.

La carga puede repetirse sin duplicar registros.

## Resultados principales

- Pacientes: 5,745.
- Encuentros: 353,175.
- Condiciones: 204,995.
- Medicamentos: 280,594.
- Observaciones: 4,534,043.
- Identificadores de paciente duplicados: 0.
- Encuentros anteriores al nacimiento: 0.
- Encuentros huérfanos: 0.
- Observaciones con valor nulo: 0 %.
- El join incorrecto aumentó las filas en 19.96 %.
- El filtro del `LEFT JOIN` en `WHERE` excluyó 1,680 pacientes.
- La consulta optimizada conservó el resultado de 143 pacientes.
- Las tres comparaciones SQL–pandas produjeron resultados equivalentes.

## Entregables

- `sql/carga.sql`: creación y carga reproducible.
- `sql/consultas.sql`: quince preguntas clínicas comentadas.
- `sql/auditoria.sql`: controles de calidad.
- `docs/diagrama_er.md`: diagrama entidad-relación.
- `notebooks/laboratorio10.ipynb`: notebook ejecutado.
- `evidencias/`: resultados, planes y tiempos reales.

Los CSV de Synthea y `clinical.duckdb` no se incluyen en Git.

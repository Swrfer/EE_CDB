# Laboratorio 13 — Exposición a fármacos y laboratorios

## Objetivo

Caracterizar `DRUG_EXPOSURE` y `MEASUREMENT`, construir eras de tratamiento,
estimar PDC, revisar unidades y plausibilidad, y obtener el valor de laboratorio
más próximo a una fecha índice.

## Reproducción

Desde la raíz del repositorio y con el ambiente `cdb` activo:

```bash
python lab13/scripts/01_generar_lab13.py
```

La base de entrada es:

```text
lab12/data/omop/synthea_omop_cdm54.duckdb
```

El script crea las tablas `results.drug_era_lisinopril`,
`results.pdc_lisinopril` y `results.weight_unit_normalized` dentro de la base
local. La base DuckDB permanece fuera de Git.

## Entregables

- `farmacoepi.sql`: consultas comentadas de las actividades 1–10.
- `notebooks/analisis_farmacoepi.ipynb`: recorrido reproducible de resultados.
- `reporte_calidad.md`: interpretación, supuestos, fuentes y limitaciones.
- `evidencias/analisis/`: tablas CSV.
- `figuras/`: distribuciones de `days_supply`, PDC, unidades y disponibilidad basal.

## Decisiones principales

- Ingrediente para eras y PDC: lisinopril (`concept_id = 1308216`).
- Gap permisible para `DRUG_ERA`: 30 días.
- Seguimiento para PDC: 365 días completos dentro de `OBSERVATION_PERIOD`.
- Unidad canónica de peso: kg; `1 lb = 0.45359237 kg`.
- Plausibilidad: presión sistólica, glucosa y peso en adultos.
- Fecha índice: primera condición de cada persona.
- Laboratorio basal: glucosa dentro de ±90 días.

## Fuentes metodológicas

- [OMOP CDM v5.4](https://ohdsi.github.io/CommonDataModel/cdm54.html)
- [PQA: Proportion of Days Covered](https://www.pqa.org/measures/measures-resources/)
- [Statistical considerations for medication adherence research](https://pmc.ncbi.nlm.nih.gov/articles/PMC7886011/)
- [NIST Handbook 44](https://nvlpubs.nist.gov/nistpubs/hb/2026/NIST.HB.44-2026.pdf)
- [Thomas et al. 2016: rangos de plausibilidad](https://doi.org/10.1155/2016/4364761)

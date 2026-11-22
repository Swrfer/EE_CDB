# Laboratorio 14 — Construir y defender un concept set

## Propósito

Definir una condición con vocabularios estándar, traducir códigos ICD-10-CM mediante `Maps to`, construir tres versiones reproducibles del concept set y cuantificar cómo cambian los pacientes capturados.

## Condición seleccionada

Se eligió **diabetes mellitus tipo 2 activa en población general adulta**. El cáncer gástrico se descartó porque solo tenía 2 pacientes; diabetes tipo 2 tiene 457 y permite comparar definiciones sin quedar sin cohorte.

## Resultado principal

- A — estricta: 1 concepto, 457 pacientes.
- B — amplia: 15 conceptos, 457 pacientes.
- C — razonada: 12 conceptos, 457 pacientes.
- Definición final: **C — razonada**, excluyendo embarazo y remisión.

La igualdad de pacientes se debe a que esta base sintética solo usa el concepto semilla en `CONDITION_OCCURRENCE`; la diferencia semántica sí queda documentada.

## Reproducibilidad

Desde la raíz del repositorio y con el ambiente `cdb` activo:

```bash
python lab14/scripts/01_generar_lab14.py
```

Entrada local no versionada: `lab12/data/omop/synthea_omop_cdm54.duckdb`.

## Entregables

- `concept_set.sql`: traducción ICD-10-CM y versiones A, B y C.
- `justificacion_concept_set.md`: decisiones clínicas y discusión sensibilidad/VPP.
- `figuras/impacto_pacientes.png`: impacto en pacientes distintos.
- `notebooks/analisis_concept_set.ipynb`: recorrido de resultados.
- `evidencias/analisis/*.csv`: resultados verificables.

## Nota sobre la revisión de 20 conceptos

La jerarquía disponible contiene solo 14 descendientes; se revisaron todos. No se duplicaron conceptos para alcanzar artificialmente 20.

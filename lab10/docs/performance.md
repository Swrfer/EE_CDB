# Medición de rendimiento

Se utilizó la pregunta clínica: **pacientes con diabetes sin ninguna
medición de HbA1c**.

## Cambio realizado

La consulta original une `patients`, `conditions` y `observations` antes de
resolver el resultado.

La versión optimizada:

1. filtra primero las condiciones relacionadas con diabetes;
2. filtra primero las observaciones con código HbA1c `4548-4`;
3. proyecta únicamente `patient_id`;
4. utiliza un `ANTI JOIN`.

## Resultados

| Versión | Resultado | Mediana | Mínimo | Máximo |
|---|---:|---:|---:|---:|
| Original | 143 | 3.751 ms | 3.488 ms | 4.308 ms |
| Optimizada | 143 | 3.321 ms | 3.160 ms | 4.493 ms |

La razón entre las medianas fue **1.130**.

La versión optimizada fue más rápida porque filtró temprano y conservó solamente patient_id.

DuckDB es un motor columnar y su optimizador puede aplicar automáticamente
proyección de columnas y filtros tempranos. Por ello, una reescritura no
siempre produce una diferencia grande, especialmente cuando la base ya está
en la caché del sistema.

Los planes completos de `EXPLAIN ANALYZE` se conservaron en:

- `evidencias/10_plan_original.txt`
- `evidencias/10_plan_optimized.txt`

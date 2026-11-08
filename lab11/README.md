# Laboratorio 11 — Analítica longitudinal

Análisis temporal de la base clínica Synthea creada en el Laboratorio 10,
utilizando DuckDB, CTEs y funciones de ventana.

## Punto de partida

Se reutiliza `lab10/clinical.duckdb`, que contiene:

| Tabla | Filas |
|---|---:|
| patients | 5,745 |
| encounters | 353,175 |
| conditions | 204,995 |
| medications | 280,594 |
| observations | 4,534,043 |

La base y los CSV permanecen excluidos de Git.

## 1. De consultas anidadas a CTEs

Se reescribieron dos consultas del Laboratorio 10:

- resumen de encuentros por paciente;
- pacientes con diabetes sin mediciones de HbA1c.

Las versiones anidadadas y las versiones con CTEs produjeron resultados
idénticos. Las CTEs separan la selección de pacientes, la agregación y el
resultado final, lo que mejora la lectura y permite validar cada etapa.

## 2. Depuración por partes

La consulta de diabetes sin HbA1c se inspeccionó por etapas:

| Etapa | Filas |
|---|---:|
| Pacientes con diabetes | 2,477 |
| Pacientes con HbA1c | 2,462 |
| Diabetes sin HbA1c | 143 |

Esta separación permite localizar errores en una etapa concreta sin ejecutar
mentalmente toda una consulta anidada.

## 3. Primera y última visita

Las soluciones con `GROUP BY` y funciones de ventana devolvieron los mismos
5,745 pacientes, sin diferencias.

Para obtener una sola fila por paciente, `GROUP BY` es más corto. Las ventanas
son preferibles cuando se necesita conservar cada encuentro junto con el
resumen longitudinal. El frame de `LAST_VALUE` se declaró hasta
`UNBOUNDED FOLLOWING` para incluir la última visita real del paciente.

## 4. Intervalos entre visitas

Se analizaron 353,175 visitas. La primera visita de cada paciente no tiene una
visita anterior, por lo que `LAG` devuelve correctamente 5,745 valores nulos.

Los nulos se excluyeron de la mediana, porque sustituirlos por cero inventaría
un intervalo inexistente. Se obtuvieron 347,430 intervalos comparables y una
mediana de 14 días.

## 5. Readmisiones a 30 días

Se definió readmisión como un nuevo encuentro `inpatient` que comienza desde
el momento del alta y hasta 30 días después, incluyendo el día 30.

Se cuentan todas las transiciones elegibles, no solamente la primera por
paciente. Una alta es elegible únicamente si existen al menos 30 días de
seguimiento posteriores en el conjunto de datos.

| Altas elegibles | Readmisiones | Tasa |
|---:|---:|---:|
| 6,771 | 751 | 11.0914 % |

La comparación utiliza timestamps completos. Esto evita clasificar como
readmisión una hospitalización que comenzó minutos antes del alta, aunque
ambos eventos hayan ocurrido el mismo día.

## 6. Episodios de tratamiento

Se eligió lisinopril, código `314076`, por su frecuencia y cobertura:
25,324 registros en 927 pacientes.

Los episodios se construyeron con el patrón gaps and islands, comparando gaps
de 30, 60 y 90 días.

| Gap | Episodios | Pacientes | Duración mediana |
|---:|---:|---:|---:|
| 30 días | 927 | 927 | 3,655 días |
| 60 días | 927 | 927 | 3,655 días |
| 90 días | 927 | 927 | 3,655 días |

Los tres gaps produjeron el mismo resultado porque los registros consecutivos
se solapan o están separados por no más de 30 días. En otros datos, un gap
mayor uniría periodos separados y reduciría el número de episodios.

## 7. Deduplicación con ROW_NUMBER

Las 4,534,043 observaciones originales se redujeron a 367,748 combinaciones
únicas de paciente y analito, conservando la medición más reciente. Se
eliminaron 4,166,295 registros históricos de la tabla deduplicada.

El filtro `rn = 1` se aplica fuera de la CTE porque `WHERE` se evalúa antes que
las funciones de ventana; el alias `rn` todavía no existe en el mismo nivel
donde se calcula.

## 8. Media acumulada y media móvil

Se seleccionó un paciente con 339 mediciones de HbA1c y 16 valores distintos.

La media acumulada utiliza todas las observaciones desde la primera medición.
La media móvil utiliza solamente la fila actual y las dos anteriores mediante
`ROWS BETWEEN 2 PRECEDING AND CURRENT ROW`.

Las columnas difirieron en 336 filas, con una diferencia máxima de 2.583117
puntos porcentuales.

## 9. Valor basal próximo a la fecha índice

La fecha índice se definió como el primer diagnóstico de diabetes. Se buscó la
HbA1c más cercana dentro de los 90 días anteriores, incluyendo el mismo día.

No se permiten mediciones posteriores porque podrían incorporar información
que todavía no estaba disponible en la fecha índice y producir fuga de
información.

De 2,477 pacientes con diabetes, 502 tuvieron una HbA1c basal elegible:
cobertura de 20.2665 %. No se incluyó ningún valor posterior.

## 10. Ventana contra self-join

Ambas estrategias identificaron 347,430 intervalos comparables y una mediana
de 14 días.

| Versión | Tiempo mediano |
|---|---:|
| `LAG` | 45.579 ms |
| Self-join | 528.544 ms |

El self-join fue 11.596 veces más lento. `LAG` es además más legible porque
representa directamente el concepto de visita anterior y evita comparar cada
encuentro con múltiples encuentros del mismo paciente.

Los planes completos de `EXPLAIN ANALYZE` se conservaron en `evidencias/`.

## Reproducción

1. Mantener disponible `lab10/clinical.duckdb`.
2. Ejecutar las consultas de `sql/analitica_longitudinal.sql`.
3. Abrir o ejecutar `notebooks/laboratorio11.ipynb`.
4. Revisar los resultados y planes guardados en `evidencias/`.

## Entregables

- `sql/analitica_longitudinal.sql`: consultas comentadas.
- `notebooks/laboratorio11.ipynb`: histogramas y comparaciones.
- `evidencias/`: tablas, muestras, planes y tiempos reales.

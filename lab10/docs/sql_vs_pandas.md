# Comparación entre SQL y pandas

Se reprodujeron tres de las quince preguntas clínicas mediante ambos
métodos. Cada implementación se ejecutó cinco veces y se reportó la
mediana.

| Consulta | Líneas SQL | Líneas pandas | Tiempo SQL | Tiempo pandas | Coinciden |
|---|---:|---:|---:|---:|---:|
| query_01 | 9 | 6 | 0.523 ms | 1.025 ms | Sí |
| query_02 | 10 | 10 | 0.999 ms | 1.420 ms | Sí |
| query_05 | 6 | 12 | 9.368 ms | 26.268 ms | Sí |

La lectura de columnas desde DuckDB se incluyó en el tiempo de pandas,
porque representa el costo real de trasladar los datos a memoria antes de
procesarlos.

## Decisión

Para este volumen y para preguntas basadas en filtros, agrupaciones y joins,
usaría **DuckDB**, porque expresa las operaciones de manera declarativa y
evita trasladar tablas grandes a la memoria de pandas.

Usaría **pandas** para trabajar con resultados ya resumidos, preparar
visualizaciones o alimentar modelos estadísticos. Cambiaría de opinión si
los datos derivados fueran pequeños y el análisis requiriera muchas
transformaciones propias del ecosistema científico de Python.

# Experimento: el join que multiplica

Al unir `encounters` directamente con `conditions`, cada encuentro se repite una vez por cada diagnóstico asociado.

| Resultado | Filas | Costo medio |
|---|---:|---:|
| Correcto | 353,175 | 111.8689 |
| Inflado | 423,684 | 114.3003 |
| Corregido | 353,175 | 111.8689 |

El join incrementó el número de filas en 19.96%.

El promedio inflado parece plausible, pero asigna más peso a los encuentros que tienen múltiples diagnósticos.

La corrección agrupa por `encounter_id` antes de calcular el promedio. Por ello recupera el conteo y el promedio originales.

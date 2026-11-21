# Experimento: la trampa del LEFT JOIN

Se buscaron encuentros cuya clase es `emergency`.

| Posición del filtro | Filas del join | Pacientes conservados |
|---|---:|---:|
| `WHERE` | 12,945 | 4,065 |
| `ON` | 14,625 | 5,745 |

El filtro colocado en `WHERE` excluyó a
**1,680 pacientes** que no tenían encuentros de urgencias.

Esto ocurre porque, después del `LEFT JOIN`, esos pacientes tienen valores
`NULL` en las columnas de `encounters`. La condición del `WHERE` no se cumple
para esas filas y el resultado se comporta como un `INNER JOIN`.

Al mover la condición al `ON`, solamente se restringen las coincidencias de
`encounters`. Los 5,745 pacientes de la tabla izquierda se
conservan, incluso cuando no tienen encuentros de urgencias.

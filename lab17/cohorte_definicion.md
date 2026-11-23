# Definición de la cohorte

## Pregunta

¿Cuál es la trayectoria de función renal durante la primera era continua de
lisinopril en adultos con diabetes mellitus tipo 2 y evaluación basal de presión
arterial, identificados como nuevos usuarios en una base OMOP sintética?

## PICOT

| Componente | Definición |
| --- | --- |
| **Población** | Personas de 18 años o más con T2DM registrado dentro del periodo continuo de observación y antes o en la fecha índice, con al menos dos fechas de presión arterial durante los 365 días basales. |
| **Exposición** | Primera exposición observada a un producto descendiente de lisinopril, excluyendo combinaciones que también contienen HCTZ. |
| **Comparador** | No se utiliza comparador en esta cohorte descriptiva; un análisis causal posterior requeriría un comparador activo. |
| **Desenlace** | Cambio posterior en función renal, especialmente eGFR o creatinina; este laboratorio construye la población y el tiempo en riesgo, no estima aún el efecto. |
| **Tiempo** | 365 días continuos de observación y lavado antes del índice; seguimiento desde el índice hasta el fin de la primera era continua, permitiendo gaps de hasta 30 días y censurando al final del periodo de observación. |

## Evento inicial

La fecha índice es la primera exposición observada a lisinopril por persona. Se
excluyen combinaciones con HCTZ para atribuir la exposición a lisinopril sin ese
coprescriptor. El resultado contiene exactamente una fila por persona.

## Criterios de inclusión

1. **Observación y lavado:** al menos 365 días continuos antes del índice dentro
   del mismo `OBSERVATION_PERIOD`, y ninguna exposición a lisinopril en
   `[-365,-1]`. Un periodo de 180 días ofrecería menos certeza de que el usuario
   es realmente nuevo y aumentaría la clasificación errónea de prevalentes.
2. **T2DM previo:** al menos una ocurrencia desde el inicio del periodo continuo
   hasta el índice. No se limita a 365 días porque T2DM es crónica: la auditoría
   mostró 17 personas con inicio durante el último año frente a 179 con un
   diagnóstico previamente observado.
3. **Evaluación de presión arterial:** al menos dos fechas distintas con presión
   sistólica o diastólica en `[-365,0]`. Dos fechas reducen la dependencia de una
   medición aislada; exigir tres habría dejado solo 10 personas antes de las
   exclusiones.

## Criterios de exclusión

1. Edad menor de 18 años en la fecha índice, calculada con fecha de nacimiento.
2. Embarazo registrado en `[-365,0]`, porque lisinopril está contraindicado y
   representa un contexto clínico diferente.

## Estrategia de salida

Las exposiciones posteriores se agrupan mediante *gaps and islands*. Un intervalo
de 30 días o menos mantiene la misma era; un gap mayor inicia otra. La salida es
el mínimo entre el final de la primera era y el final de `OBSERVATION_PERIOD`.

## Censura

Se censura al final del periodo de observación si ocurre antes que la salida por
exposición. No se infieren desenlaces ni exposición más allá de los datos.

## Limitación principal

`OBSERVATION_PERIOD` cubre a todas las personas y tiene una mediana de 11,516
días; el filtro de 365 días no elimina registros. Esto es coherente con la
historia sintética casi vitalicia de Synthea, pero es menos realista que una base
asistencial con altas, bajas y pérdidas de cobertura.

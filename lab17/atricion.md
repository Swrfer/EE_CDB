# Tabla de atrición

| step | criterion | n | lost_at_step | percent_initial_remaining | percent_lost_at_step |
| --- | --- | --- | --- | --- | --- |
| 1 | Evento inicial: primera exposición | 1014 | 0 | 100.0 | 0.0 |
| 2 | + 365 días de observación | 1014 | 0 | 100.0 | 0.0 |
| 3 | + lavado de 365 días | 1014 | 0 | 100.0 | 0.0 |
| 4 | + T2DM observado antes del índice | 179 | 835 | 17.65 | 82.35 |
| 5 | + >=2 fechas con presión arterial | 22 | 157 | 2.17 | 87.71 |
| 6 | - menores de 18 años | 22 | 0 | 2.17 | 0.0 |
| 7 | - embarazo durante los 365 días basales | 22 | 0 | 2.17 | 0.0 |

## Interpretación

La cohorte pasó de **1014** nuevos usuarios potenciales a
**22** personas finales. La mayor pérdida absoluta ocurrió
en **+ T2DM observado antes del índice**, con **835**
personas menos. Es un costo justificable porque la pregunta se limita a personas
con diabetes previamente observada y evita atribuirles esa condición usando
información posterior.

El requisito de dos fechas de presión redujo la población de 179 a 22. Aunque es
el filtro proporcionalmente más exigente, conserva evidencia basal repetida y
cumple el objetivo de caracterizar atención previa. La precisión será limitada;
no se ocultó esta consecuencia ni se flexibilizó el criterio después de ver N.

La observación previa y el lavado se reportan por separado. Ambos eliminaron cero
personas porque Synthea produjo periodos casi vitalicios y el evento índice se
definió como la primera exposición observada.

# Criterios para interpretar la comparación

Este documento establece cómo revisar las salidas generadas. No contiene
estimaciones de ejecuciones anteriores.

## 1. Distinguir los diseños de evaluación

| Evaluación | Qué permite examinar | Límite |
|---|---|---|
| TCGA aparente | Ajuste del modelo final en sus pacientes de desarrollo | Optimismo por reutilización de los datos |
| CV RSF | Selección de panel y parámetros mediante folds | El mejor valor participó en la elección del modelo |
| RSF OOB | Bosque fijo usando árboles que excluyeron a cada paciente | Condicionado al panel y parámetros previamente elegidos |
| ACRG global | Aplicación externa de las dos firmas | Transporte entre tecnologías y evaluación exploratoria |
| I–II | Comportamiento en un subgrupo | Menos pacientes/eventos e incertidumbre adicional |

No interpretar una diferencia entre estas evaluaciones como si todas
estimaran el rendimiento con el mismo diseño.

## 2. Revisar las firmas y las métricas

Verificar primero la coincidencia LASSO con la referencia y la cobertura de
genes en ambas cohortes. RSF se define por panel y bosque, no solo por la lista
de genes o su importancia. No comparar importancia RSF con coeficiente LASSO
como si fueran la misma medida.

La AUC y el C de Harrell utilizan el marcador continuo. La AUC al año discrimina
el estado hasta ese horizonte; el C utiliza el seguimiento completo. Ninguno
demuestra calibración o beneficio clínico.

Kaplan–Meier describe grupos definidos por mediana. Revisar tamaños de grupos,
pacientes en riesgo y empates antes de interpretar p de log-rank. Una p menor
no establece que una firma prediga mejor que la otra.

## 3. Examinar optimismo y transporte

La comparación aparente/OOB evalúa optimismo interno del RSF sin cambiar la
firma. No estima por sí sola el impacto de cambiar de plataforma.

Para ACRG, revisar rangos de expresión por gen, proporción de valores fuera del
rango TCGA y cantidad de puntajes distintos. Cobertura completa de genes no
garantiza unidades comparables ni variabilidad suficiente de predicción.
La estandarización del puntaje LASSO tampoco armoniza la expresión por gen.

## 4. Presentar conclusiones acotadas

La comparación principal corresponde a ACRG global, acompañada de AUC, C,
incertidumbre y limitaciones de aplicación. Las diferencias de AUC se describen
sin atribuir significación estadística a una diferencia no contrastada formalmente.

La conclusión debe referirse a estas firmas, cohortes y procesamiento.
No generalizar superioridad de un algoritmo ni proponer un umbral clínico a
partir de la mediana de una cohorte. Mantener visibles advertencias, controles
OOB pendientes y subgrupos con soporte temporal limitado.

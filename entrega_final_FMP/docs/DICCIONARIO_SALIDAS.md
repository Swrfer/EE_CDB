# Diccionario de salidas principales

| Campo | Significado y unidad |
|---|---|
| cohort | TCGA: desarrollo; ACRG: evaluación externa exploratoria |
| population | Todos: cohorte global; I_II: estadios I y II, excluye estadio desconocido |
| model | LASSO-Cox o RSF |
| evaluation | apparent_training o exploratory_external |
| OS.time_years | Seguimiento de supervivencia global en años |
| OS.event | 1: muerte; 0: censura |
| risk_score (LASSO TCGA) | Suma de expresión VST por coeficiente penalizado |
| risk_score (LASSO ACRG) | scale(suma de señal RMA log10 por coeficiente); escala de cohorte |
| risk_score (RSF) | Suma del riesgo acumulado del bosque; sin unidad de probabilidad |
| Gene | Símbolo del gen; no identificador de paciente |
| Coefficient | Coeficiente penalizado LASSO por unidad VST; no HR univariado |
| permutation_importance | Importancia OOB por permutación del bosque de selección, entrenado solo con TCGA |
| final_permutation_importance | Importancia de ese gen dentro del panel final RSF |
| rank | Orden de importancia en el bosque de selección |
| panel_size | Número de genes del panel candidato RSF |
| min_node_size | Tamaño mínimo de nodo usado en el ajuste RSF |
| C_Harrell_mean / SD | Media y desviación entre folds para elegir parámetros; no intervalo de confianza |
| cutoff | Mediana del puntaje según la regla de cohorte/subgrupo documentada |
| low_n / high_n | Pacientes con puntaje menor / mayor o igual al corte |
| logrank_p | Comparación descriptiva de curvas KM; no mide discriminación continua |
| C_Harrell_frozen | Concordancia del marcador fijo; mayor puntaje predice menor supervivencia |
| C_Harrell_SE | Error estándar del C de Harrell; no intervalo bootstrap |
| horizon_years | Horizonte ROC: un año |
| AUC | AUC acumulativa/dinámica al año de timeROC, escala 0–1 |
| lower_95 / upper_95 | Límites del IC95% de AUC, escala 0–1, cuando son estimables |
| deaths_by_horizon | Muertes conocidas hasta el horizonte inclusive |
| observed_beyond_horizon | Pacientes con seguimiento posterior al horizonte |
| censored_by_horizon | Censurados antes o en el horizonte; no controles de estado conocido |
| fraction_ACRG_below/above_TCGA | Fracción de valores externos fuera del rango de entrenamiento de un gen |
| distinct_scores | Número de puntajes diferentes; ayuda a detectar predicciones constantes |
| status | OK, soporte insuficiente, panel incompleto u otra razón explícita de no estimación |

Las matrices, los identificadores y los puntajes individuales se guardan únicamente
en data/privados/. Las tablas maestras contienen resultados agregados.

## Comprobación OOB

| Campo | Significado |
|---|---|
| evaluation=OOB_conditional_on_selected_panel | Diagnóstico interno del bosque; selección del panel no independiente |
| C_Harrell | Concordancia del marcador rowSums(CHF), con todo el seguimiento |
| refit | FALSE: no se entrenó ni se modificó el bosque en esta comprobación |
| apparent_minus_OOB | Diferencia descriptiva; no una prueba de significación |
| REVISAR_EMPATES | C recalculado difiere de 1-prediction.error; revisar antes de concluir |

AUC OOB se calcula con timeROC al año e iid=FALSE. No se reporta un IC convencional
para OOB. Los identificadores y puntajes individuales permanecen en data/privados/.

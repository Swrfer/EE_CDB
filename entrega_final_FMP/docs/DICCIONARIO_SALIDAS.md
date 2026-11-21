# Diccionario de archivos y métricas

Los archivos descritos se crean al ejecutar el proyecto. No se distribuyen
resultados previos. Las rutas son relativas a la carpeta del maestro.

## Archivos principales

| Ruta o archivo | Contenido |
|---|---|
| `resultados/tablas/lasso/LASSO_Cox_signature_lambda_min.csv` | Genes, coeficientes penalizados y dirección del puntaje |
| `resultados/tablas/lasso/estado_reproduccion_firma.csv` | Coincidencia con la referencia y tolerancia |
| `resultados/tablas/lasso/comparacion_firma_original.csv` | Comparación por gen entre referencia y ajuste |
| `resultados/tablas/lasso/TCGA_preparacion_resumen.csv` | Filtros, ensayo, dimensiones y eventos TCGA |
| `resultados/tablas/lasso/ACRG_preparacion_resumen.csv` | Preparación y transformación efectivamente aplicada en ACRG |
| `resultados/tablas/lasso/Firma_pronostica_Cox_univariado_por_gen.csv` | Asociaciones Cox univariadas de genes LASSO |
| `resultados/tablas/rsf/RSF_panel_final.csv` | Panel, orden e importancias de selección y finales |
| `resultados/tablas/rsf/RSF_CV_detalle.csv` | Evaluación por fold y configuración |
| `resultados/tablas/rsf/RSF_CV_resumen.csv` | Media y dispersión del C por configuración |
| `resultados/tablas/rsf/RSF_parametros_finales.csv` | Configuración efectiva del bosque |
| `resultados/tablas/rsf/RSF_diagnostico_escala_TCGA_ACRG.csv` | Comparación de rangos de expresión por gen |
| `resultados/tablas/rsf/RSF_diagnostico_puntajes.csv` | Rango, dispersión, puntajes distintos y empates por cohorte |
| `resultados/tablas/comparacion/COMPARACION_MAESTRA_KM_Cindex.csv` | Estratificación y concordancia de las dos firmas |
| `resultados/tablas/comparacion/COMPARACION_MAESTRA_timeROC.csv` | AUC de las dos firmas por cohorte y población |
| `resultados/tablas/oob/RSF_COMPROBACION_OOB_metricas.csv` | Rendimiento aparente y OOB del bosque guardado |
| `resultados/tablas/oob/RSF_COMPROBACION_OOB_diferencias.csv` | Diferencias descriptivas aparente menos OOB |
| `resultados/tablas/oob/RSF_COMPROBACION_OOB_checks.csv` | Verificaciones estructurales, de concordancia y conservación |

Cada bloque LASSO/RSF genera además sus `TABLA_MAESTRA_KM_Cindex.csv` y
`TABLA_MAESTRA_timeROC.csv`, tablas por análisis y cobertura de genes.

## Campos de las tablas

| Campo | Significado |
|---|---|
| `model` | LASSO-Cox o RSF |
| `cohort` | TCGA o ACRG |
| `population` | `Todos` o `I_II` |
| `n`, `events` | Pacientes y muertes durante todo el seguimiento |
| `Gene` | Símbolo del gen |
| `Coefficient` | Coeficiente penalizado LASSO por unidad de expresión |
| `Direction` | Signo de contribución al puntaje; no causalidad |
| `HR`, `lower`, `upper`, `pval` | HR, IC95% y p del Cox univariado |
| `permutation_importance` | Importancia del bosque de selección TCGA |
| `final_permutation_importance` | Importancia dentro del panel final |
| `rank` | Orden de importancia para selección |
| `panel_size`, `min_node_size` | Tamaño del panel y nodo de la configuración candidata |
| `C_Harrell_mean`, `C_Harrell_SD` | Media y desviación entre folds; no IC |
| `cutoff` | Mediana de acuerdo con la regla cohorte/subgrupo |
| `low_n`, `high_n` | Pacientes con puntaje menor y mayor o igual al corte |
| `logrank_p` | Contraste descriptivo de las curvas KM |
| `C_Harrell_frozen`, `C_Harrell` | Concordancia del marcador fijo |
| `C_Harrell_SE` | Error estándar de concordancia; no IC bootstrap |
| `horizon_years` | Horizonte de AUC, un año |
| `AUC`, `lower_95`, `upper_95` | AUC e IC95% cuando es estimable, escala 0–1 |
| `deaths_by_horizon` | Muertes conocidas hasta el horizonte inclusive |
| `observed_beyond_horizon` | Seguimiento posterior al horizonte |
| `censored_by_horizon` | Censurados hasta el horizonte, sin estado conocido en ese momento |
| `distinct_scores`, `median_ties` | Puntajes distintos y empates en la mediana |
| `fraction_ACRG_below_TCGA`, `fraction_ACRG_above_TCGA` | Fracción de valores externos fuera del rango TCGA por gen |
| `apparent_minus_OOB` | Diferencia descriptiva; no prueba de significación |
| `refit` | Si se volvió a ajustar el bosque en la comprobación; se espera `FALSE` |
| `status` | Estado del cálculo o motivo de limitación/no estimación |

`OOB_conditional_on_selected_panel` identifica OOB condicionado a la selección
previa. `REVISAR_EMPATES` identifica una diferencia de concordancia que requiere
revisión; no prueba automáticamente su causa.

## Figuras

`resultados/figuras/` contiene subcarpetas `lasso`, `rsf`, `comparacion` y `oob`.
Se generan PDF y PNG: trayectoria/CV/coeficientes LASSO, forest univariado,
importancia y ajuste RSF, KM y ROC por cohorte/población, ROC comparativas y
ROC aparente frente a OOB. Los KM completos incluyen tabla de riesgo; también
se guardan versiones de solo curva.

## Informes y procedencia

`resultados/docs/` contiene configuración, `sessionInfo`, advertencias,
huellas de entradas, copia del código ejecutado y README de cada bloque.
`ULTIMA_EJECUCION_COMPLETA.csv` informa etapa, acción, fecha UTC y rutas de
salida. Un registro `all` completo debe contener LASSO, RSF y OOB.

Las huellas MD5 de estados RDS sirven para comprobar conservación dentro de una
operación. Sus bytes pueden diferir entre equipos por rutas, configuración o
serialización; una diferencia de huella no implica necesariamente una diferencia
de firma o métricas. El `MANIFEST_SHA256.csv` del ZIP identifica los archivos
distribuidos, no las futuras salidas del análisis.

## Estados locales

| Ruta | Uso |
|---|---|
| `data/privados/lasso/TCGA_modelo_y_entradas.rds` | Matriz y entradas preparadas |
| `data/privados/lasso/FMP_original_replicada_para_comparacion.rds` | Entrada para el bloque RSF |
| `data/privados/rsf/RSF_modelo_final.rds` | Bosque ajustado |
| `data/privados/rsf/RSF_resultados_para_comparacion.rds` | Entrada para la comprobación OOB |
| `data/privados/oob/RSF_OOB_predicciones_y_ROC.rds` | Puntajes y objetos ROC de OOB |

Estos estados contienen datos individuales y no se incluyen en el repositorio
ni en el ZIP limpio. Se generan automáticamente; no requieren exportar objetos
de una sesión manual.

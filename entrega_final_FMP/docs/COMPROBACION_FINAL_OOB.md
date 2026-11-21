# Comprobación OOB sin reentrenamiento

## Objetivo

Comparar el rendimiento aparente del RSF final con el obtenido de sus
predicciones out-of-bag (OOB) guardadas, sin cambiar el panel ni ajustar de
nuevo el bosque durante esta comprobación.

La etapa `all` ya incluye OOB. Los comandos siguientes permiten repetir solo
ese diagnóstico después de disponer del estado RSF completo.

## Entrada

`data/privados/rsf/RSF_resultados_para_comparacion.rds`, generado por `all` o
`rsf`. Debe contener el bosque, CHF OOB, predicciones aparentes y clínica TCGA
alineada. Las tablas CSV y las figuras no sustituyen este estado.

## Ejecución desde R

En una sesión nueva, seleccionar el maestro:

```r
Sys.unsetenv(c("FMP_DATA_DIR", "FMP_LASSO_STATE", "FMP_RSF_STATE"))
Sys.setenv(
  FMP_STAGE = "oob",
  FMP_INSTALL = "never",
  FMP_DOWNLOAD = "never"
)
source(file.choose(), encoding = "UTF-8")
```

Si el estado está fuera de la ubicación predeterminada, indicar su ruta con
`Sys.setenv(FMP_RSF_STATE = "/ruta/RSF_resultados_para_comparacion.rds")`
antes de ejecutar `source()`. Para esta etapa no hace falta seleccionar clínica.

## Ejecución desde terminal

Desde la carpeta del proyecto:

```bash
Rscript --vanilla Script_maerstro_FMP.R \
  --stage=oob --install=never --download=never
```

Para indicar un estado en otra ruta, añadir
`--state="/ruta/RSF_resultados_para_comparacion.rds"`.
No utilizar `all` si el propósito es exclusivamente leer el bosque existente:
`all` sí construye ambos modelos.

## Cálculo y salidas

Se calcula `rowSums(CHF)` de las predicciones almacenadas. Para cada paciente,
el CHF OOB procede de árboles que no lo incluyeron en su muestra de entrenamiento.
Se obtiene AUC al año y C de Harrell con todo el seguimiento.

Se comprueban CHF finito/completo, panel y orden clínico, concordancia con
`1 - prediction.error` de ranger y conservación del MD5 del RDS antes/después.
La comprobación no llama a funciones de entrenamiento ni altera ese archivo.

| Salida | Ubicación |
|---|---|
| ROC aparente/OOB, PDF y PNG | `resultados/figuras/oob/` |
| Métricas, diferencias y controles | `resultados/tablas/oob/` |
| Informe, procedencia y entorno | `resultados/docs/README_oob.md`, `OOB_procedencia.csv`, `OOB_sessionInfo.txt` |
| Predicciones individuales y objetos ROC | `data/privados/oob/` |

El informe se genera con los valores de la ejecución. El README general de la
entrega describe el procedimiento y no contiene un resultado OOB precargado.

## Interpretación

La selección del panel y de parámetros utilizó TCGA; OOB no valida de manera
independiente esas decisiones. Se informa como diagnóstico interno condicionado
a la firma seleccionada. No se calculan IC convencionales OOB.

Una caída aparente–OOB evidencia optimismo del desempeño aparente, pero no
corrige el sobreajuste. La evaluación externa sigue respondiendo otra pregunta.
No equiparar OOB RSF con desempeño aparente LASSO para declarar superioridad.

Si aparece `REVISAR_EMPATES`, documentar la diferencia de concordancia y
examinarla; no asumir una causa solo por la etiqueta ni declarar que todos los
controles pasaron.

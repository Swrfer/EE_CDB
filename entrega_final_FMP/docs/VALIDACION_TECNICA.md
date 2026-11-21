# Validación técnica y pruebas

## Alcance

El flujo completo se ha comprobado con R 4.4.0, macOS ARM y Bioconductor 3.20.
Las versiones efectivas y la configuración se guardan automáticamente en cada
ejecución. La reproducción numérica requiere entradas, anotación, orden y entorno
equivalentes; no se garantiza por disponer únicamente de la misma versión de R.

Las pruebas de programación se ejecutan aparte del análisis. Usan datos
sintéticos y directorios temporales. No alimentan los resultados científicos ni
se ejecutan automáticamente al utilizar el maestro.

## Pruebas disponibles

| Archivo en `tests/` | Alcance |
|---|---|
| `test_funciones_puras.R` | Alineación, puntajes, comparación de firma, grupos, estadios y horizonte ROC |
| `test_flujo_sesion_vacia.R` | Maestro por Rscript/source sin objetos globales, con dobles de cálculo |
| `test_descarga_y_csv.R` | Esquemas clínicos, codificación, caché atómica y reanudación con servicios simulados |
| `test_geo_https_y_reanudacion.R` | Validación de gzip/tabla, reintentos y reutilización de matriz válida |
| `test_organizacion.R` | Rutas compartidas, copia, respaldo, fallos y restauración de publicación |
| `test_instalador.R` | Resolución de dependencias, prioridad binaria, conservación y diagnóstico, sin instalar |
| `test_rsf_desde_archivo.R` | RSF a partir del estado LASSO y orquestación completa en procesos vacíos |
| `test_rsf_real.R` | Ajuste ranger con datos sintéticos, reproducibilidad y predicción |
| `test_oob_sin_reentrenar.R` | Lectura OOB sintética, ausencia de reentrenamiento y conservación del estado |

Algunas pruebas sustituyen gráficos, descargas o timeROC por dobles. Las pruebas
que ajustan bosques sintéticos reducen su tamaño solo en sus copias temporales.
No certifican una AUC o un panel específico en las cohortes reales.

## Ejecución de pruebas

En terminal, desde la carpeta del proyecto, por ejemplo:

```bash
Rscript --vanilla tests/test_funciones_puras.R
Rscript --vanilla tests/test_instalador.R
Rscript --vanilla tests/test_descarga_y_csv.R
Rscript --vanilla tests/test_geo_https_y_reanudacion.R
Rscript --vanilla tests/test_flujo_sesion_vacia.R
Rscript --vanilla tests/test_organizacion.R
```

Las pruebas de RSF requieren `ranger` y `survival`. Se ejecutan explícitamente:

```bash
Rscript --vanilla tests/test_rsf_desde_archivo.R
Rscript --vanilla tests/test_rsf_real.R
Rscript --vanilla tests/test_oob_sin_reentrenar.R
```

Para comprobar únicamente la orquestación de RSF desde archivo, sin ajustar
bosques sintéticos, existe el modo:

```bash
FMP_TEST_NO_FIT=true Rscript --vanilla tests/test_rsf_desde_archivo.R
```

Este último ejemplo utiliza sintaxis de entorno de shells POSIX, como bash o
zsh. No es un comando de la consola de R.

## Comprobación de una ejecución científica

1. Utilizar una carpeta nueva con el ZIP limpio y el archivo clínico real.
2. Ejecutar `all` según el README principal.
3. Confirmar finalización de LASSO, RSF y OOB en
   `resultados/docs/ULTIMA_EJECUCION_COMPLETA.csv`.
4. Revisar cobertura, dimensiones, eventos y coincidencia de la firma LASSO.
5. Examinar las tablas conjuntas, los controles OOB y todas las advertencias.
6. Conservar configuración, huellas, código ejecutado y `sessionInfo`.

La finalización técnica, la coincidencia de firma y el rendimiento pronóstico
son comprobaciones distintas. Un análisis que termina correctamente puede
mostrar desempeño limitado o advertencias que deban documentarse.

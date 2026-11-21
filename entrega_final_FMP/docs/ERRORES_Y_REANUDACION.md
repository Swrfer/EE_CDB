# Errores, advertencias y reanudación

## Elegir la forma de ejecución correcta

`source(...)`, `Sys.setenv(...)` y `file.choose()` son instrucciones de R.
`Rscript --vanilla ...` es un comando de terminal. Escribirlo en la consola de
R produce `unexpected symbol` y no inicia el análisis.

Desde una sesión nueva de R, el bloque completo del README selecciona primero
la clínica ACRG y después el maestro. No se requieren objetos manuales ni
restaurar un archivo `.RData`.

## Falta la clínica ACRG

El archivo debe existir en la ruta indicada por `FMP_ACRG_CLINICAL` o por
`--acrg-clinical`. Seleccionarlo explícitamente evita depender de su nombre:

```r
archivo_acrg <- normalizePath(file.choose(), mustWork = TRUE)
Sys.unsetenv(c(
  "FMP_DATA_DIR", "FMP_LEGACY_RUN",
  "FMP_LASSO_STATE", "FMP_RSF_STATE"
))
Sys.setenv(
  FMP_STAGE = "all", FMP_INSTALL = "missing", FMP_DOWNLOAD = "missing",
  FMP_ACRG_CLINICAL = archivo_acrg
)
source(file.choose(), encoding = "UTF-8")
```

El segundo archivo seleccionado es `Script_maerstro_FMP.R`.
Dejar un CSV junto a los scripts no configura por sí mismo su ruta. La búsqueda
automática se limita a `data/raw/ACRG_clinical.csv` y a los nombres del suplemento
admitidos por el código. CSV y Excel se leen según su formato real.

Si el encabezado o la codificación son ambiguos, revisar la estructura del
README: tiempo en meses, identificador numérico y una sola columna de estado.
No completar códigos desconocidos como censura para evitar el error.

## Solicitud de `--legacy-run`

Ese argumento corresponde a la etapa `organize`, que importa una ejecución
anterior. Para reproducir desde cero, seleccionar explícitamente `all` mediante
el bloque del README o `--stage=all`. No se debe crear una carpeta de resultados
previos para satisfacer un error causado por elegir otra etapa.

## Error al cargar paquetes

Abrir una sesión nueva y ejecutar la etapa `install` con instalación de faltantes.
Consultar `data/instalacion/estado_paquetes.csv` y `acciones.csv`. El instalador
comprueba la carga real y conserva paquetes utilizables; no hace falta reinstalar
todo R como primer paso.

Un aviso de que un paquete fue construido con otra versión menor de R no
equivale al error de carga de una dependencia ni al fallo de un compilador.
Si falta un binario o existe una incompatibilidad, conservar el mensaje completo.
Véase [Instalación](INSTALACION_R44.md).

## Interrupción de GDC o GEO

Volver a ejecutar el bloque `all` con el mismo archivo clínico y
`FMP_DOWNLOAD = "missing"`. Se reutilizan los RDS completos y se adquieren las
entradas ausentes. TCGAbiolinks puede reutilizar archivos GDC ya descargados.
Esto reanuda la adquisición, pero los bloques de modelado de `all` se ejecutan
de nuevo; no es una recuperación del punto exacto de cada cálculo.

La matriz oficial GEO se obtiene de:
[GSE62254 Series Matrix](https://ftp.ncbi.nlm.nih.gov/geo/series/GSE62nnn/GSE62254/matrix/GSE62254_series_matrix.txt.gz).
El código hace hasta tres intentos, verifica el gzip y la tabla completa y la
lee sin descargar GPL. Si la transferencia automática falla, puede guardarse
ese mismo archivo oficial en `data/raw/`, con su nombre y compresión originales,
y volver a ejecutar el maestro. No usar una página HTML renombrada como matriz.

Una caché RDS ilegible no se reemplaza silenciosamente. Conservar o mover el
archivo identificado antes de repetir la adquisición. Para diagnosticar un error
en R, guardar el mensaje completo y ejecutar `traceback()` inmediatamente después.

## Firma LASSO distinta de la referencia

El flujo compara genes y coeficientes a tolerancia absoluta `1e-6`. Si difieren,
se detiene para evitar usar otra firma sin advertencia. Revisar la comparación
guardada, los filtros TCGA, las versiones, la anotación y el orden de entradas.
No reemplazar coeficientes, añadir genes ni cambiar la tolerancia solo para
obtener coincidencia.

Las advertencias de `glmnet` sobre convergencia en ciertos valores de lambda
deben conservarse en `LASSO_advertencias.csv`. Revisar su relación con el ajuste
seleccionado; que el proceso termine no significa que todas las soluciones
de la trayectoria hayan convergido. Modificar `maxit` o el ajuste requiere una
revisión metodológica, no una corrección de carpetas.

## Avisos durante las figuras

- `Median survival not reached`: alguna curva no alcanza supervivencia 0.5;
  no debe forzarse ni inventarse una mediana.
- Aviso de deprecación de `geom_errorbarh`: identifica una API gráfica obsoleta
  en versiones recientes de ggplot2; no es por sí mismo un fallo de ajuste.

Las advertencias quedan registradas por bloque. Si no se produce una figura,
revisar el error concreto además de la tabla de advertencias.

## Comprobaciones OOB

Si se marca `REVISAR_EMPATES`, el C recalculado difiere de
`1 - prediction.error` de ranger. Revisar la magnitud, alineación y tratamiento
de tiempos y puntajes; el nombre del estado no confirma una causa. AUC y C
son cálculos distintos. No sustituir una métrica por otra para ocultar la señal.

La etapa OOB requiere el estado RSF completo, no solo CSV o imágenes. Si falta,
ejecutar primero `all` o `rsf` con sus entradas correspondientes.

## Resultados después de una interrupción

Los nuevos archivos se publican al completar los bloques solicitados. Un fallo
antes de publicar conserva el conjunto anterior. Comprobar la acción y fecha UTC
en `resultados/docs/ULTIMA_EJECUCION_COMPLETA.csv` antes de atribuir los archivos
a una nueva ejecución. Existe un único respaldo en
`data/respaldos/ultima_ejecucion/`.

Para una comprobación desde cero, descomprimir el ZIP limpio en otra carpeta,
sin trasladar `data/` ni `resultados/`. No es necesario borrar la ejecución
completa para iniciar esa comprobación separada.

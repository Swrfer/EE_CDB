# Instalación de dependencias y entorno

## Entorno de referencia

El flujo completo se ha ejecutado con R 4.4.0 en macOS ARM. Para R 4.4, el
instalador utiliza CRAN y los repositorios de Bioconductor 3.20. Para otro R se
requiere `BiocManager` disponible para resolver la versión correspondiente de
Bioconductor; ese entorno no debe asumirse idéntico al de referencia.

| Paquetes principales | Versiones del entorno de referencia |
|---|---|
| `glmnet`, `survival`, `timeROC`, `ranger` | 4.1-10; 3.8-6; 0.4; 0.18.0 |
| `ggplot2`, `survminer`, `readxl` | 4.0.2; 0.5.2; 1.4.5 |
| `TCGAbiolinks`, `DESeq2`, `SummarizedExperiment` | 2.34.1; 1.46.0; 1.36.0 |
| `AnnotationDbi`, `org.Hs.eg.db` | 1.68.0; 3.20.0 |
| `GEOquery`, `Biobase`, `limma`, `hgu133plus2.db` | 2.74.0; 2.66.0; 3.62.2; 3.13.0 |

Estas versiones describen el entorno de referencia. El instalador no impone
un lockfile ni reinstala todos los paquetes para igualar esta tabla.

## Política de instalación

Con `FMP_INSTALL = "missing"` o `--install=missing`:

1. Se comprueban instalación, versión y carga real de los paquetes requeridos.
2. Si hace falta instalar, se resuelven `Depends`, `Imports` y `LinkingTo`, sus
   restricciones de versión y su orden. No se incluyen dependencias `Suggests`.
3. Se conservan los paquetes utilizables. Si falla la carga por una dependencia
   ausente, se repara primero esa dependencia, sin reinstalar automáticamente
   todos los paquetes que dependen de ella.
4. En macOS/Windows tienen prioridad los binarios compatibles, incluso si existe
   una fuente más reciente. No se pregunta si se desea compilar esa otra versión.
5. Cuando no hay binario se admiten fuentes R puras o de datos. Si un paquete
   requiere compilación y no hay binario compatible en macOS/Windows, se informa
   el paquete y se detiene. En Linux pueden requerirse herramientas del sistema.
6. Para R 4.4, si no hay un candidato compatible de `Deriv` en los catálogos,
   se contempla `Deriv 4.2.0` de CRAN Archive, R puro, con MD5 verificado.
7. Se registra el estado final y se comprueba que las dependencias carguen.

No hay actualización general, cambio automático de R ni instalación de
compiladores. Un paquete ya cargado que requiera sustitución exige reiniciar
la sesión; no se cambia silenciosamente durante su uso.

`FMP_INSTALL = "never"` o `--install=never` impide instalar. Una biblioteca
local `.R-library/` existente se incorpora también en ese modo. Los paquetes
requeridos deben estar disponibles para ejecutar el bloque solicitado.

## Comprobar solo dependencias

En una sesión nueva de R:

```r
Sys.setenv(FMP_STAGE = "install", FMP_INSTALL = "missing")
source(file.choose(), encoding = "UTF-8")
```

Seleccionar `Script_maerstro_FMP.R`. Esta etapa no requiere archivo clínico,
no descarga cohortes y no entrena modelos. El mensaje de éxito es
`Comprobacion de dependencias terminada`.

En terminal, desde la carpeta del proyecto:

```bash
Rscript --vanilla Script_maerstro_FMP.R --stage=install --install=missing
```

Para ejecutar después el análisis completo se debe fijar `FMP_STAGE = "all"`
o `--stage=all` y proporcionar el archivo clínico según el README principal.

## Archivos de diagnóstico

Se generan en `data/instalacion/`: `plan_paquetes.csv`, `estado_inicial.csv`,
`estado_paquetes.csv`, `acciones.csv`, `repositorios.csv` y `sessionInfo.txt`.
La carpeta puede conservar archivos descargados para instalación; no se incluye
en Git ni en el ZIP limpio. Los errores de carga se guardan completos.

La disponibilidad futura de binarios depende de los repositorios. Conservar
estas versiones y registros permite identificar diferencias entre entornos;
instalar faltantes por sí solo no garantiza resultados numéricos idénticos.

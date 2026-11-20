# Instalación de dependencias con R 4.4 — 20/11/2026

El primer intento independiente se realizó con R 4.4.0 en macOS ARM. El registro
mostró instalación de numerosos binarios CRAN, seguida de una pregunta sobre
compilar statmod 1.5.2 en lugar de usar el binario 1.5.1 disponible. Al aceptar,
faltó `/opt/gfortran/bin/gfortran` y la compilación falló. El mensaje agregado
indicó que GEOquery y limma no cargaban. La dependencia declarada
GEOquery → limma → statmod explica esa propagación; el registro original no
incluye el error completo de loadNamespace de cada uno.

También apareció «Deriv is not available». La versión actual 4.3.6 requiere
R >= 4.5 y compilación. Para R 4.4/macOS ARM el índice CRAN consultado ofrece
Deriv 4.2.0, que no necesita compilación. Se conserva esa compatibilidad sin
cambiar la versión de R. Los avisos de paquetes construidos con R 4.4.1/4.4.2
se distinguen del error explícito de compilador ausente.

## Cambio del instalador

- Se consultan los repositorios CRAN y Bioconductor 3.20 para R 4.4.
- Se resuelven las dependencias obligatorias, sus requisitos de versión y el
  orden de instalación antes de descargar los paquetes. No se incluyen Suggests.
- Se conservan paquetes existentes que cargan y cumplen los requisitos.
  Primero se reparan sus dependencias ausentes; no se reinstala GEOquery o
  limma simplemente por no poder cargar statmod.
- En macOS/Windows se prefieren binarios compatibles, aunque exista una versión
  fuente más reciente. No se usa type="both" ni se pregunta por compilación.
- Las fuentes R puras/de datos se instalan cuando no hay binario, por ejemplo
  TCGAbiolinksGUI.data y hgu133plus2.db. No necesitan gfortran.
- Si Deriv no tiene candidato compatible en los catálogos, para R 4.4 se admite
  el archivo CRAN 4.2.0, con MD5 verificado, como excepción documentada.
- Si falta un binario y se necesita compilar en macOS/Windows, se detiene con
  el paquete concreto. No se instalan compiladores del sistema automáticamente.
  En Linux, los paquetes fuente compilados requieren las herramientas del sistema.
- Un paquete existente que siga fallando después de reparar dependencias deja
  el error de carga completo. No se sustituye silenciosamente un paquete en uso.
- Una biblioteca local .R-library existente se incorpora también con install=never.

## Reintentar primero solo la instalación

Cerrar la sesión anterior de R y abrir una nueva. Reemplazar
`Funciones_fmp_comparacion.R` por la versión corregida junto al maestro. Ejecutar:

```r
Sys.setenv(FMP_STAGE = "install", FMP_INSTALL = "missing")
source(file.choose(), encoding = "UTF-8")
```

Seleccionar **Script_maerstro_FMP.R**. Esta etapa no requiere elegir el CSV ACRG,
no descarga TCGA/GEO y no entrena modelos. Reutiliza las instalaciones ya logradas.
El mensaje de éxito es `Comprobacion de dependencias terminada`.

Después, ejecutar el bloque de inicio rápido del README, seleccionando primero
el CSV y fijando explícitamente `FMP_STAGE = "all"`, `FMP_DOWNLOAD = "missing"`
y `FMP_INSTALL = "missing"`. Se reutilizan los paquetes y las entradas guardadas.

Por terminal, desde la carpeta del proyecto:

```bash
Rscript --vanilla Script_maerstro_FMP.R --stage=install --install=missing
```

## Diagnóstico y límites de la comprobación

`data/instalacion/` contiene plan_paquetes.csv, estado_inicial.csv,
estado_paquetes.csv, acciones.csv, repositorios.csv y sessionInfo.txt. Las
versiones concretas, rutas y errores de carga se guardan allí; esta carpeta queda
excluida de Git por ser parte de data/.

Las pruebas de la corrección usan servicios simulados y metadatos reales de los
repositorios. La planificación para R 4.4/macOS ARM eligió statmod 1.5.1 y
Deriv 4.2.0 binarios, limma 3.62.2 y GEOquery 2.74.0 binarios y los paquetes de
datos pertinentes en fuente R pura. No se ejecutó una instalación completa en
un Mac nuevo desde este entorno. La compañera debe repetir esa comprobación;
el fallo inicial todavía no constituye una validación integral del proyecto.
El código de ajuste, preparación y evaluación científica se conserva.

## Fuentes técnicas

- [R: instalación de paquetes y tipos binario/fuente](https://stat.ethz.ch/R-manual/R-devel/library/utils/html/install.packages.html).
- [Bioconductor 3.20 y R 4.4](https://bioconductor.org/news/bioc_3_20_release/).
- [Deriv actual y requisitos de R](https://cran.r-project.org/web/packages/Deriv/refman/Deriv.html).
- [Archivo CRAN de Deriv](https://cran.r-project.org/src/contrib/Archive/Deriv/).
- [GEOquery 3.20: dependencias](https://bioconductor.uib.no/packages/3.20/bioc/html/GEOquery.html).
- [limma 3.20: dependencias](https://bioconductor.uib.no/packages/3.20/bioc/html/limma.html).

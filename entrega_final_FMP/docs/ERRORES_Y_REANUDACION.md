# Recuperación de descargas

## Error de conexión al iniciar GEO

Caso observado el 20/11/2026: GDC descargó y preparó los conteos TCGA y se avanzó
a la clínica. Al iniciar GEO apareció `Error in open.connection(x, "rb")`.
El mensaje por sí solo no identifica si falló un listado, una transferencia o una
conexión GPL; se requiere traceback para atribuir esa causa con certeza.

La corrección usa directamente la matriz oficial:

https://ftp.ncbi.nlm.nih.gov/geo/series/GSE62nnn/GSE62254/matrix/GSE62254_series_matrix.txt.gz

Se descarga por HTTPS, se valida gzip/cabeceras/fin de tabla y se lee localmente
con GEOquery sin obtener GPL. Las sondas se anotan después con hgu133plus2.db,
como en el análisis confirmado. La matriz y su procedencia se guardan en data/raw/.

## Continuar después de actualizar el código

Actualizar `funciones_fmp_original.R` dentro de la misma carpeta de entrega y
conservar `data/raw/` en su ubicación actual. No hace falta abrir los RDS ni crear
objetos manuales. En R, después del setwd habitual:

```r
Sys.setenv(FMP_STAGE = "all", FMP_INSTALL = "never", FMP_DOWNLOAD = "missing")
source("ejecutar_replica_fmp.R", encoding = "UTF-8")
```

Si se solicita una entrada, seleccionar únicamente el CSV clínico ACRG.
El maestro reutiliza `tcga_counts_metadata.rds` y `tcga_clinical_original.rds` si
están completos; descarga solo la entrada GEO que falta.

## Si falla también HTTPS

La descarga hace tres intentos y conserva el detalle del último error. Se puede
guardar manualmente **ese mismo archivo oficial**, manteniendo su nombre y su
compresión .txt.gz, en `data/raw/` y volver a ejecutar el maestro. Antes de leerlo,
el código comprueba que no sea una página HTML ni una tabla incompleta.

Si la lectura GEOquery falla después de descargar, el error identifica el archivo
conservado y la versión del paquete. Compartir ese mensaje y `traceback()` justo
después del error permite diagnosticarlo sin volver a descargar TCGA.

Esta corrección no instala paquetes. `FMP_INSTALL="never"` mantiene desactivado
todo el bloque de instalación del maestro.

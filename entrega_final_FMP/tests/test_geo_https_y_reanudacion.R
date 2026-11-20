# Transporte HTTPS real de produccion con respuestas HTTP simuladas controladas.
args <- commandArgs(trailingOnly = FALSE)
script <- sub("^--file=", "", args[grepl("^--file=", args)])[1L]
root <- dirname(dirname(normalizePath(script)))
source(file.path(root, "funciones_fmp_original.R"), encoding = "UTF-8")
temporal <- tempfile("geo_https_"); dir.create(temporal)
on.exit(unlink(temporal, recursive = TRUE), add = TRUE)
crear <- function(archivo, completo = TRUE) {
  con <- gzfile(archivo, "wt")
  on.exit(close(con))
  writeLines(c('!Series_geo_accession\t"GSE62254"',
    '!Sample_platform_id\t"GPL570"\t"GPL570"',
    '!series_matrix_table_begin', '"ID_REF"\t"GSM_TEST1"\t"GSM_TEST2"',
    '"1007_s_at"\t2.3\t2.4', if (completo) '!series_matrix_table_end'), con)
}
fixture <- file.path(temporal, "fixture.txt.gz"); crear(fixture)
stopifnot(fmp_geo_matriz_valida(fixture))
incompleto <- file.path(temporal, "incompleto.txt.gz"); crear(incompleto, FALSE)
stopifnot(!fmp_geo_matriz_valida(incompleto))
html <- file.path(temporal, "html.txt.gz"); writeLines("<html>503 Service Unavailable</html>",html)
stopifnot(!fmp_geo_matriz_valida(html))
intentos <- 0L
descargador <- function(url,destfile,mode,method,quiet,cacheOK) {
  stopifnot(startsWith(url,"https://ftp.ncbi.nlm.nih.gov/"), mode=="wb", !cacheOK)
  intentos <<- intentos+1L
  if(intentos==1L) file.copy(html,destfile) else file.copy(fixture,destfile)
  0L
}
carpeta <- file.path(temporal,"cache")
archivo <- fmp_geo_descargar_matriz(carpeta,descargar=descargador,esperar=function(...)NULL)
stopifnot(intentos==2L,fmp_geo_matriz_valida(archivo),
  file.exists(file.path(carpeta,"GSE62254_series_matrix_procedencia.csv")))
md5 <- tools::md5sum(archivo)
otra <- fmp_geo_descargar_matriz(carpeta,descargar=function(...)stop("No debe descargar otra vez"))
stopifnot(identical(archivo,otra),identical(md5,tools::md5sum(otra)))
# Un archivo anterior incompleto se conserva y se reemplaza por una descarga valida.
writeLines("incompleto",archivo)
otra <- fmp_geo_descargar_matriz(carpeta,descargar=descargador,esperar=function(...)NULL)
stopifnot(fmp_geo_matriz_valida(otra),length(list.files(carpeta,pattern="incompleto_"))==1L)
fallo <- tryCatch(fmp_geo_descargar_matriz(file.path(temporal,"red_caida"),
  descargar=function(...)stop("HTTP 503 simulado"),esperar=function(...)NULL,intentos=2L),error=identity)
stopifnot(inherits(fallo,"error"),grepl("HTTP 503 simulado",conditionMessage(fallo),fixed=TRUE),
  grepl("RDS TCGA existentes se conservaron",conditionMessage(fallo),fixed=TRUE))
cat("GEO HTTPS: gzip/cabeceras/tabla, reintentos, cache y errores informativos: PASS\n")

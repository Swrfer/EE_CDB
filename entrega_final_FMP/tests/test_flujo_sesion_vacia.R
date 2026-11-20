# Prueba de regresion: un maestro, proceso R vacio, ningun modelo precargado.
# Los dobles sustituyen SOLO pasos cientificos; el maestro y la orquestacion son reales.
args <- commandArgs(trailingOnly = FALSE)
script <- sub("^--file=", "", args[grepl("^--file=", args)])[1L]
root <- dirname(dirname(normalizePath(script)))
temporal <- tempfile("fmp_flujo_")
dir.create(temporal)
on.exit(unlink(temporal, recursive = TRUE), add = TRUE)
proyecto <- file.path(temporal, "proyecto")
entradas <- file.path(proyecto, "data", "raw")
salida <- file.path(temporal, "resultados")
dir.create(entradas, recursive = TRUE)
dir.create(file.path(proyecto, "referencias"))
for (nombre in c("Script_maerstro_FMP.R", "Funciones_fmp_comparacion.R")) {
  stopifnot(file.copy(file.path(root, nombre), file.path(proyecto, nombre)))
}
refs <- c("216_GED.csv", "LASSO_Cox_signature_lambda_min_confirmada_8genes.csv")
for (nombre in refs) stopifnot(file.copy(file.path(root, "referencias", nombre),
  file.path(proyecto, "referencias", nombre)))
for (nombre in c("tcga_counts_metadata.rds", "tcga_clinical_original.rds", "GSE62254_eset.rds")) {
  saveRDS(list(fixture = TRUE), file.path(entradas, nombre))
}
writeLines("fixture: no es un suplemento clinico", file.path(entradas,
  "41591_2015_BFnm3850_MOESM34_ESM.xls"))

# Se agregan dobles al modulo copiado en la carpeta TEMPORAL de la prueba.
# No se modifica el archivo de produccion ni se exportan resultados ficticios.
referencia <- file.path(proyecto, "referencias", refs[2L])
dobles <- c(
  'fmp_instalar_dependencias <- function(...) invisible(NULL)',
  paste0(".firma_test <- fmp_leer_firma(", encodeString(referencia, quote = '"'), ")"),
  'fmp_paquetes <- function() {',
  '  stopifnot(!any(vapply(c("cvfit", "x", "y"), exists, logical(1), envir = .GlobalEnv, inherits = FALSE)))',
  '}',
  'fmp_importar_tcga <- function(...) list(test = TRUE)',
  'fmp_preparar_tcga <- function(entrada, genes, carpetas) {',
  '  xx <- matrix(seq_len(8 * nrow(.firma_test))/10, nrow=8, dimnames=list(paste0("test_",1:8), .firma_test$Gene))',
  '  dd <- data.frame(OS.time=365*(1:8)/2, OS.time_years=(1:8)/2, OS.event=rep(c(1L,0L),4), stage_simple=rep(c("i","ii","iii","iv"),2), row.names=rownames(xx))',
  '  list(x=xx, y=cbind(time=dd$OS.time,status=dd$OS.event), clinical=dd)',
  '}',
  'fmp_ajustar_lasso <- function(datos, carpetas) list(signature=.firma_test, cvfit=list(test_training_calls=1L))',
  'fmp_figuras_lasso <- function(ajuste, carpetas) {',
  '  zz <- readRDS(file.path(carpetas$privados,"TCGA_modelo_y_entradas.rds"))',
  '  stopifnot(identical(dim(zz$x),c(8L,8L)), nrow(zz$y)==8L, nrow(zz$signature)==8L)',
  '}',
  'fmp_forest_genes <- function(...) invisible(NULL)',
  'fmp_importar_acrg <- function(archivo_geo,archivo_clinico,firma,carpetas) {',
  '  z <- fmp_preparar_tcga(NULL,NULL,NULL); z$clinical$risk_score <- fmp_puntuar(z$x,firma); z',
  '}',
  'fmp_evaluar <- function(clinica,cohort,population,carpeta_figuras,carpetas,tiempos=1,corte=NULL,regla=">=",hacer_ajustado=FALSE) {',
  '  stopifnot(nrow(clinica)>0L, all(is.finite(clinica$risk_score)))',
  '  if(is.null(corte)) corte <- median(clinica$risk_score)',
  '  list(summary=data.frame(cohort=cohort,population=population,n=nrow(clinica),events=sum(clinica$OS.event),cutoff=corte,low_n=sum(clinica$risk_score<corte),high_n=sum(clinica$risk_score>=corte),logrank_p=NA_real_,C_Harrell_frozen=NA_real_),',
  '       timeROC=data.frame(cohort=cohort,population=population,horizon_years=tiempos,AUC=NA_real_,status="TEST_DOUBLE"))',
  '}',
  'fmp_documentar <- function(cfg,carpetas,coincidencia,estado,advertencias) writeLines(estado,file.path(carpetas$docs,"estado_test.txt"))'
)
cat("\n", paste(dobles, collapse = "\n"), "\n", file = file.path(proyecto,
  "Funciones_fmp_comparacion.R"), append = TRUE)

rscript <- file.path(R.home("bin"), "Rscript")
comando <- c("--vanilla", shQuote(file.path(proyecto, "Script_maerstro_FMP.R")),
  "--stage=lasso", shQuote(paste0("--data-dir=", entradas)), shQuote(paste0("--output-dir=", salida)))
log <- system2(rscript, comando, stdout = TRUE, stderr = TRUE)
codigo <- attr(log, "status")
if (!is.null(codigo) && codigo != 0L) stop(paste(log, collapse = "\n"))
ejecucion <- salida
stopifnot(dir.exists(file.path(salida,"tablas","lasso")))
modelo <- readRDS(file.path(proyecto, "data", "privados", "lasso", "TCGA_modelo_y_entradas.rds"))
final <- readRDS(file.path(proyecto, "data", "privados", "lasso", "FMP_original_replicada_para_comparacion.rds"))
km <- read.csv(file.path(ejecucion, "tablas", "lasso", "TABLA_MAESTRA_KM_Cindex.csv"))
roc <- read.csv(file.path(ejecucion, "tablas", "lasso", "TABLA_MAESTRA_timeROC.csv"))
stopifnot(modelo$cvfit$test_training_calls == 1L, nrow(km) == 4L, nrow(roc) == 4L,
  isTRUE(final$signature_matches), final$status == "COMPLETADO_REFERENCIA_8GENES_COINCIDENTE",
  all(c("TCGA", "ACRG") %in% km$cohort), all(c("Todos", "I_II") %in% km$population))

# Tambien debe funcionar mediante source(), desde otro directorio y sin --file.
expresion <- paste0("setwd(tempdir()); Sys.setenv(FMP_STAGE='lasso'); source(",
  encodeString(file.path(proyecto, "Script_maerstro_FMP.R"), quote = '"'),
  ", encoding=\"UTF-8\"); stopifnot(is.list(resultado_fmp), nrow(resultado_fmp$tcga$x)==8L)")
log_source <- system2(rscript, c("--vanilla", "-e", shQuote(expresion)),
  stdout = TRUE, stderr = TRUE)
codigo_source <- attr(log_source, "status")
if (!is.null(codigo_source) && codigo_source != 0L) stop(paste(log_source, collapse = "\n"))

# Sin entradas, la misma entrada CLI debe fallar por el archivo faltante,
# nunca por cvfit/x/y ni intentar abrir un selector en un proceso no interactivo.
vacio <- file.path(temporal, "entradas_vacias"); dir.create(vacio)
fallo <- suppressWarnings(system2(rscript, c("--vanilla",
  shQuote(file.path(proyecto, "Script_maerstro_FMP.R")),
  "--stage=lasso", "--download=never",
  shQuote(paste0("--acrg-clinical=",file.path(entradas,"41591_2015_BFnm3850_MOESM34_ESM.xls"))),
  shQuote(paste0("--data-dir=", vacio))), stdout = TRUE, stderr = TRUE))
stopifnot(!is.null(attr(fallo, "status")),
  any(grepl("No se encuentra tcga_counts_metadata.rds", fallo, fixed = TRUE)))
cat("Maestro por Rscript y source(), sin objetos previos: PASS (dobles de prueba)\n")

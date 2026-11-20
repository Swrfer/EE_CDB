# Prueba de adquisicion: maestro real en un proceso --vanilla, directorio vacio.
# Las llamadas remotas/instalacion se sustituyen por transportes simulados.
args <- commandArgs(trailingOnly = FALSE)
script <- sub("^--file=", "", args[grepl("^--file=", args)])[1L]
root <- dirname(dirname(normalizePath(script)))
source(file.path(root, "funciones_fmp_original.R"), encoding = "UTF-8")
temporal <- tempfile("fmp_descarga_"); dir.create(temporal)
on.exit(unlink(temporal, recursive = TRUE), add = TRUE)
falla <- function(expr) inherits(tryCatch({force(expr); NULL}, error = identity), "error")

# Se conserva la semantica del suplemento y se exige una unidad temporal explicita.
cl <- data.frame("Tumor ID" = 1:4, "OS (months)" = c(6, 12, 18, 24),
  "FU status0=alive,1=alive,2=dead,3=dead,4=dead,5=loss" = c(0, 2, 4, 5),
  pStage = c("I", "II", "III", "IV"), check.names = FALSE)
csv <- file.path(temporal, "ACRG.csv")
write.csv(cl, csv, row.names = FALSE)
a <- fmp_leer_clinica_acrg(csv)
csv2 <- file.path(temporal, "ACRG_punto_coma.csv")
write.csv2(cl, csv2, row.names = FALSE)
stopifnot(identical(a, fmp_leer_clinica_acrg(csv2)), identical(a[["FU status"]], c(0, 2, 4, 5)))
bin <- data.frame(patient_id = 1:4, OS_months = c(6, 12, 18, 24), OS_event = c(0, 1, 1, 0), stage = c("I", "II", "III", "IV"))
binary <- file.path(temporal, "binaria.csv"); write.csv(bin, binary, row.names = FALSE)
stopifnot(identical(fmp_leer_clinica_acrg(binary)[["FU status"]], c(0, 2, 2, 0)))
sin_unidad <- bin; names(sin_unidad)[2L] <- "OS_time"
bad <- file.path(temporal, "invalida.csv"); write.csv(sin_unidad, bad, row.names = FALSE)
stopifnot(falla(fmp_leer_clinica_acrg(bad)))
bin$OS_event[1L] <- 2; write.csv(bin, bad, row.names = FALSE)
stopifnot(falla(fmp_leer_clinica_acrg(bad)))
cl[["OS (months)"]][1L] <- "texto"; write.csv(cl, bad, row.names = FALSE)
stopifnot(falla(fmp_leer_clinica_acrg(bad)))

# Cache atomica: no vuelve a descargar ni sustituye una entrada ilegible.
cache <- file.path(temporal, "cache.rds"); llamadas <- 0L
crear <- function() {llamadas <<- llamadas + 1L; list(valor = 7)}
stopifnot(fmp_cache_rds(cache, crear, is.list))
md5 <- tools::md5sum(cache)
stopifnot(!fmp_cache_rds(cache, crear, is.list), llamadas == 1L, identical(md5, tools::md5sum(cache)))
writeLines("RDS roto", cache)
stopifnot(falla(fmp_cache_rds(cache, crear, is.list)), llamadas == 1L)

# Un proceso aislado entra al maestro con SOLO el CSV clinico local.
proyecto <- file.path(temporal, "proyecto"); dir.create(proyecto)
for (f in c("ejecutar_replica_fmp.R", "funciones_fmp_original.R")) {
  stopifnot(file.copy(file.path(root, f), file.path(proyecto, f)))
}
logfile <- file.path(proyecto, "pasos.txt")
dobles <- c(
  paste0(".log_test <- ", encodeString(logfile, quote = '"')),
  '.anotar_test <- function(x) cat(x,"\n",file=.log_test,append=TRUE)',
  'fmp_instalar_dependencias <- function(cfg) {stopifnot(!any(vapply(c("cvfit","x","y"), exists, logical(1), envir=.GlobalEnv,inherits=FALSE))); .anotar_test("install"); invisible(NULL)}',
  '.servicio <- new.env(parent=baseenv())',
  '.servicio$GDCquery <- function(...) { .anotar_test("query"); list(project="TCGA-STAD") }',
  '.servicio$getResults <- function(...) data.frame(id="uuid_sintetico",file_name="synthetic_counts.tsv")',
  '.servicio$getGDCInfo <- function(...) list(data_release="synthetic_test_only")',
  '.servicio$GDCdownload <- function(...) {.anotar_test("counts_download"); invisible(NULL)}',
  '.servicio$GDCprepare <- function(...) list(counts=matrix(1:12,nrow=3,dimnames=list(paste0("ENSG",1:3),paste0("TCGA-XX-000",1:4,"-01A"))))',
  '.servicio$assayNames <- function(...) c("unstranded","tpm_unstrand")',
  '.servicio$assay <- function(z,name) {stopifnot(name=="unstranded");z$counts}',
  '.servicio$colData <- function(z) data.frame(sample=colnames(z$counts))',
  '.servicio$GDCquery_clinic <- function(...) {.anotar_test("clinical_download");data.frame(submitter_id=paste0("TCGA-XX-000",1:4),vital_status=c("Alive","Dead","Alive","Dead"),days_to_death=c(NA,100,NA,200),days_to_last_follow_up=c(300,NA,400,NA))}',
  '.servicio$getGEO <- function(GEO,GSEMatrix,destdir,returnType=c("SummarizedExperiment","ExpressionSet")) {stopifnot(GEO=="GSE62254",GSEMatrix,identical(returnType,"ExpressionSet"));.anotar_test("geo_download");list(structure(list(values=matrix(1:12,nrow=3)),class="ExpressionSet"))}',
  '.servicio$annotation <- function(z) "GPL570"',
  '.servicio$exprs <- function(z) z$values',
  '.txt <- paste(deparse(body(fmp_descargar_entradas)),collapse="\n")',
  '.txt <- gsub("TCGAbiolinks::|SummarizedExperiment::|Biobase::|GEOquery::",".servicio$",.txt)',
  'body(fmp_descargar_entradas) <- parse(text=.txt)[[1L]]'
)
cat("\n", paste(dobles, collapse = "\n"), "\n", file = file.path(proyecto, "funciones_fmp_original.R"), append = TRUE)
rscript <- file.path(R.home("bin"), "Rscript")
correr <- function() {
  out <- system2(rscript, c("--vanilla", shQuote(file.path(proyecto, "ejecutar_replica_fmp.R")),
    "--stage=download", shQuote(paste0("--acrg-clinical=", csv))), stdout = TRUE, stderr = TRUE)
  code <- attr(out, "status"); if (!is.null(code) && code != 0L) stop(paste(out, collapse = "\n"))
}
correr()
raw <- file.path(proyecto, "data", "raw")
archivos <- file.path(raw, c("tcga_counts_metadata.rds", "tcga_clinical_original.rds", "GSE62254_eset.rds"))
stopifnot(all(file.exists(archivos)), identical(readRDS(archivos[1L])$provenance$assay, "unstranded"),
  identical(trimws(readLines(logfile)), c("install", "query", "counts_download", "clinical_download", "geo_download")),
  !dir.exists(file.path(proyecto, "resultados_replica_FMP")))
huellas <- tools::md5sum(archivos)
correr()
stopifnot(identical(huellas, tools::md5sum(archivos)), sum(trimws(readLines(logfile)) == "geo_download") == 1L)
# Recuperar solo una descarga que falta sin alterar los otros objetos.
unlink(archivos[2L]); correr()
stopifnot(identical(unname(huellas[c(1,3)]), unname(tools::md5sum(archivos[c(1,3)]))),
  sum(trimws(readLines(logfile)) == "clinical_download") == 2L,
  sum(trimws(readLines(logfile)) == "counts_download") == 1L)
cat("CSV, cache, maestro desde cero sin objetos, retorno GEO explicito y reanudacion parcial: PASS (servicios remotos simulados)\n")

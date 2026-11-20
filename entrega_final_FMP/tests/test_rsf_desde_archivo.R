# El maestro real ejecuta solo RSF desde un resultado LASSO guardado.
# Ranger/survival reales; se sustituyen graficos y timeROC por dobles sintéticos.
args <- commandArgs(trailingOnly = FALSE)
script <- sub("^--file=", "", args[grepl("^--file=", args)])[1L]
root <- dirname(dirname(normalizePath(script)))
stopifnot(requireNamespace("ranger", quietly = TRUE), requireNamespace("survival", quietly = TRUE))
temporal <- tempfile("fmp_rsf_entrada_"); dir.create(temporal)
on.exit(unlink(temporal, recursive = TRUE), add = TRUE)
proyecto <- file.path(temporal, "proyecto"); dir.create(proyecto)
for (f in c("Funciones_fmp_comparacion.R", "Script_maerstro_FMP.R")) {
  stopifnot(file.copy(file.path(root, f), file.path(proyecto, f)))
}
base_lasso <- file.path(temporal, "LASSO_prev"); dir.create(base_lasso)
dir.create(file.path(base_lasso, "data_privada")); dir.create(file.path(base_lasso, "tablas"))

set.seed(52); n <- 120L; p <- 25L
x <- matrix(rnorm(n * p), n, p, dimnames = list(paste0("synthetic_", seq_len(n)), paste0("G", seq_len(p))))
d <- data.frame(OS.time_years = rexp(n, rate = exp(x[, 1L])) + .01,
  OS.event = rbinom(n, 1, .7), stage_simple = rep(c("i", "ii", "iii", "iv"), length.out = n),
  row.names = rownames(x))
km <- data.frame(cohort = rep(c("TCGA", "ACRG"), each = 2), population = rep(c("Todos", "I_II"), 2),
  n = c(n, n/2, n, n/2), events = NA_integer_, cutoff = 0,
  low_n = NA_integer_, high_n = NA_integer_, logrank_p = NA_real_, C_Harrell_frozen = .6,
  C_Harrell_SE = NA_real_, status = "TEST_ONLY")
roc <- data.frame(cohort = km$cohort, population = km$population, horizon_years = 1,
  n = km$n, deaths_by_horizon = NA_integer_, observed_beyond_horizon = NA_integer_,
  censored_by_horizon = NA_integer_, AUC = .6, lower_95 = NA_real_, upper_95 = NA_real_, status = "TEST_ONLY")
write.csv(km, file.path(base_lasso, "tablas", "TABLA_MAESTRA_KM_Cindex.csv"), row.names = FALSE)
write.csv(roc, file.path(base_lasso, "tablas", "TABLA_MAESTRA_timeROC.csv"), row.names = FALSE)
estado <- file.path(base_lasso, "data_privada", "FMP_original_replicada_para_comparacion.rds")
objeto <- list(TCGA_x = x, TCGA_clinical = d, cvfit = list(foldid = rep(1:3, length.out = n)),
  ACRG_x = x[, 1:8, drop = FALSE], ACRG_clinical = d, ACRG_expression = t(x), config = list())
saveRDS(objeto, estado)
md5_antes <- tools::md5sum(estado)

# Dobles de prueba en la copia temporal. Los metodos de ajuste RSF siguen siendo los reales.
dobles <- c(
  'fmp_instalar_dependencias <- function(...) invisible(NULL)',
  '.ejecutar_lasso_real_test <- ejecutar_replica_fmp',
  '.config_real_test <- fmp_rsf_configuracion',
  'fmp_rsf_configuracion <- function() {z <- .config_real_test(); z$num.trees <- 30L; z$num.threads <- 1L; z}',
  'fmp_rsf_paquetes <- function() {stopifnot(!any(vapply(c("cvfit","x","y"), exists, logical(1), envir=.GlobalEnv,inherits=FALSE)))}',
  'ejecutar_replica_fmp <- function(...) stop("ERROR: se intento volver a entrenar LASSO")',
  'fmp_rsf_figuras <- function(...) invisible(NULL)',
  'fmp_oob_paquetes <- function() invisible(NULL)',
  'fmp_oob_auc <- function(...) list(AUC=NA_real_,roc=NULL,status="TEST_ONLY")',
  'fmp_oob_figuras <- function(...) invisible(NULL)',
  'fmp_evaluar <- function(clinica,cohort,population,carpeta_figuras,carpetas,tiempos=1,corte=NULL,...) {',
  ' if(is.null(corte)) corte<-median(clinica$risk_score)',
  ' list(summary=data.frame(cohort=cohort,population=population,n=nrow(clinica),events=sum(clinica$OS.event),cutoff=corte,low_n=sum(clinica$risk_score<corte),high_n=sum(clinica$risk_score>=corte),logrank_p=NA_real_,C_Harrell_frozen=fmp_rsf_concordancia(clinica,clinica$risk_score),C_Harrell_SE=NA_real_,status="TEST_ONLY"),',
  ' timeROC=data.frame(cohort=cohort,population=population,horizon_years=1,n=nrow(clinica),deaths_by_horizon=sum(clinica$OS.event==1 & clinica$OS.time_years<=1),observed_beyond_horizon=sum(clinica$OS.time_years>1),censored_by_horizon=sum(clinica$OS.event==0 & clinica$OS.time_years<=1),AUC=NA_real_,lower_95=NA_real_,upper_95=NA_real_,status="TEST_ONLY"))',
  '}'
)
# Modo de comprobacion de rutas: ningun bosque se ajusta. Solo se fabrican
# estructuras minimas dentro de la copia temporal de esta prueba.
# Activar con FMP_TEST_NO_FIT=true; no afecta al codigo de produccion.
if (identical(Sys.getenv("FMP_TEST_NO_FIT"), "true")) dobles <- c(dobles,
  'fmp_rsf_entrenar <- function(x,clinica,folds,cfg,carpetas) {',
  ' genes<-colnames(x)[1:5]; score<-exp(x[,1]); chf<-matrix(score,ncol=1,dimnames=list(rownames(x),NULL))',
  ' bosque<-structure(list(treetype="survival",chf=chf,unique.death.times=1,num.samples=nrow(x),num.trees=0L,forest=list(independent.variable.names=genes),prediction.error=1-fmp_rsf_concordancia(clinica,score)),class="ranger")',
  ' list(forest=bosque,signature=data.frame(Gene=genes),config=cfg)',
  '}',
  'fmp_rsf_predecir <- function(bosque,x,num.threads=1L) exp(x[,bosque$forest$independent.variable.names[1L]])'
)
cat("\n", paste(dobles, collapse="\n"), "\n", file=file.path(proyecto,"Funciones_fmp_comparacion.R"),append=TRUE)
rscript <- file.path(R.home("bin"), "Rscript")
salida <- file.path(temporal, "salida_rsf")
correr <- function() {
  log <- suppressWarnings(system2(rscript, c("--vanilla", shQuote(file.path(proyecto, "Script_maerstro_FMP.R")),
    "--stage=rsf", shQuote(paste0("--state=", estado)), shQuote(paste0("--output-dir=", salida))),
    stdout=TRUE,stderr=TRUE))
  codigo <- attr(log,"status")
  if(!is.null(codigo) && codigo!=0L) stop(paste(log,collapse="\n"))
  resultados <- file.path(proyecto,"data","privados","rsf","RSF_resultados_para_comparacion.rds")
  readRDS(tail(sort(resultados),1L))
}
res <- correr()
stopifnot(nrow(res$comparison$KM_Cindex)==8L, nrow(res$comparison$timeROC)==8L,
  res$status=="COMPLETADO_RSF_Y_COMPARACION", identical(tools::md5sum(estado),md5_antes),
  nrow(res$model$signature) %in% c(5L,10L,20L), all(res$coverage$present_ACRG))

# Una firma congelada sin cobertura externa no se recorta ni se reentrena con ACRG.
ausente <- res$model$signature$Gene[1L]
objeto$ACRG_expression <- objeto$ACRG_expression[setdiff(rownames(objeto$ACRG_expression),ausente),,drop=FALSE]
saveRDS(objeto,estado)
res2 <- correr()
stopifnot(res2$status=="COMPLETADO_RSF_SIN_COBERTURA_EXTERNA",
  identical(res$model$signature,res2$model$signature),
  all(is.na(res2$timeROC$AUC[res2$timeROC$cohort=="ACRG"])),
  all(res2$timeROC$status[res2$timeROC$cohort=="ACRG"]=="panel_incompleto"))

# Por defecto all debe encadenar los dos bloques desde entradas en disco.
dir.create(file.path(proyecto,"referencias"))
for (f in c("216_GED.csv","LASSO_Cox_signature_lambda_min_confirmada_8genes.csv")) {
  stopifnot(file.copy(file.path(root,"referencias",f),file.path(proyecto,"referencias",f)))
}
firma <- read.csv(file.path(proyecto,"referencias","LASSO_Cox_signature_lambda_min_confirmada_8genes.csv"))
objeto$TCGA_x <- x
colnames(objeto$TCGA_x)[seq_len(nrow(firma))] <- firma$Gene
objeto$ACRG_x <- objeto$TCGA_x[,firma$Gene,drop=FALSE]
objeto$ACRG_expression <- t(objeto$TCGA_x)
fixture <- file.path(temporal,"fixture_all.rds"); saveRDS(objeto,fixture)
raw <- file.path(proyecto,"data","raw"); dir.create(raw,recursive=TRUE)
for(f in c("tcga_counts_metadata.rds","tcga_clinical_original.rds","GSE62254_eset.rds")) {
  saveRDS(list(test=TRUE),file.path(raw,f))
}
writeLines("test",file.path(raw,"41591_2015_BFnm3850_MOESM34_ESM.xls"))
dobles_all <- c(
  'ejecutar_replica_fmp <- .ejecutar_lasso_real_test',
  paste0('.fixture_all <- readRDS(',encodeString(fixture,quote='"'),')'),
  paste0('.firma_all <- fmp_leer_firma(',encodeString(file.path(proyecto,"referencias","LASSO_Cox_signature_lambda_min_confirmada_8genes.csv"),quote='"'),')'),
  'fmp_paquetes <- function() invisible(NULL)',
  'fmp_importar_tcga <- function(...) list(test=TRUE)',
  'fmp_preparar_tcga <- function(...) list(x=.fixture_all$TCGA_x, clinical=.fixture_all$TCGA_clinical, y=survival::Surv(.fixture_all$TCGA_clinical$OS.time_years,.fixture_all$TCGA_clinical$OS.event))',
  '.calls_lasso_test <- 0L',
  'fmp_ajustar_lasso <- function(...) {.calls_lasso_test <<- .calls_lasso_test+1L; list(signature=.firma_all,cvfit=list(foldid=.fixture_all$cvfit$foldid,test_training_calls=.calls_lasso_test))}',
  'fmp_figuras_lasso <- function(...) invisible(NULL)',
  'fmp_forest_genes <- function(...) invisible(NULL)',
  'fmp_documentar <- function(...) invisible(NULL)',
  'fmp_importar_acrg <- function(...) {dd <- .fixture_all$ACRG_clinical; dd$risk_score<-fmp_puntuar(.fixture_all$ACRG_x,.firma_all,TRUE); list(x=.fixture_all$ACRG_x,clinical=dd,expression=.fixture_all$ACRG_expression)}'
)
cat("\n",paste(dobles_all,collapse="\n"),"\n",file=file.path(proyecto,"Funciones_fmp_comparacion.R"),append=TRUE)
salida_all <- file.path(temporal,"salida_all")
log_all <- system2(rscript,c("--vanilla",shQuote(file.path(proyecto,"Script_maerstro_FMP.R")),
  "--stage=all",shQuote(paste0("--output-dir=",salida_all))),stdout=TRUE,stderr=TRUE)
codigo_all <- attr(log_all,"status")
if(!is.null(codigo_all) && codigo_all!=0L) stop(paste(log_all,collapse="\n"))
f_lasso <- file.path(proyecto,"data","privados","lasso","FMP_original_replicada_para_comparacion.rds")
f_rsf <- file.path(proyecto,"data","privados","rsf","RSF_resultados_para_comparacion.rds")
stopifnot(length(f_lasso)==1L,length(f_rsf)==1L,
  readRDS(f_lasso)$cvfit$test_training_calls==1L,
  readRDS(f_rsf)$status=="COMPLETADO_RSF_Y_COMPARACION")
cat("Maestro RSF desde RDS y cobertura externa ausente: PASS; modo sin ajuste = ", Sys.getenv("FMP_TEST_NO_FIT", "false"), "\n",sep="")
cat("Maestro completo all: bloques LASSO y RSF encadenados desde disco: PASS\n")

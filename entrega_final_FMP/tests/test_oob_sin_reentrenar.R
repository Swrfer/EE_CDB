# Ranger real para crear UN modelo sintetico; la etapa OOB solo lo lee.
args <- commandArgs(trailingOnly = FALSE)
script <- sub("^--file=", "", args[grepl("^--file=", args)])[1L]
root <- dirname(dirname(normalizePath(script)))
source(file.path(root, "Funciones_fmp_comparacion.R"), encoding = "UTF-8")
stopifnot(requireNamespace("ranger",quietly=TRUE),requireNamespace("survival",quietly=TRUE))
set.seed(2026); n<-120L
x<-matrix(rnorm(n*6),n,6,dimnames=list(paste0("synthetic_",seq_len(n)),paste0("G",1:6)))
tt<-rexp(n,rate=exp(x[,1])); cc<-runif(n,1.2,3)
d<-data.frame(OS.time_years=pmin(tt,cc)+.01,OS.event=as.integer(tt<=cc),
  stage_simple=rep(c("i","ii","iii","iv"),length.out=n),row.names=rownames(x))
cfg<-fmp_rsf_configuracion();cfg$num.trees<-60L;cfg$num.threads<-1L
bosque<-fmp_rsf_bosque(x,d,cfg,15L,123L,"permutation")
d$risk_score<-as.numeric(fmp_rsf_predecir(bosque,x,1L))
objeto<-list(model=list(forest=bosque,signature=data.frame(Gene=colnames(x))),TCGA_clinical=d)
entrada<-fmp_oob_extraer(objeto)
stopifnot(identical(entrada$oob,rowSums(bosque$chf)),
  abs(fmp_rsf_concordancia(d,entrada$oob)-(1-bosque$prediction.error))<1e-7)

# AUC empírica exacta para la prueba, sin censura antes del año.
# La implementación de producción usa timeROC y contempla la censura.
auc_test<-function(clinica,riesgo,horizonte=1) {
  casos<-riesgo[clinica$OS.event==1 & clinica$OS.time_years<=horizonte]
  controles<-riesgo[clinica$OS.time_years>horizonte]
  a<-mean(outer(casos,controles,">"))+.5*mean(outer(casos,controles,"=="))
  list(AUC=a,roc=NULL,status="TEST_ONLY")
}
res<-fmp_oob_calcular(entrada,auc_fun=auc_test)
stopifnot(nrow(res$metrics)==2L,all(res$metrics$AUC>=0 & res$metrics$AUC<=1),
  all(res$metrics$refit==FALSE),all(res$checks$status=="PASS"))
debe_fallar<-function(expr) inherits(tryCatch({force(expr);NULL},error=identity),"error")
sin_oob<-objeto;sin_oob$model$forest$chf<-NULL
stopifnot(debe_fallar(fmp_oob_extraer(sin_oob)))
sin_panel<-objeto;sin_panel$model$signature$Gene<-rev(colnames(x))
stopifnot(debe_fallar(fmp_oob_extraer(sin_panel)))
chf_na<-objeto;chf_na$model$forest$chf[1,1]<-NA
stopifnot(debe_fallar(fmp_oob_extraer(chf_na)))

temporal<-tempfile("oob_fmp_");dir.create(temporal)
on.exit(unlink(temporal,recursive=TRUE),add=TRUE)
proyecto<-file.path(temporal,"proyecto");dir.create(proyecto)
for(f in c("Script_maerstro_FMP.R","Funciones_fmp_comparacion.R")) {
  stopifnot(file.copy(file.path(root,f),file.path(proyecto,f)))
}
estado<-file.path(temporal,"RSF_resultados_para_comparacion.rds");saveRDS(objeto,estado)
huella<-tools::md5sum(estado)
readme<-file.path(proyecto,"README.md")
writeLines(c("# Proyecto","Texto antes","<!-- INICIO_RESULTADOS_OOB -->","PENDIENTE",
  "<!-- FIN_RESULTADOS_OOB -->","Texto despues"),readme)
dobles<-c(
 'fmp_instalar_dependencias <- function(...) invisible(NULL)',
 'fmp_oob_paquetes <- function() invisible(NULL)',
 'fmp_oob_figuras <- function(...) invisible(NULL)',
 'fmp_oob_auc <- function(clinica,riesgo,horizonte=1) {a<-riesgo[clinica$OS.event==1 & clinica$OS.time_years<=horizonte];b<-riesgo[clinica$OS.time_years>horizonte];list(AUC=mean(outer(a,b,">"))+.5*mean(outer(a,b,"==")),roc=NULL,status="TEST_ONLY")}',
 'fmp_rsf_bosque <- fmp_rsf_entrenar <- fmp_ajustar_lasso <- ejecutar_replica_fmp <- ejecutar_bloque_rsf <- function(...) stop("ERROR: se intento reentrenar")'
)
cat("\n",paste(dobles,collapse="\n"),"\n",file=file.path(proyecto,"Funciones_fmp_comparacion.R"),append=TRUE)
rscript<-file.path(R.home("bin"),"Rscript")
salida<-file.path(temporal,"resultados")
log<-system2(rscript,c("--vanilla",shQuote(file.path(proyecto,"Script_maerstro_FMP.R")),
  "--stage=oob",shQuote(paste0("--state=",estado)),shQuote(paste0("--output-dir=",salida))),
  stdout=TRUE,stderr=TRUE)
codigo<-attr(log,"status");if(!is.null(codigo) && codigo!=0L)stop(paste(log,collapse="\n"))
metricas<-list.files(salida,pattern="RSF_COMPROBACION_OOB_metricas.csv",recursive=TRUE,full.names=TRUE)
stopifnot(length(metricas)==1L,identical(tools::md5sum(estado),huella),
  all(read.csv(metricas)$refit==FALSE))
texto<-readLines(readme)
stopifnot(any(texto=="PENDIENTE"),any(texto=="Texto antes"),any(texto=="Texto despues"))
informe <- readLines(file.path(salida,"docs","README_oob.md"))
stopifnot(any(grepl("OOB, condicionado",informe,fixed=TRUE)))
cat("OOB desde RDS: ranger real, sin reentrenar, entrada intacta e informe de ejecucion separado: PASS\n")

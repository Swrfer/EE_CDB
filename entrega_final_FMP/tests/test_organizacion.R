# Integracion de rutas/transacciones sin ajustar modelos ni acceder a red.
a <- commandArgs(FALSE); script <- sub("^--file=", "", a[grepl("^--file=", a)])[1L]
root <- dirname(dirname(normalizePath(script)))
modulo <- new.env(parent = globalenv())
source(file.path(root, "Funciones_fmp_comparacion.R"), local = modulo)
tmp <- tempfile("fmp_organizacion_"); dir.create(tmp)
on.exit(unlink(tmp, recursive = TRUE), add = TRUE)
base <- file.path(tmp,"proyecto"); dir.create(base)
for (f in c("Script_maerstro_FMP.R", "Funciones_fmp_comparacion.R")) file.copy(file.path(root,f), base)
modulo$fmp_preparar_ejecucion <- function(...) stop("No debe descargar ni instalar")
modulo$fmp_rsf_paquetes <- function() invisible(NULL)
modulo$ejecutar_replica_fmp <- function(cfg, carpetas) {
  writeLines("LASSO",file.path(carpetas$figuras,"TCGA_KM_global.png"))
  saveRDS(list(TCGA_x=1,signature="ocho genes"),file.path(carpetas$privados,"FMP_original_replicada_para_comparacion.rds"))
  list(folders=carpetas)
}
modulo$ejecutar_bloque_rsf <- function(archivo_estado,cfg_rsf,carpetas) {
  stopifnot(file.exists(archivo_estado))
  writeLines("RSF",file.path(carpetas$figuras,"TCGA_KM_global.png"))
  writeLines("comparacion",file.path(carpetas$tablas_comparacion,"comparacion.csv"))
  saveRDS(list(signature="veinte genes"),file.path(carpetas$privados,"RSF_resultados_para_comparacion.rds"))
  list(folders=carpetas)
}
modulo$ejecutar_comprobacion_oob <- function(archivo_estado,carpetas,...) {
  stopifnot(file.exists(archivo_estado))
  for (ext in c("pdf","png")) writeLines("OOB",file.path(carpetas$figuras,paste0("RSF_ROC_aparente_vs_OOB_1anio.",ext)))
  writeLines("OOB",file.path(carpetas$tablas,"OOB.csv"))
  saveRDS(list(refit=FALSE),file.path(carpetas$privados,"oob.rds"))
  list(folders=carpetas)
}
# Desactivar servicios por construccion; esta prueba tampoco carga un modelo real.
modulo$fmp_preparar_ejecucion <- function(...) invisible(NULL)
cfg <- list(base=base, stage="all", rsf=list(), archivos_codigo=file.path(base,c("Script_maerstro_FMP.R","Funciones_fmp_comparacion.R")),
  organizacion=modulo$fmp_organizacion(base))
r <- modulo$ejecutar_proyecto_fmp(cfg)
stopifnot(r$folders$root==cfg$organizacion$root,r$rsf$folders$root==r$oob$folders$root,
  file.exists(file.path(base,"resultados","figuras","oob","RSF_ROC_aparente_vs_OOB_1anio.pdf")),
  file.exists(file.path(base,"data","privados","rsf","RSF_resultados_para_comparacion.rds")))
archivos <- list.files(file.path(base,"resultados"),recursive=TRUE)
stopifnot(!any(grepl("replica_|OOB_20|data_privada|resultados_RSF",archivos)))
# Fallo en RSF: bytes y registro anteriores permanecen intactos.
huellas <- function() tools::md5sum(list.files(file.path(base,"resultados"),recursive=TRUE,full.names=TRUE))
antes <- huellas(); rsf_ok <- modulo$ejecutar_bloque_rsf
modulo$ejecutar_bloque_rsf <- function(...) stop("FALLO_CONTROLADO")
stopifnot(inherits(tryCatch(modulo$ejecutar_proyecto_fmp(cfg),error=identity),"error"),identical(antes,huellas()))
modulo$ejecutar_bloque_rsf <- rsf_ok
modulo$ejecutar_proyecto_fmp(cfg)
stopifnot(dir.exists(file.path(base,"data","respaldos","ultima_ejecucion","resultados")))
# Error al promover una carpeta: se restaura la salida completa anterior.
antes <- huellas(); fallo_promover <- TRUE
modulo$file.rename <- function(from,to) {
 if (fallo_promover && grepl("/\\.fmp_en_curso_[^/]+/privados/rsf$",from)) {
   fallo_promover <<- FALSE; return(FALSE)
 }
 base::file.rename(from,to)
}
stopifnot(inherits(tryCatch(modulo$ejecutar_proyecto_fmp(cfg),error=identity),"error"),
  !fallo_promover, identical(antes,huellas()))
rm("file.rename",envir=modulo)
# OOB aislado no pasa por entrenamiento ni altera el RDS RSF.
rsf <- file.path(base,"data","privados","rsf","RSF_resultados_para_comparacion.rds")
md5 <- tools::md5sum(rsf)
modulo$ejecutar_replica_fmp <- modulo$ejecutar_bloque_rsf <- function(...) stop("NO_REENTRENAR")
cfg$stage <- "oob"; cfg$archivo_estado <- rsf
modulo$ejecutar_proyecto_fmp(cfg)
stopifnot(identical(md5,tools::md5sum(rsf)))
# Migracion real de archivos: usa un formato antiguo sintetico; no lee modelos.
legacy <- file.path(tmp,"replica_20261120_114731"); dir.create(legacy)
raices <- c(lasso=legacy, rsf=file.path(legacy,"resultados_RSF","replica_20261120_114900"),
  oob=file.path(legacy,"resultados_RSF","replica_20261120_114900","comprobacion_OOB","OOB_20261120_115108_x"))
for (b in names(raices)) {
 for (d in c("tablas","figuras","data_privada","docs")) dir.create(file.path(raices[[b]],d),recursive=TRUE)
 writeLines("informe",file.path(raices[[b]],"README.md"))
 saveRDS(list(marker=b),file.path(raices[[b]],"data_privada",paste0(b,".rds")))
}
for (f in c("TABLA_MAESTRA_KM_Cindex.csv","TABLA_MAESTRA_timeROC.csv")) {
 write.csv(data.frame(cohort="TCGA",estimate=.65),file.path(legacy,"tablas",f),row.names=FALSE)
}
dir.create(file.path(legacy,"figuras","02_TCGA"))
dir.create(file.path(legacy,"figuras","03_ACRG"))
writeLines("TCGA",file.path(legacy,"figuras","02_TCGA","KM_Todos.png"))
writeLines("ACRG",file.path(legacy,"figuras","03_ACRG","KM_Todos.png"))
writeLines("comparacion",file.path(raices[["rsf"]],"tablas","COMPARACION_MAESTRA_timeROC.csv"))
for (ext in c("pdf","png")) writeLines("OOB recibido",file.path(raices[["oob"]],"figuras",paste0("RSF_ROC_aparente_vs_OOB_1anio.",ext)))
write.csv(data.frame(estimate=.65),file.path(raices[["oob"]],"tablas","RSF_COMPROBACION_OOB_metricas.csv"),row.names=FALSE)
saveRDS(list(marker="rsf"),file.path(raices[["rsf"]],"data_privada","RSF_resultados_para_comparacion.rds"))
antes_legacy <- tools::md5sum(list.files(legacy,recursive=TRUE,full.names=TRUE))
# La etapa organize evita tanto preparacion como ajuste; nunca modifica el origen.
modulo$fmp_preparar_ejecucion <- function(...) stop("NO_RED_NI_INSTALAR")
cfg$stage <- "organize";cfg$legacy_run <- legacy
modulo$ejecutar_proyecto_fmp(cfg)
stopifnot(identical(antes_legacy,tools::md5sum(list.files(legacy,recursive=TRUE,full.names=TRUE))))
for (c in c("TCGA","ACRG")) stopifnot(file.exists(file.path(base,"resultados","figuras","lasso",paste0(c,"_KM_global.png"))))
for (ext in c("pdf","png")) {
 n <- paste0("RSF_ROC_aparente_vs_OOB_1anio.",ext)
 stopifnot(identical(unname(tools::md5sum(file.path(raices[["oob"]],"figuras",n))),
   unname(tools::md5sum(file.path(base,"resultados","figuras","oob",n)))) )
}
stopifnot(file.exists(file.path(base,"resultados","tablas","comparacion","COMPARACION_MAESTRA_timeROC.csv")))
# Un estado antiguo organizado conserva sus bytes y tiene indice adyacente.
fuentes <- modulo$fmp_fuentes_lasso(file.path(base,"data","privados","lasso","lasso.rds"))
stopifnot(nrow(fuentes$KM_Cindex)==1L)
cat("Rutas compartidas, fallo sin publicacion, respaldo unico, OOB aislado y migracion sin ajustes: PASS\n")

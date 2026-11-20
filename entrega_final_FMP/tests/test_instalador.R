# Sin red, instalaciones ni modelos. Reproduce las dependencias del fallo R 4.4/macOS.
a <- commandArgs(FALSE); script <- sub("^--file=", "", a[grepl("^--file=", a)])[1L]
root <- dirname(dirname(normalizePath(script)))
m <- new.env(parent = globalenv())
source(file.path(root, "Funciones_fmp_comparacion.R"), local = m)
tmp <- tempfile("fmp_instalador_"); dir.create(tmp)
on.exit(unlink(tmp,recursive=TRUE),add=TRUE)
columnas <- c("Package","Version","Depends","Imports","LinkingTo","NeedsCompilation","install_type","Repository","MD5sum")
fila <- function(Package, Version, Imports=NA_character_, Depends=NA_character_, tipo="mac.binary.big-sur-arm64", compilado="no") {
 data.frame(Package,Version,Depends,Imports,LinkingTo=NA_character_,NeedsCompilation=compilado,
   install_type=tipo,Repository="https://repositorio.test/contrib",MD5sum=NA_character_,stringsAsFactors=FALSE)
}
catalogo <- rbind(fila("statmod","1.5.1","stats, graphics",tipo="mac.binary.big-sur-arm64",compilado="yes"),
 fila("Deriv","4.2.0","methods"),
 fila("statmod","1.5.2","stats, graphics",tipo="source",compilado="yes"),
 fila("Deriv","4.3.6","Rcpp",Depends="R (>= 4.5)",tipo="source",compilado="yes"),
 fila("hgu133plus2.db","3.13.0","methods",tipo="source"))
instalados <- rbind(fila("GEOquery","2.74.0","limma"),fila("limma","3.62.2","statmod"),
 fila("survminer","0.5.2","Deriv"),fila("methods","4.4.0"),fila("stats","4.4.0"),fila("graphics","4.4.0"))
instalados$install_type <- "installed"
p <- m$fmp_plan_instalacion(c("GEOquery","survminer","hgu133plus2.db"),catalogo,instalados,version_r=package_version("4.4.0"))
stopifnot(p$nodes$statmod$Version=="1.5.1",p$nodes$Deriv$Version=="4.2.0",
 p$nodes$statmod$install_type=="mac.binary.big-sur-arm64",
 match("statmod",p$order)<match("limma",p$order),match("limma",p$order)<match("GEOquery",p$order))
# Falta de binario Deriv: fuente compatible R puro de CRAN Archive, MD5 fijado.
archivo <- m$fmp_elegir_instalacion("Deriv",catalogo[0,],NULL,version_r=package_version("4.4.0"))
stopifnot(archivo$Version=="4.2.0",archivo$NeedsCompilation=="no",grepl("Archive/Deriv",archivo$archive_url))
# Rechazar una dependencia que exija un R posterior; no cambiar R en silencio.
mal <- rbind(catalogo,fila("nuevo","1.0",Depends="R (>= 4.5)",tipo="source"))
stopifnot(inherits(tryCatch(m$fmp_plan_instalacion("nuevo",mal,instalados,version_r=package_version("4.4.0")),error=identity),"error"))
# Las restricciones de version de dependencias se tienen en cuenta.
stopifnot(!m$fmp_version_cumple("1.5.1",data.frame(op=">=",version="1.5.2")))
# Prohibir fuente compilada en macOS cuando no hay binario: no aparece pregunta.
m$.Platform <- list(pkgType="mac.binary.big-sur-arm64")
stopifnot(inherits(tryCatch(m$fmp_instalar_paquete(as.list(catalogo[3,]),tmp,tmp),error=identity),"error"))

# Ejecutar instalador real con servicios dobles, conservando GEOquery/limma instalados.
db <- instalados; llamadas <- character(); consultas <- 0L
lib <- file.path(tmp,"lib");dir.create(lib)
m$.libPaths <- function(new=NULL) if(is.null(new))lib else invisible(new)
m$fmp_dependencias <- function(cfg) list(cran="survminer",bioc=c("GEOquery","hgu133plus2.db"))
m$fmp_instalados <- function() db
m$fmp_repos_instalacion <- function(cfg) c(CRAN="https://test")
m$fmp_catalogo_instalacion <- function(...) {consultas <<- consultas+1L;catalogo}
m$fmp_estado_paquete <- function(p) {
 esta <- p %in% db$Package
 cargar <- function(q,visitado=character()) {
  if(q=="R") return(TRUE)
  if(q %in% visitado || !q %in% db$Package) return(FALSE)
  deps <- m$fmp_deps_paquete(as.list(db[match(q,db$Package),]))$package
  all(vapply(deps,cargar,logical(1),visitado=c(visitado,q)))
 }
 ok <- esta && cargar(p)
 data.frame(package=p,version=if(esta)db$Version[match(p,db$Package)]else"",loadable=ok,library=lib,
  error=if(ok)""else paste("dependencia ausente para",p))
}
m$fmp_instalar_paquete <- function(nodo,biblioteca,directorio) {
 stopifnot(!nodo$Package %in% db$Package) # no reinstalar los ya instalados
 llamadas <<- c(llamadas,nodo$Package)
 row <- as.data.frame(nodo,stringsAsFactors=FALSE)[,columnas];row$install_type<-"installed"
 db <<- rbind(db,row)
}
# La nueva etapa install no exige CSV ni activa adquisicion/modelos.
real <- new.env(parent=globalenv());source(file.path(root,"Funciones_fmp_comparacion.R"),local=real)
config_install <- real$fmp_configuracion(tmp,"--stage=install",permitir_selector=FALSE)
stopifnot(is.null(config_install$archivo_clinico_acrg),"ranger" %in% real$fmp_dependencias(config_install)$cran)
real$fmp_instalar_dependencias <- function(...) invisible(NULL)
real$fmp_estado_paquete <- function(p) data.frame(package=p,loadable=TRUE)
real$fmp_descargar_entradas <- real$ejecutar_replica_fmp <- function(...) stop("NO_DATOS_NI_MODELOS")
stopifnot(real$ejecutar_proyecto_fmp(config_install)$status=="DEPENDENCIAS_COMPROBADAS")
real$fmp_estado_paquete <- function(p) data.frame(package=p,loadable=FALSE)
stopifnot(inherits(tryCatch(real$ejecutar_proyecto_fmp(config_install),error=identity),"error"))
cfg <- list(base=tmp,stage="all",install="missing")
opciones <- options()[c("install.packages.check.source","install.packages.compile.from.source")]
m$fmp_instalar_dependencias(cfg)
stopifnot(setequal(llamadas,c("statmod","Deriv","hgu133plus2.db")),consultas==1L,
 !any(c("GEOquery","limma","survminer") %in% llamadas),
 all(read.csv(file.path(tmp,"data","instalacion","estado_paquetes.csv"))$loadable))
n <- length(llamadas);m$fmp_instalar_dependencias(cfg)
stopifnot(length(llamadas)==n,consultas==1L) # segunda ejecucion sin reinstalar ni red
cfg$install <- "never"
m$fmp_instalados <- function(...) stop("No consultar ni instalar con never")
m$fmp_instalar_dependencias(cfg)
# El diagnostico conserva el error real de carga tras un intento fallido.
cfg$install <- "missing";db <- instalados
m$fmp_instalados <- function()db
m$fmp_instalar_paquete <- function(...) invisible(NULL)
e <- tryCatch(m$fmp_instalar_dependencias(cfg),error=identity)
stopifnot(inherits(e,"error"),grepl("Deriv",conditionMessage(e)),grepl("Diagnostico completo",conditionMessage(e)))
estado <- read.csv(file.path(tmp,"data","instalacion","estado_paquetes.csv"))
stopifnot(any(!estado$loadable),any(grepl("dependencia ausente",estado$error)))
# Detectar ciclos antes de instalar.
ciclo <- rbind(fila("A","1","B"),fila("B","1","A"))
stopifnot(inherits(tryCatch(m$fmp_plan_instalacion("A",ciclo,instalados),error=identity),"error"))
cat("Instalador: binarios R4.4, orden de dependencias, compatibilidad Deriv, fuentes puras, conservacion, never y diagnostico: PASS\n")

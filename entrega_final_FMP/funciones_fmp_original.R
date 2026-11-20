# Funciones del proyecto: LASSO-Cox confirmado y nuevo RSF.
# Un unico maestro ejecuta las fases desde archivos, sin objetos globales previos.

# CONFIGURACION Y ADQUISICION. Las funciones cientificas se conservan debajo.
fmp_configuracion <- function(base, argumentos = character(), permitir_selector = interactive()) {
  reconocidos <- grepl("^--(data-dir|output-dir|stage|state|acrg-clinical|install|download)=", argumentos)
  fmp_exigir(!length(argumentos) || all(reconocidos),
    "Usa --stage=all|download|lasso|rsf|oob, --acrg-clinical=CSV, --data-dir=RUTA, --output-dir=RUTA, --state=RDS, --install=missing|never y --download=missing|never.")
  leer <- function(nombre, defecto) {
    z <- argumentos[startsWith(argumentos, paste0("--", nombre, "="))]
    fmp_exigir(length(z) <= 1L, paste("Argumento repetido:", nombre))
    if (length(z)) substring(z, nchar(nombre) + 4L) else defecto
  }
  etapa <- leer("stage", Sys.getenv("FMP_STAGE", "all"))
  instalar <- leer("install", Sys.getenv("FMP_INSTALL", "missing"))
  descargar <- leer("download", Sys.getenv("FMP_DOWNLOAD", "missing"))
  fmp_exigir(etapa %in% c("all", "download", "lasso", "rsf", "oob"), "stage no valido.")
  fmp_exigir(instalar %in% c("missing", "never") && descargar %in% c("missing", "never"),
    "install y download admiten missing o never.")
  datos <- path.expand(leer("data-dir", Sys.getenv("FMP_DATA_DIR", file.path(base, "data", "raw"))))
  salida <- path.expand(leer("output-dir", file.path(base, "resultados_replica_FMP")))
  cfg <- list(base = base, stage = etapa, install = instalar, download = descargar,
    data_dir = datos, carpeta_salida = salida,
    archivos_codigo = file.path(base, c("ejecutar_replica_fmp.R", "funciones_fmp_original.R")),
    archivo_readme = file.path(base, "README.md"), rsf = fmp_rsf_configuracion())
  if (etapa %in% c("rsf", "oob")) {
    variable <- if (etapa == "rsf") "FMP_LASSO_STATE" else "FMP_RSF_STATE"
    estado <- path.expand(leer("state", Sys.getenv(variable, "")))
    if (!nzchar(estado) && isTRUE(permitir_selector)) {
      message("Selecciona el RDS final del bloque ", if (etapa == "rsf") "LASSO." else "RSF.")
      estado <- file.choose()
    }
    fmp_exigir(nzchar(estado) && file.exists(estado), paste("Para", etapa, "indica --state=RUTA al RDS final correspondiente."))
    cfg$archivo_estado <- normalizePath(estado)
    if (!any(startsWith(argumentos, "--output-dir="))) cfg$carpeta_salida <- NULL
    return(cfg)
  }
  clinica <- path.expand(leer("acrg-clinical", Sys.getenv("FMP_ACRG_CLINICAL", "")))
  if (!nzchar(clinica)) {
    candidatos <- file.path(datos, c("ACRG_clinical.csv", "41591_2015_BFnm3850_MOESM34_ESM.csv",
      "41591_2015_BFnm3850_MOESM34_ESM.xls"))
    presentes <- candidatos[file.exists(candidatos)]
    if (length(presentes)) clinica <- presentes[1L]
  }
  if (!nzchar(clinica) && isTRUE(permitir_selector)) {
    message("Selecciona tu CSV clinico de ACRG; es la unica entrada externa local necesaria.")
    clinica <- file.choose()
  }
  fmp_exigir(nzchar(clinica) && file.exists(clinica),
    "Falta el CSV clinico ACRG. Usa --acrg-clinical=/ruta/ACRG.csv o colocalo como data/raw/ACRG_clinical.csv.")
  cfg$archivo_tcga <- file.path(datos, "tcga_counts_metadata.rds")
  cfg$archivo_clinico_tcga <- file.path(datos, "tcga_clinical_original.rds")
  cfg$archivo_acrg <- file.path(datos, "GSE62254_eset.rds")
  cfg$archivo_clinico_acrg <- normalizePath(clinica)
  cfg$archivo_genes <- file.path(base, "referencias", "216_GED.csv")
  cfg$archivo_firma_referencia <- file.path(base, "referencias", "LASSO_Cox_signature_lambda_min_confirmada_8genes.csv")
  cfg$archivo_metricas_referencia <- ""
  cfg$tiempos_roc <- 1
  cfg$tolerancia_coeficientes <- 1e-6
  cfg$exigir_coincidencia_firma <- TRUE
  cfg$hacer_cox_ajustado <- FALSE
  cfg
}

fmp_dependencias <- function(cfg) {
  if (cfg$stage == "oob") return(list(cran = c("survival", "timeROC"), bioc = character()))
  if (cfg$stage == "rsf") return(list(cran = c("ranger", "survival", "ggplot2", "survminer", "timeROC"), bioc = character()))
  if (cfg$stage == "download") return(list(cran = "readxl", bioc = c("TCGAbiolinks", "SummarizedExperiment", "GEOquery", "Biobase")))
  list(cran = c("glmnet", "survival", "ggplot2", "survminer", "readxl", "timeROC",
      if (cfg$stage == "all") "ranger"),
    bioc = c("TCGAbiolinks", "DESeq2", "SummarizedExperiment", "AnnotationDbi",
      "org.Hs.eg.db", "GEOquery", "Biobase", "limma", "hgu133plus2.db"))
}

fmp_instalar_dependencias <- function(cfg) {
  if (identical(cfg$install, "never")) return(invisible(NULL))
  deps <- fmp_dependencias(cfg)
  falta <- function(p) p[!vapply(p, requireNamespace, logical(1), quietly = TRUE)]
  cran <- falta(deps$cran); bioc <- falta(deps$bioc)
  if (!length(c(cran, bioc))) return(invisible(NULL))
  biblioteca <- .libPaths()[1L]
  if (!dir.exists(biblioteca) || file.access(biblioteca, 2L) != 0L) {
    biblioteca <- file.path(cfg$base, ".R-library", paste0(R.version$major, ".", strsplit(R.version$minor, ".", fixed = TRUE)[[1L]][1L]), R.version$platform)
    dir.create(biblioteca, recursive = TRUE, showWarnings = FALSE)
    .libPaths(c(biblioteca, .libPaths()))
  }
  repos <- getOption("repos")
  if (is.null(repos) || !length(repos) || !"CRAN" %in% names(repos) || repos[["CRAN"]] == "@CRAN@") {
    repos <- c(CRAN = "https://cloud.r-project.org")
  }
  options(repos = repos, timeout = max(3600, getOption("timeout")))
  if (length(cran)) {
    message("Instalando dependencias CRAN faltantes: ", paste(cran, collapse = ", "))
    utils::install.packages(cran, repos = repos, lib = biblioteca)
  }
  if (length(bioc)) {
    if (!requireNamespace("BiocManager", quietly = TRUE)) utils::install.packages("BiocManager", repos = repos, lib = biblioteca)
    message("Instalando dependencias Bioconductor faltantes: ", paste(bioc, collapse = ", "))
    BiocManager::install(bioc, update = FALSE, ask = FALSE, lib = biblioteca)
  }
  pendientes <- falta(c(deps$cran, deps$bioc))
  fmp_exigir(!length(pendientes), paste("No se pudieron instalar:", paste(pendientes, collapse = ", "),
    ". Revisa la salida de instalacion y la compatibilidad de R/Bioconductor. No se actualizo R automaticamente."))
  invisible(NULL)
}

fmp_leer_clinica_acrg <- function(archivo) {
  # CSV del suplemento o esquema explicito patient_id, OS_months, OS_event, stage.
  # No se infieren unidades ni se convierte un estado ambiguo en evento.
  clave <- function(x) gsub("[^a-z0-9]", "", tolower(trimws(x)))
  extraer <- function(d, posibles) which(clave(names(d)) %in% posibles)
  if (tolower(tools::file_ext(archivo)) %in% c("xls", "xlsx")) {
    fmp_exigir(requireNamespace("readxl", quietly = TRUE), "Para el suplemento Excel se necesita readxl.")
    d <- as.data.frame(readxl::read_excel(archivo))
  } else {
    opciones <- lapply(c(",", ";", "\t"), function(separador) tryCatch(
      utils::read.table(archivo, header = TRUE, sep = separador, quote = '"',
        comment.char = "", check.names = FALSE, colClasses = "character", fill = FALSE,
        na.strings = c("", "NA", "N/A"), fileEncoding = "UTF-8-BOM"), error = function(e) NULL))
    valida <- vapply(opciones, function(z) !is.null(z) &&
      length(extraer(z, c("tumorid", "patientid"))) == 1L &&
      length(extraer(z, "osmonths")) == 1L, logical(1))
    fmp_exigir(any(valida), paste("CSV ACRG no reconocido. Requiere Tumor ID, OS (months), FU status y pStage;",
      "o patient_id, OS_months, OS_event, stage. Separador: coma, punto y coma o tabulador."))
    d <- opciones[[which(valida)[1L]]]
  }
  nombres <- clave(names(d))
  tomar <- function(posibles, requerido = TRUE) {
    i <- extraer(d, posibles)
    fmp_exigir(length(i) <= 1L && (!requerido || length(i) == 1L), paste("Columna ACRG ausente o ambigua:", paste(posibles, collapse = "/")))
    if (length(i)) d[[i]] else NULL
  }
  numero <- function(x) {
    texto <- trimws(as.character(x))
    z <- fmp_num(gsub(",", ".", texto, fixed = TRUE))
    fmp_exigir(!any(!is.na(texto) & nzchar(texto) & !texto %in% c("NA", "N/A") & is.na(z)),
      "La clinica ACRG contiene texto no numerico en una columna de ID/tiempo/estado.")
    z
  }
  id <- numero(tomar(c("tumorid", "patientid"))); meses <- numero(tomar("osmonths"))
  fu <- which(startsWith(nombres, "fustatus")); evento <- extraer(d, "osevent")
  fmp_exigir((length(fu) == 1L && !length(evento)) || (!length(fu) && length(evento) == 1L),
    "Indica una unica columna FU status (codigos del suplemento) u OS_event (0=censura, 1=muerte), no ambas.")
  if (length(fu)) {
    estado <- numero(d[[fu]])
    fmp_exigir(all(is.na(estado) | estado %in% 0:5), "FU status contiene codigos distintos de 0:5.")
  } else {
    e <- numero(d[[evento]])
    fmp_exigir(all(is.na(e) | e %in% c(0, 1)), "OS_event debe ser 0=censura o 1=muerte.")
    estado <- ifelse(is.na(e), NA_real_, ifelse(e == 1, 2, 0))
  }
  fmp_exigir(length(id) > 0L && all(is.na(meses) | (is.finite(meses) & meses >= 0)), "OS (months) tiene valores no validos.")
  out <- data.frame("Tumor ID" = id, "OS (months)" = meses, "FU status" = estado, check.names = FALSE)
  stage <- tomar(c("pstage", "stage"), requerido = FALSE)
  if (!is.null(stage)) out$pStage <- stage
  edad <- tomar(c("age", "ageyears"), requerido = FALSE)
  sexo <- tomar(c("sex", "gender"), requerido = FALSE)
  if (!is.null(edad)) out$age <- numero(edad)
  if (!is.null(sexo)) out$sex <- sexo
  out
}

fmp_cache_rds <- function(archivo, crear, validar) {
  if (file.exists(archivo)) {
    objeto <- tryCatch(readRDS(archivo), error = function(e) stop(paste("Cache RDS ilegible:", archivo,
      ". No se reemplazo. Conserva o mueve ese archivo y vuelve a ejecutar."), call. = FALSE))
    fmp_exigir(isTRUE(validar(objeto)), paste("Cache no valida:", archivo))
    return(invisible(FALSE))
  }
  objeto <- crear()
  fmp_exigir(isTRUE(validar(objeto)), paste("La descarga no produjo el objeto esperado:", basename(archivo)))
  dir.create(dirname(archivo), recursive = TRUE, showWarnings = FALSE)
  temporal <- tempfile(".descarga_", tmpdir = dirname(archivo))
  on.exit(unlink(temporal), add = TRUE)
  saveRDS(objeto, temporal)
  fmp_exigir(file.rename(temporal, archivo), paste("No se pudo guardar:", archivo))
  invisible(TRUE)
}

fmp_descargar_entradas <- function(cfg) {
  rutas <- c(cfg$archivo_tcga, cfg$archivo_clinico_tcga, cfg$archivo_acrg)
  faltan <- !file.exists(rutas)
  if (!any(faltan)) return(invisible(NULL))
  fmp_exigir(!identical(cfg$download, "never"), paste("No se encuentra", basename(rutas[which(faltan)[1L]]),
    ". Habilita --download=missing para descargar las entradas."))
  # Fallar antes de una descarga larga si el unico archivo local no es legible.
  fmp_leer_clinica_acrg(cfg$archivo_clinico_acrg)
  dir.create(cfg$data_dir, recursive = TRUE, showWarnings = FALSE)
  options(timeout = max(3600, getOption("timeout")))
  ahora <- function() format(Sys.time(), "%Y-%m-%dT%H:%M:%SZ", tz = "UTC")
  creado <- rep(FALSE, 3L); fechas <- rep("", 3L)
  if (faltan[1L]) {
    message("Descarga TCGA-STAD: STAR - Counts abiertos; esta etapa puede tardar y ocupar varios GB.")
    query_file <- file.path(cfg$data_dir, "tcga_query.rds")
    fmp_cache_rds(query_file, function() TCGAbiolinks::GDCquery(project = "TCGA-STAD",
      data.category = "Transcriptome Profiling", data.type = "Gene Expression Quantification",
      workflow.type = "STAR - Counts", access = "open"), function(z) is.list(z))
    query <- readRDS(query_file)
    utils::write.csv(TCGAbiolinks::getResults(query), file.path(cfg$data_dir, "TCGA_query_resultados.csv"), row.names = FALSE)
    estado_gdc <- tryCatch(capture.output(str(TCGAbiolinks::getGDCInfo())), error = function(e) paste("Estado GDC no recuperado:", conditionMessage(e)))
    writeLines(c(paste("Consulta UTC:", ahora()), estado_gdc), file.path(cfg$data_dir, "GDC_estado_en_descarga.txt"))
    creado[1L] <- fmp_cache_rds(cfg$archivo_tcga, function() {
      directorio <- file.path(cfg$data_dir, "GDCdata")
      TCGAbiolinks::GDCdownload(query, directory = directorio, method = "api", files.per.chunk = 20)
      se <- TCGAbiolinks::GDCprepare(query, directory = directorio)
      ensayos <- SummarizedExperiment::assayNames(se)
      fmp_exigir("unstranded" %in% ensayos, paste("No se encontro unstranded. Ensayos:", paste(ensayos, collapse = ", ")))
      list(counts = as.matrix(SummarizedExperiment::assay(se, "unstranded")),
        sample_metadata = as.data.frame(SummarizedExperiment::colData(se)),
        provenance = list(source = "GDC/TCGA-STAD/STAR - Counts", assay = "unstranded",
          available_assays = ensayos, downloaded_UTC = ahora(), query_file = basename(query_file)))
    }, function(z) is.list(z) && is.matrix(z$counts) && is.numeric(z$counts) &&
      ncol(z$counts) > 0L && all(is.finite(z$counts) & z$counts >= 0) &&
      all(abs(z$counts - round(z$counts)) < 1e-6) && !is.null(colnames(z$counts)) &&
      all(grepl("^ENSG", rownames(z$counts))))
    fechas[1L] <- ahora()
  }
  if (faltan[2L]) {
    message("Descarga de clinica original TCGA-STAD desde GDC...")
    creado[2L] <- fmp_cache_rds(cfg$archivo_clinico_tcga,
      function() TCGAbiolinks::GDCquery_clinic(project = "TCGA-STAD", type = "clinical"),
      function(z) is.data.frame(z) && nrow(z) > 0L && all(c("submitter_id", "vital_status",
        "days_to_death", "days_to_last_follow_up") %in% names(z)))
    fechas[2L] <- ahora()
  }
  if (faltan[3L]) {
    message("Descarga de GSE62254/GPL570 desde GEO...")
    creado[3L] <- fmp_cache_rds(cfg$archivo_acrg, function() {
      args_geo <- list(GEO = "GSE62254", GSEMatrix = TRUE, destdir = cfg$data_dir)
      # Las versiones nuevas de GEOquery cambiaron el retorno por defecto.
      if ("returnType" %in% names(formals(GEOquery::getGEO))) args_geo$returnType <- "ExpressionSet"
      geo <- do.call(GEOquery::getGEO, args_geo)
      candidatos <- if (inherits(geo, "ExpressionSet")) list(geo) else geo
      idx <- which(vapply(candidatos, function(z) inherits(z, "ExpressionSet") && Biobase::annotation(z) == "GPL570", logical(1)))
      fmp_exigir(length(idx) == 1L, "GEO no devolvio una unica ExpressionSet GPL570.")
      candidatos[[idx]]
    }, function(z) inherits(z, "ExpressionSet") && Biobase::annotation(z) == "GPL570" &&
      ncol(Biobase::exprs(z)) > 0L && all(is.finite(Biobase::exprs(z))))
    fechas[3L] <- ahora()
  }
  tabla <- data.frame(file = basename(rutas), source = c("GDC STAR - Counts unstranded", "GDC clinical", "GEO GSE62254 GPL570"),
    downloaded_UTC = fechas, action = ifelse(creado, "downloaded_now", "existing_file_date_not_inferred"),
    md5 = unname(tools::md5sum(rutas)))
  archivo <- file.path(cfg$data_dir, "procedencia_descargas.csv")
  if (file.exists(archivo)) {
    anterior <- utils::read.csv(archivo, stringsAsFactors = FALSE)
    if (all(names(tabla) %in% names(anterior))) {
      j <- match(tabla$file, anterior$file)
      mantener <- !creado & !is.na(j) & tabla$md5 == anterior$md5[j]
      tabla$downloaded_UTC[mantener] <- anterior$downloaded_UTC[j[mantener]]
      tabla$action[mantener] <- "reused_cached_download"
    }
  }
  fmp_csv(tabla, archivo)
  writeLines(capture.output(utils::sessionInfo()), file.path(cfg$data_dir, "sessionInfo_descarga.txt"))
  invisible(tabla)
}

fmp_preparar_ejecucion <- function(cfg) {
  fmp_instalar_dependencias(cfg)
  if (cfg$stage %in% c("all", "lasso", "download")) fmp_descargar_entradas(cfg)
  invisible(NULL)
}

fmp_registrar_ejecucion <- function(cfg, resultado) {
  if (cfg$stage != "all") return(invisible(NULL))
  registros <- data.frame(stage = c("LASSO", "RSF", "OOB"),
    output_directory = c(resultado$folders$root, resultado$rsf$folders$root, resultado$oob$folders$root),
    completed_UTC = format(Sys.time(), "%Y-%m-%dT%H:%M:%SZ", tz = "UTC"))
  fmp_csv(registros, file.path(cfg$carpeta_salida, "ULTIMA_EJECUCION_COMPLETA.csv"))
  fmp_csv(registros, file.path(resultado$folders$docs, "ejecucion_completa.csv"))
  invisible(registros)
}


fmp_exigir <- function(condicion, mensaje) {
  if (!isTRUE(condicion)) stop(mensaje, call. = FALSE)
}

fmp_paquetes <- function() {
  paquetes <- c("DESeq2", "SummarizedExperiment", "AnnotationDbi",
    "org.Hs.eg.db", "glmnet", "survival", "ggplot2", "survminer",
    "GEOquery", "Biobase", "limma", "hgu133plus2.db", "readxl")
  faltantes <- paquetes[!vapply(paquetes, requireNamespace, logical(1), quietly = TRUE)]
  fmp_exigir(!length(faltantes), paste("Faltan paquetes:", paste(faltantes, collapse = ", "),
    ". El bloque inicial instala faltantes salvo --install=never. Consulta README.md."))
  fmp_exigir(requireNamespace("timeROC", quietly = TRUE), "Falta timeROC.")
  # Surv debe estar disponible para algunos metodos de supervivencia.
  suppressPackageStartupMessages(library("survival", character.only = TRUE))
  invisible(paquetes)
}

fmp_num <- function(x) suppressWarnings(as.numeric(as.character(x)))

fmp_csv <- function(x, archivo) {
  dir.create(dirname(archivo), recursive = TRUE, showWarnings = FALSE)
  utils::write.csv(x, archivo, row.names = FALSE, na = "")
  invisible(archivo)
}

fmp_rds <- function(x, archivo) {
  dir.create(dirname(archivo), recursive = TRUE, showWarnings = FALSE)
  saveRDS(x, archivo)
  invisible(archivo)
}

fmp_carpetas <- function(raiz) {
  # Cada ejecucion tiene su carpeta: no se mezclan ajustes diferentes.
  raiz <- path.expand(raiz)
  dir.create(raiz, recursive = TRUE, showWarnings = FALSE)
  id <- format(Sys.time(), "%Y%m%d_%H%M%S")
  salida <- file.path(raiz, paste0("replica_", id))
  if (dir.exists(salida)) salida <- tempfile(paste0("replica_", id, "_"), tmpdir = raiz)
  carpetas <- list(root = salida, tablas = file.path(salida, "tablas"),
    docs = file.path(salida, "docs"), privados = file.path(salida, "data_privada"),
    lasso = file.path(salida, "figuras", "01_LASSO"),
    tcga = file.path(salida, "figuras", "02_TCGA"),
    acrg = file.path(salida, "figuras", "03_ACRG"))
  for (d in carpetas) dir.create(d, recursive = TRUE, showWarnings = FALSE)
  writeLines(c("data_privada/", ".RData", ".Rhistory", ".Renviron"),
    file.path(salida, ".gitignore"))
  carpetas
}

fmp_estadio <- function(x) {
  z <- tolower(trimws(as.character(x)))
  z <- gsub("^(stage|estadio)[[:space:]]*", "", z)
  z <- gsub("[[:space:]]", "", z)
  z <- gsub("[abc]", "", z)
  z[z %in% c("1", "2", "3", "4")] <- c("i", "ii", "iii", "iv")[
    match(z[z %in% c("1", "2", "3", "4")], c("1", "2", "3", "4"))]
  factor(z, levels = c("i", "ii", "iii", "iv"))
}

fmp_leer_genes <- function(archivo) {
  d <- utils::read.csv(archivo, stringsAsFactors = FALSE, check.names = FALSE,
    fileEncoding = "UTF-8-BOM")
  fmp_exigir("gene" %in% names(d), "El CSV de candidatos requiere una columna gene.")
  g <- trimws(as.character(d$gene))
  fmp_exigir(length(g) == 216L && !anyNA(g) && all(nzchar(g)) && !anyDuplicated(g),
    "Se requieren los 216 candidatos originales, sin duplicados.")
  g
}

fmp_leer_firma <- function(archivo) {
  d <- utils::read.csv(archivo, stringsAsFactors = FALSE, check.names = FALSE,
    fileEncoding = "UTF-8-BOM")
  fmp_exigir(all(c("Gene", "Coefficient") %in% names(d)),
    "La referencia debe ser la tabla de coeficientes LASSO, con Gene y Coefficient; no la tabla de HR univariados.")
  d <- d[, c("Gene", "Coefficient"), drop = FALSE]
  d$Gene <- trimws(as.character(d$Gene)); d$Coefficient <- fmp_num(d$Coefficient)
  fmp_exigir(nrow(d) > 0 && !anyNA(d$Gene) && all(nzchar(d$Gene)) &&
    !anyDuplicated(d$Gene) && all(is.finite(d$Coefficient)) && all(d$Coefficient != 0),
    "La tabla de referencia tiene genes o coeficientes no validos.")
  d
}

fmp_importar_tcga <- function(archivo_conteos, archivo_clinico = "") {
  # Acepta el RDS crudo del primer bloque o un SummarizedExperiment original.
  # No suma Ensembl por simbolo: eso cambiaria el procedimiento original.
  objeto <- readRDS(archivo_conteos)
  if (inherits(objeto, "SummarizedExperiment")) {
    conteos <- SummarizedExperiment::assay(objeto)
    ensayo <- SummarizedExperiment::assayNames(objeto)[1L]
    clinica <- NULL
  } else {
    fmp_exigir(is.list(objeto) && "counts" %in% names(objeto),
      "Selecciona tcga_counts_metadata.rds o el SummarizedExperiment original con conteos crudos.")
    conteos <- objeto$counts; clinica <- objeto$clinical
    ensayo <- if (!is.null(objeto$provenance$assay)) objeto$provenance$assay else
      "counts del RDS; ensayo historico no recuperado"
  }
  if (nzchar(archivo_clinico)) clinica <- readRDS(archivo_clinico)
  fmp_exigir(!is.null(clinica), "Falta la tabla clinica TCGA original.")
  clinica <- as.data.frame(clinica)
  requeridas <- c("submitter_id", "vital_status", "days_to_death", "days_to_last_follow_up")
  fmp_exigir(all(requeridas %in% names(clinica)), paste(
    "Se requiere tcga_clinical_original.rds. Faltan:",
    paste(setdiff(requeridas, names(clinica)), collapse = ", ")))
  conteos <- as.matrix(conteos)
  fmp_exigir(is.numeric(conteos) && !is.null(rownames(conteos)) &&
    !is.null(colnames(conteos)) && all(is.finite(conteos)) && all(conteos >= 0) &&
    all(abs(conteos - round(conteos)) < 1e-6), "La matriz TCGA no contiene conteos crudos validos.")
  fmp_exigir(all(grepl("^ENSG", rownames(conteos))),
    "Se necesitan filas Ensembl originales; una matriz previamente sumada por simbolo no permite replicar este procedimiento.")
  fmp_exigir(!anyDuplicated(colnames(conteos)), "Hay barcodes de muestra duplicados.")
  clinica$submitter_id <- as.character(clinica$submitter_id)
  fmp_exigir(!anyNA(clinica$submitter_id) && !anyDuplicated(clinica$submitter_id),
    "Hay IDs clinicos TCGA ausentes o repetidos: resolver antes de unir.")

  # El original prioriza days_to_death cuando existe; se conserva esa regla.
  clinica$OS.time <- ifelse(is.na(fmp_num(clinica$days_to_death)),
    fmp_num(clinica$days_to_last_follow_up), fmp_num(clinica$days_to_death))
  estado <- tolower(trimws(as.character(clinica$vital_status)))
  fmp_exigir(all(is.na(estado) | estado %in% c("alive", "dead")),
    "vital_status tiene categorias distintas de Alive/Dead; no se reclasifican como vivos.")
  clinica$OS.event <- ifelse(estado == "dead", 1L, 0L)
  validos <- !is.na(clinica$OS.time) & !is.na(clinica$OS.event)
  clinica <- clinica[validos, , drop = FALSE]
  paciente_expr <- substr(colnames(conteos), 1L, 12L)
  clinica$sample_id <- substr(clinica$submitter_id, 1L, 12L)
  comunes <- intersect(paciente_expr, clinica$sample_id)
  mantener <- paciente_expr %in% comunes
  conteos <- conteos[, mantener, drop = FALSE]
  clinica <- clinica[match(paciente_expr[mantener], clinica$sample_id), , drop = FALSE]
  primarios <- substr(colnames(conteos), 14L, 15L) == "01"
  conteos <- conteos[, primarios, drop = FALSE]
  clinica <- clinica[primarios, , drop = FALSE]
  fmp_exigir(ncol(conteos) >= 20L &&
    identical(substr(colnames(conteos), 1L, 12L), as.character(clinica$sample_id)),
    "No quedaron suficientes tumores primarios correctamente alineados.")
  rownames(clinica) <- colnames(conteos)
  # Se mantiene el orden de entrada: no se ordenan barcodes antes de cv.glmnet.
  repetidos <- duplicated(clinica$sample_id)
  if (any(repetidos)) warning(
    "Hay varios tumores primarios del mismo paciente. Se conservan como en el original; revisar el informe de muestras antes de interpretar independencia.")
  if (!"gender" %in% names(clinica)) {
    alias <- c("sex_at_birth", "sex"); alias <- alias[alias %in% names(clinica)]
    if (length(alias)) clinica$gender <- clinica[[alias[1L]]]
  }
  if ("gender" %in% names(clinica)) clinica$gender <- factor(
    tolower(as.character(clinica$gender)), levels = c("female", "male"))
  clinica$stage_simple <- if ("ajcc_pathologic_stage" %in% names(clinica)) {
    fmp_estadio(clinica$ajcc_pathologic_stage)
  } else factor(rep(NA_character_, nrow(clinica)), levels = c("i", "ii", "iii", "iv"))
  clinica$OS.time_years <- clinica$OS.time / 365
  list(counts = conteos, clinical = clinica, assay = ensayo,
    repeated_patients = sum(repetidos), source = normalizePath(archivo_conteos))
}

fmp_preparar_tcga <- function(entrada, genes, carpetas) {
  conteos <- entrada$counts; clinica <- entrada$clinical
  # Mismo orden del original: filtro -> VST -> anotacion -> candidatos -> tiempo > 0.
  keep <- rowSums(conteos >= 10) >= (0.2 * ncol(conteos))
  fmp_exigir(sum(keep) > 1000L, "No hay suficientes genes expresados para vst() con sus valores originales.")
  dds <- DESeq2::DESeqDataSetFromMatrix(countData = conteos[keep, , drop = FALSE],
    colData = clinica, design = ~ 1)
  rownames(dds) <- sub("\\..*", "", rownames(dds))
  fmp_exigir(!anyDuplicated(rownames(dds)), "Ensembl repetidos tras retirar versiones; no se agregan silenciosamente.")
  dds <- DESeq2::estimateSizeFactors(dds)
  vsd <- DESeq2::vst(dds, blind = TRUE)
  expr <- SummarizedExperiment::assay(vsd)
  simbolos <- AnnotationDbi::mapIds(org.Hs.eg.db::org.Hs.eg.db,
    keys = rownames(expr), column = "SYMBOL", keytype = "ENSEMBL", multiVals = "first")
  simbolos <- unname(simbolos[rownames(expr)])
  anotados <- !is.na(simbolos)
  primeros <- !duplicated(simbolos[anotados])
  filas <- which(anotados)[primeros]
  mapa <- data.frame(ENSEMBL = rownames(expr), SYMBOL = simbolos,
    retained_first_symbol_row = seq_len(nrow(expr)) %in% filas)
  expr <- expr[filas, , drop = FALSE]; rownames(expr) <- simbolos[filas]
  # %in% conserva el orden de las filas originales; [genes, ] las reordenaria.
  expr_lasso <- expr[rownames(expr) %in% genes, , drop = FALSE]
  cobertura <- data.frame(gene = genes, found_after_original_filter = genes %in% rownames(expr))
  fmp_csv(cobertura, file.path(carpetas$tablas, "TCGA_cobertura_216_original.csv"))
  fmp_csv(mapa, file.path(carpetas$tablas, "TCGA_anotacion_original.csv"))
  fmp_exigir(nrow(expr_lasso) >= 2L, "Menos de dos candidatos tras el filtro original.")
  valid_idx <- is.finite(clinica$OS.time) & clinica$OS.time > 0
  x <- t(expr_lasso)[valid_idx, , drop = FALSE]
  clinica <- clinica[valid_idx, , drop = FALSE]
  fmp_exigir(identical(rownames(x), rownames(clinica)) && all(is.finite(x)),
    "La expresion VST y la clinica no estan alineadas.")
  y <- survival::Surv(clinica$OS.time, clinica$OS.event)
  resumen <- data.frame(source = entrada$source, assay = entrada$assay,
    samples_before_positive_time = ncol(conteos), samples_model = nrow(x),
    patients_model = length(unique(clinica$sample_id)), deaths = sum(clinica$OS.event),
    count_rows_input = nrow(conteos), rows_after_counts_filter = sum(keep),
    rows_after_annotation = nrow(expr), candidate_genes_eligible = ncol(x),
    candidate_genes_requested = length(genes))
  fmp_csv(resumen, file.path(carpetas$tablas, "TCGA_preparacion_resumen.csv"))
  # IDs y matrices se guardan unicamente en data_privada/.
  fmp_rds(list(x = x, clinical = clinica, y = y, gene_annotation = mapa,
    vst = vsd, normalization_dataset = dds, input_summary = resumen),
    file.path(carpetas$privados, "TCGA_preparado_original.rds"))
  fmp_csv(data.frame(sample_id = rownames(x), patient_id = clinica$sample_id,
    cv_input_order = seq_len(nrow(x))), file.path(carpetas$privados, "TCGA_orden_modelo.csv"))
  list(x = x, y = y, clinical = clinica, coverage = cobertura, summary = resumen)
}

fmp_ajustar_lasso <- function(datos, carpetas) {
  # Se usa cv.glmnet original. keep=TRUE solo conserva los folds/predicciones
  # auxiliares; los KM posteriores son del ajuste completo, NO son OOF.
  set.seed(123)
  cvfit <- glmnet::cv.glmnet(datos$x, datos$y, family = "cox", alpha = 1,
    nfolds = 10, type.measure = "deviance", standardize = TRUE, keep = TRUE)
  beta <- as.matrix(stats::coef(cvfit, s = "lambda.min"))[, 1L]
  seleccion <- beta != 0
  firma <- data.frame(Gene = names(beta)[seleccion], Coefficient = unname(beta[seleccion]),
    Direction = ifelse(beta[seleccion] > 0, "Risk", "Protective"), row.names = NULL)
  fmp_exigir(nrow(firma) > 0L, "lambda.min selecciono cero genes. No se cambia lambda para forzar una firma.")
  fmp_csv(firma, file.path(carpetas$tablas, "LASSO_Cox_signature_lambda_min.csv"))
  fmp_csv(data.frame(lambda_min = cvfit$lambda.min, lambda_1se = cvfit$lambda.1se,
    selected_genes = nrow(firma), seed = 123L, nfolds = 10L,
    criterion = "partial_likelihood_deviance", alpha = 1),
    file.path(carpetas$tablas, "LASSO_parametros_originales.csv"))
  resultado <- list(cvfit = cvfit, signature = firma, beta_all = beta)
  fmp_rds(resultado, file.path(carpetas$privados, "LASSO_modelo_reestimado.rds"))
  resultado
}

fmp_comparar_firmas <- function(actual, referencia, tolerancia = 1e-6) {
  genes <- union(referencia$Gene, actual$Gene)
  esperado <- referencia$Coefficient[match(genes, referencia$Gene)]
  obtenido <- actual$Coefficient[match(genes, actual$Gene)]
  diferencia <- abs(obtenido - esperado)
  tabla <- data.frame(Gene = genes, Coefficient_original = esperado,
    Coefficient_reestimated = obtenido, absolute_difference = diferencia,
    status = ifelse(is.na(esperado), "GEN_NUEVO", ifelse(is.na(obtenido),
      "GEN_ORIGINAL_NO_SELECCIONADO", ifelse(diferencia <= tolerancia,
      "COINCIDE_A_TOLERANCIA", "COEFICIENTE_DIFERENTE"))))
  list(table = tabla, matches = setequal(actual$Gene, referencia$Gene) &&
    all(is.finite(diferencia)) && all(diferencia <= tolerancia))
}

fmp_puntuar <- function(x, firma, estandarizar = FALSE) {
  fmp_exigir(!is.null(colnames(x)) && all(firma$Gene %in% colnames(x)),
    "Faltan genes de la firma en la matriz. No se eliminan ni imputan.")
  score <- as.vector(x[, firma$Gene, drop = FALSE] %*% firma$Coefficient)
  fmp_exigir(all(is.finite(score)), "El puntaje contiene valores no finitos.")
  if (estandarizar) {
    fmp_exigir(length(score) > 1 && stats::sd(score) > 0,
      "No se puede estandarizar un puntaje constante o un unico paciente.")
    score <- as.numeric(scale(score))
  }
  score
}

fmp_grupos <- function(score, corte = stats::median(score), regla = ">=") {
  fmp_exigir(all(is.finite(score)) && length(corte) == 1L && is.finite(corte),
    "Puntajes o corte no validos.")
  alto <- if (regla == ">=") score >= corte else if (regla == ">") score > corte else {
    stop("La regla debe ser >= o >.", call. = FALSE)
  }
  factor(ifelse(alto, "High risk", "Low risk"), levels = c("Low risk", "High risk"))
}

fmp_dispositivo <- function(nombre, dibujo, ancho = 8, alto = 6, dpi = 300) {
  dir.create(dirname(nombre), recursive = TRUE, showWarnings = FALSE)
  for (tipo in c("pdf", "png")) {
    if (tipo == "pdf") grDevices::pdf(paste0(nombre, ".pdf"), width = ancho, height = alto)
    else grDevices::png(paste0(nombre, ".png"), width = ancho, height = alto,
      units = "in", res = dpi, bg = "white")
    tryCatch(dibujo(), finally = grDevices::dev.off())
  }
  invisible(nombre)
}

fmp_trayectorias_lasso <- function(ajuste, carpetas) {
  fit <- ajuste$cvfit
  firma <- ajuste$signature
  b <- as.matrix(fit$glmnet.fit$beta)
  lambdas <- fit$glmnet.fit$lambda
  fmp_exigir(ncol(b) == length(lambdas) && all(is.finite(lambdas) & lambdas > 0) &&
    all(firma$Gene %in% rownames(b)), "Trayectorias LASSO incompatibles con la firma.")
  datos <- data.frame(Gene = rep(rownames(b), times = ncol(b)),
    minus_log_lambda = rep(-log(lambdas), each = nrow(b)),
    Coefficient = as.vector(b), stringsAsFactors = FALSE)
  genes <- firma$Gene
  seleccion <- datos[datos$Gene %in% genes, , drop = FALSE]
  seleccion$Gene <- factor(seleccion$Gene, levels = genes)
  punto <- data.frame(Gene = factor(genes, levels = genes),
    minus_log_lambda = -log(fit$lambda.min), Coefficient = firma$Coefficient)
  colores_base <- c("#0072B2", "#D55E00", "#009E73", "#CC79A7",
    "#E69F00", "#56B4E9", "#000000", "#999933")
  colores <- if (length(genes) <= length(colores_base)) colores_base[seq_along(genes)] else {
    grDevices::hcl.colors(length(genes), palette = "Dark 3")
  }
  names(colores) <- genes
  p <- ggplot2::ggplot() +
    ggplot2::geom_line(data = datos,
      ggplot2::aes(x = minus_log_lambda, y = Coefficient, group = Gene),
      colour = "grey78", linewidth = .25, alpha = .65) +
    ggplot2::geom_line(data = seleccion,
      ggplot2::aes(x = minus_log_lambda, y = Coefficient, colour = Gene, group = Gene),
      linewidth = .8) +
    ggplot2::geom_vline(xintercept = -log(fit$lambda.min), linetype = "dashed",
      colour = "grey20", linewidth = .5) +
    ggplot2::geom_point(data = punto,
      ggplot2::aes(x = minus_log_lambda, y = Coefficient, colour = Gene),
      size = 1.7, show.legend = FALSE) +
    ggplot2::scale_colour_manual(values = colores, breaks = genes,
      name = paste0("Firma final (", length(genes), " genes)")) +
    ggplot2::labs(title = "LASSO-Cox: trayectoria de coeficientes",
      x = expression(-log(lambda)), y = "Coeficiente por unidad VST",
      caption = paste0("Gris: candidatos restantes. Color: genes seleccionados en lambda.min.\n",
        "Linea vertical: lambda.min; puntos: coeficientes del modelo final.")) +
    ggplot2::theme_classic(base_size = 13) +
    ggplot2::theme(legend.position = "right", legend.text = ggplot2::element_text(size = 10),
      plot.caption = ggplot2::element_text(size = 9, hjust = 0),
      plot.title = ggplot2::element_text(size = 14))
  fmp_dispositivo(file.path(carpetas$lasso, "LASSO_Coefficient_Path_lambda_min"),
    function() print(p), 10, 6.5)
  fmp_csv(datos, file.path(carpetas$tablas, "LASSO_trayectorias_coeficientes.csv"))
  invisible(p)
}

fmp_figuras_lasso <- function(ajuste, carpetas) {
  fit <- ajuste$cvfit; firma <- ajuste$signature
  # Estos son los metodos de plot utilizados en el script original.
  fmp_dispositivo(file.path(carpetas$lasso, "LASSO_CV_plot"), function() plot(fit), 7, 6)
  fmp_trayectorias_lasso(ajuste, carpetas)
  d <- firma[order(firma$Coefficient), , drop = FALSE]
  d$Gene <- factor(d$Gene, levels = d$Gene)
  p <- ggplot2::ggplot(d, ggplot2::aes(x = Coefficient, y = Gene, fill = Direction)) +
    ggplot2::geom_col(width = .7) + ggplot2::geom_vline(xintercept = 0, linetype = "dashed") +
    ggplot2::scale_fill_manual(values = c(Risk = "#C0392B", Protective = "#2E86C1")) +
    ggplot2::labs(x = "LASSO-Cox coefficient (VST unit)", y = NULL, fill = NULL) +
    ggplot2::theme_classic(base_size = 14) + ggplot2::theme(legend.position = "bottom")
  fmp_dispositivo(file.path(carpetas$lasso, "LASSO_coeficientes"), function() print(p), 8, 5)
}

fmp_cox_tabla <- function(fit, cohort, population, purpose) {
  s <- summary(fit)
  data.frame(cohort = cohort, population = population, purpose = purpose,
    term = rownames(s$coefficients), coefficient = s$coefficients[, "coef"],
    HR = s$conf.int[, "exp(coef)"], lower_95 = s$conf.int[, "lower .95"],
    upper_95 = s$conf.int[, "upper .95"], p_wald = s$coefficients[, "Pr(>|z|)"],
    n = fit$n, events = fit$nevent, row.names = NULL)
}

fmp_forest_genes <- function(datos, ajuste, carpetas) {
  filas <- lapply(ajuste$signature$Gene, function(g) {
    d <- datos$clinical; d$expression <- datos$x[, g]
    fit <- survival::coxph(survival::Surv(OS.time_years, OS.event) ~ expression, data = d)
    s <- summary(fit)
    data.frame(Gene = g, HR = s$conf.int[1L, "exp(coef)"],
      lower = s$conf.int[1L, "lower .95"], upper = s$conf.int[1L, "upper .95"],
      pval = s$coefficients[1L, "Pr(>|z|)"])
  })
  d <- do.call(rbind, filas)
  fmp_csv(d, file.path(carpetas$tablas, "Firma_pronostica_Cox_univariado_por_gen.csv"))
  d <- d[order(d$HR), , drop = FALSE]; d$Gene <- factor(d$Gene, levels = rev(d$Gene))
  p <- ggplot2::ggplot(d, ggplot2::aes(x = HR, y = Gene)) +
    ggplot2::geom_point(size = 3) + ggplot2::geom_errorbarh(
      ggplot2::aes(xmin = lower, xmax = upper), height = .2, linewidth = .6) +
    ggplot2::geom_vline(xintercept = 1, linetype = "dashed") + ggplot2::scale_x_log10() +
    ggplot2::labs(x = "Hazard ratio (univariate Cox)", y = NULL) +
    ggplot2::theme_classic(base_size = 14) + ggplot2::theme(
      axis.line.y = ggplot2::element_blank(), axis.ticks.y = ggplot2::element_blank())
  fmp_dispositivo(file.path(carpetas$lasso, "ForestPlot_genes_seleccionados"), function() print(p), 8, 5)
  invisible(d)
}

fmp_indices_roc <- function(tiempos_objeto, tiempos_solicitados) {
  # timeROC agrega el tiempo cero cuando se solicita un unico horizonte.
  # Se extrae por tiempo, nunca se presupone que AUC[1] corresponde al anio.
  j <- match(tiempos_solicitados, tiempos_objeto)
  fmp_exigir(!anyNA(j), "timeROC no devolvio todos los tiempos solicitados.")
  j
}

fmp_evaluar <- function(clinica, cohort, population, carpeta_figuras, carpetas,
    tiempos = 1, corte = NULL, regla = ">=", hacer_ajustado = FALSE) {
  d <- clinica
  etiqueta <- paste(cohort, population, sep = "_")
  if (!nrow(d)) return(list(summary = data.frame(cohort = cohort, population = population,
    n = 0, events = 0, cutoff = NA_real_, low_n = 0, high_n = 0,
    logrank_p = NA_real_, C_Harrell_frozen = NA_real_, C_Harrell_SE = NA_real_,
    status = "sin_pacientes"), timeROC = data.frame()))
  fmp_exigir(all(is.finite(d$risk_score)) && all(is.finite(d$OS.time_years)) &&
    all(d$OS.time_years > 0) && all(d$OS.event %in% c(0, 1)),
    "Hay entradas de supervivencia o puntaje no validas.")
  if (is.null(corte)) corte <- stats::median(d$risk_score)
  d$risk_group <- fmp_grupos(d$risk_score, corte, regla)
  grupos <- table(d$risk_group); dos <- all(grupos > 0)
  p_logrank <- NA_real_
  if (dos && sum(d$OS.event) > 0) {
    lr <- survival::survdiff(survival::Surv(OS.time_years, OS.event) ~ risk_group, data = d)
    p_logrank <- stats::pchisq(lr$chisq, df = 1, lower.tail = FALSE)
  }
  d$risk_group <- droplevels(d$risk_group)
  fit_km <- survival::survfit(survival::Surv(OS.time_years, OS.event) ~ risk_group, data = d)
  colores <- c("Low risk" = "#2E86C1", "High risk" = "#C0392B")
  km <- survminer::ggsurvplot(fit_km, data = d, risk.table = TRUE,
    pval = if (is.finite(p_logrank)) p_logrank else FALSE, conf.int = FALSE,
    palette = unname(colores[levels(d$risk_group)]),
    legend.title = "Risk group", legend.labs = levels(d$risk_group),
    xlab = "Time (years)", ylab = "Overall survival probability",
    title = paste(cohort, population, sep = " | "), break.time.by = 1,
    surv.median.line = "hv", risk.table.height = .25,
    ggtheme = ggplot2::theme_classic(base_size = 14))
  fmp_dispositivo(file.path(carpeta_figuras, paste0("KM_", population)),
    function() print(km, newpage = TRUE), 8, 7)
  fmp_dispositivo(file.path(carpeta_figuras, paste0("KM_", population, "_solo_curva")),
    function() print(km$plot), 8, 6)
  fmp_rds(list(clinical_scored = d, KM = fit_km),
    file.path(carpetas$privados, paste0(etiqueta, "_KM_y_puntajes.rds")))

  # Concordancia del marcador congelado: no se estima un coeficiente nuevo
  # que invierta automaticamente la direccion del riesgo.
  cc <- survival::concordance(survival::Surv(OS.time_years, OS.event) ~ risk_score,
    data = d, reverse = TRUE)
  resumen <- data.frame(cohort = cohort, population = population, n = nrow(d),
    events = sum(d$OS.event), cutoff = corte, low_n = unname(grupos[1L]),
    high_n = unname(grupos[2L]), logrank_p = p_logrank,
    C_Harrell_frozen = unname(cc$concordance), C_Harrell_SE = sqrt(cc$var),
    status = if (dos) "dos_grupos" else "un_solo_grupo_logrank_no_estimable")
  fmp_csv(resumen, file.path(carpetas$tablas, paste0(etiqueta, "_KM_Cindex.csv")))
  if (stats::sd(d$risk_score) > 0 && sum(d$OS.event) > 0) {
    cox <- survival::coxph(survival::Surv(OS.time_years, OS.event) ~ risk_score, data = d)
    fmp_csv(fmp_cox_tabla(cox, cohort, population,
      "asociacion_del_puntaje; no_reestima_la_firma"),
      file.path(carpetas$tablas, paste0(etiqueta, "_Cox_puntaje.csv")))
    s <- summary(cox)
    fmp_csv(data.frame(cohort = cohort, population = population,
      C_Harrell_from_refitted_Cox = unname(s$concordance[1L]),
      SE = unname(s$concordance[2L]),
      purpose = "replica_summary_cox; no_comparar_con_marcador_fijo_si_se_invierte_el_signo"),
      file.path(carpetas$tablas, paste0(etiqueta, "_Cindex_Cox_asociacion.csv")))
  }
  if (hacer_ajustado) fmp_cox_ajustado(d, cohort, population, carpetas)

  roc_filas <- list(); objetos <- list()
  for (t in tiempos) {
    casos <- sum(d$OS.event == 1 & d$OS.time_years <= t)
    controles <- sum(d$OS.time_years > t)
    estado <- if (casos < 2L || controles < 2L) "soporte_insuficiente" else "OK"
    auc <- inferior <- superior <- NA_real_
    if (estado == "OK") {
      roc <- timeROC::timeROC(T = d$OS.time_years, delta = d$OS.event,
        marker = d$risk_score, cause = 1, weighting = "marginal", times = t, iid = TRUE)
      j <- fmp_indices_roc(roc$times, t)
      auc <- roc$AUC[j]
      if (!is.finite(auc)) estado <- "AUC_no_estimable"
      if (is.finite(auc)) {
        # confint.timeROC devuelve limites en porcentaje en las versiones
        # originales de timeROC; se conserva la escala segun el codigo del metodo.
        ci <- tryCatch(stats::confint(roc), error = function(e) {
          warning("IC de timeROC no disponible: ", conditionMessage(e)); NULL
        })
        if (!is.null(ci) && !is.null(ci$CI_AUC)) {
          limites <- as.matrix(ci$CI_AUC)
          jj <- if (nrow(limites) == length(roc$times)) j else {
            match(t, roc$times[roc$times != 0])
          }
          if (length(jj) == 1L && !is.na(jj) && jj <= nrow(limites)) {
            # La unidad del metodo se comprueba por la implementacion instalada,
            # no se infiere a partir de si un limite es mayor que uno.
            unidad <- fmp_unidad_ic_timeROC()
            inferior <- limites[jj, 1L] / unidad
            superior <- limites[jj, 2L] / unidad
          }
        }
        objetos[[as.character(t)]] <- roc
        fmp_dispositivo(file.path(carpeta_figuras, paste0("timeROC_", population, "_", t, "anio")),
          function() {
            plot(roc, time = t, col = "#1B9E77", lwd = 2, title = FALSE)
            graphics::legend("bottomright", legend = paste0(t, "-year AUC = ", round(auc, 3)),
              col = "#1B9E77", lwd = 2, bty = "n")
          }, 6, 6)
      }
    }
    roc_filas[[length(roc_filas) + 1L]] <- data.frame(cohort = cohort, population = population,
      horizon_years = t, n = nrow(d), deaths_by_horizon = casos,
      observed_beyond_horizon = controles,
      censored_by_horizon = sum(d$OS.event == 0 & d$OS.time_years <= t),
      AUC = auc, lower_95 = inferior, upper_95 = superior, status = estado)
  }
  tabla_roc <- do.call(rbind, roc_filas)
  fmp_csv(tabla_roc, file.path(carpetas$tablas, paste0(etiqueta, "_timeROC.csv")))
  fmp_rds(objetos, file.path(carpetas$privados, paste0(etiqueta, "_timeROC.rds")))
  list(summary = resumen, timeROC = tabla_roc)
}

fmp_unidad_ic_timeROC <- function() {
  # timeROC 0.4/0.4.1 multiplica CI_AUC por 100. Una version nueva debe
  # verificarse expresamente antes de publicar un IC en otra escala.
  version <- as.character(utils::packageVersion("timeROC"))
  if (version %in% c("0.4", "0.4.1")) return(100)
  warning("No se reconoce la unidad de confint.timeROC; los IC quedan pendientes de revision.")
  NA_real_
}

fmp_cox_ajustado <- function(d, cohort, population, carpetas) {
  if (!all(c("age_years", "gender", "stage_simple") %in% names(d))) return(invisible(NULL))
  d <- d[stats::complete.cases(d[, c("OS.time_years", "OS.event", "risk_score",
    "age_years", "gender", "stage_simple")]), , drop = FALSE]
  d$gender <- droplevels(d$gender); d$stage_simple <- droplevels(d$stage_simple)
  if (nrow(d) < 10L || nlevels(d$gender) < 2L || nlevels(d$stage_simple) < 2L ||
      sum(d$OS.event) < 5L) return(invisible(NULL))
  fit <- survival::coxph(survival::Surv(OS.time_years, OS.event) ~
    risk_score + age_years + gender + stage_simple, data = d)
  fmp_csv(fmp_cox_tabla(fit, cohort, population,
    "asociacion_ajustada; no_prediccion_externa_del_modelo_combinado"),
    file.path(carpetas$tablas, paste0(cohort, "_", population, "_Cox_ajustado.csv")))
  invisible(fit)
}

fmp_preparar_acrg <- function(archivo_geo, archivo_clinico, carpetas) {
  objeto <- readRDS(archivo_geo)
  if (inherits(objeto, "ExpressionSet")) eset <- objeto else {
    fmp_exigir(is.list(objeto), "Selecciona GSE62254_eset.rds, no la matriz de genes ya procesada.")
    elegir <- which(vapply(objeto, function(z) inherits(z, "ExpressionSet") &&
      Biobase::annotation(z) == "GPL570", logical(1)))
    fmp_exigir(length(elegir) == 1L, "No se identifica una unica plataforma GPL570 de ACRG.")
    eset <- objeto[[elegir]]
  }
  fmp_exigir(Biobase::annotation(eset) == "GPL570", "Se esperaba ACRG/GPL570.")
  expr_raw <- Biobase::exprs(eset); pd <- Biobase::pData(eset)
  fmp_exigir(all(is.finite(expr_raw)) && !anyDuplicated(colnames(expr_raw)),
    "La matriz original ACRG contiene valores no finitos o muestras duplicadas.")
  # Replica historica: quantile -> log2 si max > 50 -> media por simbolo.
  # GSE62254 procesado esta documentado como RMA log10; en la ejecucion
  # confirmada max<=50 y NO se aplico otro log. No cambia el calculo original.
  expr_norm <- limma::normalizeBetweenArrays(expr_raw, method = "quantile")
  hizo_log2 <- max(expr_norm) > 50
  if (hizo_log2) expr_norm <- log2(expr_norm + 1)
  simbolos <- AnnotationDbi::mapIds(hgu133plus2.db::hgu133plus2.db,
    keys = rownames(expr_norm), column = "SYMBOL", keytype = "PROBEID", multiVals = "first")
  simbolos <- unname(simbolos[rownames(expr_norm)])
  conservar <- !is.na(simbolos)
  grupos <- simbolos[conservar]
  expr <- rowsum(expr_norm[conservar, , drop = FALSE], group = grupos, reorder = TRUE)
  n_sondas <- as.numeric(table(factor(grupos, levels = rownames(expr))))
  expr <- expr / n_sondas
  pd <- pd[match(colnames(expr), rownames(pd)), , drop = FALSE]
  fmp_exigir("patient:ch1" %in% names(pd), "ACRG no contiene patient:ch1.")
  id_geo <- fmp_num(gsub("patient: ", "", pd[["patient:ch1"]], fixed = TRUE))
  cl <- fmp_leer_clinica_acrg(archivo_clinico)
  names(cl) <- trimws(gsub("[[:space:]]+", " ", names(cl)))
  fmp_exigir(all(c("Tumor ID", "OS (months)") %in% names(cl)),
    "Faltan Tumor ID u OS (months) en el suplemento ACRG.")
  fu_col <- grep("^FU status", names(cl), value = TRUE)
  fmp_exigir(length(fu_col) == 1L, "No se identifica de forma unica FU status.")
  id_cl <- fmp_num(trimws(as.character(cl[["Tumor ID"]])))
  fmp_exigir(!anyDuplicated(id_geo[!is.na(id_geo)]) && !anyDuplicated(id_cl[!is.na(id_cl)]),
    "Hay pacientes ACRG duplicados.")
  j <- match(id_geo, id_cl); cl <- cl[j, , drop = FALSE]
  fu <- fmp_num(cl[[fu_col]])
  evento <- ifelse(fu %in% c(2, 3, 4), 1L, ifelse(fu %in% c(0, 1), 0L, NA_integer_))
  dias <- fmp_num(cl[["OS (months)"]]) * 30.44
  validos <- !is.na(j) & is.finite(dias) & dias > 0 & !is.na(evento)
  d <- data.frame(sample_id = colnames(expr)[validos], patient_id = id_geo[validos],
    OS.time = dias[validos], OS.time_years = dias[validos] / 365,
    OS.event = evento[validos], row.names = colnames(expr)[validos])
  d$stage_simple <- if ("pStage" %in% names(cl)) fmp_estadio(cl$pStage[validos]) else {
    factor(rep(NA_character_, nrow(d)), levels = c("i", "ii", "iii", "iv"))
  }
  if ("age" %in% names(cl)) d$age_years <- fmp_num(cl$age[validos])
  if ("sex" %in% names(cl)) {
    sexo <- tolower(as.character(cl$sex[validos]))
    sexo[sexo == "f"] <- "female"; sexo[sexo == "m"] <- "male"
    d$gender <- factor(sexo, levels = c("female", "male"))
  }
  expr <- expr[, validos, drop = FALSE]
  resumen <- data.frame(cohort = "ACRG", n = nrow(d), deaths = sum(d$OS.event),
    quantile_normalization = TRUE, additional_log2 = hizo_log2,
    time_conversion = "months * 30.44 / 365; equivalencia exacta con el script original")
  resultado <- list(expression = expr, clinical = d, summary = resumen)
  fmp_rds(resultado, file.path(carpetas$privados, "ACRG_expresion_completa_preparada.rds"))
  resultado
}

fmp_importar_acrg <- function(archivo_geo, archivo_clinico, firma, carpetas) {
  entrada <- fmp_preparar_acrg(archivo_geo, archivo_clinico, carpetas)
  expr <- entrada$expression; d <- entrada$clinical
  cobertura <- data.frame(Gene = firma$Gene, present_ACRG = firma$Gene %in% rownames(expr))
  fmp_csv(cobertura, file.path(carpetas$tablas, "ACRG_cobertura_firma_original.csv"))
  fmp_exigir(all(cobertura$present_ACRG), paste("Firma incompleta en ACRG:",
    paste(cobertura$Gene[!cobertura$present_ACRG], collapse = ", ")))
  x <- t(expr[firma$Gene, , drop = FALSE])
  d$risk_score_raw <- fmp_puntuar(x, firma)
  d$risk_score <- fmp_puntuar(x, firma, estandarizar = TRUE)
  fmp_exigir(identical(rownames(x), rownames(d)), "ACRG: expresion y clinica desalineadas.")
  resumen <- entrada$summary
  resumen$score_scale <- "scale(score) en ACRG; no normalizacion por gen"
  fmp_csv(resumen, file.path(carpetas$tablas, "ACRG_preparacion_resumen.csv"))
  fmp_rds(list(x = x, clinical = d, signature = firma,
    score_center = mean(d$risk_score_raw), score_sd = stats::sd(d$risk_score_raw)),
    file.path(carpetas$privados, "ACRG_preparado_original.rds"))
  list(x = x, clinical = d, summary = resumen, expression = expr)
}

fmp_comparar_metricas <- function(obtenidas, archivo_referencia, carpeta) {
  # Referencia opcional: cohort,population,metric,estimate,tolerance.
  # Sin valores historicos no se declara que TODOS los resultados coinciden.
  if (!nzchar(archivo_referencia)) {
    estado <- data.frame(status = "PENDIENTE_REFERENCIAS_NUMERICAS_DE_KM_AUC_CINDEX",
      detail = "Se comparan genes/coeficientes; faltan valores historicos para certificar todos los resultados.")
    fmp_csv(estado, file.path(carpeta, "comparacion_metricas_originales.csv"))
    return(FALSE)
  }
  ref <- utils::read.csv(archivo_referencia, stringsAsFactors = FALSE)
  fmp_exigir(all(c("cohort", "population", "metric", "estimate", "tolerance") %in% names(ref)),
    "La referencia de metricas no tiene el formato documentado.")
  claves <- function(d) paste(d$cohort, d$population, d$metric, sep = "|")
  j <- match(claves(ref), claves(obtenidas))
  ref$obtained <- obtenidas$estimate[j]
  ref$absolute_difference <- abs(ref$obtained - ref$estimate)
  ref$status <- ifelse(!is.finite(ref$estimate) | !is.finite(ref$obtained),
    "NO_COMPROBADO", ifelse(ref$absolute_difference <= ref$tolerance, "COINCIDE", "DIFIERE"))
  fmp_csv(ref, file.path(carpeta, "comparacion_metricas_originales.csv"))
  nrow(ref) > 0 && all(ref$status == "COINCIDE")
}

fmp_documentar <- function(cfg, carpetas, coincidencia, estado, advertencias) {
  texto <- c("# Replica LASSO-Cox original: fase 1", "",
    paste("Estado:", estado), paste("Coincidencia de genes y coeficientes:", coincidencia), "",
    "## Metodo conservado", "216 candidatos; filtro >=10 conteos en >=20% de muestras.",
    "DESeq2: estimateSizeFactors + vst(blind=TRUE), antes de excluir tiempos <=0.",
    "Ensembl -> SYMBOL con org.Hs.eg.db; primera fila por simbolo DESPUES de VST.",
    "cv.glmnet Cox: alpha=1, 10 folds, semilla 123, deviance, lambda.min.",
    "Sin CV anidada, sin rangos, sin sumas previas de conteos por simbolo.",
    "Puntaje = expresion VST por coeficientes LASSO; no probabilidad al anio.",
    "TCGA: KM aparente del modelo final en sus pacientes de desarrollo; no es OOF.",
    "ACRG: senal RMA log10 documentada en GEO; quantile adicional y media de sondas.",
    "Se conserva la regla historica log2 si max>50; en la ejecucion confirmada no se aplico.",
    "ACRG: se estandariza el puntaje completo con scale(), como en el script GEO.",
    "KM TCGA: mediana de TCGA; TCGA I-II: mediana dentro de I-II.",
    "KM ACRG: mediana de ACRG; ACRG I-II: conserva la mediana global ACRG (script GEO original).",
    "Alto >= mediana; Bajo < mediana. No se selecciona corte por p minimo.",
    "KM usa supervivencia global completa. timeROC usa marcador continuo y censura marginal.",
    paste("Horizontes timeROC en anios:", paste(cfg$tiempos_roc, collapse = ", ")),
    "TCGA: dias/365. ACRG: meses*30.44/365, conservando la conversion historica.", "",
    "## Interpretacion", "La mediana de cada cohorte describe riesgo relativo; no valida un umbral clinico transportable.",
    "La estandarizacion del puntaje ACRG usa la cohorte; no constituye una regla absoluta para un paciente aislado.",
    "El C de Harrell del marcador fijo se separa del C de un Cox de asociacion reestimado.",
    "Los HR por gen del forest son Cox univariados; no son coeficientes LASSO ni efectos causales.",
    "La significacion de KM en TCGA puede ser optimista por reutilizar los pacientes de desarrollo.",
    "ACRG se ha examinado previamente: es una evaluacion externa exploratoria, no ciega.",
    "No se garantiza equivalencia de unidades VST y microarreglos RMA log10; una AUC favorable no demuestra calibracion.",
    "Se registra la presencia de muestras repetidas por paciente sin cambiar silenciosamente el original.", "",
    "## Reproduccion", "La coincidencia numerica requiere datos, orden de muestras/genes, anotacion y versiones equivalentes.",
    "La referencia actual contiene ocho genes confirmados con la ejecucion manual del autor.",
    "La tabla previa de diez genes queda como antecedente y no es la referencia activa.",
    "No se sustituyen coeficientes reestimados por los historicos para forzar coincidencia.",
    "Sin metricas historicas no se declara reproduccion de todos los KM/AUC/C-index.",
    "Un solo maestro genera todas las entradas intermedias y los resultados de esta fase.",
    "Este directorio corresponde al bloque LASSO. RSF usa este resultado sin modificarlo.",
    "La etapa all ejecuta despues RSF; la etapa rsf permite ejecutar solo ese bloque.", "",
    "## Archivos", "tablas/: resultados agregados y comparacion con la referencia.",
    "figuras/01_LASSO, 02_TCGA y 03_ACRG: PDF y PNG; KM incluye tabla de riesgo.",
    "data_privada/: matrices, IDs, objetos de modelos y folds; excluir del repositorio.",
    "TCGA_modelo_y_entradas.rds se genera automaticamente antes de las figuras.",
    "docs/: configuracion, advertencias, procedencia y sessionInfo.", "",
    "## Uso de IA", "Funciones y organizacion tecnica elaboradas con asistencia de ChatGPT/Codex.",
    "La formulacion cientifica y revision de resultados corresponden al autor del proyecto.")
  writeLines(texto, file.path(carpetas$root, "README.md"))
  writeLines(capture.output(str(cfg)), file.path(carpetas$docs, "configuracion.txt"))
  writeLines(capture.output(utils::sessionInfo()), file.path(carpetas$docs, "sessionInfo.txt"))
  paquetes <- c("R", "DESeq2", "org.Hs.eg.db", "glmnet", "survival", "timeROC", "hgu133plus2.db")
  versiones <- vapply(paquetes, function(p) if (p == "R") as.character(getRversion()) else
    as.character(utils::packageVersion(p)), character(1))
  fmp_csv(data.frame(package = paquetes, version = versiones),
    file.path(carpetas$tablas, "versiones_paquetes.csv"))
  if (length(advertencias)) fmp_csv(do.call(rbind, advertencias),
    file.path(carpetas$docs, "advertencias.csv"))
  archivos <- c(cfg$archivo_tcga, cfg$archivo_clinico_tcga, cfg$archivo_acrg,
    cfg$archivo_clinico_acrg, cfg$archivo_genes, cfg$archivo_firma_referencia)
  archivos <- archivos[nzchar(archivos) & file.exists(archivos)]
  fmp_csv(data.frame(file = basename(archivos), md5 = unname(tools::md5sum(archivos))),
    file.path(carpetas$docs, "entradas_md5.csv"))
}

ejecutar_replica_fmp <- function(cfg) {
  fmp_paquetes()
  fmp_exigir(is.numeric(cfg$tiempos_roc) && length(cfg$tiempos_roc) > 0 &&
    all(is.finite(cfg$tiempos_roc) & cfg$tiempos_roc > 0), "Horizontes ROC no validos.")
  carpetas <- fmp_carpetas(cfg$carpeta_salida)
  if (!is.null(cfg$archivos_codigo)) {
    dir_codigo <- file.path(carpetas$docs, "codigo_ejecutado")
    dir.create(dir_codigo, recursive = TRUE, showWarnings = FALSE)
    for (archivo in cfg$archivos_codigo) {
      fmp_exigir(file.copy(archivo, file.path(dir_codigo, basename(archivo)), overwrite = FALSE),
        "No se pudo guardar una copia del codigo ejecutado.")
    }
  }
  estado <- "INICIADO"; coincidencia <- FALSE; advertencias <- list()
  on.exit(fmp_documentar(cfg, carpetas, coincidencia, estado, advertencias), add = TRUE)
  withCallingHandlers({
    message("1/6: leyendo los 216 genes y la referencia confirmada de ocho genes...")
    genes <- fmp_leer_genes(cfg$archivo_genes)
    referencia <- fmp_leer_firma(cfg$archivo_firma_referencia)
    fmp_csv(referencia, file.path(carpetas$tablas, "firma_confirmada_solo_referencia.csv"))
    message("2/6: reproduciendo filtro, VST y anotacion del script original...")
    entrada <- fmp_importar_tcga(cfg$archivo_tcga, cfg$archivo_clinico_tcga)
    tcga <- fmp_preparar_tcga(entrada, genes, carpetas)
    if ("age_at_diagnosis" %in% names(tcga$clinical)) tcga$clinical$age_years <-
      fmp_num(tcga$clinical$age_at_diagnosis) / 365.25
    message("3/6: LASSO-Cox original, semilla 123, 10 folds y lambda.min...")
    ajuste <- fmp_ajustar_lasso(tcga, carpetas)
    comp <- fmp_comparar_firmas(ajuste$signature, referencia, cfg$tolerancia_coeficientes)
    coincidencia <- comp$matches
    fmp_csv(comp$table, file.path(carpetas$tablas, "comparacion_firma_original.csv"))
    fmp_csv(data.frame(signature_matches = coincidencia,
      coefficient_absolute_tolerance = cfg$tolerancia_coeficientes,
      original_genes = nrow(referencia), reestimated_genes = nrow(ajuste$signature)),
      file.path(carpetas$tablas, "estado_reproduccion_firma.csv"))
    # Estos objetos se producen aqui, a partir de las entradas en disco.
    tcga$clinical$risk_score <- fmp_puntuar(tcga$x, ajuste$signature)
    fmp_rds(list(cvfit = ajuste$cvfit, signature = ajuste$signature,
      x = tcga$x, y = tcga$y, clinical = tcga$clinical,
      candidate_genes = genes, config = cfg, reference_matches = coincidencia),
      file.path(carpetas$privados, "TCGA_modelo_y_entradas.rds"))
    fmp_figuras_lasso(ajuste, carpetas)
    if (!coincidencia && isTRUE(cfg$exigir_coincidencia_firma)) {
      estado <- "FIRMA_REESTIMADA_DIFERENTE"
      print(comp$table, row.names = FALSE)
      stop(paste0("La firma reestimada no coincide con la referencia. No se cambiaron genes ni coeficientes.\n",
        "Revisa comparacion_firma_original.csv y TCGA_preparacion_resumen.csv.\n",
        "Modelos y figuras LASSO guardados en: ", carpetas$root), call. = FALSE)
    }
    fmp_forest_genes(tcga, ajuste, carpetas)
    message("4/6: KM y timeROC del modelo final en TCGA...")
    evaluaciones <- list()
    evaluaciones$TCGA_global <- fmp_evaluar(tcga$clinical, "TCGA", "Todos", carpetas$tcga,
      carpetas, cfg$tiempos_roc, hacer_ajustado = cfg$hacer_cox_ajustado)
    temprano <- tcga$clinical[tcga$clinical$stage_simple %in% c("i", "ii"), , drop = FALSE]
    evaluaciones$TCGA_I_II <- fmp_evaluar(temprano, "TCGA", "I_II", carpetas$tcga,
      carpetas, cfg$tiempos_roc)
    message("5/6: validacion ACRG con normalizacion y puntaje del script GEO...")
    acrg <- fmp_importar_acrg(cfg$archivo_acrg, cfg$archivo_clinico_acrg, ajuste$signature, carpetas)
    corte_acrg <- stats::median(acrg$clinical$risk_score)
    evaluaciones$ACRG_global <- fmp_evaluar(acrg$clinical, "ACRG", "Todos", carpetas$acrg,
      carpetas, cfg$tiempos_roc, corte = corte_acrg, hacer_ajustado = cfg$hacer_cox_ajustado)
    temprano <- acrg$clinical[acrg$clinical$stage_simple %in% c("i", "ii"), , drop = FALSE]
    evaluaciones$ACRG_I_II <- fmp_evaluar(temprano, "ACRG", "I_II", carpetas$acrg,
      carpetas, cfg$tiempos_roc, corte = corte_acrg)
    resumen <- do.call(rbind, lapply(evaluaciones, function(e) e$summary))
    fmp_csv(resumen, file.path(carpetas$tablas, "TABLA_MAESTRA_KM_Cindex.csv"))
    roc <- do.call(rbind, lapply(evaluaciones, function(e) e$timeROC))
    fmp_csv(roc, file.path(carpetas$tablas, "TABLA_MAESTRA_timeROC.csv"))
    metricas <- do.call(rbind, lapply(c("n", "events", "cutoff", "low_n", "high_n",
      "logrank_p", "C_Harrell_frozen"), function(m) data.frame(cohort = resumen$cohort,
      population = resumen$population, metric = m, estimate = resumen[[m]])))
    metricas <- rbind(metricas, data.frame(cohort = roc$cohort, population = roc$population,
      metric = paste0("AUC_", roc$horizon_years, "y"), estimate = roc$AUC))
    fmp_csv(metricas, file.path(carpetas$tablas, "metricas_para_comparar_originales.csv"))
    message("6/6: guardando la comparacion numerica y la documentacion...")
    metricas_ok <- fmp_comparar_metricas(metricas, cfg$archivo_metricas_referencia, carpetas$tablas)
    estado <- if (coincidencia) "COMPLETADO_REFERENCIA_8GENES_COINCIDENTE" else
      "COMPLETADO_CON_FIRMA_DIFERENTE_DE_LA_REFERENCIA"
    fmp_rds(list(signature = ajuste$signature, cvfit = ajuste$cvfit,
      TCGA_x = tcga$x, TCGA_clinical = tcga$clinical,
      ACRG_x = acrg$x, ACRG_clinical = acrg$clinical, ACRG_expression = acrg$expression, config = cfg,
      status = estado, signature_matches = coincidencia, reference_metrics_match = metricas_ok),
      file.path(carpetas$privados, "FMP_original_replicada_para_comparacion.rds"))
    cat("\nFASE 1 LASSO TERMINADA\n", estado, "\n\n", sep = "")
    print(comp$table, row.names = FALSE); print(resumen, row.names = FALSE)
    print(roc, row.names = FALSE)
    cat("\nArchivos LASSO guardados en:\n", carpetas$root, "\n")
    invisible(list(folders = carpetas, comparison = comp, KM_Cindex = resumen,
      timeROC = roc, status = estado, lasso = ajuste, tcga = tcga, acrg = acrg))
  }, warning = function(w) {
    advertencias[[length(advertencias) + 1L]] <<- data.frame(
      message = conditionMessage(w), call = paste(deparse(conditionCall(w)), collapse = " "))
    # El aviso tambien aparece en consola; no se oculta.
  })
}

# BLOQUE 2: RSF. Todas las entradas vienen del bloque LASSO guardado en disco.
fmp_rsf_configuracion <- function() {
  list(seed = 20261118L, num.trees = 1000L, num.threads = 2L,
    panel_sizes = c(5L, 10L, 20L), node_sizes = c(20L, 10L),
    screen_node_size = 15L, min.bucket = 3L, splitrule = "logrank",
    importance = "permutation", replace = TRUE, sample.fraction = 1)
}

fmp_rsf_paquetes <- function() {
  paquetes <- c("ranger", "survival", "ggplot2", "survminer", "timeROC")
  faltantes <- paquetes[!vapply(paquetes, requireNamespace, logical(1), quietly = TRUE)]
  fmp_exigir(!length(faltantes), paste("Faltan paquetes para RSF:",
    paste(faltantes, collapse = ", "), ". Consulta README.md."))
  suppressPackageStartupMessages(library("survival", character.only = TRUE))
  invisible(paquetes)
}

fmp_rsf_validar <- function(x, clinica, folds = NULL) {
  fmp_exigir(is.matrix(x) && is.numeric(x) && nrow(x) == nrow(clinica) &&
    nrow(x) > 2L && ncol(x) > 0L && all(is.finite(x)) &&
    !is.null(rownames(x)) && !is.null(colnames(x)) &&
    !anyDuplicated(rownames(x)) && !anyDuplicated(colnames(x)) &&
    identical(rownames(x), rownames(clinica)), "RSF: matriz y clinica no validas o desalineadas.")
  fmp_exigir(all(c("OS.time_years", "OS.event", "stage_simple") %in% names(clinica)) &&
    all(is.finite(clinica$OS.time_years) & clinica$OS.time_years > 0) &&
    !anyNA(clinica$OS.event) && all(clinica$OS.event %in% c(0, 1)) &&
    sum(clinica$OS.event) >= 2L, "RSF: supervivencia no valida o sin eventos suficientes.")
  if (!is.null(folds)) fmp_exigir(length(folds) == nrow(x) && !anyNA(folds) &&
    length(unique(folds)) >= 3L && all(table(folds) >= 2L),
    "RSF: folds guardados por LASSO ausentes o incompatibles con las filas de TCGA.")
  invisible(TRUE)
}

fmp_rsf_bosque <- function(x, clinica, cfg, node_size, seed, importancia = "none") {
  # La API de nombres evita depender de un Surv() suelto en .GlobalEnv.
  d <- data.frame(.fmp_time = clinica$OS.time_years, .fmp_event = clinica$OS.event,
    x, check.names = FALSE)
  ranger::ranger(dependent.variable.name = ".fmp_time",
    status.variable.name = ".fmp_event", data = d,
    num.trees = cfg$num.trees, mtry = max(1L, floor(sqrt(ncol(x)))),
    min.node.size = node_size, min.bucket = cfg$min.bucket,
    splitrule = cfg$splitrule, importance = importancia,
    replace = cfg$replace, sample.fraction = cfg$sample.fraction,
    num.threads = cfg$num.threads, seed = seed, write.forest = TRUE)
}

fmp_rsf_predecir <- function(bosque, x, num.threads = 2L) {
  genes <- bosque$forest$independent.variable.names
  fmp_exigir(is.matrix(x) && nrow(x) > 0L && !is.null(genes) &&
    all(genes %in% colnames(x)), "RSF: faltan genes del panel; no se eliminan ni imputan.")
  z <- x[, genes, drop = FALSE]
  fmp_exigir(all(is.finite(z)), "RSF: expresion no finita al predecir.")
  p <- stats::predict(bosque, data = as.data.frame(z, check.names = FALSE),
    num.threads = num.threads)
  # ranger puede simplificar dimensiones con un paciente o un tiempo.
  chf <- p$chf
  fmp_exigir(!is.null(chf) && length(chf) == nrow(z) * length(p$unique.death.times),
    "RSF: dimensiones de riesgo acumulado inesperadas.")
  chf <- matrix(chf, nrow = nrow(z), ncol = length(p$unique.death.times))
  riesgo <- rowSums(chf)
  fmp_exigir(all(is.finite(riesgo) & riesgo >= 0), "RSF: puntajes no validos.")
  # Suma del CHF en la malla temporal del bosque: marcador, NO probabilidad.
  stats::setNames(riesgo, rownames(z))
}

fmp_rsf_concordancia <- function(clinica, riesgo) {
  d <- clinica; d$risk_score <- as.numeric(riesgo)
  cc <- survival::concordance(survival::Surv(OS.time_years, OS.event) ~ risk_score,
    data = d, reverse = TRUE)
  unname(cc$concordance)
}

fmp_rsf_orden_importancia <- function(bosque) {
  v <- bosque$variable.importance
  fmp_exigir(length(v) > 0L && all(is.finite(v)),
    "RSF: no se obtuvo importancia por permutacion finita.")
  d <- data.frame(Gene = names(v), permutation_importance = unname(v))
  d <- d[order(-d$permutation_importance, d$Gene), , drop = FALSE]
  rownames(d) <- NULL
  d$rank <- seq_len(nrow(d))
  d
}

fmp_rsf_entrenar <- function(x, clinica, folds, cfg, carpetas) {
  fmp_rsf_validar(x, clinica, folds)
  fmp_exigir(is.list(cfg) && cfg$num.trees >= 2L && cfg$num.threads >= 1L &&
    all(cfg$panel_sizes >= 1L) && all(cfg$node_sizes >= cfg$min.bucket) &&
    !anyDuplicated(cfg$panel_sizes) && !anyDuplicated(cfg$node_sizes),
    "RSF: configuracion no valida.")
  grilla <- expand.grid(panel_size = cfg$panel_sizes, min_node_size = cfg$node_sizes)
  filas <- list(); indices <- sort(unique(folds))
  fmp_csv(data.frame(sample_id = rownames(x), fold = folds),
    file.path(carpetas$privados, "RSF_folds_iguales_a_LASSO.csv"))
  for (i in seq_along(indices)) {
    message("RSF: seleccion interna TCGA, fold ", i, "/", length(indices), "...")
    train <- which(folds != indices[i]); test <- which(folds == indices[i])
    variables <- vapply(seq_len(ncol(x)), function(j) stats::sd(x[train, j]), numeric(1)) > 1e-8
    xx <- x[, variables, drop = FALSE]
    fmp_exigir(ncol(xx) >= max(cfg$panel_sizes),
      "RSF: no hay suficientes genes variables en un fold para la grilla prefijada.")
    pantalla <- fmp_rsf_bosque(xx[train, , drop = FALSE], clinica[train, , drop = FALSE],
      cfg, cfg$screen_node_size, cfg$seed + i * 100L, cfg$importance)
    ranking <- fmp_rsf_orden_importancia(pantalla)
    filas_fold <- list()
    for (j in seq_len(nrow(grilla))) {
      g <- head(ranking$Gene, grilla$panel_size[j])
      bosque <- fmp_rsf_bosque(xx[train, g, drop = FALSE], clinica[train, , drop = FALSE],
        cfg, grilla$min_node_size[j], cfg$seed + i * 100L + j)
      score <- fmp_rsf_predecir(bosque, xx[test, g, drop = FALSE], cfg$num.threads)
      filas_fold[[j]] <- data.frame(fold = indices[i], panel_size = length(g),
        min_node_size = grilla$min_node_size[j], n_validation = length(test),
        events_validation = sum(clinica$OS.event[test]),
        C_Harrell = fmp_rsf_concordancia(clinica[test, , drop = FALSE], score))
    }
    filas[[i]] <- do.call(rbind, filas_fold)
    # Guardar evidencia de cada fold; no contiene un filtro basado en ACRG.
    fmp_rds(list(fold = indices[i], training_ids = rownames(x)[train],
      validation_ids = rownames(x)[test], importance = ranking, metrics = filas[[i]]),
      file.path(carpetas$privados, sprintf("RSF_cv_fold_%02d.rds", i)))
  }
  detalle <- do.call(rbind, filas)
  resumen <- do.call(rbind, lapply(seq_len(nrow(grilla)), function(j) {
    z <- detalle[detalle$panel_size == grilla$panel_size[j] &
      detalle$min_node_size == grilla$min_node_size[j], , drop = FALSE]
    data.frame(panel_size = grilla$panel_size[j], min_node_size = grilla$min_node_size[j],
      C_Harrell_mean = if (all(is.finite(z$C_Harrell))) mean(z$C_Harrell) else NA_real_,
      C_Harrell_SD = stats::sd(z$C_Harrell), valid_folds = sum(is.finite(z$C_Harrell)),
      requested_folds = length(indices))
  }))
  orden <- order(-resumen$C_Harrell_mean, resumen$panel_size, -resumen$min_node_size,
    na.last = TRUE)
  fmp_exigir(any(is.finite(resumen$C_Harrell_mean)),
    "RSF: C de validacion interna no estimable. Revisar eventos de los folds.")
  mejor <- resumen[orden[1L], , drop = FALSE]
  fmp_csv(detalle, file.path(carpetas$tablas, "RSF_CV_detalle.csv"))
  fmp_csv(resumen, file.path(carpetas$tablas, "RSF_CV_resumen.csv"))
  fmp_rds(list(detail = detalle, summary = resumen, best = mejor, config = cfg),
    file.path(carpetas$privados, "RSF_tuning_completado.rds"))
  message("RSF: congelando el panel final con todo TCGA (", mejor$panel_size, " genes)...")
  variables <- vapply(seq_len(ncol(x)), function(j) stats::sd(x[, j]), numeric(1)) > 1e-8
  xx <- x[, variables, drop = FALSE]
  pantalla <- fmp_rsf_bosque(xx, clinica, cfg, cfg$screen_node_size,
    cfg$seed + 10000L, cfg$importance)
  ranking <- fmp_rsf_orden_importancia(pantalla)
  seleccion <- head(ranking, mejor$panel_size)
  bosque <- fmp_rsf_bosque(xx[, seleccion$Gene, drop = FALSE], clinica, cfg,
    mejor$min_node_size, cfg$seed + 10001L, cfg$importance)
  seleccion$final_permutation_importance <- unname(bosque$variable.importance[seleccion$Gene])
  fmp_csv(ranking, file.path(carpetas$tablas, "RSF_importancia_candidatos.csv"))
  fmp_csv(seleccion, file.path(carpetas$tablas, "RSF_panel_final.csv"))
  parametros <- data.frame(parameter = c("seed_screen", "seed_final", "num.trees", "mtry_screen",
    "mtry_final", "min.node.size_screen", "min.node.size_final", "min.bucket", "splitrule",
    "importance", "replace", "sample.fraction", "num.threads", "selected_genes", "folds",
    "tuning_criterion", "risk_score"), value = as.character(c(cfg$seed + 10000L,
    cfg$seed + 10001L, cfg$num.trees, floor(sqrt(ncol(xx))),
    floor(sqrt(nrow(seleccion))), cfg$screen_node_size, mejor$min_node_size,
    cfg$min.bucket, cfg$splitrule, cfg$importance, cfg$replace, cfg$sample.fraction,
    cfg$num.threads, nrow(seleccion), length(indices), "mean validation Harrell C",
    "rowSums(CHF); no probabilidad")))
  fmp_csv(parametros, file.path(carpetas$tablas, "RSF_parametros_finales.csv"))
  resultado <- list(forest = bosque, signature = seleccion, ranking = ranking,
    tuning = list(detail = detalle, summary = resumen, best = mejor), config = cfg)
  fmp_rds(resultado, file.path(carpetas$privados, "RSF_modelo_final.rds"))
  resultado
}

fmp_rsf_diagnosticos <- function(x_tcga, x_acrg, clinical_tcga, clinical_acrg) {
  escala <- do.call(rbind, lapply(colnames(x_tcga), function(g) {
    a <- x_tcga[, g]; b <- x_acrg[, g]
    data.frame(Gene = g, TCGA_min = min(a), TCGA_median = stats::median(a), TCGA_max = max(a),
      ACRG_min = min(b), ACRG_median = stats::median(b), ACRG_max = max(b),
      fraction_ACRG_below_TCGA = mean(b < min(a)), fraction_ACRG_above_TCGA = mean(b > max(a)))
  }))
  puntajes <- do.call(rbind, lapply(c("TCGA", "ACRG"), function(cohorte) {
    d <- if (cohorte == "TCGA") clinical_tcga else clinical_acrg
    s <- d$risk_score
    data.frame(cohort = cohorte, n = nrow(d), distinct_scores = length(unique(s)),
      min = min(s), max = max(s), mean = mean(s), SD = stats::sd(s),
      score_type = "RSF rowSums(CHF); NOT probability",
      median_ties = sum(s == stats::median(s)))
  }))
  list(scale = escala, predictions = puntajes)
}

fmp_rsf_figuras <- function(ajuste, carpetas) {
  d <- ajuste$signature
  d$Gene <- factor(d$Gene, levels = rev(d$Gene))
  p <- ggplot2::ggplot(d, ggplot2::aes(x = permutation_importance, y = Gene)) +
    ggplot2::geom_col(fill = "#1B9E77") + ggplot2::geom_vline(xintercept = 0, linetype = "dashed") +
    ggplot2::labs(x = "Permutation importance (selection forest; TCGA only)", y = NULL) +
    ggplot2::theme_classic(base_size = 14)
  fmp_dispositivo(file.path(carpetas$rsf, "RSF_importancia_genes_panel"),
    function() print(p), 8, max(5, .25 * nrow(d) + 2))
  d <- ajuste$tuning$summary
  p <- ggplot2::ggplot(d, ggplot2::aes(x = factor(panel_size), y = C_Harrell_mean,
      group = factor(min_node_size), color = factor(min_node_size))) +
    ggplot2::geom_line() + ggplot2::geom_point(size = 3) +
    ggplot2::geom_errorbar(ggplot2::aes(ymin = C_Harrell_mean - C_Harrell_SD,
      ymax = C_Harrell_mean + C_Harrell_SD), width = .1) +
    ggplot2::geom_hline(yintercept = .5, linetype = "dashed") +
    ggplot2::labs(x = "Number of genes", y = "Internal validation C-index (mean +/- SD)",
      color = "min.node.size") + ggplot2::theme_classic(base_size = 14)
  fmp_dispositivo(file.path(carpetas$rsf, "RSF_ajuste_parametros"), function() print(p), 8, 5)
}

fmp_rsf_comparar <- function(raiz_lasso, carpetas, km_rsf, roc_rsf) {
  km_lasso <- utils::read.csv(file.path(raiz_lasso, "tablas", "TABLA_MAESTRA_KM_Cindex.csv"),
    stringsAsFactors = FALSE)
  roc_lasso <- utils::read.csv(file.path(raiz_lasso, "tablas", "TABLA_MAESTRA_timeROC.csv"),
    stringsAsFactors = FALSE)
  km_lasso$model <- roc_lasso$model <- "LASSO-Cox"
  km_rsf$model <- roc_rsf$model <- "RSF"
  juntar <- function(a, b) {
    cols <- union(names(a), names(b))
    for (z in setdiff(cols, names(a))) a[[z]] <- rep(NA, nrow(a))
    for (z in setdiff(cols, names(b))) b[[z]] <- rep(NA, nrow(b))
    rbind(a[, cols, drop = FALSE], b[, cols, drop = FALSE])
  }
  km <- juntar(km_lasso, km_rsf); roc <- juntar(roc_lasso, roc_rsf)
  km$evaluation <- ifelse(km$cohort == "TCGA", "apparent_training", "exploratory_external")
  roc$evaluation <- ifelse(roc$cohort == "TCGA", "apparent_training", "exploratory_external")
  fmp_csv(km, file.path(carpetas$tablas, "COMPARACION_MAESTRA_KM_Cindex.csv"))
  fmp_csv(roc, file.path(carpetas$tablas, "COMPARACION_MAESTRA_timeROC.csv"))
  for (cohorte in intersect(unique(roc$cohort), c("TCGA", "ACRG"))) {
    for (pop in c("Todos", "I_II")) {
      nombre <- paste0(cohorte, "_", pop, "_timeROC.rds")
      archivos <- c(file.path(raiz_lasso, "data_privada", nombre),
        file.path(carpetas$privados, nombre))
      if (!all(file.exists(archivos))) next
      objetos <- lapply(archivos, readRDS)
      if (!all(vapply(objetos, function(z) !is.null(z[["1"]]), logical(1)))) next
      a <- objetos[[1L]][["1"]]; b <- objetos[[2L]][["1"]]
      fmp_dispositivo(file.path(carpetas$comparacion, paste0(cohorte, "_", pop, "_ROC_comparativa_1anio")),
        function() {
          plot(a, time = 1, col = "#C0392B", lwd = 2, title = FALSE)
          plot(b, time = 1, add = TRUE, col = "#1B9E77", lwd = 2, title = FALSE)
          graphics::legend("bottomright", legend = c(
            paste0("LASSO-Cox AUC = ", round(a$AUC[fmp_indices_roc(a$times, 1)], 3)),
            paste0("RSF AUC = ", round(b$AUC[fmp_indices_roc(b$times, 1)], 3))),
            col = c("#C0392B", "#1B9E77"), lwd = 2, bty = "n")
        }, 6, 6)
    }
  }
  list(KM_Cindex = km, timeROC = roc)
}

fmp_rsf_documentar <- function(carpetas, cfg, archivo_estado, advertencias, estado) {
  writeLines(c("# Bloque RSF y comparacion con LASSO-Cox", "", paste("Estado:", estado), "",
    "## Metodo", "Entradas: matriz VST y clinica producidas por el bloque LASSO confirmado.",
    "Mismo pool original de 216 GED; se usan los candidatos elegibles de TCGA guardados (210 en la replica confirmada).",
    "Se guardan los mismos folds de LASSO. Dentro de cada fold se ordenan genes por importancia de permutacion",
    "de un bosque de seleccion usando SOLO el entrenamiento; se validan paneles de 5, 10 y 20 genes.",
    "min.node.size: 10 y 20; 1000 arboles; mtry=floor(sqrt(p)); splitrule=logrank; min.bucket=3.",
    "Se elige el mayor C de Harrell medio; empate: menos genes, despues nodo mayor.",
    "El bosque final vuelve a seleccionar en todo TCGA y se congela antes de comprobar cobertura externa.",
    "No se filtran genes por su presencia en ACRG antes del entrenamiento; no se imputan genes ausentes.",
    "RSF no tiene coeficientes por gen: se exportan el panel, importancia y parametros del bosque.",
    "Puntaje = suma del riesgo acumulado (rowSums(CHF)) en la malla del bosque. NO es una probabilidad.",
    "Mayor puntaje indica peor pronostico; el C del marcador fijo no reestima ni invierte el signo.",
    "No se ajusta un Cox sobre los genes RSF para construir una firma diferente.", "",
    "## Evaluacion", "TCGA: prediccion del bosque final sobre los pacientes de desarrollo (aparente).",
    "La CV sirve para elegir el panel/parametros. Su mejor C no es una estimacion independiente del rendimiento.",
    "La seleccion original de GED, el filtro inicial y VST ya estaban fijados antes de esta CV.",
    "La CV no reevalua todo el procesamiento desde conteos: no se presenta como validacion anidada del pipeline.",
    "ACRG: misma preparacion del bloque LASSO: RMA log10 del repositorio y cuantiles adicionales, sin reajuste con desenlaces ACRG.",
    "Las unidades VST y microarreglos RMA log10 no son equivalentes; se documenta el desplazamiento por gen.",
    "Predicciones externas constantes o casi constantes se conservan y se informan: no se fuerzan dos grupos.",
    "KM: supervivencia global completa; timeROC: marcador continuo, horizonte de un anio.",
    "Mismas reglas de medianas que LASSO: TCGA global y subgrupo propias; ACRG global conservada en I-II.",
    "Las medianas son descriptivas y dependen de la cohorte; no son umbrales clinicos transportables.",
    "No se compara significacion de p KM para declarar un ganador; usar rendimiento externo e incertidumbre.",
    "El C de Harrell usa todo el seguimiento y no es el C de Uno truncado del enfoque previo.",
    "ACRG ya fue explorada. Evaluacion externa exploratoria; sin afirmar utilidad clinica ni causalidad.", "",
    "## Salidas", "tablas/: panel RSF, importancia, CV, parametros, diagnosticos y tablas maestras comparativas.",
    "figuras/: importancia, ajuste, KM global/I-II, ROC individuales y ROC superpuestas de ambos modelos.",
    "data_privada/: bosque, matrices, folds y predicciones. No publicar en GitHub.",
    "La carpeta LASSO anterior permanece intacta. El bloque no vuelve a entrenar LASSO.", "",
    "## Uso de IA", "ChatGPT/Codex apoyo la programacion, refactorizacion y pruebas tecnicas.",
    "El autor define la pregunta, revisa datos y resultados y asume su interpretacion cientifica."),
    file.path(carpetas$root, "README.md"))
  writeLines(capture.output(str(cfg)), file.path(carpetas$docs, "configuracion_RSF.txt"))
  writeLines(capture.output(utils::sessionInfo()), file.path(carpetas$docs, "sessionInfo.txt"))
  fmp_csv(data.frame(file = basename(archivo_estado), md5 = unname(tools::md5sum(archivo_estado))),
    file.path(carpetas$docs, "entrada_LASSO_md5.csv"))
  if (length(advertencias)) fmp_csv(do.call(rbind, advertencias),
    file.path(carpetas$docs, "advertencias_RSF.csv"))
}

ejecutar_bloque_rsf <- function(archivo_estado, cfg_rsf, archivos_codigo = NULL, carpeta_salida = NULL) {
  fmp_rsf_paquetes()
  entrada <- readRDS(archivo_estado)
  fmp_exigir(is.list(entrada) && all(c("TCGA_x", "TCGA_clinical", "cvfit",
    "ACRG_clinical", "config") %in% names(entrada)),
    "Selecciona FMP_original_replicada_para_comparacion.rds, no un RDS intermedio.")
  x <- entrada$TCGA_x; clin <- entrada$TCGA_clinical; folds <- entrada$cvfit$foldid
  fmp_exigir(!is.null(folds), "Faltan folds en el modelo guardado. Usa el RDS final del maestro LASSO con keep=TRUE.")
  fmp_rsf_validar(x, clin, folds)
  raiz_lasso <- dirname(dirname(normalizePath(archivo_estado)))
  tablas_lasso <- file.path(raiz_lasso, "tablas", c("TABLA_MAESTRA_KM_Cindex.csv", "TABLA_MAESTRA_timeROC.csv"))
  fmp_exigir(all(file.exists(tablas_lasso)), "Conserva la carpeta completa del bloque LASSO, incluidas sus tablas maestras.")
  if (is.null(carpeta_salida)) carpeta_salida <- file.path(raiz_lasso, "resultados_RSF")
  carpetas <- fmp_carpetas(carpeta_salida)
  carpetas$rsf <- file.path(carpetas$root, "figuras", "01_RSF_importancia")
  carpetas$comparacion <- file.path(carpetas$root, "figuras", "04_Comparacion")
  dir.create(carpetas$rsf, recursive = TRUE); dir.create(carpetas$comparacion, recursive = TRUE)
  if (length(archivos_codigo)) {
    destino <- file.path(carpetas$docs, "codigo_ejecutado"); dir.create(destino)
    for (archivo in archivos_codigo) fmp_exigir(file.copy(archivo, destino),
      "No se pudo guardar el codigo ejecutado en RSF.")
  }
  estado <- "INICIADO"; advertencias <- list()
  on.exit(fmp_rsf_documentar(carpetas, cfg_rsf, archivo_estado, advertencias, estado), add = TRUE)
  withCallingHandlers({
    message("RSF 1/4: seleccion de panel y parametros usando solo TCGA...")
    ajuste <- fmp_rsf_entrenar(x, clin, folds, cfg_rsf, carpetas)
    clin$risk_score <- as.numeric(fmp_rsf_predecir(ajuste$forest, x, cfg_rsf$num.threads))
    fmp_rsf_figuras(ajuste, carpetas)
    message("RSF 2/4: KM global e I-II, C-index y timeROC en TCGA...")
    evaluaciones <- list()
    evaluaciones$TCGA_global <- fmp_evaluar(clin, "TCGA", "Todos", carpetas$tcga, carpetas, tiempos = 1)
    temprano <- clin[clin$stage_simple %in% c("i", "ii"), , drop = FALSE]
    evaluaciones$TCGA_I_II <- fmp_evaluar(temprano, "TCGA", "I_II", carpetas$tcga, carpetas, tiempos = 1)
    message("RSF 3/4: comprobando cobertura del panel congelado en ACRG...")
    expresion <- entrada$ACRG_expression; clin_acrg <- entrada$ACRG_clinical
    if (is.null(expresion)) {
      message("El RDS LASSO anterior contiene solo ocho genes ACRG. Se recuperara la matriz completa de sus fuentes.")
      archivos <- c(entrada$config$archivo_acrg, entrada$config$archivo_clinico_acrg)
      if (length(archivos) != 2L || !all(file.exists(archivos))) {
        if (interactive()) {
          message("Selecciona GSE62254_eset.rds original."); archivos <- file.choose()
          message("Selecciona el CSV clinico ACRG o el suplemento Excel original."); archivos <- c(archivos, file.choose())
        } else stop("Las fuentes ACRG guardadas ya no estan en su ruta; conserva sus rutas o ejecuta --stage=all con las entradas originales.", call. = FALSE)
      }
      preparados <- fmp_preparar_acrg(archivos[1L], archivos[2L], carpetas)
      fmp_exigir(identical(rownames(preparados$clinical), rownames(clin_acrg)) &&
        identical(preparados$clinical$OS.event, clin_acrg$OS.event) &&
        isTRUE(all.equal(preparados$clinical$OS.time_years, clin_acrg$OS.time_years)),
        "La nueva entrada ACRG no coincide con la utilizada por LASSO.")
      genes_lasso <- colnames(entrada$ACRG_x)
      fmp_exigir(length(genes_lasso) > 0L &&
        all(genes_lasso %in% rownames(preparados$expression)) &&
        isTRUE(all.equal(t(preparados$expression[genes_lasso, , drop = FALSE]),
          entrada$ACRG_x, tolerance = 1e-10)),
        "La expresion ACRG recuperada no reproduce la guardada en LASSO; revisar archivos y anotacion.")
      expresion <- preparados$expression
    }
    fmp_exigir(is.matrix(expresion) && identical(colnames(expresion), rownames(clin_acrg)) &&
      !anyDuplicated(rownames(expresion)), "ACRG: matriz completa no valida o desalineada.")
    cobertura <- data.frame(Gene = ajuste$signature$Gene,
      present_ACRG = ajuste$signature$Gene %in% rownames(expresion))
    fmp_csv(cobertura, file.path(carpetas$tablas, "ACRG_cobertura_panel_RSF.csv"))
    cobertura_ok <- all(cobertura$present_ACRG)
    if (cobertura_ok) {
      xa <- t(expresion[ajuste$signature$Gene, , drop = FALSE])
      clin_acrg$risk_score <- as.numeric(fmp_rsf_predecir(ajuste$forest, xa, cfg_rsf$num.threads))
      corte <- stats::median(clin_acrg$risk_score)
      diag <- fmp_rsf_diagnosticos(x[, ajuste$signature$Gene, drop = FALSE], xa, clin, clin_acrg)
      fmp_csv(diag$scale, file.path(carpetas$tablas, "RSF_diagnostico_escala_TCGA_ACRG.csv"))
      fmp_csv(diag$predictions, file.path(carpetas$tablas, "RSF_diagnostico_puntajes.csv"))
      evaluaciones$ACRG_global <- fmp_evaluar(clin_acrg, "ACRG", "Todos", carpetas$acrg,
        carpetas, tiempos = 1, corte = corte)
      temprano <- clin_acrg[clin_acrg$stage_simple %in% c("i", "ii"), , drop = FALSE]
      evaluaciones$ACRG_I_II <- fmp_evaluar(temprano, "ACRG", "I_II", carpetas$acrg,
        carpetas, tiempos = 1, corte = corte)
    } else {
      warning("Panel RSF incompleto en ACRG: evaluacion externa no disponible. No se modifica el panel.")
      # Conservar filas explicitas NA; nunca evaluar un bosque incompleto.
      for (pop in c("Todos", "I_II")) {
        d <- if (pop == "Todos") clin_acrg else clin_acrg[clin_acrg$stage_simple %in% c("i", "ii"), , drop = FALSE]
        evaluaciones[[paste0("ACRG_", pop)]] <- list(
          summary = data.frame(cohort = "ACRG", population = pop, n = nrow(d),
            events = sum(d$OS.event), cutoff = NA_real_, low_n = NA_integer_, high_n = NA_integer_,
            logrank_p = NA_real_, C_Harrell_frozen = NA_real_, C_Harrell_SE = NA_real_, status = "panel_incompleto"),
          timeROC = data.frame(cohort = "ACRG", population = pop, horizon_years = 1, n = nrow(d),
            deaths_by_horizon = sum(d$OS.event == 1 & d$OS.time_years <= 1),
            observed_beyond_horizon = sum(d$OS.time_years > 1),
            censored_by_horizon = sum(d$OS.event == 0 & d$OS.time_years <= 1),
            AUC = NA_real_, lower_95 = NA_real_, upper_95 = NA_real_, status = "panel_incompleto"))
      }
      xa <- NULL; clin_acrg$risk_score <- NA_real_
    }
    message("RSF 4/4: guardando tablas y curvas comparativas de los dos modelos...")
    km <- do.call(rbind, lapply(evaluaciones, function(e) e$summary))
    roc <- do.call(rbind, lapply(evaluaciones, function(e) e$timeROC))
    fmp_csv(km, file.path(carpetas$tablas, "TABLA_MAESTRA_KM_Cindex.csv"))
    fmp_csv(roc, file.path(carpetas$tablas, "TABLA_MAESTRA_timeROC.csv"))
    comparacion <- fmp_rsf_comparar(raiz_lasso, carpetas, km, roc)
    estado <- if (cobertura_ok) "COMPLETADO_RSF_Y_COMPARACION" else "COMPLETADO_RSF_SIN_COBERTURA_EXTERNA"
    fmp_rds(list(model = ajuste, TCGA_clinical = clin, ACRG_clinical = clin_acrg,
      ACRG_x = xa, lasso_state = normalizePath(archivo_estado), coverage = cobertura,
      KM_Cindex = km, timeROC = roc, comparison = comparacion, status = estado),
      file.path(carpetas$privados, "RSF_resultados_para_comparacion.rds"))
    cat("\nBLOQUE RSF COMPLETADO\n\n")
    print(ajuste$signature, row.names = FALSE)
    print(comparacion$KM_Cindex, row.names = FALSE)
    print(comparacion$timeROC, row.names = FALSE)
    cat("\nArchivos RSF y comparacion guardados en:\n", carpetas$root, "\n")
    invisible(list(folders = carpetas, model = ajuste, KM_Cindex = km, timeROC = roc,
      comparison = comparacion, status = estado))
  }, warning = function(w) {
    advertencias[[length(advertencias) + 1L]] <<- data.frame(message = conditionMessage(w),
      call = paste(deparse(conditionCall(w)), collapse = " "))
  })
}

ejecutar_proyecto_fmp <- function(cfg) {
  fmp_preparar_ejecucion(cfg)
  if (cfg$stage == "download") {
    message("Entradas descargadas y guardadas. No se entrenaron modelos.")
    return(invisible(list(status = "DESCARGA_COMPLETADA", config = cfg)))
  }
  if (cfg$stage == "oob") return(invisible(list(oob = ejecutar_comprobacion_oob(
    cfg$archivo_estado, cfg$carpeta_salida, cfg$archivo_readme, cfg$archivos_codigo))))
  if (cfg$stage == "rsf") {
    rsf <- ejecutar_bloque_rsf(cfg$archivo_estado, cfg$rsf, cfg$archivos_codigo, cfg$carpeta_salida)
    archivo_rsf <- file.path(rsf$folders$privados, "RSF_resultados_para_comparacion.rds")
    oob <- ejecutar_comprobacion_oob(archivo_rsf, archivo_readme = cfg$archivo_readme,
      archivos_codigo = cfg$archivos_codigo)
    return(invisible(list(rsf = rsf, oob = oob)))
  }
  if (cfg$stage == "all") fmp_rsf_paquetes() # comprobar ANTES del entrenamiento largo.
  resultado <- ejecutar_replica_fmp(cfg)
  if (cfg$stage == "all") {
    archivo <- file.path(resultado$folders$privados, "FMP_original_replicada_para_comparacion.rds")
    resultado$rsf <- ejecutar_bloque_rsf(archivo, cfg$rsf, cfg$archivos_codigo)
    archivo_rsf <- file.path(resultado$rsf$folders$privados, "RSF_resultados_para_comparacion.rds")
    resultado$oob <- ejecutar_comprobacion_oob(archivo_rsf, archivo_readme = NULL,
      archivos_codigo = cfg$archivos_codigo)
  }
  fmp_registrar_ejecucion(cfg, resultado)
  invisible(resultado)
}

# COMPROBACION FINAL: leer OOB del bosque existente. Ninguna llamada de ajuste.
fmp_oob_extraer <- function(resultado) {
  fmp_exigir(is.list(resultado) && all(c("model", "TCGA_clinical") %in% names(resultado)),
    "Selecciona RSF_resultados_para_comparacion.rds; el modelo aislado no contiene la clinica alineada.")
  modelo <- resultado$model; bosque <- modelo$forest; clin <- resultado$TCGA_clinical
  fmp_exigir(inherits(bosque, "ranger") && tolower(bosque$treetype) == "survival",
    "El RDS no contiene el bosque de supervivencia ranger esperado.")
  requeridas <- c("OS.time_years", "OS.event", "risk_score")
  fmp_exigir(is.data.frame(clin) && all(requeridas %in% names(clin)) && nrow(clin) > 2L &&
    !is.null(rownames(clin)) && !anyDuplicated(rownames(clin)) &&
    all(is.finite(clin$OS.time_years) & clin$OS.time_years > 0) &&
    !anyNA(clin$OS.event) && all(clin$OS.event %in% c(0, 1)) &&
    all(is.finite(clin$risk_score)), "Clinica TCGA o puntajes aparentes no validos.")
  chf <- bosque$chf; tiempos <- bosque$unique.death.times
  fmp_exigir(!is.null(chf) && length(tiempos) > 0L &&
    is.matrix(chf) && identical(dim(chf), c(nrow(clin), length(tiempos))) &&
    bosque$num.samples == nrow(clin),
    "El bosque no contiene CHF OOB completo alineado con la clinica. No se reconstruye ni se reentrena.")
  fmp_exigir(all(is.finite(chf)) && all(chf >= 0),
    "CHF OOB con valores ausentes o no validos. No se excluyen pacientes silenciosamente.")
  if (!is.null(rownames(chf))) fmp_exigir(identical(rownames(chf), rownames(clin)),
    "Los nombres de fila del CHF y de la clinica no coinciden.")
  genes <- bosque$forest$independent.variable.names
  fmp_exigir(!is.null(modelo$signature) && identical(genes, as.character(modelo$signature$Gene)),
    "El panel guardado no coincide, en genes y orden, con el bosque final.")
  fmp_exigir(length(bosque$prediction.error) == 1L && is.finite(bosque$prediction.error),
    "Falta el error OOB calculado por ranger; no se etiqueta una prediccion aparente como OOB.")
  list(clinical = clin, apparent = as.numeric(clin$risk_score), oob = rowSums(chf),
    C_ranger_OOB = 1 - bosque$prediction.error, genes = genes,
    num.trees = bosque$num.trees, alignment = "orden conservado dentro del mismo RDS de resultados")
}

fmp_oob_auc <- function(clinica, riesgo, horizonte = 1) {
  casos <- sum(clinica$OS.event == 1 & clinica$OS.time_years <= horizonte)
  controles <- sum(clinica$OS.time_years > horizonte)
  if (casos < 2L || controles < 2L) return(list(AUC = NA_real_, roc = NULL, status = "soporte_insuficiente"))
  roc <- timeROC::timeROC(T = clinica$OS.time_years, delta = clinica$OS.event,
    marker = as.numeric(riesgo), cause = 1, weighting = "marginal", times = horizonte,
    iid = FALSE)
  auc <- unname(roc$AUC[fmp_indices_roc(roc$times, horizonte)])
  list(AUC = auc, roc = roc, status = if (is.finite(auc)) "OK" else "AUC_no_estimable")
}

fmp_oob_calcular <- function(entrada, auc_fun = fmp_oob_auc) {
  filas <- list(); rocs <- list(); d <- entrada$clinical
  for (nombre in c("apparent", "oob")) {
    score <- entrada[[nombre]]
    r <- auc_fun(d, score, 1)
    cindex <- fmp_rsf_concordancia(d, score)
    filas[[nombre]] <- data.frame(model = "RSF", cohort = "TCGA", population = "Todos",
      evaluation = if (nombre == "apparent") "apparent_training" else "OOB_conditional_on_selected_panel",
      horizon_years = 1, n = nrow(d), events_all_followup = sum(d$OS.event),
      deaths_by_horizon = sum(d$OS.event == 1 & d$OS.time_years <= 1),
      observed_beyond_horizon = sum(d$OS.time_years > 1),
      censored_by_horizon = sum(d$OS.event == 0 & d$OS.time_years <= 1),
      AUC = r$AUC, C_Harrell = cindex, distinct_scores = length(unique(score)),
      selected_genes = length(entrada$genes), num.trees = entrada$num.trees,
      refit = FALSE, status = r$status)
    rocs[[nombre]] <- r$roc
  }
  tabla <- do.call(rbind, filas); rownames(tabla) <- NULL
  diferencia_c <- abs(tabla$C_Harrell[2L] - entrada$C_ranger_OOB)
  verificaciones <- data.frame(check = c("CHF OOB completo y finito", "Panel identico al bosque",
    "Filas clinicas preservadas", "C OOB coincide con 1 - prediction.error de ranger"),
    status = c("PASS", "PASS", "PASS", if (diferencia_c < 1e-7) "PASS" else "REVISAR_EMPATES"),
    detail = c("sin pacientes excluidos", paste(length(entrada$genes), "genes; no reestimados"),
      entrada$alignment, paste0("diferencia absoluta = ", format(diferencia_c, digits = 8))))
  list(metrics = tabla, rocs = rocs, checks = verificaciones,
    differences = data.frame(comparison = "apparent_minus_OOB", metric = c("AUC_1year", "C_Harrell"),
      difference = c(tabla$AUC[1L] - tabla$AUC[2L], tabla$C_Harrell[1L] - tabla$C_Harrell[2L])))
}

fmp_oob_texto <- function(res) {
  m <- res$metrics
  formato <- function(x) if (is.finite(x)) formatC(x, digits = 4, format = "f") else "NA"
  c("Comprobacion del bosque existente, sin reentrenamiento ni modificacion de genes/arboles.", "",
    "| Evaluacion RSF en TCGA global | AUC al anio | C de Harrell |",
    "|---|---:|---:|",
    paste0("| Aparente | ", formato(m$AUC[1L]), " | ", formato(m$C_Harrell[1L]), " |"),
    paste0("| OOB, condicionado al panel seleccionado | ", formato(m$AUC[2L]), " | ", formato(m$C_Harrell[2L]), " |"),
    "", paste0("Pacientes: ", m$n[1L], "; genes: ", m$selected_genes[1L],
      "; arboles: ", m$num.trees[1L], "."),
    "El marcador sigue siendo rowSums(CHF); no es una probabilidad de muerte.",
    "El C usa todo el seguimiento; la ROC evalua un anio. No se usa el estado al anio como predictor.",
    "Una caida aparente-OOB indica optimismo dentro de TCGA; no mide el efecto de cambiar de tecnologia.",
    "Los genes y parametros se escogieron usando TCGA: OOB no valida independientemente esa seleccion.",
    "Se informa como diagnostico interno condicionado al panel, no como validacion externa ni AUC real.",
    "No se calculan IC convencionales para OOB: las predicciones comparten arboles y seleccion de genes.",
    "Los resultados ACRG y las firmas originales se conservan.")
}

fmp_oob_actualizar_readme <- function(archivo, texto) {
  if (is.null(archivo) || !nzchar(archivo) || !file.exists(archivo)) return(FALSE)
  lineas <- readLines(archivo, warn = FALSE, encoding = "UTF-8")
  inicio <- which(lineas == "<!-- INICIO_RESULTADOS_OOB -->")
  fin <- which(lineas == "<!-- FIN_RESULTADOS_OOB -->")
  if (length(inicio) != 1L || length(fin) != 1L || inicio >= fin) return(FALSE)
  resultado <- c(lineas[seq_len(inicio)], texto, lineas[seq.int(fin, length(lineas))])
  writeLines(resultado, archivo, useBytes = TRUE)
  TRUE
}

fmp_oob_figuras <- function(res, carpeta) {
  if (is.null(res$rocs$apparent) || is.null(res$rocs$oob)) return(invisible(NULL))
  fmp_dispositivo(file.path(carpeta, "RSF_ROC_aparente_vs_OOB_1anio"), function() {
    plot(res$rocs$apparent, time = 1, col = "#C0392B", lwd = 2, title = FALSE)
    plot(res$rocs$oob, time = 1, add = TRUE, col = "#1B9E77", lwd = 2, title = FALSE)
    graphics::legend("bottomright", legend = c(
      paste0("Apparent AUC = ", round(res$metrics$AUC[1L], 3)),
      paste0("OOB AUC = ", round(res$metrics$AUC[2L], 3))),
      col = c("#C0392B", "#1B9E77"), lwd = 2, bty = "n")
  }, 6, 6)
}

fmp_oob_paquetes <- function() {
  paquetes <- c("survival", "timeROC")
  fmp_exigir(all(vapply(paquetes, requireNamespace, logical(1), quietly = TRUE)),
    "La comprobacion OOB requiere survival y timeROC, ya utilizados en el proyecto.")
  invisible(paquetes)
}

ejecutar_comprobacion_oob <- function(archivo_estado, carpeta_salida = NULL,
    archivo_readme = NULL, archivos_codigo = NULL) {
  fmp_oob_paquetes()
  md5_antes <- unname(tools::md5sum(archivo_estado))
  entrada <- fmp_oob_extraer(readRDS(archivo_estado))
  if (is.null(carpeta_salida)) carpeta_salida <- file.path(dirname(dirname(archivo_estado)), "comprobacion_OOB")
  dir.create(carpeta_salida, recursive = TRUE, showWarnings = FALSE)
  raiz <- tempfile(paste0("OOB_", format(Sys.time(), "%Y%m%d_%H%M%S"), "_"), tmpdir = carpeta_salida)
  dir.create(raiz)
  carpetas <- list(root = raiz, tablas = file.path(raiz, "tablas"),
    figuras = file.path(raiz, "figuras"), docs = file.path(raiz, "docs"), privados = file.path(raiz, "data_privada"))
  for (d in carpetas[-1L]) dir.create(d)
  writeLines("data_privada/", file.path(raiz, ".gitignore"))
  message("OOB 1/3: leyendo CHF ya guardado; no se ajusta ningun modelo...")
  res <- fmp_oob_calcular(entrada)
  message("OOB 2/3: calculando AUC al anio y C de Harrell global...")
  fmp_oob_figuras(res, carpetas$figuras)
  fmp_csv(res$metrics, file.path(carpetas$tablas, "RSF_COMPROBACION_OOB_metricas.csv"))
  fmp_csv(res$differences, file.path(carpetas$tablas, "RSF_COMPROBACION_OOB_diferencias.csv"))
  md5_despues <- unname(tools::md5sum(archivo_estado))
  fmp_exigir(identical(md5_antes, md5_despues), "El RDS de entrada cambio durante la comprobacion.")
  res$checks <- rbind(res$checks, data.frame(check = "RDS de entrada conservado byte a byte",
    status = "PASS", detail = md5_antes))
  fmp_csv(res$checks, file.path(carpetas$tablas, "RSF_COMPROBACION_OOB_checks.csv"))
  texto <- fmp_oob_texto(res)
  writeLines(c("# Comprobacion OOB del RSF congelado", "", texto), file.path(raiz, "README.md"))
  fmp_rds(list(patient_ids = rownames(entrada$clinical), oob_scores = entrada$oob,
    apparent_scores = entrada$apparent, metrics = res$metrics, rocs = res$rocs),
    file.path(carpetas$privados, "RSF_OOB_predicciones_y_ROC.rds"))
  fmp_csv(data.frame(file = basename(archivo_estado), md5 = md5_antes, refit = FALSE),
    file.path(carpetas$docs, "procedencia_OOB.csv"))
  writeLines(capture.output(utils::sessionInfo()), file.path(carpetas$docs, "sessionInfo.txt"))
  if (length(archivos_codigo)) {
    codigo <- file.path(carpetas$docs, "codigo_ejecutado"); dir.create(codigo)
    for (f in archivos_codigo) fmp_exigir(file.copy(f, codigo), "No se pudo guardar el codigo OOB ejecutado.")
  }
  message("OOB 3/3: guardando informe y actualizando la seccion OOB del README...")
  actualizado <- fmp_oob_actualizar_readme(archivo_readme, texto)
  if (!actualizado) message("README principal sin marcadores OOB; el informe completo esta en ", raiz)
  cat("\nCOMPROBACION OOB COMPLETADA; SIN REENTRENAMIENTO\n")
  print(res$metrics, row.names = FALSE); print(res$checks, row.names = FALSE)
  cat("\nArchivos guardados en:\n", raiz, "\n")
  invisible(list(folders = carpetas, metrics = res$metrics, checks = res$checks,
    differences = res$differences, readme_updated = actualizado))
}

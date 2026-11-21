# Pruebas de supervivencia con ranger REAL y datos exclusivamente sinteticos.
# No requiere DESeq2, GEO, timeROC ni matrices de pacientes.
args <- commandArgs(trailingOnly = FALSE)
script <- sub("^--file=", "", args[grepl("^--file=", args)])[1L]
root <- dirname(dirname(normalizePath(script)))
source(file.path(root, "Funciones_fmp_comparacion.R"))
stopifnot(requireNamespace("ranger", quietly = TRUE), requireNamespace("survival", quietly = TRUE))

set.seed(49)
n <- 120L; p <- 25L
x <- matrix(rnorm(n * p), n, p, dimnames = list(paste0("synthetic_", seq_len(n)), paste0("G", seq_len(p))))
tte <- rexp(n, rate = exp(.9 * x[, 1L] - .6 * x[, 2L]))
censor <- rexp(n, rate = .2)
clin <- data.frame(OS.time_years = pmin(tte, censor) + .01, OS.event = as.integer(tte <= censor),
  stage_simple = rep(c("i", "ii", "iii", "iv"), length.out = n), row.names = rownames(x))
folds <- rep(1:3, length.out = n)
cfg <- fmp_rsf_configuracion()
cfg$num.trees <- 50L; cfg$num.threads <- 1L # Solo para prueba rapida; produccion: 1000.
cfg$panel_sizes <- c(5L, 10L)
temporal <- tempfile("fmp_rsf_real_"); dir.create(temporal)
on.exit(unlink(temporal, recursive = TRUE), add = TRUE)
carpetas <- fmp_carpetas(temporal)
ajuste <- fmp_rsf_entrenar(x, clin, folds, cfg, carpetas)
score <- fmp_rsf_predecir(ajuste$forest, x, 1L)
stopifnot(length(score) == n, all(is.finite(score)), all(score >= 0),
  nrow(ajuste$signature) %in% cfg$panel_sizes, all(ajuste$signature$Gene %in% colnames(x)),
  nrow(ajuste$tuning$detail) == length(unique(folds)) * 4L,
  identical(rownames(x), names(score)), length(unique(score)) > 10L)

# El mismo paciente debe recibir el mismo puntaje solo, en lote y con columnas reordenadas.
uno <- fmp_rsf_predecir(ajuste$forest, x[1L, , drop = FALSE], 1L)
rev_cols <- fmp_rsf_predecir(ajuste$forest, x[, rev(colnames(x)), drop = FALSE], 1L)
stopifnot(isTRUE(all.equal(as.numeric(uno), as.numeric(score[1L]), tolerance = 1e-12)),
  isTRUE(all.equal(score, rev_cols, tolerance = 1e-12)))

# Semilla y parametros reproducen exactamente el bosque final; no se reelige un panel.
replica <- fmp_rsf_bosque(x[, ajuste$signature$Gene, drop = FALSE], clin, cfg,
  ajuste$tuning$best$min_node_size, cfg$seed + 10001L, cfg$importance)
stopifnot(isTRUE(all.equal(score, fmp_rsf_predecir(replica, x, 1L), tolerance = 1e-12)))

# Nunca se permite predecir con un gen seleccionado ausente ni con IDs desalineados.
error_gen <- tryCatch({fmp_rsf_predecir(ajuste$forest,
  x[, setdiff(colnames(x), ajuste$signature$Gene[1L]), drop = FALSE]); FALSE}, error = function(e) TRUE)
error_id <- tryCatch({fmp_rsf_validar(x, clin[n:1L, , drop = FALSE], folds); FALSE}, error = function(e) TRUE)
stopifnot(error_gen, error_id)
for (i in seq_len(3L)) {
  z <- readRDS(file.path(carpetas$privados, sprintf("RSF_cv_fold_%02d.rds", i)))
  stopifnot(!length(intersect(z$training_ids, z$validation_ids)),
    setequal(z$validation_ids, rownames(x)[folds == i]))
}
cc <- fmp_rsf_concordancia(clin, score)
stopifnot(is.finite(cc), cc >= 0, cc <= 1,
  identical(fmp_rsf_concordancia(clin, rep(1, n)), .5))

# Un bosque con un unico tiempo tambien conserva la dimension de un paciente.
una_fecha <- clin; una_fecha$OS.time_years <- 1; una_fecha$OS.event <- 1L
fit_fecha <- fmp_rsf_bosque(x[, 1:5], una_fecha, cfg, 20L, 100L)
s_fecha <- fmp_rsf_predecir(fit_fecha, x[1L, 1:5, drop = FALSE], 1L)
stopifnot(length(s_fecha) == 1L, is.finite(s_fecha))

# La aplicacion externa no cambia el modelo, incluso con expresion desplazada.
xa <- x[, ajuste$signature$Gene, drop = FALSE] + 50
clin_a <- clin; clin$risk_score <- as.numeric(score)
clin_a$risk_score <- as.numeric(fmp_rsf_predecir(ajuste$forest, xa, 1L))
diag <- fmp_rsf_diagnosticos(x[, ajuste$signature$Gene, drop = FALSE], xa, clin, clin_a)
stopifnot(all(diag$scale$fraction_ACRG_above_TCGA == 1),
  identical(ajuste$signature$Gene, ajuste$forest$forest$independent.variable.names))
cat("RSF real: seleccion por folds, semillas, prediccion individual, cobertura y diagnosticos: PASS\n")

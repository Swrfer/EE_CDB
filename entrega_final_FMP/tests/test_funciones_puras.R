# Ejecutar desde cualquier directorio: Rscript tests/test_funciones_puras.R
args <- commandArgs(trailingOnly = FALSE)
f <- sub("^--file=", "", args[grepl("^--file=", args)])
if (length(f)) root <- dirname(dirname(normalizePath(f))) else root <- normalizePath(".")
source(file.path(root, "Funciones_fmp_comparacion.R"), encoding = "UTF-8")

debe_fallar <- function(expr) inherits(tryCatch({force(expr); NULL}, error = identity), "error")
ref <- data.frame(Gene = c("A", "B"), Coefficient = c(.2, -.1))
# Comparar por gen; el orden de un CSV no debe crear diferencias ficticias.
stopifnot(fmp_comparar_firmas(ref[2:1, ], ref)$matches)
stopifnot(!fmp_comparar_firmas(ref[1, , drop = FALSE], ref)$matches)
cambio <- ref; cambio$Coefficient[1] <- .3
stopifnot(!fmp_comparar_firmas(cambio, ref)$matches)
cambio <- ref; cambio$Gene[1] <- "C"
stopifnot(!fmp_comparar_firmas(cambio, ref)$matches)

# Un error de orden genes/coeficientes cambia la firma; la funcion lo evita.
x <- matrix(c(3, 7, 1, 2), nrow = 2,
  dimnames = list(c("p1", "p2"), c("B", "A")))
esperado <- c(1, 2) * .2 - c(3, 7) * .1
stopifnot(isTRUE(all.equal(fmp_puntuar(x, ref), esperado)))
stopifnot(debe_fallar(fmp_puntuar(x[, "A", drop = FALSE], ref)))
stopifnot(isTRUE(all.equal(fmp_puntuar(x, ref, TRUE), as.numeric(scale(esperado)))))

# Caso con empates: se conserva la desigualdad declarada, sin repartir al azar.
stopifnot(identical(as.character(fmp_grupos(c(1, 2, 2, 3), 2)),
  c("Low risk", "High risk", "High risk", "High risk")))
stopifnot(identical(as.character(fmp_grupos(c(1, 2, 2, 3), 2, ">")),
  c("Low risk", "Low risk", "Low risk", "High risk")))
stopifnot(identical(as.character(fmp_grupos(rep(.1, 5))), rep("High risk", 5)))

# Unico horizonte: timeROC puede insertar tiempo cero con AUC NA.
stopifnot(identical(fmp_indices_roc(c(0, 1), 1), 2L))
stopifnot(identical(fmp_indices_roc(c(1, 3, 5), c(1, 5)), c(1L, 3L)))
stopifnot(debe_fallar(fmp_indices_roc(c(0, 1), 3)))

stopifnot(identical(as.character(fmp_estadio(c("Stage IA", "IIB", "III", "IV", "2", "unknown"))),
  c("i", "ii", "iii", "iv", "ii", NA_character_)))
cat("Pruebas de funciones puras: PASS\n")

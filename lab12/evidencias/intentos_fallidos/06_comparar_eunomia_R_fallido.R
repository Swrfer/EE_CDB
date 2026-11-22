#!/usr/bin/env Rscript

options(repos = c(CRAN = "https://cloud.r-project.org"))

paquetes <- c("Eunomia", "DBI", "duckdb")
for (paquete in paquetes) {
  if (!requireNamespace(paquete, quietly = TRUE)) {
    install.packages(paquete)
  }
}

dir.create("lab12/data/reference", recursive = TRUE, showWarnings = FALSE)
dir.create(
  "lab12/data/reference/eunomia_cache",
  recursive = TRUE,
  showWarnings = FALSE
)
dir.create("lab12/evidencias/analisis", recursive = TRUE, showWarnings = FALSE)

archivo_db <- normalizePath(
  "lab12/data/reference/eunomia_gibleed.duckdb",
  mustWork = FALSE
)

cat("===== PREPARAR EUNOMIA =====\n")
archivo_db <- Eunomia::getDatabaseFile(
  datasetName = "GiBleed",
  cdmVersion = "5.3",
  pathToData = normalizePath(
    "lab12/data/reference/eunomia_cache",
    mustWork = TRUE
  ),
  dbms = "duckdb",
  databaseFile = archivo_db,
  inputFormat = "csv",
  verbose = TRUE,
  overwrite = FALSE
)

conexion <- DBI::dbConnect(
  duckdb::duckdb(),
  dbdir = archivo_db,
  read_only = TRUE
)

consultar <- function(sql) {
  resultado <- DBI::dbGetQuery(conexion, sql)
  names(resultado) <- tolower(names(resultado))
  resultado
}

guardar <- function(nombre, datos) {
  ruta <- file.path("lab12/evidencias/analisis", nombre)
  write.csv(datos, ruta, row.names = FALSE, na = "")
  cat("OK:", ruta, "(", nrow(datos), "filas)\n")
}

personas_sexo <- consultar("
  SELECT
    COALESCE(c.concept_name, 'Sin concepto legible') AS sexo,
    COUNT(DISTINCT p.person_id) AS personas
  FROM main.person p
  LEFT JOIN main.concept c
    ON c.concept_id = p.gender_concept_id
  GROUP BY COALESCE(c.concept_name, 'Sin concepto legible')
  ORDER BY personas DESC
")

personas_nacimiento <- consultar("
  SELECT
    year_of_birth AS anio_nacimiento,
    COUNT(DISTINCT person_id) AS personas
  FROM main.person
  GROUP BY year_of_birth
  ORDER BY year_of_birth
")

observacion_persona <- consultar("
  SELECT
    person_id,
    SUM(
      DATE_DIFF(
        'day',
        observation_period_start_date,
        observation_period_end_date
      ) + 1
    ) AS dias_observacion
  FROM main.observation_period
  GROUP BY person_id
")

observacion_resumen <- data.frame(
  personas = length(unique(observacion_persona$person_id)),
  mediana_dias_observacion = median(
    observacion_persona$dias_observacion,
    na.rm = TRUE
  ),
  media_dias_observacion = round(
    mean(observacion_persona$dias_observacion, na.rm = TRUE),
    2
  ),
  minimo_dias = min(observacion_persona$dias_observacion, na.rm = TRUE),
  maximo_dias = max(observacion_persona$dias_observacion, na.rm = TRUE)
)

top20_diagnosticos <- consultar("
  SELECT
    co.condition_concept_id AS concept_id,
    c.concept_name AS concept_name,
    COUNT(*) AS eventos,
    COUNT(DISTINCT co.person_id) AS personas
  FROM main.condition_occurrence co
  LEFT JOIN main.concept c
    ON c.concept_id = co.condition_concept_id
  WHERE co.condition_concept_id <> 0
  GROUP BY co.condition_concept_id, c.concept_name
  ORDER BY eventos DESC, personas DESC
  LIMIT 20
")

visitas_resumen <- consultar("
  SELECT
    COUNT(*) AS personas,
    SUM(visitas) AS visitas,
    ROUND(AVG(visitas), 4) AS media_visitas_por_persona
  FROM (
    SELECT
      p.person_id,
      COUNT(v.visit_occurrence_id) AS visitas
    FROM main.person p
    LEFT JOIN main.visit_occurrence v
      ON v.person_id = p.person_id
    GROUP BY p.person_id
  ) resumen
")

visitas_tipo <- consultar("
  SELECT
    v.visit_concept_id AS concept_id,
    COALESCE(c.concept_name, 'Sin concepto legible') AS tipo_visita,
    COUNT(*) AS visitas,
    COUNT(DISTINCT v.person_id) AS personas,
    ROUND(
      COUNT(*) * 1.0 / NULLIF(COUNT(DISTINCT v.person_id), 0),
      4
    ) AS media_visitas_por_persona
  FROM main.visit_occurrence v
  LEFT JOIN main.concept c
    ON c.concept_id = v.visit_concept_id
  GROUP BY v.visit_concept_id, c.concept_name
  ORDER BY visitas DESC
")

guardar("eunomia_personas_sexo.csv", personas_sexo)
guardar("eunomia_personas_nacimiento.csv", personas_nacimiento)
guardar("eunomia_observacion_resumen.csv", observacion_resumen)
guardar("eunomia_top20_diagnosticos.csv", top20_diagnosticos)
guardar("eunomia_visitas_resumen.csv", visitas_resumen)
guardar("eunomia_visitas_tipo.csv", visitas_tipo)

propio_sexo <- read.csv(
  "lab12/evidencias/analisis/personas_sexo.csv",
  check.names = FALSE
)
propio_observacion <- read.csv(
  "lab12/evidencias/analisis/observacion_mediana.csv",
  check.names = FALSE
)
propio_top <- read.csv(
  "lab12/evidencias/analisis/top20_diagnosticos.csv",
  check.names = FALSE
)
propio_visitas <- read.csv(
  "lab12/evidencias/analisis/visitas_resumen.csv",
  check.names = FALSE
)

comparacion <- data.frame(
  metrica = c(
    "Personas",
    "Categorías de sexo",
    "Mediana de días de observación",
    "Visitas",
    "Media de visitas por persona",
    "Diagnóstico más frecuente",
    "Eventos del diagnóstico más frecuente"
  ),
  synthea_propio = c(
    sum(propio_sexo$personas),
    nrow(propio_sexo),
    propio_observacion$mediana_dias_observacion[1],
    propio_visitas$visitas[1],
    propio_visitas$media_visitas_por_persona[1],
    propio_top$concept_name[1],
    propio_top$eventos[1]
  ),
  eunomia = c(
    sum(personas_sexo$personas),
    nrow(personas_sexo),
    observacion_resumen$mediana_dias_observacion[1],
    visitas_resumen$visitas[1],
    visitas_resumen$media_visitas_por_persona[1],
    top20_diagnosticos$concept_name[1],
    top20_diagnosticos$eventos[1]
  ),
  stringsAsFactors = FALSE
)

guardar("comparacion_synthea_eunomia.csv", comparacion)

tabla_markdown <- function(datos) {
  datos[] <- lapply(datos, function(columna) {
    columna <- ifelse(is.na(columna), "", as.character(columna))
    gsub("\\|", "\\\\|", columna)
  })

  encabezado <- paste0(
    "| ", paste(names(datos), collapse = " | "), " |"
  )
  separador <- paste0(
    "| ", paste(rep("---", ncol(datos)), collapse = " | "), " |"
  )
  filas <- apply(datos, 1, function(fila) {
    paste0("| ", paste(fila, collapse = " | "), " |")
  })

  paste(c(encabezado, separador, filas), collapse = "\n")
}

ruta_reporte <- "lab12/reporte_calidad.md"
reporte <- paste(readLines(ruta_reporte, warn = FALSE), collapse = "\n")

comparacion_origen <- read.csv(
  "lab12/evidencias/analisis/estandar_vs_origen.csv",
  check.names = FALSE
)

if (comparacion_origen$diferencia_eventos[1] == 0) {
  explicacion_origen <- paste(
    "En esta base ambos conteos coinciden porque la condición seleccionada",
    "apareció con un solo código de origen. Esto no contradice el modelo OMOP:",
    "en otras fuentes varios códigos pueden converger en el mismo concepto",
    "estándar, mientras que los códigos sin mapeo se representan con",
    "`concept_id = 0`."
  )

  reporte <- sub(
    "La diferencia se debe a que varios[\\s\\S]*?quedan en `concept_id = 0`\\.",
    explicacion_origen,
    reporte,
    perl = TRUE
  )
}

seccion_referencia <- paste0(
  "## 10. Comparación con Eunomia\n\n",
  tabla_markdown(comparacion),
  "\n\n",
  "Eunomia se utilizó como base OMOP de demostración y referencia. La base ",
  "propia contiene una población mayor y una densidad de visitas diferente. ",
  "También cambia el diagnóstico dominante, lo que refleja que ambas bases ",
  "fueron generadas para escenarios clínicos distintos. Por ello, la ",
  "semejanza estructural con OMOP no implica igualdad en distribución de ",
  "enfermedades, seguimiento o utilización de servicios.\n"
)

reporte <- sub(
  "## 10\\. Base de referencia[\\s\\S]*$",
  seccion_referencia,
  reporte,
  perl = TRUE
)

writeLines(reporte, ruta_reporte, useBytes = TRUE)

DBI::dbDisconnect(conexion, shutdown = TRUE)

cat("\n===== COMPARACIÓN CON EUNOMIA COMPLETADA =====\n")
print(comparacion, row.names = FALSE)

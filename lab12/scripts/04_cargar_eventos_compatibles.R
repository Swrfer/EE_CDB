#!/usr/bin/env Rscript

library(ETLSyntheaBuilder)
library(DatabaseConnector)
library(SqlRender)

raiz <- normalizePath(
  getwd(),
  mustWork = TRUE
)

ruta_base <- file.path(
  raiz,
  "lab12",
  "data",
  "omop",
  "synthea_omop_cdm54.duckdb"
)

ruta_evidencias <- file.path(
  raiz,
  "lab12",
  "evidencias"
)

ruta_sql <- file.path(
  ruta_evidencias,
  "sql_eventos_compatibles"
)

dir.create(
  ruta_sql,
  recursive = TRUE,
  showWarnings = FALSE
)

detalles <- createConnectionDetails(
  dbms = "duckdb",
  server = ruta_base,
  extraSettings = list(
    config = list(
      threads = "4",
      memory_limit = "12GB",
      preserve_insertion_order = "false"
    )
  )
)

identificador <- function(valor) {
  paste0(
    '"',
    gsub(
      '"',
      '""',
      valor,
      fixed = TRUE
    ),
    '"'
  )
}

cat("===== 1. VALIDAR ESTADO PREVIO =====\n")

conexion <- connect(detalles)

estado <- querySql(
  conexion,
  paste(
    "SELECT",
    "(SELECT COUNT(*) FROM cdm.concept)",
    "AS concepts,",
    "(SELECT COUNT(*) FROM",
    "cdm.source_to_standard_vocab_map)",
    "AS standard_maps,",
    "(SELECT COUNT(*) FROM cdm.person)",
    "AS persons,",
    "(SELECT COUNT(*) FROM cdm.visit_occurrence)",
    "AS visits"
  )
)

print(estado)

if (
  any(
    is.na(estado[1, ]) |
      estado[1, ] == 0
  )
) {
  stop(
    "Los prerrequisitos no están completos."
  )
}

cat("\n===== 2. VACIAR EVENTOS DESDE CONDITION =====\n")

tablas_a_vaciar <- c(
  "condition_occurrence",
  "observation",
  "measurement",
  "procedure_occurrence",
  "drug_exposure",
  "condition_era",
  "drug_era",
  "cdm_source",
  "device_exposure",
  "death",
  "payer_plan_period",
  "cost"
)

for (tabla in tablas_a_vaciar) {
  cat(
    "Vaciando:",
    tabla,
    "\n"
  )

  executeSql(
    conexion,
    paste0(
      "TRUNCATE TABLE cdm.",
      identificador(tabla),
      ";"
    )
  )
}

disconnect(conexion)

cat("\n===== 3. PREPARAR CONSULTAS COMPATIBLES =====\n")

consultas <- list(
  list(
    file = "insert_condition_occurrence.sql",
    params = list(
      cdm_schema = "cdm",
      synthea_schema = "synthea_native",
      synthea_version = "3.3.0"
    )
  ),
  list(
    file = "insert_observation.sql",
    params = list(
      cdm_schema = "cdm",
      synthea_schema = "synthea_native"
    )
  ),
  list(
    file = "insert_measurement.sql",
    params = list(
      cdm_schema = "cdm",
      synthea_schema = "synthea_native",
      synthea_version = "3.3.0"
    )
  ),
  list(
    file = "insert_procedure_occurrence.sql",
    params = list(
      cdm_schema = "cdm",
      synthea_schema = "synthea_native",
      synthea_version = "3.3.0"
    )
  ),
  list(
    file = "insert_drug_exposure.sql",
    params = list(
      cdm_schema = "cdm",
      synthea_schema = "synthea_native"
    )
  ),
  list(
    file = "insert_cdm_source.sql",
    params = list(
      cdm_schema = "cdm",
      cdm_version = "5.4",
      cdm_source_name =
        "Synthea synthetic health database",
      cdm_source_abbreviation = "Synthea",
      cdm_holder = "OHDSI",
      source_description = paste(
        "Synthea 3.4.0-18 compatible con",
        "ETL-Synthea 3.3.0; OMOP CDM v5.4"
      )
    )
  )
)

patron_datetime <- paste0(
  "(?m)^(\\s*)",
  "([^,\\n]+?)",
  "\\s+(?:as\\s+)?",
  "([A-Za-z][A-Za-z0-9_]*_datetime)",
  "(\\s*,?\\s*)$"
)

conexion <- connect(detalles)

for (consulta in consultas) {
  archivo <- consulta$file

  ruta_original <- system.file(
    "sql",
    "sql_server",
    "cdm_version",
    "v540",
    archivo,
    package = "ETLSyntheaBuilder"
  )

  if (!file.exists(ruta_original)) {
    stop(
      "No se encontró el SQL: ",
      archivo
    )
  }

  sql_original <- readSql(
    ruta_original
  )

  coincidencias <- gregexpr(
    patron_datetime,
    sql_original,
    perl = TRUE
  )[[1]]

  n_correcciones <- if (
    length(coincidencias) == 1L &&
      coincidencias[1] == -1L
  ) {
    0L
  } else {
    length(coincidencias)
  }

  sql_compatible <- gsub(
    pattern = patron_datetime,
    replacement = paste0(
      "\\1cast(null as datetime) ",
      "\\3\\4"
    ),
    x = sql_original,
    perl = TRUE
  )

  argumentos_render <- c(
    list(sql = sql_compatible),
    consulta$params
  )

  sql_renderizado <- do.call(
    render,
    argumentos_render
  )

  sql_traducido <- translate(
    sql_renderizado,
    targetDialect = "duckdb"
  )

  writeLines(
    sql_traducido,
    file.path(
      ruta_sql,
      archivo
    )
  )

  cat(
    "\nEjecutando:",
    archivo,
    "| datetime sustituidos:",
    n_correcciones,
    "\n"
  )

  executeSql(
    conexion,
    sql_traducido
  )
}

disconnect(conexion)

cat("\n===== 4. GENERAR CONTEOS Y VALIDACIONES =====\n")

conexion <- connect(detalles)

tablas <- querySql(
  conexion,
  paste(
    "SELECT table_name",
    "FROM information_schema.tables",
    "WHERE table_schema = 'cdm'",
    "ORDER BY table_name"
  )
)

nombres_tablas <- as.character(
  tablas[[1]]
)

conteos <- lapply(
  nombres_tablas,
  function(tabla) {
    resultado <- querySql(
      conexion,
      paste0(
        "SELECT COUNT(*) AS n FROM cdm.",
        identificador(tabla)
      )
    )

    data.frame(
      table_name = tabla,
      row_count = as.numeric(
        resultado[[1]][1]
      ),
      stringsAsFactors = FALSE
    )
  }
)

conteos <- do.call(
  rbind,
  conteos
)

write.csv(
  conteos,
  file.path(
    ruta_evidencias,
    "04_conteos_omop.csv"
  ),
  row.names = FALSE
)

resumen_vocabulario <- querySql(
  conexion,
  paste(
    "SELECT",
    "COUNT(*) AS total_concepts,",
    "SUM(CASE",
    "WHEN standard_concept = 'S'",
    "THEN 1 ELSE 0 END)",
    "AS standard_concepts",
    "FROM cdm.concept"
  )
)

write.csv(
  resumen_vocabulario,
  file.path(
    ruta_evidencias,
    "05_vocabulario_resumen.csv"
  ),
  row.names = FALSE
)

validacion <- querySql(
  conexion,
  paste(
    "SELECT",
    "(SELECT COUNT(*) FROM cdm.person)",
    "AS persons,",
    "(SELECT COUNT(*) FROM cdm.visit_occurrence)",
    "AS visits,",
    "(SELECT COUNT(*) FROM cdm.condition_occurrence)",
    "AS conditions,",
    "(SELECT COUNT(*) FROM cdm.drug_exposure)",
    "AS drugs,",
    "(SELECT COUNT(*) FROM cdm.measurement)",
    "AS measurements,",
    "(SELECT COUNT(*) FROM cdm.procedure_occurrence)",
    "AS procedures,",
    "(SELECT COUNT(*) FROM cdm.device_exposure)",
    "AS devices,",
    "(SELECT COUNT(*) FROM cdm.death)",
    "AS deaths"
  )
)

write.csv(
  validacion,
  file.path(
    ruta_evidencias,
    "08_validacion_clinica.csv"
  ),
  row.names = FALSE
)

datetime_no_nulos <- querySql(
  conexion,
  paste(
    "SELECT",
    "(SELECT COUNT(*)",
    "FROM cdm.condition_occurrence",
    "WHERE condition_start_datetime IS NOT NULL",
    "OR condition_end_datetime IS NOT NULL)",
    "AS condition_datetime_non_null,",
    "(SELECT COUNT(*)",
    "FROM cdm.measurement",
    "WHERE measurement_datetime IS NOT NULL)",
    "AS measurement_datetime_non_null,",
    "(SELECT COUNT(*)",
    "FROM cdm.drug_exposure",
    "WHERE drug_exposure_start_datetime IS NOT NULL",
    "OR drug_exposure_end_datetime IS NOT NULL)",
    "AS drug_datetime_non_null"
  )
)

write.csv(
  datetime_no_nulos,
  file.path(
    ruta_evidencias,
    "11_datetime_nulos_documentados.csv"
  ),
  row.names = FALSE
)

print(resumen_vocabulario)
print(validacion)
print(datetime_no_nulos)

executeSql(
  conexion,
  "CHECKPOINT;"
)

disconnect(conexion)

campos_esenciales <- c(
  "persons",
  "visits",
  "conditions",
  "drugs",
  "measurements",
  "procedures"
)

valores_esenciales <- as.numeric(
  validacion[
    1,
    campos_esenciales
  ]
)

if (
  any(
    is.na(valores_esenciales) |
      valores_esenciales == 0
  )
) {
  stop(
    "Una o más tablas clínicas esenciales quedaron vacías."
  )
}

cat(
  "\n===== CARGA COMPATIBLE COMPLETADA =====\n"
)

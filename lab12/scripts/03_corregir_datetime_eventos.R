#!/usr/bin/env Rscript

library(ETLSyntheaBuilder)
library(DatabaseConnector)

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

ruta_ajuste <- file.path(
  raiz,
  "lab12",
  "scripts",
  "schema_fix.R"
)

source(ruta_ajuste)

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

tablas_preservadas <- tolower(
  c(
    cdmVocabularyTables,
    "source_to_concept_map",
    "source_to_standard_vocab_map",
    "source_to_source_vocab_map",
    "states_map",
    "all_visits",
    "assign_all_visit_ids",
    "final_visit_ids"
  )
)

cat("===== 1. VALIDAR VOCABULARIO Y MAPAS =====\n")

conexion <- connect(detalles)

prerrequisitos <- querySql(
  conexion,
  paste(
    "SELECT",
    "(SELECT COUNT(*) FROM cdm.concept)",
    "AS concepts,",
    "(SELECT COUNT(*)",
    "FROM cdm.source_to_standard_vocab_map)",
    "AS standard_maps,",
    "(SELECT COUNT(*)",
    "FROM cdm.source_to_source_vocab_map)",
    "AS source_maps,",
    "(SELECT COUNT(*) FROM cdm.final_visit_ids)",
    "AS final_visit_ids"
  )
)

print(prerrequisitos)

if (
  any(
    is.na(prerrequisitos[1, ]) |
      prerrequisitos[1, ] == 0
  )
) {
  stop(
    "Los vocabularios o mapas no están completos."
  )
}

cat("\n===== 2. VACIAR TABLAS CLÍNICAS PARCIALES =====\n")

inventario <- querySql(
  conexion,
  paste(
    "SELECT table_name",
    "FROM information_schema.tables",
    "WHERE table_schema = 'cdm'",
    "ORDER BY table_name"
  )
)

tablas_cdm <- as.character(
  inventario[[1]]
)

tablas_clinicas <- tablas_cdm[
  !tolower(tablas_cdm) %in%
    tablas_preservadas
]

for (tabla in tablas_clinicas) {
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

cat("\n===== 3. AUDITAR COLUMNAS DATETIME =====\n")

datetime_antes <- querySql(
  conexion,
  paste(
    "SELECT",
    "table_name,",
    "column_name,",
    "data_type",
    "FROM information_schema.columns",
    "WHERE table_schema = 'cdm'",
    "AND lower(column_name) LIKE '%_datetime'",
    "ORDER BY table_name, ordinal_position"
  )
)

print(datetime_antes)

write.csv(
  datetime_antes,
  file.path(
    ruta_evidencias,
    "09_datetime_antes.csv"
  ),
  row.names = FALSE
)

nombres_tabla <- as.character(
  datetime_antes[[1]]
)

nombres_columna <- as.character(
  datetime_antes[[2]]
)

tipos <- toupper(
  as.character(
    datetime_antes[[3]]
  )
)

requiere_correccion <- !grepl(
  "^TIMESTAMP",
  tipos
)

if (!any(requiere_correccion)) {
  cat(
    "Todos los campos datetime ya son TIMESTAMP.\n"
  )
} else {
  cat(
    "\n===== 4. CORREGIR DATETIME A TIMESTAMP =====\n"
  )

  for (i in which(requiere_correccion)) {
    tabla <- nombres_tabla[i]
    columna <- nombres_columna[i]

    cat(
      tabla,
      ".",
      columna,
      ": ",
      tipos[i],
      " -> TIMESTAMP\n",
      sep = ""
    )

    executeSql(
      conexion,
      paste0(
        "ALTER TABLE cdm.",
        identificador(tabla),
        " ALTER COLUMN ",
        identificador(columna),
        " SET DATA TYPE TIMESTAMP;"
      )
    )
  }
}

datetime_despues <- querySql(
  conexion,
  paste(
    "SELECT",
    "table_name,",
    "column_name,",
    "data_type",
    "FROM information_schema.columns",
    "WHERE table_schema = 'cdm'",
    "AND lower(column_name) LIKE '%_datetime'",
    "ORDER BY table_name, ordinal_position"
  )
)

write.csv(
  datetime_despues,
  file.path(
    ruta_evidencias,
    "10_datetime_despues.csv"
  ),
  row.names = FALSE
)

tipos_despues <- toupper(
  as.character(
    datetime_despues[[3]]
  )
)

if (
  any(
    !grepl(
      "^TIMESTAMP",
      tipos_despues
    )
  )
) {
  stop(
    "Persisten columnas datetime con un tipo incorrecto."
  )
}

disconnect(conexion)

cat("\n===== 5. RECARGAR EVENTOS CLÍNICOS =====\n")

LoadEventTables(
  connectionDetails = detalles,
  cdmSchema = "cdm",
  syntheaSchema = "synthea_native",
  cdmVersion = "5.4",
  syntheaVersion = "3.3.0"
)

cat("\n===== 6. MATERIALIZAR EVENTOS =====\n")

materializeSchemaQualifiedTables(
  connectionDetails = detalles,
  schema = "cdm",
  tables = cdmEventTables
)

cat("\n===== 7. GENERAR VALIDACIONES FINALES =====\n")

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
    "AS procedures"
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

print(resumen_vocabulario)
print(validacion)

executeSql(
  conexion,
  "CHECKPOINT;"
)

disconnect(conexion)

if (
  any(
    is.na(validacion[1, ]) |
      validacion[1, ] == 0
  )
) {
  stop(
    "Una o más tablas clínicas esenciales quedaron vacías."
  )
}

cat(
  "\n===== CORRECCIÓN DATETIME COMPLETADA =====\n"
)

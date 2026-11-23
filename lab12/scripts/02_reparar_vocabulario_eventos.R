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

ruta_ajuste <- file.path(
  raiz,
  "lab12",
  "scripts",
  "schema_fix.R"
)

if (!file.exists(ruta_base)) {
  stop(
    "No se encontró la base OMOP: ",
    ruta_base
  )
}

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

esquema_cdm <- "cdm"
esquema_synthea <- "synthea_native"
version_cdm <- "5.4"
version_synthea <- "3.3.0"

tablas_vocabulario <- c(
  "concept",
  "concept_ancestor",
  "concept_class",
  "concept_relationship",
  "concept_synonym",
  "domain",
  "drug_strength",
  "relationship",
  "vocabulary"
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

cat(
  "===== 1. LOCALIZAR Y MATERIALIZAR VOCABULARIOS =====\n"
)

conexion <- connect(detalles)

inventario <- querySql(
  conexion,
  paste(
    "SELECT table_schema, table_name",
    "FROM information_schema.tables",
    "ORDER BY table_schema, table_name"
  )
)

schema_col <- as.character(
  inventario[[1]]
)

table_col <- as.character(
  inventario[[2]]
)

resultado_materializacion <- list()

for (tabla in tablas_vocabulario) {
  nombre_esperado <- paste0(
    "cdm.",
    tabla
  )

  coincidencias <- which(
    tolower(schema_col) == "main" &
      tolower(table_col) == nombre_esperado
  )

  if (length(coincidencias) != 1L) {
    stop(
      "Se esperaba una tabla literal para ",
      nombre_esperado,
      "; se encontraron ",
      length(coincidencias),
      "."
    )
  }

  nombre_literal <- table_col[
    coincidencias
  ]

  origen <- paste0(
    identificador("main"),
    ".",
    identificador(nombre_literal)
  )

  destino <- paste0(
    identificador(esquema_cdm),
    ".",
    identificador(tabla)
  )

  conteo_origen <- querySql(
    conexion,
    paste0(
      "SELECT COUNT(*) AS n FROM ",
      origen
    )
  )

  n_origen <- as.numeric(
    conteo_origen[[1]][1]
  )

  if (
    is.na(n_origen) ||
      n_origen == 0
  ) {
    stop(
      "La tabla literal está vacía: ",
      nombre_literal
    )
  }

  cat(
    sprintf(
      "%-28s %s filas\n",
      tabla,
      format(
        n_origen,
        big.mark = ",",
        scientific = FALSE
      )
    )
  )

  executeSql(
    conexion,
    paste0(
      "TRUNCATE TABLE ",
      destino,
      ";"
    )
  )

  executeSql(
    conexion,
    paste0(
      "INSERT INTO ",
      destino,
      " SELECT * FROM ",
      origen,
      ";"
    )
  )

  conteo_destino <- querySql(
    conexion,
    paste0(
      "SELECT COUNT(*) AS n FROM ",
      destino
    )
  )

  n_destino <- as.numeric(
    conteo_destino[[1]][1]
  )

  if (
    is.na(n_destino) ||
      n_destino != n_origen
  ) {
    stop(
      "Conteo desigual después de materializar ",
      tabla,
      ": origen=",
      n_origen,
      ", destino=",
      n_destino
    )
  }

  resultado_materializacion[[
    length(resultado_materializacion) + 1L
  ]] <- data.frame(
    table_name = tabla,
    source_rows = n_origen,
    target_rows = n_destino,
    stringsAsFactors = FALSE
  )
}

resultado_materializacion <- do.call(
  rbind,
  resultado_materializacion
)

write.csv(
  resultado_materializacion,
  file.path(
    ruta_evidencias,
    "06_materializacion_vocabulario.csv"
  ),
  row.names = FALSE
)

disconnect(conexion)

cat(
  "\n===== 2. RECONSTRUIR MAPAS SIN ÍNDICES =====\n"
)

consultas_mapeo <- c(
  "create_source_to_standard_vocab_map.sql",
  "create_source_to_source_vocab_map.sql",
  "create_states_map.sql"
)

conexion <- connect(detalles)

for (consulta in consultas_mapeo) {
  cat(
    "Ejecutando:",
    consulta,
    "\n"
  )

  sql <- loadRenderTranslateSql(
    sqlFilename = paste0(
      "cdm_version/v540/",
      consulta
    ),
    packageName = "ETLSyntheaBuilder",
    dbms = detalles$dbms,
    cdm_schema = esquema_cdm
  )

  sql <- gsub(
    pattern = "(?is)create\\s+index\\s+[^;]+;",
    replacement = "",
    x = sql,
    perl = TRUE
  )

  executeSql(
    conexion,
    sql
  )
}

disconnect(conexion)

cat(
  "\n===== 3. RECONSTRUIR ROLLUP DE VISITAS =====\n"
)

CreateVisitRollupTables(
  connectionDetails = detalles,
  cdmSchema = esquema_cdm,
  syntheaSchema = esquema_synthea,
  cdmVersion = version_cdm
)

cat(
  "\n===== 4. VALIDAR MAPAS =====\n"
)

conexion <- connect(detalles)

tablas_mapeo <- c(
  "source_to_standard_vocab_map",
  "source_to_source_vocab_map",
  "states_map",
  "all_visits",
  "assign_all_visit_ids",
  "final_visit_ids"
)

conteos_mapeo <- lapply(
  tablas_mapeo,
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

conteos_mapeo <- do.call(
  rbind,
  conteos_mapeo
)

print(conteos_mapeo)

if (
  any(
    is.na(conteos_mapeo$row_count) |
      conteos_mapeo$row_count == 0
  )
) {
  stop(
    "Una o más tablas de mapeo quedaron vacías."
  )
}

write.csv(
  conteos_mapeo,
  file.path(
    ruta_evidencias,
    "07_conteos_mapeo.csv"
  ),
  row.names = FALSE
)

cat(
  "\n===== 5. VACIAR TABLAS CLÍNICAS PREVIAS =====\n"
)

inventario_cdm <- querySql(
  conexion,
  paste(
    "SELECT table_name",
    "FROM information_schema.tables",
    "WHERE table_schema = 'cdm'",
    "ORDER BY table_name"
  )
)

tablas_cdm <- as.character(
  inventario_cdm[[1]]
)

tablas_preservadas <- tolower(
  c(
    tablas_vocabulario,
    "source_to_concept_map",
    tablas_mapeo
  )
)

tablas_a_vaciar <- tablas_cdm[
  !tolower(tablas_cdm) %in%
    tablas_preservadas
]

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

cat(
  "\n===== 6. RECARGAR TABLAS CLÍNICAS =====\n"
)

LoadEventTables(
  connectionDetails = detalles,
  cdmSchema = esquema_cdm,
  syntheaSchema = esquema_synthea,
  cdmVersion = version_cdm,
  syntheaVersion = version_synthea
)

cat(
  "\n===== 7. MATERIALIZAR TABLAS CLÍNICAS =====\n"
)

materializeSchemaQualifiedTables(
  connectionDetails = detalles,
  schema = esquema_cdm,
  tables = cdmEventTables
)

cat(
  "\n===== 8. GENERAR CONTEOS FINALES =====\n"
)

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
    "THEN 1 ELSE 0 END",
    ") AS standard_concepts",
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

validacion_clinica <- querySql(
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
  validacion_clinica,
  file.path(
    ruta_evidencias,
    "08_validacion_clinica.csv"
  ),
  row.names = FALSE
)

executeSql(
  conexion,
  "CHECKPOINT;"
)

disconnect(conexion)

print(resumen_vocabulario)
print(validacion_clinica)

if (
  any(
    is.na(validacion_clinica[1, ]) |
      validacion_clinica[1, ] == 0
  )
) {
  stop(
    "Una o más tablas clínicas esenciales quedaron vacías."
  )
}

cat(
  "\n===== REPARACIÓN COMPLETADA =====\n"
)

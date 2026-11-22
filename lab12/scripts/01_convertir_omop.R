#!/usr/bin/env Rscript

options(
  repos = c(
    CRAN = "https://cloud.r-project.org"
  )
)

paquetes <- c(
  "ETLSyntheaBuilder",
  "DatabaseConnector",
  "SqlRender",
  "duckdb",
  "CommonDataModel"
)

faltantes <- paquetes[
  !vapply(
    paquetes,
    requireNamespace,
    logical(1),
    quietly = TRUE
  )
]

if (length(faltantes)) {
  stop(
    "Faltan paquetes: ",
    paste(faltantes, collapse = ", ")
  )
}

library(ETLSyntheaBuilder)
library(DatabaseConnector)
library(SqlRender)

raiz <- normalizePath(
  getwd(),
  mustWork = TRUE
)

ruta_synthea <- file.path(
  raiz,
  "lab10",
  "data",
  "raw",
  "synthea_5000",
  "csv"
)

candidatos_vocabulario <- list.files(
  file.path(
    raiz,
    "lab12",
    "data",
    "raw",
    "athena"
  ),
  pattern = "^CONCEPT\\.csv$",
  recursive = TRUE,
  full.names = TRUE
)

if (length(candidatos_vocabulario) != 1L) {
  stop(
    "Se esperaba exactamente un CONCEPT.csv; se encontraron ",
    length(candidatos_vocabulario),
    "."
  )
}

ruta_vocabulario <- dirname(
  normalizePath(
    candidatos_vocabulario,
    mustWork = TRUE
  )
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

dir.create(
  dirname(ruta_base),
  recursive = TRUE,
  showWarnings = FALSE
)

dir.create(
  ruta_evidencias,
  recursive = TRUE,
  showWarnings = FALSE
)

if (!dir.exists(ruta_synthea)) {
  stop(
    "No se encontró el directorio de Synthea: ",
    ruta_synthea
  )
}

if (!file.exists(ruta_ajuste)) {
  stop(
    "No se encontró schema_fix.R: ",
    ruta_ajuste
  )
}

if (file.exists(ruta_base)) {
  stop(
    paste0(
      "La base ya existe y no será sobrescrita: ",
      ruta_base,
      "\nRevísala antes de decidir si debe eliminarse."
    )
  )
}

archivos_synthea <- c(
  "allergies.csv",
  "careplans.csv",
  "claims.csv",
  "claims_transactions.csv",
  "conditions.csv",
  "devices.csv",
  "encounters.csv",
  "imaging_studies.csv",
  "immunizations.csv",
  "medications.csv",
  "observations.csv",
  "organizations.csv",
  "patients.csv",
  "payer_transitions.csv",
  "payers.csv",
  "procedures.csv",
  "providers.csv",
  "supplies.csv"
)

faltantes_synthea <- archivos_synthea[
  !file.exists(
    file.path(
      ruta_synthea,
      archivos_synthea
    )
  )
]

if (length(faltantes_synthea)) {
  stop(
    "Faltan CSV de Synthea: ",
    paste(faltantes_synthea, collapse = ", ")
  )
}

archivos_vocabulario <- c(
  "CONCEPT.csv",
  "CONCEPT_RELATIONSHIP.csv",
  "CONCEPT_ANCESTOR.csv",
  "VOCABULARY.csv",
  "DOMAIN.csv",
  "CONCEPT_CLASS.csv",
  "RELATIONSHIP.csv",
  "CONCEPT_SYNONYM.csv",
  "DRUG_STRENGTH.csv"
)

faltantes_vocabulario <- archivos_vocabulario[
  !file.exists(
    file.path(
      ruta_vocabulario,
      archivos_vocabulario
    )
  )
]

if (length(faltantes_vocabulario)) {
  stop(
    "Faltan tablas de vocabulario: ",
    paste(
      faltantes_vocabulario,
      collapse = ", "
    )
  )
}

source(ruta_ajuste)

version_cdm <- "5.4"

# Los CSV proceden de Synthea 3.4.0-18, pero la auditoría demostró
# igualdad exacta de nombres, número y orden de columnas con v3.3.0.
version_synthea_etl <- "3.3.0"

esquema_cdm <- "cdm"
esquema_synthea <- "synthea_native"

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

ejecutar_etapa <- function(nombre, expresion) {
  cat(
    "\n",
    strrep("=", 70),
    "\n",
    nombre,
    "\n",
    strrep("=", 70),
    "\n",
    sep = ""
  )

  inicio <- Sys.time()

  resultado <- force(expresion)

  fin <- Sys.time()

  cat(
    "Duración:",
    round(
      as.numeric(
        difftime(
          fin,
          inicio,
          units = "mins"
        )
      ),
      3
    ),
    "minutos\n"
  )

  invisible(resultado)
}

cat("===== CONFIGURACIÓN =====\n")
cat("R:", R.version.string, "\n")
cat("Java:", Sys.getenv("JAVA_HOME"), "\n")
cat("DatabaseConnector:", as.character(packageVersion("DatabaseConnector")), "\n")
cat("SqlRender:", as.character(packageVersion("SqlRender")), "\n")
cat("duckdb:", as.character(packageVersion("duckdb")), "\n")
cat("CommonDataModel:", as.character(packageVersion("CommonDataModel")), "\n")
cat("ETLSyntheaBuilder:", as.character(packageVersion("ETLSyntheaBuilder")), "\n")
cat("Synthea original: 3.4.0-18-ga07a65555\n")
cat("Esquema compatible utilizado por el ETL:", version_synthea_etl, "\n")
cat("CDM:", version_cdm, "\n")
cat("CSV Synthea:", ruta_synthea, "\n")
cat("Vocabularios:", ruta_vocabulario, "\n")
cat("Base de salida:", ruta_base, "\n")

ejecutar_etapa(
  "1. Crear esquemas de DuckDB",
  {
    conexion <- connect(detalles)

    for (esquema in c(
      esquema_cdm,
      esquema_synthea
    )) {
      sql <- sprintf(
        "CREATE SCHEMA IF NOT EXISTS %s;",
        esquema
      )

      executeSql(
        conexion,
        sql
      )
    }

    disconnect(conexion)
  }
)

ejecutar_etapa(
  "2. Crear tablas OMOP CDM v5.4",
  CreateCDMTables(
    connectionDetails = detalles,
    cdmSchema = esquema_cdm,
    cdmVersion = version_cdm
  )
)

ejecutar_etapa(
  "3. Crear tablas nativas de Synthea",
  CreateSyntheaTables(
    connectionDetails = detalles,
    syntheaSchema = esquema_synthea,
    syntheaVersion = version_synthea_etl
  )
)

ejecutar_etapa(
  "4. Cargar CSV de Synthea",
  LoadSyntheaTables(
    connectionDetails = detalles,
    syntheaSchema = esquema_synthea,
    syntheaFileLoc = ruta_synthea
  )
)

ejecutar_etapa(
  "5. Materializar esquema nativo",
  materializeSchemaQualifiedTables(
    connectionDetails = detalles,
    schema = esquema_synthea,
    tables = syntheaSourceTables
  )
)

ejecutar_etapa(
  "6. Cargar vocabularios de ATHENA",
  LoadVocabFromCsv(
    connectionDetails = detalles,
    cdmSchema = esquema_cdm,
    vocabFileLoc = ruta_vocabulario,
    delimiter = "\t"
  )
)

ejecutar_etapa(
  "7. Materializar vocabularios",
  materializeSchemaQualifiedTables(
    connectionDetails = detalles,
    schema = esquema_cdm,
    tables = cdmVocabularyTables
  )
)

ejecutar_etapa(
  "8. Crear tablas de mapeo y rollup",
  CreateMapAndRollupTables(
    connectionDetails = detalles,
    cdmSchema = esquema_cdm,
    syntheaSchema = esquema_synthea,
    cdmVersion = version_cdm,
    syntheaVersion = version_synthea_etl
  )
)

cat(
  paste0(
    "\n",
    strrep("=", 70),
    "\n",
    "9. Índices adicionales omitidos",
    "\n",
    strrep("=", 70),
    "\n",
    "CreateExtraIndices() se omitió porque produjo un ",
    "Abort trap nativo con DuckDB 1.5.0. ",
    "Esta etapa es opcional y no modifica el contenido del CDM.\n"
  )
)

ejecutar_etapa(
  "10. Cargar tablas clínicas OMOP",
  LoadEventTables(
    connectionDetails = detalles,
    cdmSchema = esquema_cdm,
    syntheaSchema = esquema_synthea,
    cdmVersion = version_cdm,
    syntheaVersion = version_synthea_etl
  )
)

ejecutar_etapa(
  "11. Materializar tablas clínicas",
  materializeSchemaQualifiedTables(
    connectionDetails = detalles,
    schema = esquema_cdm,
    tables = cdmEventTables
  )
)

ejecutar_etapa(
  "12. Contar filas de las tablas OMOP",
  {
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
          sprintf(
            'SELECT COUNT(*) AS n FROM cdm."%s"',
            tabla
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

    disconnect(conexion)

    print(conteos)
    print(resumen_vocabulario)
  }
)

cat("\n===== ETL COMPLETADO =====\n")
cat("Base creada:", ruta_base, "\n")

sessionInfo()

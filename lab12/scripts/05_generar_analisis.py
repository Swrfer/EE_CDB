#!/usr/bin/env python3
"""Genera las evidencias analíticas del Laboratorio 12 desde la base OMOP DuckDB."""

from pathlib import Path

import duckdb
import pandas as pd


BASE = Path("lab12/data/omop/synthea_omop_cdm54.duckdb")
SALIDA = Path("lab12/evidencias/analisis")


def consultar(conexion: duckdb.DuckDBPyConnection, sql: str) -> pd.DataFrame:
    return conexion.execute(sql).df()


def guardar(nombre: str, datos: pd.DataFrame) -> None:
    ruta = SALIDA / nombre
    datos.to_csv(ruta, index=False)
    print(f"OK: {ruta} ({len(datos)} filas)")


def tabla_markdown(datos: pd.DataFrame) -> str:
    columnas = [str(columna) for columna in datos.columns]
    lineas = [
        "| " + " | ".join(columnas) + " |",
        "| " + " | ".join(["---"] * len(columnas)) + " |",
    ]
    for _, fila in datos.iterrows():
        valores = []
        for valor in fila:
            if pd.isna(valor):
                texto = ""
            elif isinstance(valor, float):
                texto = f"{valor:.4f}".rstrip("0").rstrip(".")
            else:
                texto = str(valor)
            valores.append(texto.replace("|", r"\|"))
        lineas.append("| " + " | ".join(valores) + " |")
    return "\n".join(lineas)


CONSULTAS = {
    "calidad_mapeo": """
        WITH calidad AS (
            SELECT 'Condition' dominio, COUNT(*) eventos,
                   COUNT(DISTINCT person_id) personas,
                   COUNT_IF(COALESCE(condition_concept_id, 0) = 0) concept_id_cero
            FROM cdm.condition_occurrence
            UNION ALL
            SELECT 'Drug', COUNT(*), COUNT(DISTINCT person_id),
                   COUNT_IF(COALESCE(drug_concept_id, 0) = 0)
            FROM cdm.drug_exposure
            UNION ALL
            SELECT 'Measurement', COUNT(*), COUNT(DISTINCT person_id),
                   COUNT_IF(COALESCE(measurement_concept_id, 0) = 0)
            FROM cdm.measurement
            UNION ALL
            SELECT 'Observation', COUNT(*), COUNT(DISTINCT person_id),
                   COUNT_IF(COALESCE(observation_concept_id, 0) = 0)
            FROM cdm.observation
            UNION ALL
            SELECT 'Procedure', COUNT(*), COUNT(DISTINCT person_id),
                   COUNT_IF(COALESCE(procedure_concept_id, 0) = 0)
            FROM cdm.procedure_occurrence
            UNION ALL
            SELECT 'Visit', COUNT(*), COUNT(DISTINCT person_id),
                   COUNT_IF(COALESCE(visit_concept_id, 0) = 0)
            FROM cdm.visit_occurrence
        )
        SELECT dominio, eventos, personas, concept_id_cero,
               ROUND(100.0 * concept_id_cero / NULLIF(eventos, 0), 4)
                   porcentaje_concept_id_cero
        FROM calidad
        ORDER BY porcentaje_concept_id_cero DESC, dominio
    """,
    "personas_sexo": """
        SELECT COALESCE(c.concept_name, 'Sin concepto legible') sexo,
               COUNT(DISTINCT p.person_id) personas,
               ROUND(100.0 * COUNT(DISTINCT p.person_id)
                     / SUM(COUNT(DISTINCT p.person_id)) OVER (), 2) porcentaje
        FROM cdm.person p
        LEFT JOIN cdm.concept c ON c.concept_id = p.gender_concept_id
        GROUP BY 1
        ORDER BY personas DESC
    """,
    "personas_nacimiento": """
        SELECT year_of_birth anio_nacimiento, COUNT(DISTINCT person_id) personas
        FROM cdm.person
        GROUP BY year_of_birth
        ORDER BY year_of_birth
    """,
    "observacion_mediana": """
        WITH por_persona AS (
            SELECT person_id,
                   SUM(DATE_DIFF('day', observation_period_start_date,
                                 observation_period_end_date) + 1) dias_observacion
            FROM cdm.observation_period
            GROUP BY person_id
        )
        SELECT COUNT(DISTINCT person_id) personas,
               MEDIAN(dias_observacion) mediana_dias_observacion,
               ROUND(AVG(dias_observacion), 2) media_dias_observacion,
               MIN(dias_observacion) minimo_dias,
               MAX(dias_observacion) maximo_dias
        FROM por_persona
    """,
    "top20_diagnosticos": """
        SELECT co.condition_concept_id concept_id, c.concept_name,
               COUNT(*) eventos, COUNT(DISTINCT co.person_id) personas
        FROM cdm.condition_occurrence co
        LEFT JOIN cdm.concept c ON c.concept_id = co.condition_concept_id
        WHERE co.condition_concept_id <> 0
        GROUP BY co.condition_concept_id, c.concept_name
        ORDER BY eventos DESC, personas DESC
        LIMIT 20
    """,
    "visitas_resumen": """
        WITH por_persona AS (
            SELECT p.person_id, COUNT(v.visit_occurrence_id) visitas
            FROM cdm.person p
            LEFT JOIN cdm.visit_occurrence v ON v.person_id = p.person_id
            GROUP BY p.person_id
        )
        SELECT COUNT(DISTINCT person_id) personas, SUM(visitas) visitas,
               ROUND(AVG(visitas), 4) media_visitas_por_persona,
               MEDIAN(visitas) mediana_visitas_por_persona
        FROM por_persona
    """,
    "visitas_tipo": """
        SELECT v.visit_concept_id concept_id,
               COALESCE(c.concept_name, 'Sin concepto legible') tipo_visita,
               COUNT(*) visitas, COUNT(DISTINCT v.person_id) personas,
               ROUND(COUNT(*) * 1.0 / NULLIF(COUNT(DISTINCT v.person_id), 0), 4)
                   media_visitas_por_persona
        FROM cdm.visit_occurrence v
        LEFT JOIN cdm.concept c ON c.concept_id = v.visit_concept_id
        GROUP BY v.visit_concept_id, c.concept_name
        ORDER BY visitas DESC
    """,
    "estandar_vs_origen": """
        WITH frecuente AS (
            SELECT condition_concept_id,
                   COUNT(*) eventos_estandar,
                   COUNT(DISTINCT person_id) personas_estandar
            FROM cdm.condition_occurrence
            WHERE condition_concept_id <> 0
            GROUP BY condition_concept_id
            ORDER BY eventos_estandar DESC
            LIMIT 1
        ), origen AS (
            SELECT co.condition_concept_id, co.condition_source_value,
                   COUNT(*) eventos_origen,
                   COUNT(DISTINCT co.person_id) personas_origen,
                   ROW_NUMBER() OVER (
                       PARTITION BY co.condition_concept_id
                       ORDER BY COUNT(*) DESC, co.condition_source_value
                   ) posicion
            FROM cdm.condition_occurrence co
            JOIN frecuente f ON f.condition_concept_id = co.condition_concept_id
            GROUP BY co.condition_concept_id, co.condition_source_value
        )
        SELECT f.condition_concept_id concept_id, c.concept_name,
               f.eventos_estandar, f.personas_estandar,
               o.condition_source_value codigo_origen_mas_frecuente,
               o.eventos_origen, o.personas_origen,
               f.eventos_estandar - o.eventos_origen diferencia_eventos,
               ROUND(100.0 * (f.eventos_estandar - o.eventos_origen)
                     / NULLIF(f.eventos_estandar, 0), 4) diferencia_porcentaje
        FROM frecuente f
        LEFT JOIN cdm.concept c ON c.concept_id = f.condition_concept_id
        LEFT JOIN origen o ON o.condition_concept_id = f.condition_concept_id
                           AND o.posicion = 1
    """,
    "codigos_origen_condicion": """
        WITH frecuente AS (
            SELECT condition_concept_id
            FROM cdm.condition_occurrence
            WHERE condition_concept_id <> 0
            GROUP BY condition_concept_id
            ORDER BY COUNT(*) DESC
            LIMIT 1
        )
        SELECT co.condition_concept_id concept_id, c.concept_name,
               co.condition_source_value codigo_origen,
               COUNT(*) eventos, COUNT(DISTINCT co.person_id) personas
        FROM cdm.condition_occurrence co
        JOIN frecuente f ON f.condition_concept_id = co.condition_concept_id
        LEFT JOIN cdm.concept c ON c.concept_id = co.condition_concept_id
        GROUP BY co.condition_concept_id, c.concept_name,
                 co.condition_source_value
        ORDER BY eventos DESC
    """,
    "ventana_observacion": """
        WITH evaluados AS (
            SELECT co.*,
                   EXISTS (
                       SELECT 1
                       FROM cdm.observation_period op
                       WHERE op.person_id = co.person_id
                         AND co.condition_start_date BETWEEN
                             op.observation_period_start_date
                             AND op.observation_period_end_date
                   ) dentro
            FROM cdm.condition_occurrence co
        )
        SELECT COUNT(*) eventos_sin_filtrar,
               COUNT(*) FILTER (WHERE dentro) eventos_dentro_observacion,
               COUNT(*) FILTER (WHERE NOT dentro) eventos_fuera_observacion,
               ROUND(100.0 * COUNT(*) FILTER (WHERE NOT dentro)
                     / NULLIF(COUNT(*), 0), 4) diferencia_porcentaje,
               COUNT(DISTINCT person_id) personas_sin_filtrar,
               COUNT(DISTINCT person_id) FILTER (WHERE dentro)
                   personas_dentro_observacion
        FROM evaluados
    """,
    "athena_top3": """
        WITH top3 AS (
            SELECT condition_concept_id,
                   COUNT(*) eventos,
                   COUNT(DISTINCT person_id) personas
            FROM cdm.condition_occurrence
            WHERE condition_concept_id <> 0
            GROUP BY condition_concept_id
            ORDER BY eventos DESC
            LIMIT 3
        ), hijos AS (
            SELECT ca.ancestor_concept_id,
                   COUNT(DISTINCT ca.descendant_concept_id) conceptos_hijos
            FROM cdm.concept_ancestor ca
            JOIN top3 t ON t.condition_concept_id = ca.ancestor_concept_id
            WHERE ca.descendant_concept_id <> ca.ancestor_concept_id
            GROUP BY ca.ancestor_concept_id
        ), origen AS (
            SELECT co.condition_concept_id, co.condition_source_value,
                   ROW_NUMBER() OVER (
                       PARTITION BY co.condition_concept_id
                       ORDER BY COUNT(*) DESC, co.condition_source_value
                   ) posicion
            FROM cdm.condition_occurrence co
            JOIN top3 t ON t.condition_concept_id = co.condition_concept_id
            GROUP BY co.condition_concept_id, co.condition_source_value
        )
        SELECT t.condition_concept_id concept_id, c.concept_name,
               c.vocabulary_id, c.domain_id, c.standard_concept,
               t.eventos, t.personas,
               COALESCE(h.conceptos_hijos, 0) conceptos_hijos,
               o.condition_source_value codigo_origen_ejemplo
        FROM top3 t
        LEFT JOIN cdm.concept c ON c.concept_id = t.condition_concept_id
        LEFT JOIN hijos h ON h.ancestor_concept_id = t.condition_concept_id
        LEFT JOIN origen o ON o.condition_concept_id = t.condition_concept_id
                          AND o.posicion = 1
        ORDER BY t.eventos DESC
    """,
    "conteos_tablas": """
        SELECT 'person' tabla, COUNT(*) filas FROM cdm.person
        UNION ALL SELECT 'observation_period', COUNT(*) FROM cdm.observation_period
        UNION ALL SELECT 'visit_occurrence', COUNT(*) FROM cdm.visit_occurrence
        UNION ALL SELECT 'condition_occurrence', COUNT(*) FROM cdm.condition_occurrence
        UNION ALL SELECT 'drug_exposure', COUNT(*) FROM cdm.drug_exposure
        UNION ALL SELECT 'measurement', COUNT(*) FROM cdm.measurement
        UNION ALL SELECT 'observation', COUNT(*) FROM cdm.observation
        UNION ALL SELECT 'procedure_occurrence', COUNT(*) FROM cdm.procedure_occurrence
        UNION ALL SELECT 'concept', COUNT(*) FROM cdm.concept
        UNION ALL SELECT 'concept_relationship', COUNT(*) FROM cdm.concept_relationship
        UNION ALL SELECT 'concept_ancestor', COUNT(*) FROM cdm.concept_ancestor
        ORDER BY tabla
    """,
}


def crear_reporte(resultados: dict[str, pd.DataFrame]) -> None:
    calidad = resultados["calidad_mapeo"]
    peor = calidad.iloc[0]
    obs = resultados["observacion_mediana"].iloc[0]
    comp = resultados["estandar_vs_origen"].iloc[0]
    ventana = resultados["ventana_observacion"].iloc[0]

    reporte = f"""# Reporte de calidad — Laboratorio 12

## 1. Ruta de conversión

Se eligió **ETL-Synthea**, el paquete de OHDSI orientado a transformar CSV de
Synthea al OMOP CDM. Esta ruta conserva reglas de mapeo reproducibles y evita
construir manualmente cada tabla clínica.

La fuente se generó con Synthea `v3.4.0-18-ga07a65555`. Se comprobó que las 18
tablas de entrada tenían las columnas esperadas por la implementación compatible
con Synthea 3.3.0.

## 2. Implementación

- OMOP CDM: 5.4.
- ETLSyntheaBuilder: 2.1.
- DatabaseConnector: 7.1.0.
- SqlRender: 1.19.4.
- DuckDB de R: 1.5.0.
- Java: 17.0.18.
- Personas convertidas: 5,745.
- Conceptos: 2,026,160.
- Conceptos estándar: 846,202.

Se cargaron los vocabularios SNOMED, ICD10CM, RxNorm, LOINC y ATC, incluidas
`CONCEPT`, `CONCEPT_RELATIONSHIP` y `CONCEPT_ANCESTOR`.

## 3. Conteos de tablas

{tabla_markdown(resultados['conteos_tablas'])}

## 4. Calidad del mapeo

{tabla_markdown(calidad)}

El mayor porcentaje de `concept_id = 0` correspondió a **{peor['dominio']}**
con **{peor['porcentaje_concept_id_cero']}%**. Estos eventos pueden perderse en
silencio al definir cohortes exclusivamente con conceptos estándar.

## 5. Caracterización de la población

### Sexo

{tabla_markdown(resultados['personas_sexo'])}

La mediana de observación fue de **{obs['mediana_dias_observacion']} días** por
persona y la media de **{obs['media_dias_observacion']} días**.

### Diagnósticos más frecuentes

{tabla_markdown(resultados['top20_diagnosticos'])}

### Visitas

{tabla_markdown(resultados['visitas_resumen'])}

{tabla_markdown(resultados['visitas_tipo'])}

## 6. Concepto estándar frente a origen

{tabla_markdown(resultados['estandar_vs_origen'])}

Para **{comp['concept_name']}** (`concept_id = {comp['concept_id']}`) se
contaron **{comp['eventos_estandar']} eventos** por concepto estándar, frente a
**{comp['eventos_origen']}** para el código fuente más frecuente
(`{comp['codigo_origen_mas_frecuente']}`). La diferencia se debe a que varios
códigos de origen pueden mapear al mismo concepto estándar; los no mapeados
quedan en `concept_id = 0`.

## 7. Ventana de observación

{tabla_markdown(resultados['ventana_observacion'])}

Sin filtrar se contaron **{ventana['eventos_sin_filtrar']} eventos** y dentro de
la ventana quedaron **{ventana['eventos_dentro_observacion']}**. La diferencia
fue **{ventana['diferencia_porcentaje']}%**. Ignorar `OBSERVATION_PERIOD` puede
incluir eventos fuera del seguimiento y sesgar denominadores, incidencia y
tiempo hasta evento.

## 8. Conceptos revisados para ATHENA

{tabla_markdown(resultados['athena_top3'])}

Los descendientes se calcularon con `CONCEPT_ANCESTOR`; el código de origen es
el más frecuente observado para cada concepto estándar.

## 9. Simplificaciones documentadas

1. Se corrigió la materialización inicial del vocabulario dentro del esquema
   `cdm` antes de construir los mapas.
2. Los campos `*_datetime` afectados se dejaron nulos porque la fuente aporta
   fechas sin hora verificable; los campos `*_date` se conservaron.
3. `condition_era`, `drug_era`, `device_exposure`, `death`,
   `payer_plan_period` y `cost` no se materializaron porque no intervienen en
   las consultas exigidas y presentaron incompatibilidades específicas con
   DuckDB.

## 10. Base de referencia

La comparación con Eunomia se incorporará mediante `06_comparar_eunomia.R`.
"""
    Path("lab12/reporte_calidad.md").write_text(reporte, encoding="utf-8")


def crear_diagrama() -> None:
    diagrama = """# Diagrama entidad-relación

```mermaid
erDiagram
    PERSON {
        bigint person_id PK
        integer gender_concept_id FK
        integer year_of_birth
    }
    OBSERVATION_PERIOD {
        bigint observation_period_id PK
        bigint person_id FK
        date observation_period_start_date
        date observation_period_end_date
    }
    VISIT_OCCURRENCE {
        bigint visit_occurrence_id PK
        bigint person_id FK
        integer visit_concept_id FK
    }
    CONDITION_OCCURRENCE {
        bigint condition_occurrence_id PK
        bigint person_id FK
        integer condition_concept_id FK
        bigint visit_occurrence_id FK
    }
    DRUG_EXPOSURE {
        bigint drug_exposure_id PK
        bigint person_id FK
        integer drug_concept_id FK
        bigint visit_occurrence_id FK
    }
    MEASUREMENT {
        bigint measurement_id PK
        bigint person_id FK
        integer measurement_concept_id FK
        bigint visit_occurrence_id FK
    }
    CONCEPT {
        integer concept_id PK
        string concept_name
        string domain_id
        string vocabulary_id
    }
    CONCEPT_RELATIONSHIP {
        integer concept_id_1 FK
        integer concept_id_2 FK
        string relationship_id
    }
    CONCEPT_ANCESTOR {
        integer ancestor_concept_id FK
        integer descendant_concept_id FK
    }
    PERSON ||--o{ OBSERVATION_PERIOD : tiene
    PERSON ||--o{ VISIT_OCCURRENCE : realiza
    PERSON ||--o{ CONDITION_OCCURRENCE : presenta
    PERSON ||--o{ DRUG_EXPOSURE : recibe
    PERSON ||--o{ MEASUREMENT : tiene
    VISIT_OCCURRENCE ||--o{ CONDITION_OCCURRENCE : contiene
    VISIT_OCCURRENCE ||--o{ DRUG_EXPOSURE : contiene
    VISIT_OCCURRENCE ||--o{ MEASUREMENT : contiene
    CONCEPT ||--o{ CONDITION_OCCURRENCE : define
    CONCEPT ||--o{ DRUG_EXPOSURE : define
    CONCEPT ||--o{ MEASUREMENT : define
    CONCEPT ||--o{ CONCEPT_RELATIONSHIP : relaciona
    CONCEPT ||--o{ CONCEPT_ANCESTOR : jerarquiza
```

## Comparación con OMOP CDM 5.4

1. El esquema conserva las columnas de OMOP 5.4, pero sólo se poblaron las
   tablas y dominios necesarios. Es una simplificación legítima del ETL.
2. Los `*_datetime` afectados quedaron nulos porque Synthea aporta fechas sin
   hora verificable y DuckDB presentó una incompatibilidad de conversión. Los
   `*_date` permanecen disponibles y no se inventaron horas inexistentes.
"""
    Path("lab12/diagrama_er.md").write_text(diagrama, encoding="utf-8")


def main() -> None:
    if not BASE.exists():
        raise SystemExit(f"No existe la base OMOP: {BASE}")

    SALIDA.mkdir(parents=True, exist_ok=True)
    conexion = duckdb.connect(str(BASE), read_only=True)
    resultados = {}

    try:
        for nombre, sql in CONSULTAS.items():
            datos = consultar(conexion, sql)
            resultados[nombre] = datos
            guardar(f"{nombre}.csv", datos)
    finally:
        conexion.close()

    secciones_sql = []
    for nombre, sql in CONSULTAS.items():
        secciones_sql.append(
            "-- ============================================================\n"
            f"-- {nombre}\n"
            "-- ============================================================\n"
            f"{sql.strip()};\n"
        )
    Path("lab12/consultas_omop.sql").write_text(
        "\n\n".join(secciones_sql) + "\n", encoding="utf-8"
    )
    crear_reporte(resultados)
    crear_diagrama()

    print("\nENTREGABLES GENERADOS:")
    print(" - lab12/consultas_omop.sql")
    print(" - lab12/reporte_calidad.md")
    print(" - lab12/diagrama_er.md")
    print(" - lab12/evidencias/analisis/*.csv")


if __name__ == "__main__":
    main()

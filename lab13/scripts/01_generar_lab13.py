#!/usr/bin/env python3
"""Genera los entregables del Laboratorio 13 a partir del CDM del Lab 12."""

from __future__ import annotations

import json
import uuid
import math
from pathlib import Path
from textwrap import dedent

import duckdb
import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path.cwd()
LAB = ROOT / "lab13"
DB = ROOT / "lab12/data/omop/synthea_omop_cdm54.duckdb"
ANALYSIS = LAB / "evidencias/analisis"
FIGURES = LAB / "figuras"
NOTEBOOKS = LAB / "notebooks"
SQL_PATH = LAB / "farmacoepi.sql"
REPORT_PATH = LAB / "reporte_calidad.md"
README_PATH = LAB / "README.md"
NOTEBOOK_PATH = NOTEBOOKS / "analisis_farmacoepi.ipynb"

INGREDIENT_ID = 1308216
INGREDIENT_NAME = "lisinopril"
WEIGHT_ID = 3025315
GLUCOSE_ID = 3000483
SBP_ID = 3004249
EGFR_ID = 46236952
LB_TO_KG = 0.45359237

SOURCE_PDC = "https://www.pqa.org/measures/measures-resources/"
SOURCE_PDC_METHOD = "https://pmc.ncbi.nlm.nih.gov/articles/PMC7886011/"
SOURCE_NIST = "https://nvlpubs.nist.gov/nistpubs/hb/2026/NIST.HB.44-2026.pdf"
SOURCE_PLAUSIBILITY = "https://doi.org/10.1155/2016/4364761"
SOURCE_OMOP = "https://ohdsi.github.io/CommonDataModel/cdm54.html"


def ensure_directories() -> None:
    for path in (ANALYSIS, FIGURES, NOTEBOOKS):
        path.mkdir(parents=True, exist_ok=True)


def md_table(frame: pd.DataFrame, max_rows: int | None = None) -> str:
    """Convierte un DataFrame pequeño en tabla Markdown sin depender de tabulate."""
    if max_rows is not None:
        frame = frame.head(max_rows)
    if frame.empty:
        return "_Sin registros._"
    clean = frame.copy()
    clean = clean.where(pd.notna(clean), "NA")
    columns = [str(column) for column in clean.columns]
    rows = []
    for values in clean.itertuples(index=False, name=None):
        rows.append([str(value).replace("|", "\\|") for value in values])
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join(["---"] * len(columns)) + " |"
    body = ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join([header, separator, *body])


def save_csv(frame: pd.DataFrame, name: str) -> Path:
    path = ANALYSIS / name
    frame.to_csv(path, index=False)
    print(f"OK: {path} ({len(frame)} filas)")
    return path


SQL = {
    "01_tipo_exposicion": dedent(
        """
        SELECT
            de.drug_type_concept_id,
            c.concept_name AS drug_type_concept_name,
            COUNT(*) AS exposiciones,
            COUNT(DISTINCT de.person_id) AS personas,
            ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 4) AS porcentaje
        FROM cdm.drug_exposure de
        LEFT JOIN cdm.concept c
          ON c.concept_id = de.drug_type_concept_id
        GROUP BY de.drug_type_concept_id, c.concept_name
        ORDER BY exposiciones DESC;
        """
    ).strip(),
    "02_top20_ingredientes": dedent(
        """
        SELECT
            ca.ancestor_concept_id AS ingredient_concept_id,
            ingredient.concept_name AS ingredient_name,
            COUNT(*) AS exposiciones,
            COUNT(DISTINCT de.person_id) AS personas,
            COUNT(DISTINCT de.drug_concept_id) AS productos_descendientes
        FROM cdm.drug_exposure de
        INNER JOIN cdm.concept_ancestor ca
          ON ca.descendant_concept_id = de.drug_concept_id
        INNER JOIN cdm.concept ingredient
          ON ingredient.concept_id = ca.ancestor_concept_id
        WHERE ingredient.domain_id = 'Drug'
          AND ingredient.concept_class_id = 'Ingredient'
          AND ingredient.standard_concept = 'S'
        GROUP BY ca.ancestor_concept_id, ingredient.concept_name
        ORDER BY personas DESC, exposiciones DESC
        LIMIT 20;
        """
    ).strip(),
    "02_days_supply": dedent(
        """
        SELECT
            COUNT(*) AS exposiciones,
            COUNT(days_supply) AS days_supply_no_nulos,
            MIN(days_supply) AS minimo,
            QUANTILE_CONT(days_supply, 0.25) AS q1,
            MEDIAN(days_supply) AS mediana,
            QUANTILE_CONT(days_supply, 0.75) AS q3,
            MAX(days_supply) AS maximo,
            COUNT(*) FILTER (WHERE days_supply <= 0) AS no_positivos,
            COUNT(*) FILTER (WHERE days_supply > 365) AS mayores_365
        FROM cdm.drug_exposure;
        """
    ).strip(),
    "02_calidad_fechas": dedent(
        """
        SELECT
            COUNT(*) AS exposiciones,
            COUNT(DISTINCT person_id) AS personas,
            ROUND(100.0 * COUNT(*) FILTER (
                WHERE drug_exposure_end_date IS NULL
            ) / COUNT(*), 4) AS porcentaje_end_date_nulo,
            ROUND(100.0 * COUNT(*) FILTER (
                WHERE drug_exposure_end_date = drug_exposure_start_date
            ) / COUNT(*), 4) AS porcentaje_misma_fecha,
            ROUND(100.0 * COUNT(*) FILTER (
                WHERE drug_concept_id = 0
            ) / COUNT(*), 4) AS porcentaje_concept_id_cero
        FROM cdm.drug_exposure;
        """
    ).strip(),
    "03_ingrediente_directo_jerarquia": dedent(
        f"""
        WITH directo AS (
            SELECT COUNT(*) AS exposiciones,
                   COUNT(DISTINCT person_id) AS personas
            FROM cdm.drug_exposure
            WHERE drug_concept_id = {INGREDIENT_ID}
        ), descendientes AS (
            SELECT COUNT(*) AS exposiciones,
                   COUNT(DISTINCT de.person_id) AS personas,
                   COUNT(DISTINCT de.drug_concept_id) AS productos
            FROM cdm.drug_exposure de
            INNER JOIN cdm.concept_ancestor ca
              ON ca.descendant_concept_id = de.drug_concept_id
            WHERE ca.ancestor_concept_id = {INGREDIENT_ID}
        )
        SELECT {INGREDIENT_ID} AS ingredient_concept_id,
               '{INGREDIENT_NAME}' AS ingredient_name,
               d.exposiciones AS exposiciones_directas,
               d.personas AS personas_directas,
               h.exposiciones AS exposiciones_jerarquia,
               h.personas AS personas_jerarquia,
               h.productos AS productos_descendientes,
               h.personas - d.personas AS diferencia_personas
        FROM directo d CROSS JOIN descendientes h;
        """
    ).strip(),
    "04_crear_drug_era": dedent(
        f"""
        CREATE SCHEMA IF NOT EXISTS results;
        CREATE OR REPLACE TABLE results.drug_era_lisinopril AS
        WITH exposiciones AS (
            SELECT
                de.person_id,
                de.drug_exposure_id,
                de.drug_exposure_start_date AS start_date,
                CASE
                    WHEN de.days_supply BETWEEN 1 AND 365
                      THEN de.drug_exposure_start_date + (de.days_supply - 1)
                    WHEN de.drug_exposure_end_date >= de.drug_exposure_start_date
                     AND DATE_DIFF('day', de.drug_exposure_start_date,
                                         de.drug_exposure_end_date) <= 364
                      THEN de.drug_exposure_end_date
                    ELSE de.drug_exposure_start_date
                END AS end_date
            FROM cdm.drug_exposure de
            INNER JOIN cdm.concept_ancestor ca
              ON ca.descendant_concept_id = de.drug_concept_id
            WHERE ca.ancestor_concept_id = {INGREDIENT_ID}
        ), maximo_previo AS (
            SELECT *,
                MAX(end_date) OVER (
                    PARTITION BY person_id
                    ORDER BY start_date, end_date, drug_exposure_id
                    ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
                ) AS previous_max_end
            FROM exposiciones
        ), comienzos AS (
            SELECT *,
                CASE
                    WHEN previous_max_end IS NULL
                      OR start_date > previous_max_end + 30
                    THEN 1 ELSE 0
                END AS new_era
            FROM maximo_previo
        ), grupos AS (
            SELECT *,
                SUM(new_era) OVER (
                    PARTITION BY person_id
                    ORDER BY start_date, end_date, drug_exposure_id
                    ROWS UNBOUNDED PRECEDING
                ) AS era_group
            FROM comienzos
        )
        SELECT
            ROW_NUMBER() OVER (
                ORDER BY person_id, MIN(start_date)
            ) AS drug_era_id,
            person_id,
            {INGREDIENT_ID} AS ingredient_concept_id,
            '{INGREDIENT_NAME}' AS ingredient_name,
            MIN(start_date) AS drug_era_start_date,
            MAX(end_date) AS drug_era_end_date,
            COUNT(*) AS exposure_count,
            DATE_DIFF('day', MIN(start_date), MAX(end_date)) + 1 AS era_days,
            30 AS permissible_gap_days
        FROM grupos
        GROUP BY person_id, era_group;
        """
    ).strip(),
    "04_resumen_drug_era": dedent(
        """
        SELECT
            COUNT(*) AS eras_manuales,
            COUNT(DISTINCT person_id) AS personas,
            MIN(drug_era_start_date) AS fecha_minima,
            MAX(drug_era_end_date) AS fecha_maxima,
            MEDIAN(era_days) AS mediana_dias,
            MAX(era_days) AS maximo_dias,
            (SELECT COUNT(*) FROM cdm.drug_era) AS eras_cdm
        FROM results.drug_era_lisinopril;
        """
    ).strip(),
    "05_crear_pdc": dedent(
        f"""
        CREATE OR REPLACE TABLE results.pdc_lisinopril AS
        WITH exposiciones AS (
            SELECT
                de.person_id,
                de.drug_exposure_id,
                de.drug_exposure_start_date AS start_date,
                CASE
                    WHEN de.days_supply BETWEEN 1 AND 365
                      THEN de.drug_exposure_start_date + (de.days_supply - 1)
                    WHEN de.drug_exposure_end_date >= de.drug_exposure_start_date
                     AND DATE_DIFF('day', de.drug_exposure_start_date,
                                         de.drug_exposure_end_date) <= 364
                      THEN de.drug_exposure_end_date
                    ELSE de.drug_exposure_start_date
                END AS end_date
            FROM cdm.drug_exposure de
            INNER JOIN cdm.concept_ancestor ca
              ON ca.descendant_concept_id = de.drug_concept_id
            WHERE ca.ancestor_concept_id = {INGREDIENT_ID}
        ), indice AS (
            SELECT person_id, MIN(start_date) AS index_date
            FROM exposiciones
            GROUP BY person_id
        ), elegibles AS (
            SELECT i.person_id, i.index_date, i.index_date + 364 AS followup_end
            FROM indice i
            WHERE EXISTS (
                SELECT 1
                FROM cdm.observation_period op
                WHERE op.person_id = i.person_id
                  AND op.observation_period_start_date <= i.index_date
                  AND op.observation_period_end_date >= i.index_date + 364
            )
        ), recortadas AS (
            SELECT
                e.person_id,
                e.index_date,
                e.followup_end,
                x.drug_exposure_id,
                GREATEST(x.start_date, e.index_date) AS covered_start,
                LEAST(x.end_date, e.followup_end) AS covered_end
            FROM elegibles e
            INNER JOIN exposiciones x ON x.person_id = e.person_id
            WHERE x.start_date <= e.followup_end
              AND x.end_date >= e.index_date
        ), previas AS (
            SELECT *,
                MAX(covered_end) OVER (
                    PARTITION BY person_id
                    ORDER BY covered_start, covered_end, drug_exposure_id
                    ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
                ) AS previous_max_end
            FROM recortadas
        ), comienzos AS (
            SELECT *,
                CASE
                    WHEN previous_max_end IS NULL
                      OR covered_start > previous_max_end + 1
                    THEN 1 ELSE 0
                END AS new_segment
            FROM previas
        ), grupos AS (
            SELECT *,
                SUM(new_segment) OVER (
                    PARTITION BY person_id
                    ORDER BY covered_start, covered_end, drug_exposure_id
                    ROWS UNBOUNDED PRECEDING
                ) AS segment_group
            FROM comienzos
        ), segmentos AS (
            SELECT person_id, index_date, followup_end, segment_group,
                   MIN(covered_start) AS segment_start,
                   MAX(covered_end) AS segment_end
            FROM grupos
            GROUP BY person_id, index_date, followup_end, segment_group
        ), cubiertos AS (
            SELECT person_id, index_date, followup_end,
                   LEAST(365, SUM(DATE_DIFF('day', segment_start, segment_end) + 1))
                       AS covered_days
            FROM segmentos
            GROUP BY person_id, index_date, followup_end
        )
        SELECT
            person_id,
            index_date,
            followup_end,
            covered_days,
            365 AS denominator_days,
            ROUND(covered_days / 365.0, 6) AS pdc,
            covered_days / 365.0 >= 0.8 AS adherent_pdc_080
        FROM cubiertos;
        """
    ).strip(),
    "05_resumen_pdc": dedent(
        """
        SELECT
            COUNT(*) AS pacientes_elegibles,
            MIN(pdc) AS minimo,
            QUANTILE_CONT(pdc, 0.25) AS q1,
            MEDIAN(pdc) AS mediana,
            QUANTILE_CONT(pdc, 0.75) AS q3,
            MAX(pdc) AS maximo,
            COUNT(*) FILTER (WHERE adherent_pdc_080) AS pacientes_pdc_080,
            ROUND(100.0 * COUNT(*) FILTER (WHERE adherent_pdc_080) / COUNT(*), 4)
                AS porcentaje_pdc_080
        FROM results.pdc_lisinopril;
        """
    ).strip(),
    "06_top15_analitos": dedent(
        """
        SELECT
            m.measurement_concept_id,
            c.concept_name AS measurement_concept_name,
            COUNT(*) AS mediciones,
            COUNT(DISTINCT m.person_id) AS personas,
            COUNT(DISTINCT m.unit_concept_id) AS unidades
        FROM cdm.measurement m
        LEFT JOIN cdm.concept c
          ON c.concept_id = m.measurement_concept_id
        GROUP BY m.measurement_concept_id, c.concept_name
        ORDER BY mediciones DESC, personas DESC
        LIMIT 15;
        """
    ).strip(),
    "06_unidades_egfr": dedent(
        f"""
        SELECT
            m.measurement_concept_id,
            mc.concept_name AS measurement_concept_name,
            m.unit_concept_id,
            COALESCE(uc.concept_name, 'No matching concept') AS unit_concept_name,
            m.unit_source_value,
            COUNT(*) AS mediciones,
            COUNT(DISTINCT m.person_id) AS personas,
            MIN(m.value_as_number) AS minimo,
            MEDIAN(m.value_as_number) AS mediana,
            MAX(m.value_as_number) AS maximo
        FROM cdm.measurement m
        LEFT JOIN cdm.concept mc
          ON mc.concept_id = m.measurement_concept_id
        LEFT JOIN cdm.concept uc
          ON uc.concept_id = m.unit_concept_id
        WHERE m.measurement_concept_id = {EGFR_ID}
        GROUP BY m.measurement_concept_id, mc.concept_name,
                 m.unit_concept_id, uc.concept_name, m.unit_source_value
        ORDER BY mediciones DESC;
        """
    ).strip(),
    "06_calidad_measurement": dedent(
        """
        SELECT
            COUNT(*) AS mediciones,
            COUNT(DISTINCT person_id) AS personas,
            ROUND(100.0 * COUNT(*) FILTER (
                WHERE value_as_number IS NULL
            ) / COUNT(*), 4) AS porcentaje_value_number_nulo,
            ROUND(100.0 * COUNT(*) FILTER (
                WHERE operator_concept_id IS NOT NULL
                  AND operator_concept_id <> 0
            ) / COUNT(*), 4) AS porcentaje_operador_no_cero,
            ROUND(100.0 * COUNT(*) FILTER (
                WHERE measurement_concept_id = 0
            ) / COUNT(*), 4) AS porcentaje_concept_id_cero
        FROM cdm.measurement;
        """
    ).strip(),
    "07_normalizar_peso": dedent(
        f"""
        CREATE OR REPLACE TABLE results.weight_unit_normalized AS
        SELECT
            measurement_id,
            person_id,
            measurement_date,
            value_as_number AS original_value_kg,
            'kg' AS original_unit,
            CASE WHEN measurement_id % 5 = 0
                 THEN value_as_number / {LB_TO_KG}
                 ELSE value_as_number END AS simulated_value,
            CASE WHEN measurement_id % 5 = 0 THEN 'lb' ELSE 'kg' END
                AS simulated_unit,
            CASE WHEN measurement_id % 5 = 0
                 THEN (value_as_number / {LB_TO_KG}) * {LB_TO_KG}
                 ELSE value_as_number END AS normalized_value_kg,
            'kg' AS canonical_unit,
            measurement_id % 5 = 0 AS converted_from_lb,
            {LB_TO_KG} AS lb_to_kg_factor
        FROM cdm.measurement
        WHERE measurement_concept_id = {WEIGHT_ID}
          AND value_as_number IS NOT NULL;
        """
    ).strip(),
    "07_resumen_normalizacion": dedent(
        """
        SELECT
            simulated_unit AS unidad_antes,
            COUNT(*) AS filas,
            MIN(simulated_value) AS minimo_antes,
            MEDIAN(simulated_value) AS mediana_antes,
            MAX(simulated_value) AS maximo_antes,
            'kg' AS unidad_despues,
            MIN(normalized_value_kg) AS minimo_despues,
            MEDIAN(normalized_value_kg) AS mediana_despues,
            MAX(normalized_value_kg) AS maximo_despues
        FROM results.weight_unit_normalized
        GROUP BY simulated_unit
        ORDER BY simulated_unit;
        """
    ).strip(),
    "08_valores_implausibles": dedent(
        f"""
        WITH limites AS (
            SELECT {SBP_ID} AS concept_id, 'Systolic blood pressure' AS concept_name,
                   40.0 AS lower_limit, 250.0 AS upper_limit, 'mmHg' AS unit
            UNION ALL
            SELECT {GLUCOSE_ID}, 'Glucose [Mass/volume] in Blood',
                   10.0, 500.0, 'mg/dL'
            UNION ALL
            SELECT {WEIGHT_ID}, 'Body weight',
                   60.0 * {LB_TO_KG}, 700.0 * {LB_TO_KG}, 'kg'
        ), adultos AS (
            SELECT
                m.measurement_id,
                m.person_id,
                m.measurement_concept_id AS concept_id,
                m.measurement_date,
                m.value_as_number,
                DATE_DIFF(
                    'year',
                    MAKE_DATE(
                        p.year_of_birth,
                        COALESCE(p.month_of_birth, 7),
                        COALESCE(p.day_of_birth, 1)
                    ),
                    m.measurement_date
                ) AS age_years
            FROM cdm.measurement m
            INNER JOIN cdm.person p ON p.person_id = m.person_id
            WHERE m.measurement_concept_id IN ({SBP_ID}, {GLUCOSE_ID}, {WEIGHT_ID})
              AND m.value_as_number IS NOT NULL
        ), evaluados AS (
            SELECT a.*, l.concept_name, l.lower_limit, l.upper_limit, l.unit,
                   a.value_as_number < l.lower_limit
                    OR a.value_as_number > l.upper_limit AS implausible
            FROM adultos a
            INNER JOIN limites l ON l.concept_id = a.concept_id
            WHERE a.age_years >= 18
        ), frecuencias AS (
            SELECT concept_id, value_as_number, COUNT(*) AS repetitions
            FROM evaluados
            GROUP BY concept_id, value_as_number
        )
        SELECT
            e.concept_id,
            e.concept_name,
            e.unit,
            e.lower_limit,
            e.upper_limit,
            COUNT(*) AS adult_measurements,
            COUNT(*) FILTER (WHERE e.implausible) AS outside_range,
            ROUND(100.0 * COUNT(*) FILTER (WHERE e.implausible) / COUNT(*), 4)
                AS outside_percentage,
            COUNT(*) FILTER (
                WHERE e.implausible AND f.repetitions >= 2
            ) AS repeated_implausible_rows,
            COUNT(DISTINCT e.value_as_number) FILTER (
                WHERE e.implausible AND f.repetitions >= 2
            ) AS repeated_implausible_values
        FROM evaluados e
        INNER JOIN frecuencias f
          ON f.concept_id = e.concept_id
         AND f.value_as_number = e.value_as_number
        GROUP BY e.concept_id, e.concept_name, e.unit,
                 e.lower_limit, e.upper_limit
        ORDER BY e.concept_id;
        """
    ).strip(),
    "08_detalle_implausibles": dedent(
        f"""
        WITH limites AS (
            SELECT {SBP_ID} AS concept_id, 40.0 AS lower_limit, 250.0 AS upper_limit
            UNION ALL SELECT {GLUCOSE_ID}, 10.0, 500.0
            UNION ALL SELECT {WEIGHT_ID}, 60.0 * {LB_TO_KG}, 700.0 * {LB_TO_KG}
        ), evaluados AS (
            SELECT m.measurement_id, m.person_id, m.measurement_concept_id AS concept_id,
                   m.measurement_date, m.value_as_number, l.lower_limit, l.upper_limit
            FROM cdm.measurement m
            INNER JOIN cdm.person p ON p.person_id = m.person_id
            INNER JOIN limites l ON l.concept_id = m.measurement_concept_id
            WHERE m.value_as_number IS NOT NULL
              AND DATE_DIFF(
                    'year',
                    MAKE_DATE(p.year_of_birth, COALESCE(p.month_of_birth, 7),
                              COALESCE(p.day_of_birth, 1)),
                    m.measurement_date
                  ) >= 18
        )
        SELECT *,
               CASE WHEN value_as_number < lower_limit THEN 'below_range'
                    WHEN value_as_number > upper_limit THEN 'above_range' END AS reason
        FROM evaluados
        WHERE value_as_number < lower_limit OR value_as_number > upper_limit
        ORDER BY concept_id, value_as_number;
        """
    ).strip(),
    "09_measurement_observation": dedent(
        f"""
        SELECT 'Body weight' AS clinical_fact,
               'MEASUREMENT' AS omop_table,
               {WEIGHT_ID} AS concept_id,
               c.concept_name,
               COUNT(*) AS events,
               COUNT(DISTINCT m.person_id) AS persons,
               'Concordant: quantitative standardized measurement' AS themis_assessment
        FROM cdm.measurement m
        INNER JOIN cdm.concept c ON c.concept_id = m.measurement_concept_id
        WHERE m.measurement_concept_id = {WEIGHT_ID}
        GROUP BY c.concept_name
        UNION ALL
        SELECT 'Tobacco smoking status', 'OBSERVATION', 43054909,
               c.concept_name, COUNT(*), COUNT(DISTINCT o.person_id),
               'Concordant: social and lifestyle fact'
        FROM cdm.observation o
        INNER JOIN cdm.concept c ON c.concept_id = o.observation_concept_id
        WHERE o.observation_concept_id = 43054909
        GROUP BY c.concept_name
        UNION ALL
        SELECT 'Systolic blood pressure', 'MEASUREMENT', {SBP_ID},
               c.concept_name, COUNT(*), COUNT(DISTINCT m.person_id),
               'Concordant: quantitative standardized measurement'
        FROM cdm.measurement m
        INNER JOIN cdm.concept c ON c.concept_id = m.measurement_concept_id
        WHERE m.measurement_concept_id = {SBP_ID}
        GROUP BY c.concept_name;
        """
    ).strip(),
    "10_glucosa_indice": dedent(
        f"""
        WITH indice AS (
            SELECT person_id, MIN(condition_start_date) AS index_date
            FROM cdm.condition_occurrence
            GROUP BY person_id
        ), candidatos AS (
            SELECT
                i.person_id,
                i.index_date,
                m.measurement_id,
                m.measurement_date,
                m.value_as_number,
                m.unit_concept_id,
                uc.concept_name AS unit_concept_name,
                ABS(DATE_DIFF('day', i.index_date, m.measurement_date)) AS distance_days,
                ROW_NUMBER() OVER (
                    PARTITION BY i.person_id
                    ORDER BY
                        ABS(DATE_DIFF('day', i.index_date, m.measurement_date)),
                        CASE WHEN m.measurement_date <= i.index_date THEN 0 ELSE 1 END,
                        m.measurement_date DESC,
                        m.measurement_id
                ) AS rn
            FROM indice i
            INNER JOIN cdm.measurement m
              ON m.person_id = i.person_id
             AND m.measurement_concept_id = {GLUCOSE_ID}
             AND m.value_as_number IS NOT NULL
             AND m.measurement_date BETWEEN i.index_date - 90 AND i.index_date + 90
            LEFT JOIN cdm.concept uc ON uc.concept_id = m.unit_concept_id
        )
        SELECT
            i.person_id,
            i.index_date,
            c.measurement_id,
            c.measurement_date,
            c.value_as_number,
            c.unit_concept_id,
            c.unit_concept_name,
            c.distance_days,
            c.measurement_id IS NOT NULL AS has_baseline_glucose
        FROM indice i
        LEFT JOIN candidatos c
          ON c.person_id = i.person_id AND c.rn = 1
        ORDER BY i.person_id;
        """
    ).strip(),
}


def write_sql_file() -> None:
    titles = {
        "01": "Actividad 1. Tipo de exposición",
        "02": "Actividad 2. Caracterización de DRUG_EXPOSURE",
        "03": "Actividad 3. Ingrediente exacto frente a jerarquía",
        "04": "Actividad 4. Construcción manual de DRUG_ERA",
        "05": "Actividad 5. PDC a un año",
        "06": "Actividad 6. Caracterización de MEASUREMENT",
        "07": "Actividad 7. Normalización de unidades",
        "08": "Actividad 8. Valores implausibles",
        "09": "Actividad 9. MEASUREMENT frente a OBSERVATION",
        "10": "Actividad 10. Último valor alrededor del índice",
    }
    parts = [
        "-- Laboratorio 13: exposición a fármacos y laboratorios",
        "-- Base: OMOP CDM v5.4 en DuckDB",
        "-- Los conteos epidemiológicos usan COUNT(DISTINCT person_id).",
        "",
    ]
    last_prefix = None
    for name, query in SQL.items():
        prefix = name[:2]
        if prefix != last_prefix:
            parts.extend(["", "-- " + "=" * 72, f"-- {titles[prefix]}", "-- " + "=" * 72])
            last_prefix = prefix
        parts.extend(["", f"-- Consulta: {name}", query.rstrip(";") + ";"])
    SQL_PATH.write_text("\n".join(parts).rstrip() + "\n", encoding="utf-8")
    print(f"OK: {SQL_PATH}")


def execute_analysis(con: duckdb.DuckDBPyConnection) -> dict[str, pd.DataFrame]:
    results: dict[str, pd.DataFrame] = {}
    creation = {
        "04_crear_drug_era",
        "05_crear_pdc",
        "07_normalizar_peso",
    }
    exports = {
        "01_tipo_exposicion": "tipo_exposicion.csv",
        "02_top20_ingredientes": "top20_ingredientes.csv",
        "02_days_supply": "days_supply_resumen.csv",
        "02_calidad_fechas": "drug_exposure_calidad.csv",
        "03_ingrediente_directo_jerarquia": "ingrediente_directo_jerarquia.csv",
        "04_resumen_drug_era": "drug_era_resumen.csv",
        "05_resumen_pdc": "pdc_resumen.csv",
        "06_top15_analitos": "top15_analitos.csv",
        "06_unidades_egfr": "unidades_egfr.csv",
        "06_calidad_measurement": "measurement_calidad.csv",
        "07_resumen_normalizacion": "normalizacion_peso_resumen.csv",
        "08_valores_implausibles": "valores_implausibles_resumen.csv",
        "08_detalle_implausibles": "valores_implausibles_detalle.csv",
        "09_measurement_observation": "measurement_vs_observation.csv",
        "10_glucosa_indice": "glucosa_indice_personas.csv",
    }
    order = list(SQL)
    for name in order:
        print(f"Ejecutando: {name}")
        if name in creation:
            con.execute(SQL[name])
            continue
        frame = con.execute(SQL[name]).df()
        results[name] = frame
        if name in exports:
            save_csv(frame, exports[name])

    eras = con.execute(
        "SELECT * FROM results.drug_era_lisinopril ORDER BY person_id, drug_era_start_date"
    ).df()
    save_csv(eras, "drug_era_lisinopril.csv")

    pdc = con.execute("SELECT * FROM results.pdc_lisinopril ORDER BY person_id").df()
    save_csv(pdc, "pdc_lisinopril.csv")
    results["pdc_personas"] = pdc

    weight_sample = con.execute(
        """
        SELECT *
        FROM results.weight_unit_normalized
        USING SAMPLE 200 ROWS
        ORDER BY measurement_id
        """
    ).df()
    save_csv(weight_sample, "normalizacion_peso_muestra.csv")

    baseline = results["10_glucosa_indice"]
    baseline_summary = pd.DataFrame(
        {
            "personas_con_indice": [len(baseline)],
            "personas_con_glucosa_basal": [int(baseline["has_baseline_glucose"].sum())],
            "personas_sin_glucosa_basal": [int((~baseline["has_baseline_glucose"]).sum())],
            "porcentaje_con_glucosa_basal": [
                round(100.0 * baseline["has_baseline_glucose"].mean(), 4)
            ],
        }
    )
    results["10_glucosa_resumen"] = baseline_summary
    save_csv(baseline_summary, "glucosa_indice_resumen.csv")

    criteria = pd.DataFrame(
        [
            {
                "concept_id": SBP_ID,
                "analito": "Systolic blood pressure",
                "poblacion": "Adultos (>=18 años)",
                "limite_inferior": 40,
                "limite_superior": 250,
                "unidad": "mmHg",
                "fuente": SOURCE_PLAUSIBILITY,
            },
            {
                "concept_id": GLUCOSE_ID,
                "analito": "Glucose [Mass/volume] in Blood",
                "poblacion": "Adultos (>=18 años)",
                "limite_inferior": 10,
                "limite_superior": 500,
                "unidad": "mg/dL",
                "fuente": SOURCE_PLAUSIBILITY,
            },
            {
                "concept_id": WEIGHT_ID,
                "analito": "Body weight",
                "poblacion": "Adultos (>=18 años)",
                "limite_inferior": round(60 * LB_TO_KG, 6),
                "limite_superior": round(700 * LB_TO_KG, 6),
                "unidad": "kg",
                "fuente": SOURCE_PLAUSIBILITY,
            },
        ]
    )
    results["08_criterios"] = criteria
    save_csv(criteria, "criterios_plausibilidad.csv")

    return results


def create_figures(con: duckdb.DuckDBPyConnection, results: dict[str, pd.DataFrame]) -> None:
    plt.style.use("seaborn-v0_8-whitegrid")

    days = con.execute(
        """
        SELECT days_supply
        FROM cdm.drug_exposure
        WHERE days_supply BETWEEN 1 AND 365
        """
    ).df()["days_supply"]
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(days, bins=40, color="#3366A5", edgecolor="white")
    ax.set(title="Distribución de days_supply (1–365 días)", xlabel="Días", ylabel="Exposiciones")
    fig.tight_layout()
    fig.savefig(FIGURES / "01_days_supply.png", dpi=180)
    plt.close(fig)

    pdc = results["pdc_personas"]
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(pdc["pdc"], bins=20, range=(0, 1), color="#3B8C6E", edgecolor="white")
    ax.axvline(0.8, color="#B43C3C", linestyle="--", label="PDC = 0.8")
    ax.set(title="PDC de lisinopril durante 365 días", xlabel="PDC", ylabel="Pacientes")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(FIGURES / "02_pdc_lisinopril.png", dpi=180)
    plt.close(fig)

    weight = con.execute(
        """
        SELECT simulated_value, simulated_unit, normalized_value_kg
        FROM results.weight_unit_normalized
        """
    ).df()
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    for unit, color in (("kg", "#3366A5"), ("lb", "#D68B2C")):
        subset = weight.loc[weight["simulated_unit"] == unit, "simulated_value"]
        axes[0].hist(subset, bins=40, alpha=0.65, label=unit, color=color)
    axes[0].set(title="Antes: unidades simuladas", xlabel="Valor registrado", ylabel="Filas")
    axes[0].legend(frameon=False)
    axes[1].hist(weight["normalized_value_kg"], bins=40, color="#3B8C6E")
    axes[1].set(title="Después: unidad canónica", xlabel="Peso (kg)", ylabel="Filas")
    fig.tight_layout()
    fig.savefig(FIGURES / "03_normalizacion_peso.png", dpi=180)
    plt.close(fig)

    baseline = results["10_glucosa_indice"]
    counts = [
        int(baseline["has_baseline_glucose"].sum()),
        int((~baseline["has_baseline_glucose"]).sum()),
    ]
    fig, ax = plt.subplots(figsize=(6, 4.5))
    ax.bar(["Con valor", "Sin valor"], counts, color=["#3B8C6E", "#B8B8B8"])
    ax.set(title="Glucosa dentro de ±90 días del índice", ylabel="Pacientes")
    for index, value in enumerate(counts):
        ax.text(index, value, str(value), ha="center", va="bottom")
    fig.tight_layout()
    fig.savefig(FIGURES / "04_glucosa_indice.png", dpi=180)
    plt.close(fig)

    print(f"OK: {FIGURES} (4 figuras)")


def create_report(results: dict[str, pd.DataFrame]) -> None:
    exposure = results["01_tipo_exposicion"]
    drug_quality = results["02_calidad_fechas"].iloc[0]
    direct = results["03_ingrediente_directo_jerarquia"].iloc[0]
    era = results["04_resumen_drug_era"].iloc[0]
    pdc = results["05_resumen_pdc"].iloc[0]
    measurement_quality = results["06_calidad_measurement"].iloc[0]
    baseline = results["10_glucosa_resumen"].iloc[0]
    converted = int(
        results["07_resumen_normalizacion"].loc[
            results["07_resumen_normalizacion"]["unidad_antes"] == "lb", "filas"
        ].sum()
    )

    report = f"""# Reporte de calidad — Laboratorio 13

## 1. Tipo de exposición

{md_table(exposure)}

La base contiene **prescripciones registradas en el EHR**. Una prescripción indica
intención de tratamiento, pero no demuestra dispensación, disponibilidad física ni
consumo. Por ello, las métricas de cobertura describen cobertura prescrita estimada y
no adherencia observada.

## 2. Calidad de `DRUG_EXPOSURE`

{md_table(results['02_calidad_fechas'])}

{md_table(results['02_days_supply'])}

El porcentaje de fechas finales nulas fue **{drug_quality['porcentaje_end_date_nulo']}%**
y **{drug_quality['porcentaje_misma_fecha']}%** de las exposiciones terminaron el mismo
día que comenzaron. Además, `days_supply` contiene valores no positivos y valores
superiores a un año. La base permite estudiar exposición prescrita si se aplican reglas
explícitas de limpieza, pero no permite inferir directamente consumo o dispensación.

### Ingredientes más frecuentes

{md_table(results['02_top20_ingredientes'], 20)}

## 3. Ingrediente exacto frente a jerarquía

{md_table(results['03_ingrediente_directo_jerarquia'])}

El concepto exacto de ingrediente de lisinopril recuperó
**{int(direct['personas_directas'])} pacientes**, mientras que la expansión con
`CONCEPT_ANCESTOR` recuperó **{int(direct['personas_jerarquia'])}**. La diferencia se
debe a que `DRUG_EXPOSURE` almacena productos clínicos o de marca; el ingrediente actúa
como ancestro de esos productos y no necesariamente aparece como exposición directa.

## 4. `DRUG_ERA` construida manualmente

{md_table(results['04_resumen_drug_era'])}

Se generaron **{int(era['eras_manuales'])} eras** de lisinopril con un gap permisible de
30 días. La tabla `cdm.drug_era` contiene **{int(era['eras_cdm'])} filas**, por lo que no
fue posible comparar fechas era por era con una derivación previa. Las eras se dejaron
en `results.drug_era_lisinopril`.

Para controlar valores anómalos, se aceptó `days_supply` entre 1 y 365 días. Cuando no
cumplió esa condición, se usó la fecha final sólo si estaba entre 0 y 364 días después
del inicio; en otro caso se asignó un día de cobertura.

## 5. Proporción de días cubiertos

{md_table(results['05_resumen_pdc'])}

Entre los pacientes con 365 días completos de observación después de su primera
prescripción, **{pdc['porcentaje_pdc_080']}%** presentó PDC ≥ 0.8.

La PDC cuenta como máximo una cobertura por día, por lo que los intervalos solapados se
fusionaron y el resultado quedó limitado a 1. La MPR, en cambio, suele sumar el suministro
obtenido y puede superar 1 cuando hay surtidos solapados. Se eligió PDC porque evita doble
conteo y es la metodología utilizada por PQA para terapias crónicas. Fuentes:
[PQA]({SOURCE_PDC}) y [Hess et al./revisión metodológica]({SOURCE_PDC_METHOD}).

Esta estimación supone que la prescripción representa disponibilidad, que la dosis se
mantiene constante y que el paciente permanece bajo observación durante todo el año.

![Distribución del PDC](figuras/02_pdc_lisinopril.png)

## 6. Calidad de `MEASUREMENT`

{md_table(results['06_calidad_measurement'])}

El **{measurement_quality['porcentaje_value_number_nulo']}%** de las mediciones no tiene
`value_as_number`. No se detectaron operadores no cero, por lo que esta base no registra
explícitamente resultados censurados como `<5` o `>200`. En una fuente real se conservaría
el operador y se aplicaría un método analítico preespecificado; no se sustituiría
silenciosamente por el límite.

### Analitos más frecuentes

{md_table(results['06_top15_analitos'], 15)}

### Unidades observadas en eGFR

{md_table(results['06_unidades_egfr'])}

Las unidades `mL/min/{{1.73_m2}}` y `mL/min` no deben tratarse automáticamente como
equivalentes: una está indexada por superficie corporal y la otra no. Convertirlas de
forma segura requeriría superficie corporal o confirmar un error de mapeo.

## 7. Normalización de unidades

Como la base contiene peso únicamente en kilogramos, se simuló que una quinta parte de
las filas había llegado en libras. Se conservaron valor y unidad originales simulados y
se normalizaron **{converted} filas** a kilogramos mediante:

`kg = lb × 0.45359237`

El factor proviene del [NIST Handbook 44]({SOURCE_NIST}).

{md_table(results['07_resumen_normalizacion'])}

![Normalización del peso](figuras/03_normalizacion_peso.png)

## 8. Valores implausibles

Los criterios se aplicaron sólo a mediciones de adultos para no clasificar pesos
pediátricos válidos como errores.

{md_table(results['08_criterios'])}

{md_table(results['08_valores_implausibles'])}

Los intervalos proceden de Thomas, Paulet y Rajpura (2016),
[_Consistency between Self-Reported and Recorded Values for Clinical Measures_]({SOURCE_PLAUSIBILITY}).
Los valores fuera del intervalo se marcan y se convierten a nulo únicamente en una vista
analítica; el dato OMOP original se conserva. Una repetición exacta dentro del intervalo
no se considera centinela. Sólo una repetición exacta fuera del intervalo, o un código
documentado por el proveedor, se clasificaría como posible centinela.

## 9. `MEASUREMENT` frente a `OBSERVATION`

{md_table(results['09_measurement_observation'])}

La ubicación coincide con las convenciones de [OMOP CDM v5.4]({SOURCE_OMOP}): peso y
presión arterial requieren una medición estandarizada, mientras que tabaquismo es un
hecho social o de estilo de vida y pertenece a `OBSERVATION`.

## 10. Valor más cercano a la fecha índice

La fecha índice se definió como la primera `condition_occurrence` de cada paciente. Se
seleccionó la glucosa con menor distancia absoluta dentro de ±90 días; ante empate se
prefirió el valor anterior al índice.

{md_table(results['10_glucosa_resumen'])}

Hubo valor basal para **{int(baseline['personas_con_glucosa_basal'])} pacientes** y no lo
hubo para **{int(baseline['personas_sin_glucosa_basal'])}**. La disponibilidad fue
**{baseline['porcentaje_con_glucosa_basal']}%**, por lo que exigir glucosa basal como
criterio de inclusión reduciría sustancialmente la cohorte.

![Disponibilidad de glucosa basal](figuras/04_glucosa_indice.png)

## Limitación principal

La limitación principal es que `DRUG_EXPOSURE` representa prescripciones de EHR y no
dispensaciones ni administraciones. Además, `days_supply` presenta valores inválidos y
extremos. En consecuencia, las eras y la PDC deben interpretarse como reconstrucciones
de cobertura prescrita bajo supuestos, no como evidencia de que el paciente obtuvo o
consumió el medicamento.
"""
    REPORT_PATH.write_text(dedent(report).strip() + "\n", encoding="utf-8")
    print(f"OK: {REPORT_PATH}")


def create_readme() -> None:
    content = f"""# Laboratorio 13 — Exposición a fármacos y laboratorios

## Objetivo

Caracterizar `DRUG_EXPOSURE` y `MEASUREMENT`, construir eras de tratamiento,
estimar PDC, revisar unidades y plausibilidad, y obtener el valor de laboratorio
más próximo a una fecha índice.

## Reproducción

Desde la raíz del repositorio y con el ambiente `cdb` activo:

```bash
python lab13/scripts/01_generar_lab13.py
```

La base de entrada es:

```text
lab12/data/omop/synthea_omop_cdm54.duckdb
```

El script crea las tablas `results.drug_era_lisinopril`,
`results.pdc_lisinopril` y `results.weight_unit_normalized` dentro de la base
local. La base DuckDB permanece fuera de Git.

## Entregables

- `farmacoepi.sql`: consultas comentadas de las actividades 1–10.
- `notebooks/analisis_farmacoepi.ipynb`: recorrido reproducible de resultados.
- `reporte_calidad.md`: interpretación, supuestos, fuentes y limitaciones.
- `evidencias/analisis/`: tablas CSV.
- `figuras/`: distribuciones de `days_supply`, PDC, unidades y disponibilidad basal.

## Decisiones principales

- Ingrediente para eras y PDC: lisinopril (`concept_id = {INGREDIENT_ID}`).
- Gap permisible para `DRUG_ERA`: 30 días.
- Seguimiento para PDC: 365 días completos dentro de `OBSERVATION_PERIOD`.
- Unidad canónica de peso: kg; `1 lb = {LB_TO_KG} kg`.
- Plausibilidad: presión sistólica, glucosa y peso en adultos.
- Fecha índice: primera condición de cada persona.
- Laboratorio basal: glucosa dentro de ±90 días.

## Fuentes metodológicas

- [OMOP CDM v5.4]({SOURCE_OMOP})
- [PQA: Proportion of Days Covered]({SOURCE_PDC})
- [Statistical considerations for medication adherence research]({SOURCE_PDC_METHOD})
- [NIST Handbook 44]({SOURCE_NIST})
- [Thomas et al. 2016: rangos de plausibilidad]({SOURCE_PLAUSIBILITY})
"""
    README_PATH.write_text(dedent(content).strip() + "\n", encoding="utf-8")
    print(f"OK: {README_PATH}")


def create_notebook() -> None:
    def markdown(source: str) -> dict:
        return {"cell_type": "markdown", "id": uuid.uuid4().hex[:8], "metadata": {}, "source": source.splitlines(True)}

    def code(source: str) -> dict:
        return {
            "cell_type": "code",
            "id": uuid.uuid4().hex[:8],
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": source.splitlines(True),
        }

    cells = [
        markdown(
            "# Laboratorio 13 — Exposición a fármacos y laboratorios\n\n"
            "Este notebook presenta las distribuciones producidas por `01_generar_lab13.py`."
        ),
        code(
            "from pathlib import Path\n"
            "import pandas as pd\n"
            "from IPython.display import Image, display\n\n"
            "cwd = Path.cwd()\n"
            "ROOT = cwd.parent.parent if cwd.name == 'notebooks' else cwd\n"
            "LAB = ROOT / 'lab13'\n"
            "ANALYSIS = LAB / 'evidencias/analisis'\n"
            "FIGURES = LAB / 'figuras'\n"
        ),
        markdown("## 1–3. Tipo de exposición, calidad y jerarquía de ingredientes"),
        code(
            "display(pd.read_csv(ANALYSIS / 'tipo_exposicion.csv'))\n"
            "display(pd.read_csv(ANALYSIS / 'drug_exposure_calidad.csv'))\n"
            "display(pd.read_csv(ANALYSIS / 'ingrediente_directo_jerarquia.csv'))\n"
            "display(Image(filename=str(FIGURES / '01_days_supply.png')))\n"
        ),
        markdown("## 4–5. Eras de lisinopril y PDC"),
        code(
            "display(pd.read_csv(ANALYSIS / 'drug_era_resumen.csv'))\n"
            "display(pd.read_csv(ANALYSIS / 'pdc_resumen.csv'))\n"
            "display(Image(filename=str(FIGURES / '02_pdc_lisinopril.png')))\n"
        ),
        markdown("## 6–7. Mediciones y normalización de unidades"),
        code(
            "display(pd.read_csv(ANALYSIS / 'top15_analitos.csv'))\n"
            "display(pd.read_csv(ANALYSIS / 'unidades_egfr.csv'))\n"
            "display(pd.read_csv(ANALYSIS / 'normalizacion_peso_resumen.csv'))\n"
            "display(Image(filename=str(FIGURES / '03_normalizacion_peso.png')))\n"
        ),
        markdown("## 8–10. Plausibilidad, dominios y valor basal"),
        code(
            "display(pd.read_csv(ANALYSIS / 'valores_implausibles_resumen.csv'))\n"
            "display(pd.read_csv(ANALYSIS / 'measurement_vs_observation.csv'))\n"
            "display(pd.read_csv(ANALYSIS / 'glucosa_indice_resumen.csv'))\n"
            "display(Image(filename=str(FIGURES / '04_glucosa_indice.png')))\n"
        ),
        markdown(
            "## Interpretación\n\n"
            "La interpretación completa, los supuestos, las fuentes y la limitación "
            "principal están documentados en `lab13/reporte_calidad.md`."
        ),
    ]
    notebook = {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "version": "3.12"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    NOTEBOOK_PATH.write_text(json.dumps(notebook, indent=1), encoding="utf-8")
    print(f"OK: {NOTEBOOK_PATH}")


def main() -> None:
    if not DB.is_file():
        raise SystemExit(f"ERROR: no existe la base OMOP: {DB}")

    ensure_directories()
    write_sql_file()

    print(f"Base: {DB}")
    con = duckdb.connect(str(DB))
    try:
        results = execute_analysis(con)
        create_figures(con, results)
    finally:
        con.close()

    create_report(results)
    create_readme()
    create_notebook()

    print("\n===== ENTREGABLES GENERADOS =====")
    for path in (README_PATH, SQL_PATH, REPORT_PATH, NOTEBOOK_PATH):
        print(path)
    print("VALIDACIÓN: generación del Laboratorio 13 completada.")


if __name__ == "__main__":
    main()

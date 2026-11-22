#!/usr/bin/env python3
"""Auditoría de vocabularios y datos para planear el Laboratorio 15."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd


ROOT = Path.cwd()
DB = ROOT / "lab12/data/omop/synthea_omop_cdm54.duckdb"
OUT = ROOT / "lab15/evidencias/auditoria"
REQUIRED_VOCABS = ["RxNorm", "RxNorm Extension", "ATC", "LOINC", "UCUM"]


def section(title: str) -> None:
    print(f"\n===== {title} =====")


def show_save(df: pd.DataFrame, filename: str, max_rows: int | None = None) -> None:
    path = OUT / filename
    df.to_csv(path, index=False)
    view = df if max_rows is None else df.head(max_rows)
    if view.empty:
        print("SIN FILAS")
    else:
        print(view.to_string(index=False))
    if max_rows is not None and len(df) > max_rows:
        print(f"... {len(df) - max_rows} filas adicionales en {path}")
    print(f"Guardado: {path} ({len(df)} filas)")


def main() -> None:
    if not DB.exists():
        raise SystemExit(f"ERROR: no existe {DB}")
    OUT.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DB), read_only=True)
    try:
        section("BASE Y VOCABULARIOS REQUERIDOS")
        vocab = con.execute("""
            SELECT c.vocabulary_id,
                   COUNT(*) AS conceptos,
                   COUNT(*) FILTER (WHERE c.standard_concept = 'S') AS estandar,
                   COUNT(*) FILTER (WHERE c.invalid_reason IS NULL) AS vigentes,
                   MAX(v.vocabulary_version) AS vocabulary_version,
                   MAX(v.vocabulary_reference) AS vocabulary_reference
            FROM cdm.concept c
            LEFT JOIN cdm.vocabulary v USING (vocabulary_id)
            WHERE c.vocabulary_id IN ('RxNorm', 'RxNorm Extension', 'ATC', 'LOINC', 'UCUM')
            GROUP BY c.vocabulary_id
            ORDER BY c.vocabulary_id
        """).df()
        show_save(vocab, "00_vocabularios_requeridos.csv")
        missing = sorted(set(REQUIRED_VOCABS) - set(vocab.vocabulary_id))
        if missing:
            print("FALTANTES:", ", ".join(missing))
        else:
            print("PASS: los cinco vocabularios están presentes.")

        section("CLASES RXNORM ESTÁNDAR Y VIGENTES")
        classes = con.execute("""
            SELECT vocabulary_id, concept_class_id, COUNT(*) conceptos
            FROM cdm.concept
            WHERE vocabulary_id IN ('RxNorm', 'RxNorm Extension')
              AND standard_concept = 'S'
              AND invalid_reason IS NULL
            GROUP BY vocabulary_id, concept_class_id
            ORDER BY vocabulary_id, conceptos DESC, concept_class_id
        """).df()
        show_save(classes, "01_clases_rxnorm.csv")

        section("TOP 20 DRUG_EXPOSURE")
        top20 = con.execute("""
            SELECT de.drug_concept_id,
                   c.concept_name,
                   c.vocabulary_id,
                   c.concept_class_id,
                   c.concept_code,
                   COUNT(*) AS exposiciones,
                   COUNT(DISTINCT de.person_id) AS pacientes
            FROM cdm.drug_exposure de
            JOIN cdm.concept c ON c.concept_id = de.drug_concept_id
            GROUP BY de.drug_concept_id, c.concept_name, c.vocabulary_id,
                     c.concept_class_id, c.concept_code
            ORDER BY exposiciones DESC, pacientes DESC, de.drug_concept_id
            LIMIT 20
        """).df()
        show_save(top20, "02_top20_drug_exposure.csv")

        section("TOP 20 RESUELTOS A INGREDIENTES")
        resolved = con.execute("""
            WITH top20 AS (
                SELECT de.drug_concept_id,
                       COUNT(*) AS exposiciones,
                       COUNT(DISTINCT de.person_id) AS pacientes
                FROM cdm.drug_exposure de
                GROUP BY de.drug_concept_id
                ORDER BY exposiciones DESC, pacientes DESC, de.drug_concept_id
                LIMIT 20
            ),
            ingredient_links AS (
                SELECT t.drug_concept_id,
                       i.concept_id AS ingredient_concept_id,
                       i.concept_name AS ingredient_name,
                       ca.min_levels_of_separation
                FROM top20 t
                JOIN cdm.concept_ancestor ca
                  ON ca.descendant_concept_id = t.drug_concept_id
                JOIN cdm.concept i
                  ON i.concept_id = ca.ancestor_concept_id
                WHERE i.domain_id = 'Drug'
                  AND i.concept_class_id = 'Ingredient'
                  AND i.standard_concept = 'S'
                  AND i.invalid_reason IS NULL
            ),
            ingredient_agg AS (
                SELECT drug_concept_id,
                       COUNT(DISTINCT ingredient_concept_id) AS numero_ingredientes,
                       STRING_AGG(
                           DISTINCT CAST(ingredient_concept_id AS VARCHAR) || ' — ' || ingredient_name,
                           ' | '
                           ORDER BY CAST(ingredient_concept_id AS VARCHAR) || ' — ' || ingredient_name
                       ) AS ingredientes,
                       MIN(min_levels_of_separation) AS separacion_minima
                FROM ingredient_links
                GROUP BY drug_concept_id
            )
            SELECT t.drug_concept_id, c.concept_name, c.concept_class_id,
                   t.exposiciones, t.pacientes,
                   COALESCE(a.numero_ingredientes, 0) AS numero_ingredientes,
                   a.ingredientes, a.separacion_minima
            FROM top20 t
            JOIN cdm.concept c ON c.concept_id = t.drug_concept_id
            LEFT JOIN ingredient_agg a USING (drug_concept_id)
            ORDER BY t.exposiciones DESC, t.drug_concept_id
        """).df()
        show_save(resolved, "03_top20_ingredientes.csv")
        print("Productos con >1 ingrediente:", int((resolved.numero_ingredientes > 1).sum()))
        print("Nota: se conserva separación 0 cuando la exposición ya está codificada como ingrediente.")

        section("CLASE ATC A10B")
        atc_seed = con.execute("""
            SELECT concept_id, concept_name, vocabulary_id, concept_class_id,
                   standard_concept, concept_code, invalid_reason
            FROM cdm.concept
            WHERE vocabulary_id = 'ATC' AND concept_code = 'A10B'
            ORDER BY invalid_reason NULLS FIRST, concept_id
        """).df()
        show_save(atc_seed, "04_atc_a10b_semilla.csv")

        atc_ingredients = con.execute("""
            WITH roots AS (
                SELECT concept_id
                FROM cdm.concept
                WHERE vocabulary_id = 'ATC'
                  AND concept_code = 'A10B'
                  AND invalid_reason IS NULL
            )
            SELECT DISTINCT i.concept_id AS ingredient_concept_id,
                   i.concept_name AS ingredient_name,
                   i.vocabulary_id, i.concept_code,
                   MIN(ca.min_levels_of_separation) AS min_separation,
                   COUNT(DISTINCT de.person_id) AS pacientes_en_base,
                   COUNT(de.drug_exposure_id) AS exposiciones_en_base
            FROM roots r
            JOIN cdm.concept_ancestor ca ON ca.ancestor_concept_id = r.concept_id
            JOIN cdm.concept i ON i.concept_id = ca.descendant_concept_id
            LEFT JOIN cdm.concept_ancestor drug_ca
              ON drug_ca.ancestor_concept_id = i.concept_id
            LEFT JOIN cdm.drug_exposure de
              ON de.drug_concept_id = drug_ca.descendant_concept_id
            WHERE i.domain_id = 'Drug'
              AND i.concept_class_id = 'Ingredient'
              AND i.standard_concept = 'S'
              AND i.invalid_reason IS NULL
            GROUP BY i.concept_id, i.concept_name, i.vocabulary_id, i.concept_code
            ORDER BY pacientes_en_base DESC, ingredient_name
        """).df()
        show_save(atc_ingredients, "05_atc_a10b_ingredientes.csv", max_rows=80)

        atc_summary = con.execute("""
            WITH root AS (
                SELECT concept_id
                FROM cdm.concept
                WHERE vocabulary_id = 'ATC' AND concept_code = 'A10B'
                  AND invalid_reason IS NULL
                LIMIT 1
            ),
            ingredients AS (
                SELECT DISTINCT i.concept_id
                FROM root r
                JOIN cdm.concept_ancestor ca ON ca.ancestor_concept_id = r.concept_id
                JOIN cdm.concept i ON i.concept_id = ca.descendant_concept_id
                WHERE i.domain_id = 'Drug'
                  AND i.concept_class_id = 'Ingredient'
                  AND i.standard_concept = 'S'
                  AND i.invalid_reason IS NULL
            ),
            selected_products AS (
                SELECT DISTINCT de.drug_concept_id
                FROM cdm.drug_exposure de
                JOIN cdm.concept_ancestor ca
                  ON ca.descendant_concept_id = de.drug_concept_id
                JOIN ingredients i ON i.concept_id = ca.ancestor_concept_id
            ),
            all_products AS (
                SELECT DISTINCT drug_concept_id
                FROM cdm.drug_exposure
                WHERE drug_concept_id <> 0
            )
            SELECT
              (SELECT COUNT(*) FROM ingredients) AS ingredientes_a10b,
              (SELECT COUNT(*) FROM selected_products) AS productos_a10b_en_base,
              (SELECT COUNT(DISTINCT de.person_id)
                 FROM cdm.drug_exposure de
                 JOIN selected_products p USING (drug_concept_id)) AS pacientes_a10b,
              (SELECT COUNT(*) FROM all_products) AS productos_totales_en_base,
              (SELECT COUNT(*) FROM all_products a
                 WHERE NOT EXISTS (
                   SELECT 1 FROM selected_products s
                   WHERE s.drug_concept_id = a.drug_concept_id
                 )) AS productos_fuera_a10b,
              (SELECT COUNT(DISTINCT de.person_id)
                 FROM cdm.drug_exposure de
                 WHERE NOT EXISTS (
                   SELECT 1 FROM selected_products s
                   WHERE s.drug_concept_id = de.drug_concept_id
                 )) AS pacientes_fuera_a10b
        """).df()
        show_save(atc_summary, "06_atc_a10b_resumen.csv")

        section("INGREDIENTE METFORMINA Y PRODUCTOS OBSERVADOS")
        metformin = con.execute("""
            SELECT concept_id, concept_name, vocabulary_id, concept_class_id,
                   standard_concept, concept_code, valid_start_date,
                   valid_end_date, invalid_reason
            FROM cdm.concept
            WHERE vocabulary_id IN ('RxNorm', 'RxNorm Extension')
              AND concept_code = '6809'
            ORDER BY invalid_reason NULLS FIRST, vocabulary_id
        """).df()
        show_save(metformin, "07_metformina_ingrediente.csv")

        met_products = con.execute("""
            WITH met AS (
                SELECT concept_id
                FROM cdm.concept
                WHERE vocabulary_id = 'RxNorm'
                  AND concept_code = '6809'
                  AND concept_class_id = 'Ingredient'
                  AND standard_concept = 'S'
                  AND invalid_reason IS NULL
            ),
            observed AS (
                SELECT de.drug_concept_id,
                       COUNT(*) exposiciones,
                       COUNT(DISTINCT de.person_id) pacientes
                FROM cdm.drug_exposure de
                JOIN cdm.concept_ancestor ca
                  ON ca.descendant_concept_id = de.drug_concept_id
                JOIN met ON met.concept_id = ca.ancestor_concept_id
                GROUP BY de.drug_concept_id
            ),
            ingredients AS (
                SELECT o.drug_concept_id,
                       i.concept_id ingredient_id,
                       i.concept_name ingredient_name
                FROM observed o
                JOIN cdm.concept_ancestor ca
                  ON ca.descendant_concept_id = o.drug_concept_id
                JOIN cdm.concept i ON i.concept_id = ca.ancestor_concept_id
                WHERE i.domain_id = 'Drug'
                  AND i.concept_class_id = 'Ingredient'
                  AND i.standard_concept = 'S'
                  AND i.invalid_reason IS NULL
            ),
            ingredient_agg AS (
                SELECT drug_concept_id,
                       COUNT(DISTINCT ingredient_id) numero_ingredientes,
                       STRING_AGG(DISTINCT ingredient_name, ' | ' ORDER BY ingredient_name) ingredientes
                FROM ingredients
                GROUP BY drug_concept_id
            )
            SELECT o.drug_concept_id, c.concept_name, c.concept_class_id,
                   o.exposiciones, o.pacientes,
                   a.numero_ingredientes, a.ingredientes
            FROM observed o
            JOIN cdm.concept c ON c.concept_id = o.drug_concept_id
            JOIN ingredient_agg a USING (drug_concept_id)
            ORDER BY o.exposiciones DESC, c.concept_name
        """).df()
        show_save(met_products, "08_metformina_productos_observados.csv", max_rows=100)
        if not met_products.empty:
            print("Productos monoterapia:", int((met_products.numero_ingredientes == 1).sum()))
            print("Productos combinación:", int((met_products.numero_ingredientes > 1).sum()))

        section("LOINC 4548-4, 2160-0 Y 2345-7 EN LA BASE")
        loinc_three = con.execute("""
            SELECT c.concept_id, c.concept_code, c.concept_name,
                   c.domain_id, c.vocabulary_id, c.concept_class_id,
                   c.standard_concept, c.invalid_reason,
                   COUNT(m.measurement_id) mediciones,
                   COUNT(DISTINCT m.person_id) pacientes,
                   COUNT(DISTINCT m.unit_concept_id) unidades_distintas
            FROM cdm.concept c
            LEFT JOIN cdm.measurement m ON m.measurement_concept_id = c.concept_id
            WHERE c.vocabulary_id = 'LOINC'
              AND c.concept_code IN ('4548-4', '2160-0', '2345-7')
            GROUP BY c.concept_id, c.concept_code, c.concept_name,
                     c.domain_id, c.vocabulary_id, c.concept_class_id,
                     c.standard_concept, c.invalid_reason
            ORDER BY c.concept_code
        """).df()
        show_save(loinc_three, "09_loinc_tres_codigos.csv")

        section("CANDIDATOS HbA1c REALMENTE OBSERVADOS")
        hba1c = con.execute("""
            SELECT m.measurement_concept_id, c.concept_code, c.concept_name,
                   c.vocabulary_id, c.concept_class_id, c.standard_concept,
                   COUNT(*) mediciones,
                   COUNT(DISTINCT m.person_id) pacientes,
                   COUNT(DISTINCT m.unit_concept_id) unidades_distintas
            FROM cdm.measurement m
            JOIN cdm.concept c ON c.concept_id = m.measurement_concept_id
            WHERE lower(c.concept_name) LIKE '%a1c%'
               OR lower(c.concept_name) LIKE '%glycated hemoglobin%'
               OR lower(c.concept_name) LIKE '%glycohemoglobin%'
            GROUP BY m.measurement_concept_id, c.concept_code, c.concept_name,
                     c.vocabulary_id, c.concept_class_id, c.standard_concept
            ORDER BY mediciones DESC, c.concept_name
        """).df()
        show_save(hba1c, "10_hba1c_candidatos_observados.csv", max_rows=100)

        section("UNIDADES DE LOS TRES ANALITOS")
        units = con.execute("""
            SELECT analyte.concept_code AS loinc_code,
                   analyte.concept_name AS analyte_name,
                   m.unit_concept_id,
                   COALESCE(unit.concept_name, '[nulo o no mapeado]') AS unit_name,
                   unit.concept_code AS unit_code,
                   COUNT(*) mediciones,
                   COUNT(DISTINCT m.person_id) pacientes,
                   COUNT(m.value_as_number) valores_numericos,
                   MIN(m.value_as_number) minimo,
                   MEDIAN(m.value_as_number) mediana,
                   MAX(m.value_as_number) maximo
            FROM cdm.measurement m
            JOIN cdm.concept analyte ON analyte.concept_id = m.measurement_concept_id
            LEFT JOIN cdm.concept unit ON unit.concept_id = m.unit_concept_id
            WHERE analyte.vocabulary_id = 'LOINC'
              AND analyte.concept_code IN ('4548-4', '2160-0', '2345-7')
            GROUP BY analyte.concept_code, analyte.concept_name,
                     m.unit_concept_id, unit.concept_name, unit.concept_code
            ORDER BY analyte.concept_code, mediciones DESC
        """).df()
        show_save(units, "11_unidades_tres_analitos.csv", max_rows=100)

        section("COBERTURA GLOBAL DE PRODUCTOS POR INGREDIENTE")
        coverage = con.execute("""
            WITH observed AS (
                SELECT DISTINCT drug_concept_id
                FROM cdm.drug_exposure WHERE drug_concept_id <> 0
            ), resolved AS (
                SELECT DISTINCT o.drug_concept_id
                FROM observed o
                JOIN cdm.concept_ancestor ca
                  ON ca.descendant_concept_id = o.drug_concept_id
                JOIN cdm.concept i ON i.concept_id = ca.ancestor_concept_id
                WHERE i.domain_id = 'Drug'
                  AND i.concept_class_id = 'Ingredient'
                  AND i.standard_concept = 'S'
                  AND i.invalid_reason IS NULL
            )
            SELECT (SELECT COUNT(*) FROM observed) productos_observados,
                   (SELECT COUNT(*) FROM resolved) productos_con_ingrediente,
                   (SELECT COUNT(*) FROM observed o
                      WHERE NOT EXISTS (
                        SELECT 1 FROM resolved r
                        WHERE r.drug_concept_id = o.drug_concept_id
                      )) productos_sin_ingrediente
        """).df()
        show_save(coverage, "12_cobertura_ingredientes.csv")

        section("CANDIDATOS PARA CATÁLOGO LOCAL")
        terms = [
            "metformin", "lisinopril", "omeprazole", "hydrochlorothiazide",
            "losartan", "amoxicillin", "acetaminophen", "insulin glargine",
            "albuterol", "sulfamethoxazole", "trimethoprim", "sitagliptin",
            "cisplatin", "sodium chloride", "lactated ringer"
        ]
        frames: list[pd.DataFrame] = []
        for term in terms:
            result = con.execute("""
                WITH exposure AS (
                    SELECT drug_concept_id, COUNT(*) exposiciones
                    FROM cdm.drug_exposure
                    GROUP BY drug_concept_id
                )
                SELECT ? AS termino_buscado,
                       c.concept_id, c.concept_name, c.vocabulary_id,
                       c.concept_class_id, c.standard_concept, c.concept_code,
                       COALESCE(e.exposiciones, 0) AS exposiciones_en_base
                FROM cdm.concept c
                LEFT JOIN exposure e ON e.drug_concept_id = c.concept_id
                WHERE c.domain_id = 'Drug'
                  AND c.standard_concept = 'S'
                  AND c.invalid_reason IS NULL
                  AND lower(c.concept_name) LIKE '%' || lower(?) || '%'
                ORDER BY (e.exposiciones IS NOT NULL) DESC,
                         e.exposiciones DESC,
                         CASE c.concept_class_id
                           WHEN 'Ingredient' THEN 1
                           WHEN 'Clinical Drug' THEN 2
                           WHEN 'Branded Drug' THEN 3
                           ELSE 4
                         END,
                         c.concept_name
                LIMIT 8
            """, [term, term]).df()
            frames.append(result)
        catalog = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
        show_save(catalog, "13_candidatos_catalogo_local.csv", max_rows=140)

        section("RESUMEN PARA DECISIONES")
        print("Vocabularios faltantes:", missing or "ninguno")
        print("Top 20 con más de un ingrediente:", int((resolved.numero_ingredientes > 1).sum()))
        if not atc_summary.empty:
            print(atc_summary.to_string(index=False))
        print("Candidatos HbA1c observados:", len(hba1c))
        print("Filas de unidades para los tres analitos:", len(units))
        print("AUDITORÍA COMPLETADA")
    finally:
        con.close()


if __name__ == "__main__":
    main()

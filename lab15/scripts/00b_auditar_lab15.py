#!/usr/bin/env python3
"""Auditoría dirigida de lisinopril, HbA1c y RxNav para el Laboratorio 15."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

import duckdb
import pandas as pd


ROOT = Path.cwd()
DB = ROOT / "lab12/data/omop/synthea_omop_cdm54.duckdb"
OUT = ROOT / "lab15/evidencias/auditoria"
RXNAV = {
    "metformin": "6809",
    "lisinopril": "29046",
    "cisplatin": "2555",
}


def section(title: str) -> None:
    print(f"\n===== {title} =====")


def save_show(df: pd.DataFrame, filename: str, limit: int = 100) -> None:
    path = OUT / filename
    df.to_csv(path, index=False)
    if df.empty:
        print("SIN FILAS")
    else:
        print(df.head(limit).to_string(index=False))
    if len(df) > limit:
        print(f"... {len(df) - limit} filas adicionales en {path}")
    print(f"Guardado: {path} ({len(df)} filas)")


def fetch_json(url: str) -> dict:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "EE_CDB-Lab15/1.0"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def rxnav_audit() -> pd.DataFrame:
    rows: list[dict] = []
    for expected_name, rxcui in RXNAV.items():
        properties_url = f"https://rxnav.nlm.nih.gov/REST/rxcui/{rxcui}/properties.json"
        related_url = f"https://rxnav.nlm.nih.gov/REST/rxcui/{rxcui}/related.json?tty=SCDF+BN"
        try:
            properties = fetch_json(properties_url).get("properties", {})
            groups = (
                fetch_json(related_url)
                .get("relatedGroup", {})
                .get("conceptGroup", [])
            )
            counts = {"SCDF": 0, "BN": 0}
            for group in groups:
                tty = group.get("tty")
                if tty in counts:
                    counts[tty] = len(group.get("conceptProperties") or [])
            rows.append({
                "medicamento": expected_name,
                "rxcui": rxcui,
                "nombre_rxnav": properties.get("name"),
                "tty": properties.get("tty"),
                "formas_clinicas_scdf": counts["SCDF"],
                "nombres_marca_bn": counts["BN"],
                "fecha_consulta": date.today().isoformat(),
                "fuente": f"https://rxnav.nlm.nih.gov/REST/rxcui/{rxcui}/related.json?tty=SCDF+BN",
                "estado": "OK",
            })
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            rows.append({
                "medicamento": expected_name,
                "rxcui": rxcui,
                "nombre_rxnav": None,
                "tty": None,
                "formas_clinicas_scdf": None,
                "nombres_marca_bn": None,
                "fecha_consulta": date.today().isoformat(),
                "fuente": related_url,
                "estado": f"ERROR: {exc}",
            })
    return pd.DataFrame(rows)


def main() -> None:
    if not DB.exists():
        raise SystemExit(f"ERROR: no existe {DB}")
    OUT.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DB), read_only=True)
    try:
        section("LISINOPRIL COMO INGREDIENTE")
        lisinopril = con.execute("""
            SELECT concept_id, concept_name, vocabulary_id, concept_class_id,
                   standard_concept, concept_code, invalid_reason
            FROM cdm.concept
            WHERE vocabulary_id IN ('RxNorm', 'RxNorm Extension')
              AND concept_code = '29046'
            ORDER BY invalid_reason NULLS FIRST, vocabulary_id
        """).df()
        save_show(lisinopril, "14_lisinopril_ingrediente.csv")

        section("TODOS LOS PRODUCTOS OBSERVADOS DE LISINOPRIL")
        products = con.execute("""
            WITH lis AS (
                SELECT concept_id
                FROM cdm.concept
                WHERE vocabulary_id = 'RxNorm'
                  AND concept_code = '29046'
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
                JOIN lis ON lis.concept_id = ca.ancestor_concept_id
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
                   c.concept_code, o.exposiciones, o.pacientes,
                   a.numero_ingredientes, a.ingredientes,
                   CASE
                     WHEN a.numero_ingredientes = 1 THEN 'monoterapia'
                     ELSE 'combinacion'
                   END AS tipo_producto,
                   CASE
                     WHEN lower(a.ingredientes) LIKE '%hydrochlorothiazide%'
                       THEN 'excluir_C_diuretico'
                     ELSE 'conservar_C'
                   END AS decision_preliminar_C
            FROM observed o
            JOIN cdm.concept c ON c.concept_id = o.drug_concept_id
            JOIN ingredient_agg a USING (drug_concept_id)
            ORDER BY o.exposiciones DESC, c.concept_name
        """).df()
        save_show(products, "15_lisinopril_productos_observados.csv", limit=200)
        if not products.empty:
            print("Productos:", len(products))
            print("Monoterapia:", int((products.tipo_producto == "monoterapia").sum()))
            print("Combinaciones:", int((products.tipo_producto == "combinacion").sum()))
            print("Combinaciones con HCTZ:", int((products.decision_preliminar_C == "excluir_C_diuretico").sum()))

        section("IMPACTO PRELIMINAR A/B/C PARA LISINOPRIL")
        impact = con.execute("""
            WITH lis AS (
                SELECT concept_id
                FROM cdm.concept
                WHERE vocabulary_id = 'RxNorm'
                  AND concept_code = '29046'
                  AND concept_class_id = 'Ingredient'
                  AND standard_concept = 'S'
                  AND invalid_reason IS NULL
            ),
            descendants AS (
                SELECT DISTINCT ca.descendant_concept_id drug_concept_id
                FROM lis
                JOIN cdm.concept_ancestor ca ON ca.ancestor_concept_id = lis.concept_id
            ),
            ingredient_counts AS (
                SELECT d.drug_concept_id,
                       COUNT(DISTINCT i.concept_id) numero_ingredientes,
                       MAX(CASE WHEN lower(i.concept_name) = 'hydrochlorothiazide' THEN 1 ELSE 0 END) tiene_hctz
                FROM descendants d
                JOIN cdm.concept_ancestor ca ON ca.descendant_concept_id = d.drug_concept_id
                JOIN cdm.concept i ON i.concept_id = ca.ancestor_concept_id
                WHERE i.domain_id = 'Drug'
                  AND i.concept_class_id = 'Ingredient'
                  AND i.standard_concept = 'S'
                  AND i.invalid_reason IS NULL
                GROUP BY d.drug_concept_id
            ),
            sets AS (
                SELECT 'A_monoterapia' version, drug_concept_id
                FROM ingredient_counts WHERE numero_ingredientes = 1
                UNION ALL
                SELECT 'B_todo_lisinopril', drug_concept_id
                FROM ingredient_counts
                UNION ALL
                SELECT 'C_sin_hctz', drug_concept_id
                FROM ingredient_counts WHERE tiene_hctz = 0
            )
            SELECT s.version,
                   COUNT(DISTINCT s.drug_concept_id) conceptos_vocabulario,
                   COUNT(DISTINCT de.drug_concept_id) productos_observados,
                   COUNT(DISTINCT de.person_id) pacientes,
                   COUNT(de.drug_exposure_id) exposiciones
            FROM sets s
            LEFT JOIN cdm.drug_exposure de ON de.drug_concept_id = s.drug_concept_id
            GROUP BY s.version
            ORDER BY s.version
        """).df()
        save_show(impact, "16_lisinopril_impacto_preliminar.csv")

        section("TODOS LOS LOINC HbA1c ESTÁNDAR Y VIGENTES")
        hba1c = con.execute("""
            SELECT c.concept_id, c.concept_code, c.concept_name,
                   c.concept_class_id, c.standard_concept,
                   COUNT(m.measurement_id) mediciones,
                   COUNT(DISTINCT m.person_id) pacientes,
                   COUNT(DISTINCT m.unit_concept_id) unidades_distintas
            FROM cdm.concept c
            LEFT JOIN cdm.measurement m ON m.measurement_concept_id = c.concept_id
            WHERE c.vocabulary_id = 'LOINC'
              AND c.domain_id = 'Measurement'
              AND c.standard_concept = 'S'
              AND c.invalid_reason IS NULL
              AND (
                lower(c.concept_name) LIKE '%hemoglobin a1c%'
                OR lower(c.concept_name) LIKE '%hba1c%'
                OR lower(c.concept_name) LIKE '%glycated hemoglobin%'
                OR lower(c.concept_name) LIKE '%glycohemoglobin%'
              )
            GROUP BY c.concept_id, c.concept_code, c.concept_name,
                     c.concept_class_id, c.standard_concept
            ORDER BY mediciones DESC, c.concept_name
        """).df()
        save_show(hba1c, "17_hba1c_vocabulario_candidatos.csv", limit=200)

        section("JERARQUÍA OMOP DE 4548-4")
        hierarchy = con.execute("""
            WITH seed AS (
                SELECT concept_id
                FROM cdm.concept
                WHERE vocabulary_id = 'LOINC' AND concept_code = '4548-4'
                  AND invalid_reason IS NULL
                LIMIT 1
            )
            SELECT 'ancestor' relacion,
                   c.concept_id, c.concept_code, c.concept_name,
                   c.vocabulary_id, c.concept_class_id,
                   ca.min_levels_of_separation, ca.max_levels_of_separation
            FROM seed
            JOIN cdm.concept_ancestor ca ON ca.descendant_concept_id = seed.concept_id
            JOIN cdm.concept c ON c.concept_id = ca.ancestor_concept_id
            WHERE ca.ancestor_concept_id <> seed.concept_id
            UNION ALL
            SELECT 'descendant',
                   c.concept_id, c.concept_code, c.concept_name,
                   c.vocabulary_id, c.concept_class_id,
                   ca.min_levels_of_separation, ca.max_levels_of_separation
            FROM seed
            JOIN cdm.concept_ancestor ca ON ca.ancestor_concept_id = seed.concept_id
            JOIN cdm.concept c ON c.concept_id = ca.descendant_concept_id
            WHERE ca.descendant_concept_id <> seed.concept_id
            ORDER BY relacion, min_levels_of_separation, concept_name
        """).df()
        save_show(hierarchy, "18_hba1c_jerarquia_4548_4.csv", limit=200)

        section("RELACIONES DIRECTAS DE 4548-4")
        relations = con.execute("""
            WITH seed AS (
                SELECT concept_id
                FROM cdm.concept
                WHERE vocabulary_id = 'LOINC' AND concept_code = '4548-4'
                  AND invalid_reason IS NULL
                LIMIT 1
            )
            SELECT 'outgoing' direccion, cr.relationship_id,
                   other.concept_id, other.concept_code,
                   other.concept_name, other.vocabulary_id,
                   other.concept_class_id, cr.invalid_reason
            FROM seed
            JOIN cdm.concept_relationship cr ON cr.concept_id_1 = seed.concept_id
            JOIN cdm.concept other ON other.concept_id = cr.concept_id_2
            WHERE cr.concept_id_2 <> seed.concept_id
            UNION ALL
            SELECT 'incoming', cr.relationship_id,
                   other.concept_id, other.concept_code,
                   other.concept_name, other.vocabulary_id,
                   other.concept_class_id, cr.invalid_reason
            FROM seed
            JOIN cdm.concept_relationship cr ON cr.concept_id_2 = seed.concept_id
            JOIN cdm.concept other ON other.concept_id = cr.concept_id_1
            WHERE cr.concept_id_1 <> seed.concept_id
            ORDER BY direccion, relationship_id, concept_name
        """).df()
        save_show(relations, "19_hba1c_relaciones_4548_4.csv", limit=200)

        section("RXNAV: IN, SCDF Y BN")
        rxnav = rxnav_audit()
        save_show(rxnav, "20_rxnav_tres_ingredientes.csv")
        if not (rxnav.estado == "OK").all():
            print("ADVERTENCIA: alguna consulta RxNav falló; se puede reintentar en el generador.")

        section("RESUMEN")
        print("Productos observados de lisinopril:", len(products))
        print("Candidatos LOINC HbA1c:", len(hba1c))
        print("Relaciones jerárquicas de 4548-4:", len(hierarchy))
        print("Consultas RxNav exitosas:", int((rxnav.estado == "OK").sum()), "de", len(rxnav))
        print("AUDITORÍA DIRIGIDA COMPLETADA")
    finally:
        con.close()


if __name__ == "__main__":
    main()

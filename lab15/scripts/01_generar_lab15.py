#!/usr/bin/env python3
"""Genera todas las actividades y entregables del Laboratorio 15."""

from __future__ import annotations

import json
import urllib.request
from datetime import date
from pathlib import Path

import duckdb
import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path.cwd()
DB = ROOT / "lab12/data/omop/synthea_omop_cdm54.duckdb"
LAB = ROOT / "lab15"
CS = LAB / "concept_sets"
EVID = LAB / "evidencias/analisis"
FIG = LAB / "figuras"
NB = LAB / "notebooks"
TODAY = date.today().isoformat()


def ensure_dirs() -> None:
    for directory in (CS, EVID, FIG, NB):
        directory.mkdir(parents=True, exist_ok=True)


def save_csv(df: pd.DataFrame, name: str) -> None:
    path = EVID / name
    df.to_csv(path, index=False)
    print(f"OK: {path} ({len(df)} filas)")


def markdown_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_Sin filas._"
    clean = df.copy().fillna("")
    columns = [str(c) for c in clean.columns]
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join(["---"] * len(columns)) + " |",
    ]
    for row in clean.itertuples(index=False, name=None):
        values = [str(v).replace("|", "\\|").replace("\n", " ") for v in row]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def rxnav_table() -> pd.DataFrame:
    drugs = {"metformin": "6809", "lisinopril": "29046", "cisplatin": "2555"}
    rows = []
    for drug, rxcui in drugs.items():
        prop_url = f"https://rxnav.nlm.nih.gov/REST/rxcui/{rxcui}/properties.json"
        rel_url = f"https://rxnav.nlm.nih.gov/REST/rxcui/{rxcui}/related.json?tty=SCDF+BN"
        try:
            request = urllib.request.Request(prop_url, headers={"User-Agent": "EE-CDB-Lab15/1.0"})
            with urllib.request.urlopen(request, timeout=60) as response:
                prop = json.load(response).get("properties", {})
            request = urllib.request.Request(rel_url, headers={"User-Agent": "EE-CDB-Lab15/1.0"})
            with urllib.request.urlopen(request, timeout=60) as response:
                groups = json.load(response).get("relatedGroup", {}).get("conceptGroup", [])
            counts = {"SCDF": 0, "BN": 0}
            for group in groups:
                tty = group.get("tty")
                if tty in counts:
                    counts[tty] = len(group.get("conceptProperties") or [])
            rows.append({
                "medicamento": drug,
                "rxcui": rxcui,
                "nombre_rxnav": prop.get("name"),
                "tty": prop.get("tty"),
                "formas_clinicas_scdf": counts["SCDF"],
                "nombres_marca_bn": counts["BN"],
                "fecha_consulta": TODAY,
                "fuente": rel_url,
            })
        except Exception as exc:
            cached = LAB / "evidencias/auditoria/20_rxnav_tres_ingredientes.csv"
            if cached.exists():
                print(f"ADVERTENCIA RxNav ({drug}): {exc}; se reutiliza auditoría validada.")
                return pd.read_csv(cached)[[
                    "medicamento", "rxcui", "nombre_rxnav", "tty",
                    "formas_clinicas_scdf", "nombres_marca_bn",
                    "fecha_consulta", "fuente",
                ]]
            raise
    return pd.DataFrame(rows)


def sql_lisinopril(rxnorm_version: str) -> str:
    return f"""-- Concept set: exposición a lisinopril
-- Vocabulario: {rxnorm_version}; consulta: {TODAY}
-- Define tres versiones por jerarquía RxNorm, no por listas de productos.
-- A: monoterapia (un ingrediente); B: todos los descendientes;
-- C: B menos combinaciones con hidroclorotiazida, que puede modificar
--    independientemente volumen, creatinina y función renal.
-- Conteos validados tras filtrar conceptos estándar y vigentes:
-- A=53, B=77, C=53 conceptos de vocabulario.

CREATE SCHEMA IF NOT EXISTS results;

CREATE OR REPLACE TABLE results.lab15_lisinopril_sets AS
WITH ingredient AS (
    SELECT concept_id
    FROM cdm.concept
    WHERE vocabulary_id = 'RxNorm'
      AND concept_code = '29046'
      AND concept_class_id = 'Ingredient'
      AND standard_concept = 'S'
      AND invalid_reason IS NULL
),
descendants AS (
    SELECT DISTINCT ca.descendant_concept_id AS drug_concept_id
    FROM ingredient i
    JOIN cdm.concept_ancestor ca ON ca.ancestor_concept_id = i.concept_id
    JOIN cdm.concept d ON d.concept_id = ca.descendant_concept_id
    WHERE d.domain_id = 'Drug'
      AND d.standard_concept = 'S'
      AND d.invalid_reason IS NULL
),
ingredient_counts AS (
    SELECT d.drug_concept_id,
           COUNT(DISTINCT i.concept_id) AS numero_ingredientes,
           MAX(CASE WHEN lower(i.concept_name) = 'hydrochlorothiazide'
                    THEN 1 ELSE 0 END) AS tiene_hctz
    FROM descendants d
    JOIN cdm.concept_ancestor ca
      ON ca.descendant_concept_id = d.drug_concept_id
    JOIN cdm.concept i ON i.concept_id = ca.ancestor_concept_id
    WHERE i.domain_id = 'Drug'
      AND i.concept_class_id = 'Ingredient'
      AND i.standard_concept = 'S'
      AND i.invalid_reason IS NULL
    GROUP BY d.drug_concept_id
)
SELECT 'A_monoterapia' AS version, ic.drug_concept_id,
       c.concept_name, ic.numero_ingredientes,
       'Solo productos con un ingrediente' AS criterio
FROM ingredient_counts ic
JOIN cdm.concept c ON c.concept_id = ic.drug_concept_id
WHERE ic.numero_ingredientes = 1
UNION ALL
SELECT 'B_todo_lisinopril', ic.drug_concept_id,
       c.concept_name, ic.numero_ingredientes,
       'Todos los descendientes, combinaciones incluidas'
FROM ingredient_counts ic
JOIN cdm.concept c ON c.concept_id = ic.drug_concept_id
UNION ALL
SELECT 'C_sin_hctz', ic.drug_concept_id,
       c.concept_name, ic.numero_ingredientes,
       'Todos los descendientes excepto combinaciones con HCTZ'
FROM ingredient_counts ic
JOIN cdm.concept c ON c.concept_id = ic.drug_concept_id
WHERE ic.tiene_hctz = 0;

SELECT * FROM results.lab15_lisinopril_sets
ORDER BY version, concept_name;
"""


def sql_atc(atc_version: str, ingredient_count: int) -> str:
    return f"""-- Concept set: hipoglucemiantes A10B, excluyendo insulinas
-- Vocabulario: {atc_version}; consulta: {TODAY}
-- Construido desde la clase ATC A10B mediante CONCEPT_ANCESTOR.
-- Devuelve {ingredient_count} ingredientes estándar vigentes.
-- La cobertura de ATC se audita porque no incluye todos los productos de la base.

CREATE SCHEMA IF NOT EXISTS results;

CREATE OR REPLACE TABLE results.lab15_atc_a10b_ingredients AS
WITH root AS (
    SELECT concept_id
    FROM cdm.concept
    WHERE vocabulary_id = 'ATC'
      AND concept_code = 'A10B'
      AND invalid_reason IS NULL
)
SELECT DISTINCT i.concept_id AS ingredient_concept_id,
       i.concept_name AS ingredient_name,
       i.vocabulary_id, i.concept_code
FROM root r
JOIN cdm.concept_ancestor ca ON ca.ancestor_concept_id = r.concept_id
JOIN cdm.concept i ON i.concept_id = ca.descendant_concept_id
WHERE i.domain_id = 'Drug'
  AND i.concept_class_id = 'Ingredient'
  AND i.standard_concept = 'S'
  AND i.invalid_reason IS NULL;

CREATE OR REPLACE TABLE results.lab15_atc_a10b_products_observed AS
SELECT DISTINCT de.drug_concept_id, c.concept_name
FROM cdm.drug_exposure de
JOIN cdm.concept c ON c.concept_id = de.drug_concept_id
JOIN cdm.concept_ancestor ca ON ca.descendant_concept_id = de.drug_concept_id
JOIN results.lab15_atc_a10b_ingredients i
  ON i.ingredient_concept_id = ca.ancestor_concept_id;

SELECT * FROM results.lab15_atc_a10b_ingredients ORDER BY ingredient_name;
SELECT * FROM results.lab15_atc_a10b_products_observed ORDER BY concept_name;
"""


def sql_hba1c(loinc_version: str, concept_count: int) -> str:
    return f"""-- Concept set: pruebas de hemoglobina A1c
-- Vocabulario: {loinc_version}; consulta: {TODAY}
-- Construcción por relación LOINC Has component con LP286151-8.
-- Incluye variantes por método, propiedad y sistema que sean pruebas de
-- laboratorio estándar y vigentes; excluye paneles, dispositivos, metas
-- clínicas y glucosa media estimada.
-- Devuelve {concept_count} conceptos.

CREATE SCHEMA IF NOT EXISTS results;

CREATE OR REPLACE TABLE results.lab15_hba1c_set AS
WITH component AS (
    SELECT concept_id
    FROM cdm.concept
    WHERE vocabulary_id = 'LOINC'
      AND concept_code = 'LP286151-8'
      AND invalid_reason IS NULL
)
SELECT DISTINCT test.concept_id AS measurement_concept_id,
       test.concept_code AS loinc_code,
       test.concept_name,
       test.concept_class_id
FROM component comp
JOIN cdm.concept_relationship cr
  ON cr.concept_id_2 = comp.concept_id
 AND cr.relationship_id = 'Has component'
 AND cr.invalid_reason IS NULL
JOIN cdm.concept test ON test.concept_id = cr.concept_id_1
WHERE test.vocabulary_id = 'LOINC'
  AND test.domain_id = 'Measurement'
  AND test.concept_class_id = 'Lab Test'
  AND test.standard_concept = 'S'
  AND test.invalid_reason IS NULL
  AND CURRENT_DATE BETWEEN test.valid_start_date AND test.valid_end_date;

SELECT * FROM results.lab15_hba1c_set ORDER BY loinc_code;
"""


def catalog_rows(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    specifications = [
        ("FAR-001", "METFORMINA CLH 500 MG LP TAB", "860975", "alta", "Coincidencia exacta de ingrediente, dosis, liberación prolongada y forma oral."),
        ("FAR-002", "LISINOPRIL 10 MG TAB", "314076", "alta", "Coincidencia exacta de ingrediente, dosis y tableta oral."),
        ("FAR-003", "HCTZ 25 MG TAB", "310798", "alta", "HCTZ se expandió manualmente a hidroclorotiazida; dosis y forma coinciden."),
        ("FAR-004", "LOSARTAN POTASICO 50 MG TAB", "979492", "alta", "Coincidencia de sal, dosis y forma oral."),
        ("FAR-005", "AMOXICILINA 500 MG TAB", "308192", "alta", "Coincidencia exacta de ingrediente, dosis y tableta oral."),
        ("FAR-006", "PARACETAMOL 500 MG TAB", "198440", "alta", "Paracetamol corresponde a acetaminophen; dosis y forma coinciden."),
        ("FAR-007", "CISPLATINO 50 MG INY", "1736854", "alta", "Coincidencia de ingrediente, cantidad y presentación inyectable."),
        ("FAR-008", "SALBUTAMOL 0.83 MG/ML SOL NEB", "630208", "alta", "Salbutamol corresponde a albuterol; concentración y vía inhalada coinciden."),
        ("FAR-009", "TMP/SMX 160/800 MG TAB", "198335", "alta", "Abreviatura expandida; combinación, dosis y forma coinciden."),
        ("FAR-010", "INSULINA GLARGINA 100 UI/ML PLUMA", "1359855", "alta", "Coincidencia de ingrediente, concentración y dispositivo tipo pluma."),
        ("FAR-011", "OMEPRAZOL 20 MG CAP LP", "207212", "alta", "Coincidencia de ingrediente, dosis y cápsula de liberación retardada."),
        ("FAR-012", "SITAGLIPTINA/METFORMINA 50/1000 MG TAB", "861769", "alta", "Coincidencia exacta de combinación, dosis y forma oral."),
        ("FAR-013", "METFORMINA 750 MG AMPOLLETA IV", None, "no mapeable", "Presentación intravenosa deliberadamente inexistente; no debe forzarse a una tableta."),
        ("FAR-014", "GASA ESTERIL 10 X 10 CM", None, "no mapeable", "Material de curación, no un medicamento del dominio Drug."),
        ("FAR-015", "CLORURO DE SODIO 0.9% 1000 ML", "313002", "dudosa", "Se mapea a 9 mg/mL inyectable, pero el concepto no conserva el volumen local de 1000 mL."),
    ]
    rows = []
    for key, description, code, confidence, rationale in specifications:
        concept_id = None
        concept_name = None
        if code:
            found = con.execute("""
                SELECT concept_id, concept_name
                FROM cdm.concept
                WHERE vocabulary_id IN ('RxNorm', 'RxNorm Extension')
                  AND concept_code = ?
                  AND standard_concept = 'S'
                  AND invalid_reason IS NULL
                ORDER BY vocabulary_id = 'RxNorm' DESC
                LIMIT 1
            """, [code]).fetchone()
            if found is None:
                raise RuntimeError(f"No se encontró el RxCUI {code} para {key}")
            concept_id, concept_name = found
        rows.append({
            "clave_local": key,
            "descripcion_local": description,
            "concept_id": concept_id,
            "concept_name": concept_name,
            "confianza": confidence,
            "quien_y_por_que": f"Alejandro García Colorado, revisión manual: {rationale}",
        })
    return pd.DataFrame(rows)


def make_notebook() -> None:
    cells = [
        {"cell_type": "markdown", "metadata": {}, "source": ["# Laboratorio 15 — RxNorm y LOINC\n", "Resumen reproducible de concept sets, unidades y catálogo local."]},
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": [
            "from pathlib import Path\n", "import pandas as pd\n", "from IPython.display import display, Image\n",
            "ROOT = Path.cwd()\n", "if ROOT.name == 'notebooks': ROOT = ROOT.parent.parent\n",
            "A = ROOT / 'lab15/evidencias/analisis'\n", "print(A)"
        ]},
        {"cell_type": "markdown", "metadata": {}, "source": ["## RxNav y productos frecuentes"]},
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": [
            "display(pd.read_csv(A / 'rxnav_tres_medicamentos.csv'))\n",
            "display(pd.read_csv(A / 'top20_productos_ingredientes.csv'))"
        ]},
        {"cell_type": "markdown", "metadata": {}, "source": ["## ATC A10B y definiciones de lisinopril"]},
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": [
            "display(pd.read_csv(A / 'atc_a10b_resumen.csv'))\n",
            "display(pd.read_csv(A / 'lisinopril_impacto.csv'))\n",
            "display(Image(filename=str(ROOT / 'lab15/figuras/impacto_lisinopril.png')))"
        ]},
        {"cell_type": "markdown", "metadata": {}, "source": ["## LOINC, HbA1c y unidades"]},
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": [
            "display(pd.read_csv(A / 'loinc_seis_ejes.csv'))\n",
            "display(pd.read_csv(A / 'hba1c_concept_set.csv'))\n",
            "display(pd.read_csv(A / 'auditoria_unidades.csv'))"
        ]},
        {"cell_type": "markdown", "metadata": {}, "source": ["## Catálogo local"]},
        {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": [
            "catalog = pd.read_csv(ROOT / 'lab15/mapeo_catalogo_local.csv')\n",
            "display(catalog)\n", "display(catalog['confianza'].value_counts())"
        ]},
    ]
    notebook = {
        "cells": cells,
        "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}, "language_info": {"name": "python"}},
        "nbformat": 4, "nbformat_minor": 5,
    }
    path = NB / "analisis_rxnorm_loinc.ipynb"
    path.write_text(json.dumps(notebook, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"OK: {path}")


def main() -> None:
    if not DB.exists():
        raise SystemExit(f"ERROR: no existe {DB}")
    ensure_dirs()
    con = duckdb.connect(str(DB))
    try:
        vocab = con.execute("""
            SELECT c.vocabulary_id, COUNT(*) conceptos,
                   MAX(v.vocabulary_version) vocabulary_version
            FROM cdm.concept c LEFT JOIN cdm.vocabulary v USING (vocabulary_id)
            WHERE c.vocabulary_id IN ('RxNorm','RxNorm Extension','ATC','LOINC','UCUM')
            GROUP BY c.vocabulary_id ORDER BY c.vocabulary_id
        """).df()
        save_csv(vocab, "vocabularios_disponibles.csv")
        versions = dict(zip(vocab.vocabulary_id, vocab.vocabulary_version))
        rxnorm_version = str(versions["RxNorm"])
        atc_version = str(versions["ATC"])
        loinc_version = str(versions["LOINC"])

        rxnav = rxnav_table()
        if not (rxnav.tty == "IN").all():
            raise RuntimeError("Algún concepto de RxNav no es ingrediente (TTY=IN).")
        save_csv(rxnav, "rxnav_tres_medicamentos.csv")

        top20 = con.execute("""
            WITH top AS (
              SELECT drug_concept_id, COUNT(*) exposiciones,
                     COUNT(DISTINCT person_id) pacientes
              FROM cdm.drug_exposure GROUP BY drug_concept_id
              ORDER BY exposiciones DESC LIMIT 20
            ), links AS (
              SELECT t.drug_concept_id, i.concept_id ingredient_id,
                     i.concept_name ingredient_name,
                     ca.min_levels_of_separation
              FROM top t
              JOIN cdm.concept_ancestor ca ON ca.descendant_concept_id=t.drug_concept_id
              JOIN cdm.concept i ON i.concept_id=ca.ancestor_concept_id
              WHERE i.domain_id='Drug' AND i.concept_class_id='Ingredient'
                AND i.standard_concept='S' AND i.invalid_reason IS NULL
            ), agg AS (
              SELECT drug_concept_id, COUNT(DISTINCT ingredient_id) numero_ingredientes,
                     STRING_AGG(DISTINCT CAST(ingredient_id AS VARCHAR)||' — '||ingredient_name,
                                ' | ' ORDER BY CAST(ingredient_id AS VARCHAR)||' — '||ingredient_name) ingredientes,
                     MIN(min_levels_of_separation) separacion_minima
              FROM links GROUP BY drug_concept_id
            )
            SELECT t.drug_concept_id, c.concept_name, c.concept_class_id,
                   t.exposiciones, t.pacientes, a.numero_ingredientes,
                   a.ingredientes, a.separacion_minima
            FROM top t JOIN cdm.concept c ON c.concept_id=t.drug_concept_id
            JOIN agg a USING(drug_concept_id)
            ORDER BY t.exposiciones DESC
        """).df()
        save_csv(top20, "top20_productos_ingredientes.csv")
        top20_summary = pd.DataFrame([{
            "productos_evaluados": len(top20),
            "filas_antes_join": len(top20),
            "filas_ingrediente_despues_join": int(top20.numero_ingredientes.sum()),
            "productos_multingrediente": int((top20.numero_ingredientes > 1).sum()),
            "decision_separacion_cero": "Se incluye para resolver exposiciones codificadas directamente como ingrediente",
        }])
        save_csv(top20_summary, "top20_resumen.csv")

        atc_ingredients = con.execute("""
            WITH root AS (SELECT concept_id FROM cdm.concept
              WHERE vocabulary_id='ATC' AND concept_code='A10B' AND invalid_reason IS NULL)
            SELECT DISTINCT i.concept_id ingredient_concept_id, i.concept_name ingredient_name,
                   i.concept_code
            FROM root r JOIN cdm.concept_ancestor ca ON ca.ancestor_concept_id=r.concept_id
            JOIN cdm.concept i ON i.concept_id=ca.descendant_concept_id
            WHERE i.domain_id='Drug' AND i.concept_class_id='Ingredient'
              AND i.standard_concept='S' AND i.invalid_reason IS NULL
            ORDER BY ingredient_name
        """).df()
        save_csv(atc_ingredients, "atc_a10b_ingredientes.csv")
        atc_summary = con.execute("""
            WITH root AS (SELECT concept_id FROM cdm.concept WHERE vocabulary_id='ATC' AND concept_code='A10B' AND invalid_reason IS NULL),
            ing AS (SELECT DISTINCT i.concept_id FROM root r JOIN cdm.concept_ancestor ca ON ca.ancestor_concept_id=r.concept_id JOIN cdm.concept i ON i.concept_id=ca.descendant_concept_id WHERE i.concept_class_id='Ingredient' AND i.standard_concept='S' AND i.invalid_reason IS NULL),
            sel AS (SELECT DISTINCT de.drug_concept_id FROM cdm.drug_exposure de JOIN cdm.concept_ancestor ca ON ca.descendant_concept_id=de.drug_concept_id JOIN ing i ON i.concept_id=ca.ancestor_concept_id),
            allp AS (SELECT DISTINCT drug_concept_id FROM cdm.drug_exposure WHERE drug_concept_id<>0)
            SELECT (SELECT COUNT(*) FROM ing) ingredientes,
                   (SELECT COUNT(*) FROM sel) productos_en_base,
                   (SELECT COUNT(DISTINCT person_id) FROM cdm.drug_exposure de JOIN sel USING(drug_concept_id)) pacientes,
                   (SELECT COUNT(*) FROM allp) productos_totales,
                   (SELECT COUNT(*) FROM allp a WHERE NOT EXISTS (SELECT 1 FROM sel s WHERE s.drug_concept_id=a.drug_concept_id)) productos_fuera_atc,
                   (SELECT COUNT(DISTINCT person_id) FROM cdm.drug_exposure de WHERE NOT EXISTS (SELECT 1 FROM sel s WHERE s.drug_concept_id=de.drug_concept_id)) pacientes_fuera_atc
        """).df()
        save_csv(atc_summary, "atc_a10b_resumen.csv")

        lis_sql = sql_lisinopril(rxnorm_version)
        (CS / "01_lisinopril.sql").write_text(lis_sql, encoding="utf-8")
        con.execute(lis_sql)
        lis_impact = con.execute("""
            SELECT s.version, COUNT(DISTINCT s.drug_concept_id) conceptos_vocabulario,
                   COUNT(DISTINCT de.drug_concept_id) productos_observados,
                   COUNT(DISTINCT de.person_id) pacientes_distintos,
                   COUNT(de.drug_exposure_id) exposiciones
            FROM results.lab15_lisinopril_sets s
            LEFT JOIN cdm.drug_exposure de ON de.drug_concept_id=s.drug_concept_id
            GROUP BY s.version ORDER BY s.version
        """).df()
        save_csv(lis_impact, "lisinopril_impacto.csv")
        atc_sql = sql_atc(atc_version, len(atc_ingredients))
        (CS / "02_atc_a10b.sql").write_text(atc_sql, encoding="utf-8")
        con.execute(atc_sql)

        hba1c_component = con.execute("""
            WITH comp AS (SELECT concept_id FROM cdm.concept WHERE vocabulary_id='LOINC' AND concept_code='LP286151-8' AND invalid_reason IS NULL)
            SELECT DISTINCT t.concept_id measurement_concept_id, t.concept_code loinc_code,
                   t.concept_name, t.concept_class_id
            FROM comp JOIN cdm.concept_relationship cr ON cr.concept_id_2=comp.concept_id
              AND cr.relationship_id='Has component' AND cr.invalid_reason IS NULL
            JOIN cdm.concept t ON t.concept_id=cr.concept_id_1
            WHERE t.vocabulary_id='LOINC' AND t.domain_id='Measurement'
              AND t.concept_class_id='Lab Test' AND t.standard_concept='S'
              AND t.invalid_reason IS NULL
            ORDER BY t.concept_code
        """).df()
        hba_sql = sql_hba1c(loinc_version, len(hba1c_component))
        (CS / "03_hba1c.sql").write_text(hba_sql, encoding="utf-8")
        con.execute(hba_sql)
        hba1c_set = con.execute("""
            SELECT s.*, COUNT(m.measurement_id) mediciones,
                   COUNT(DISTINCT m.person_id) pacientes,
                   COUNT(DISTINCT m.unit_concept_id) unidades_distintas
            FROM results.lab15_hba1c_set s
            LEFT JOIN cdm.measurement m ON m.measurement_concept_id=s.measurement_concept_id
            GROUP BY ALL ORDER BY mediciones DESC, loinc_code
        """).df()
        save_csv(hba1c_set, "hba1c_concept_set.csv")
        hba_compare = pd.DataFrame([
            {"definicion": "Solo 4548-4", "conceptos": 1,
             "mediciones": int(hba1c_set.loc[hba1c_set.loinc_code == "4548-4", "mediciones"].sum()),
             "pacientes": int(hba1c_set.loc[hba1c_set.loinc_code == "4548-4", "pacientes"].sum())},
            {"definicion": "Concept set por componente", "conceptos": len(hba1c_set),
             "mediciones": int(hba1c_set.mediciones.sum()),
             "pacientes": int(con.execute("SELECT COUNT(DISTINCT m.person_id) FROM cdm.measurement m JOIN results.lab15_hba1c_set s ON s.measurement_concept_id=m.measurement_concept_id").fetchone()[0])},
        ])
        save_csv(hba_compare, "hba1c_comparacion_4548.csv")

        axes = pd.DataFrame([
            {"loinc":"4548-4","component":"Hemoglobin A1c/Hemoglobin.total","property":"MFr","time":"Pt","system":"Bld","scale":"Qn","method":"No especificado","descripcion":"Fracción de masa de HbA1c respecto a hemoglobina total en sangre, cuantitativa y puntual.","fuente":"https://loinc.org/4548-4"},
            {"loinc":"2160-0","component":"Creatinine","property":"MCnc","time":"Pt","system":"Ser/Plas","scale":"Qn","method":"No especificado","descripcion":"Concentración de masa de creatinina en suero o plasma, cuantitativa y puntual.","fuente":"https://loinc.org/2160-0"},
            {"loinc":"2345-7","component":"Glucose","property":"MCnc","time":"Pt","system":"Ser/Plas","scale":"Qn","method":"No especificado","descripcion":"Concentración de masa de glucosa en suero o plasma, cuantitativa y puntual.","fuente":"https://loinc.org/2345-7"},
        ])
        save_csv(axes, "loinc_seis_ejes.csv")

        units = con.execute("""
            SELECT a.concept_code loinc, a.concept_name analito,
                   m.unit_concept_id, COALESCE(u.concept_name,'[nulo/no mapeado]') unidad,
                   u.concept_code codigo_ucum, COUNT(*) mediciones,
                   COUNT(DISTINCT m.person_id) pacientes,
                   ROUND(100.0*COUNT(*) FILTER (WHERE m.unit_concept_id IS NULL OR m.unit_concept_id=0)/COUNT(*),4) porcentaje_unidad_0_nula,
                   MIN(m.value_as_number) minimo, MEDIAN(m.value_as_number) mediana,
                   MAX(m.value_as_number) maximo
            FROM cdm.measurement m JOIN cdm.concept a ON a.concept_id=m.measurement_concept_id
            LEFT JOIN cdm.concept u ON u.concept_id=m.unit_concept_id
            WHERE a.vocabulary_id='LOINC' AND a.concept_code IN ('4548-4','2160-0','2345-7')
            GROUP BY a.concept_code,a.concept_name,m.unit_concept_id,u.concept_name,u.concept_code
            ORDER BY a.concept_code,mediciones DESC
        """).df()
        save_csv(units, "auditoria_unidades.csv")

        fig, ax = plt.subplots(figsize=(8,5))
        labels = ["A — monoterapia","B — todo lisinopril","C — sin HCTZ"]
        bars = ax.bar(labels, lis_impact.pacientes_distintos, color=["#2563eb","#f59e0b","#059669"])
        ax.set_ylabel("Pacientes distintos"); ax.set_title("Impacto de tres definiciones de exposición a lisinopril")
        ax.set_ylim(0, lis_impact.pacientes_distintos.max()*1.18); ax.grid(axis="y",alpha=.25)
        for bar, value in zip(bars, lis_impact.pacientes_distintos):
            ax.text(bar.get_x()+bar.get_width()/2, value+12, str(int(value)), ha="center")
        fig.tight_layout(); fig.savefig(FIG/"impacto_lisinopril.png",dpi=180); plt.close(fig)

        for code, short in [("4548-4","hba1c"),("2160-0","creatinina"),("2345-7","glucosa")]:
            data = con.execute("""
                SELECT m.value_as_number, COALESCE(u.concept_name,'[nulo/no mapeado]') unidad
                FROM cdm.measurement m JOIN cdm.concept a ON a.concept_id=m.measurement_concept_id
                LEFT JOIN cdm.concept u ON u.concept_id=m.unit_concept_id
                WHERE a.vocabulary_id='LOINC' AND a.concept_code=? AND m.value_as_number IS NOT NULL
            """,[code]).df()
            fig, ax = plt.subplots(figsize=(8,5))
            for unit, group in data.groupby("unidad"):
                ax.hist(group.value_as_number,bins=35,alpha=.7,label=unit,edgecolor="white")
            ax.set_title(f"{short.capitalize()}: distribución separada por unidad")
            ax.set_xlabel("value_as_number"); ax.set_ylabel("Frecuencia"); ax.legend(); fig.tight_layout()
            fig.savefig(FIG/f"histograma_{short}_por_unidad.png",dpi=180); plt.close(fig)

        catalog = catalog_rows(con)
        catalog.to_csv(LAB/"mapeo_catalogo_local.csv",index=False)
        print(f"OK: {LAB/'mapeo_catalogo_local.csv'} ({len(catalog)} filas)")
        catalog_summary = catalog.confianza.value_counts().rename_axis("confianza").reset_index(name="filas")
        catalog_summary["porcentaje"] = (100*catalog_summary.filas/len(catalog)).round(2)
        save_csv(catalog_summary,"mapeo_catalogo_resumen.csv")

        verdicts = pd.DataFrame([
            {"loinc":"4548-4","analito":"HbA1c","veredicto":"Sí, en esta base: todas las mediciones usan %. No mezclar con mmol/mol IFCC sin conversión."},
            {"loinc":"2160-0","analito":"Creatinina","veredicto":"Sí, en esta base: todas usan mg/dL. No mezclar con µmol/L; el factor aproximado es 88.4."},
            {"loinc":"2345-7","analito":"Glucosa","veredicto":"Sí, en esta base: todas usan mg/dL. Convertir mmol/L antes de combinar si apareciera."},
        ])
        save_csv(verdicts,"veredictos_unidades.csv")
        audit_md = f"""# Auditoría de unidades

## Resultados cuantitativos

{markdown_table(units)}

## Veredicto por analito

{markdown_table(verdicts)}

Los histogramas se generaron separados por `unit_concept_id`. En esta base cada analito presenta una sola unidad y 0% de unidades nulas o no mapeadas, por lo que sus valores pueden resumirse dentro de cada analito tal como están. Esta limpieza no debe generalizarse a una base real.

## Figuras

- `figuras/histograma_hba1c_por_unidad.png`
- `figuras/histograma_creatinina_por_unidad.png`
- `figuras/histograma_glucosa_por_unidad.png`

## Fuentes

- [LOINC 4548-4](https://loinc.org/4548-4)
- [LOINC 2160-0](https://loinc.org/2160-0)
- [LOINC 2345-7](https://loinc.org/2345-7)
"""
        (LAB/"auditoria_unidades.md").write_text(audit_md,encoding="utf-8")

        limitation = "RxNorm Extension no estaba presente; los 331 productos observados sí resolvieron a ingredientes RxNorm estándar."
        readme = f"""# Laboratorio 15 — Concept sets de medicamentos y laboratorios

## Propósito

Construir concept sets reutilizables de exposición farmacológica y HbA1c, auditar unidades y mapear un catálogo local mexicano sin ocultar ambigüedad.

## Decisiones principales

- Se eligió **lisinopril** para A/B/C porque metformina solo tenía una presentación observada.
- La versión final para un estudio renal es **C — lisinopril sin combinaciones con hidroclorotiazida**.
- HbA1c se construyó mediante `Has component` con `LP286151-8`, excluyendo dispositivos, paneles, metas clínicas y glucosa estimada.
- {limitation}

## Resultados

- Top 20: {int((top20.numero_ingredientes>1).sum())} productos con múltiples ingredientes.
- A10B: {int(atc_summary.iloc[0].ingredientes)} ingredientes, {int(atc_summary.iloc[0].productos_en_base)} productos y {int(atc_summary.iloc[0].pacientes)} pacientes.
- Fuera de A10B: {int(atc_summary.iloc[0].productos_fuera_atc)} de {int(atc_summary.iloc[0].productos_totales)} productos observados.
- Lisinopril A/B/C: {', '.join(str(int(x)) for x in lis_impact.pacientes_distintos)} pacientes.
- Catálogo local: 15 filas; 80% con confianza alta, una dudosa y dos no mapeables.

## Archivos

- `concept_sets/01_lisinopril.sql`
- `concept_sets/02_atc_a10b.sql`
- `concept_sets/03_hba1c.sql`
- `mapeo_catalogo_local.csv`
- `auditoria_unidades.md`
- `notebooks/analisis_rxnorm_loinc.ipynb`
- `evidencias/analisis/*.csv`
- `figuras/*.png`

## Reproducibilidad

```bash
python lab15/scripts/01_generar_lab15.py
```

Vocabularios: {rxnorm_version}, {atc_version}, {loinc_version}, UCUM {versions['UCUM']}. Fecha de consulta: {TODAY}.

Fuentes: [RxNav](https://mor.nlm.nih.gov/RxNav/), [LOINC](https://loinc.org/), [Compendio Nacional de Insumos para la Salud](https://www.gob.mx/csg/articulos/compendio-nacional-de-insumos-para-la-salud-367182).
"""
        (LAB/"README.md").write_text(readme,encoding="utf-8")
        make_notebook()

        # Comprobaciones internas.
        if len(top20)!=20 or int((top20.numero_ingredientes>1).sum())!=3: raise RuntimeError("Top 20 inesperado")
        if tuple(atc_summary.iloc[0][["ingredientes","productos_en_base","pacientes","productos_fuera_atc"]].astype(int))!=(42,2,246,329): raise RuntimeError("A10B inesperado")
        if lis_impact.conceptos_vocabulario.astype(int).tolist()!=[53,77,53]: raise RuntimeError("Membresía de lisinopril inesperada")
        if lis_impact.pacientes_distintos.astype(int).tolist()!=[1014,1024,1014]: raise RuntimeError("Impacto de lisinopril inesperado")
        if len(hba1c_set)<5 or "4548-4" not in set(hba1c_set.loinc_code): raise RuntimeError("Concept set HbA1c insuficiente")
        if len(catalog)!=15 or (catalog.confianza=="alta").sum()!=12: raise RuntimeError("Catálogo local inesperado")
        if not (units.porcentaje_unidad_0_nula==0).all(): raise RuntimeError("Unidades nulas inesperadas")
    finally:
        con.close()

    print("\n===== LABORATORIO 15 GENERADO =====")
    print("Fármaco final: lisinopril, versión C sin HCTZ")
    print("Analito: HbA1c por componente LOINC")
    print("Commit y push: NO ejecutados")


if __name__ == "__main__":
    main()

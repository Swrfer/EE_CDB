#!/usr/bin/env python3
"""Validación formal del Laboratorio 14. No modifica Git ni la base OMOP."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import duckdb
import pandas as pd


ROOT = Path.cwd()
LAB = ROOT / "lab14"
A = LAB / "evidencias/analisis"
DB = ROOT / "lab12/data/omop/synthea_omop_cdm54.duckdb"
EXPECTED_BRANCH = "lab14-concept-set"
checks = 0


def passed(message: str) -> None:
    global checks
    checks += 1
    print(f"PASS: {message}")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")
    passed(message)


def read_csv(name: str) -> pd.DataFrame:
    path = A / name
    require(path.is_file(), str(path))
    return pd.read_csv(path)


print("===== VALIDACIÓN FORMAL DEL LABORATORIO 14 =====")

print("\n1. Rama")
branch = subprocess.check_output(
    ["git", "branch", "--show-current"], cwd=ROOT, text=True
).strip()
require(branch == EXPECTED_BRANCH, f"rama = {branch}")

print("\n2. Archivos obligatorios")
required = [
    LAB / "README.md",
    LAB / "concept_set.sql",
    LAB / "justificacion_concept_set.md",
    LAB / "figuras/impacto_pacientes.png",
    LAB / "notebooks/analisis_concept_set.ipynb",
    LAB / "scripts/01_generar_lab14.py",
    LAB / "scripts/02_validar_lab14.py",
]
for path in required:
    require(path.is_file() and path.stat().st_size > 0, str(path))

print("\n3. Notebook")
notebook_path = LAB / "notebooks/analisis_concept_set.ipynb"
notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
code_cells = [c for c in notebook["cells"] if c["cell_type"] == "code"]
require(len(code_cells) == 5, f"celdas de código = {len(code_cells)}")
require(all(c.get("execution_count") is not None for c in code_cells),
        "todas las celdas de código fueron ejecutadas")
errors = [
    output
    for cell in code_cells
    for output in cell.get("outputs", [])
    if output.get("output_type") == "error"
]
require(not errors, "notebook sin salidas de error")
require(all("id" in c for c in notebook["cells"]), "todas las celdas tienen identificador")

print("\n4. Selección y concepto semilla")
choice = read_csv("seleccion_condicion.csv")
gastric = choice[choice.concept_id == 196044].iloc[0]
t2dm = choice[choice.concept_id == 201826].iloc[0]
require(int(gastric.pacientes) == 2, "cáncer gástrico descartado con 2 pacientes")
require(int(t2dm.pacientes) == 457, "diabetes tipo 2 seleccionada con 457 pacientes")
seed = read_csv("concepto_semilla.csv")
s = seed.iloc[0]
require(int(s.concept_id) == 201826, "concept_id semilla = 201826")
require(s.concept_name == "Type 2 diabetes mellitus", "nombre legible de la semilla")
require(s.domain_id == "Condition", "dominio de la semilla = Condition")
require(s.vocabulary_id == "SNOMED", "vocabulario de la semilla = SNOMED")
require(s.concept_class_id == "Disorder", "clase de la semilla = Disorder")
require(s.standard_concept == "S", "semilla estándar")
require(pd.isna(s.invalid_reason), "semilla vigente")

print("\n5. Jerarquía")
parent = read_csv("padre_inmediato.csv")
require(len(parent) == 1 and int(parent.iloc[0].concept_id) == 201820,
        "padre inmediato = Diabetes mellitus (201820)")
hierarchy = read_csv("resumen_jerarquia.csv").iloc[0]
require(int(hierarchy.descendientes_sin_semilla) == 14, "14 descendientes sin la semilla")
require(int(hierarchy.conceptos_version_amplia) == 15, "15 conceptos en la versión amplia")
require(int(hierarchy.profundidad_maxima) == 2, "profundidad máxima = 2")

print("\n6. Traducción ICD-10-CM")
mapping = read_csv("icd10_mapeo.csv")
cardinality = read_csv("icd10_cardinalidad.csv")
mapping_summary = read_csv("icd10_resumen.csv").iloc[0]
require(len(cardinality) == 12, "12 códigos ICD-10-CM evaluados")
require(len(mapping) == 23, "23 filas después del join Maps to")
require(int(mapping_summary.sin_mapeo) == 0, "ningún código sin mapeo")
require(int(mapping_summary.mapeo_1_a_1) == 1, "un código con mapeo 1:1")
require(int(mapping_summary.mapeo_1_a_N) == 11, "once códigos con mapeo 1:N")
require(mapping.concept_id_estandar.notna().all(), "todos los destinos tienen concept_id")
require(mapping.nombre_estandar.notna().all(), "todos los destinos tienen nombre legible")
require((mapping.standard_concept == "S").all(), "todos los destinos son estándar")
require((mapping.relationship_id == "Maps to").all(), "relación correcta = Maps to")

print("\n7. Versiones del concept set")
membership = read_csv("concept_set_membresia.csv")
counts = membership.groupby("version").concept_id.nunique().to_dict()
require(counts == {"A_estricta": 1, "B_amplia": 15, "C_razonada": 12},
        "membresía A=1, B=15 y C=12")
require(len(membership) == 28, "28 filas de membresía en total")
for version in counts:
    require(
        membership.loc[membership.version == version, "concept_name"].notna().all(),
        f"{version} incluye nombres legibles",
    )
require(
    201826 in set(membership.loc[membership.version == "A_estricta", "concept_id"]),
    "versión A contiene la semilla",
)
excluded_ids = {4129519, 43531010, 45766052}
c_ids = set(membership.loc[membership.version == "C_razonada", "concept_id"])
require(not (excluded_ids & c_ids), "versión C elimina embarazo y remisión")

print("\n8. Revisión clínica")
review = read_csv("revision_descendientes.csv")
exclusions = read_csv("exclusiones.csv")
require(len(review) == 14, "se revisaron todos los 14 descendientes disponibles")
require(review.concept_id.nunique() == 14, "revisión sin conceptos duplicados")
require(review.justificacion_clinica.str.len().gt(30).all(), "cada decisión tiene justificación clínica")
require(set(exclusions.concept_id.astype(int)) == excluded_ids, "tres exclusiones clínicas esperadas")
require((exclusions.incluido == "No").all(), "exclusiones marcadas como no incluidas")
require(review.metodo_revision.str.contains("exhaustiva", case=False).all(),
        "se documentó por qué no se muestrearon 20 conceptos")

print("\n9. Impacto en pacientes")
impact = read_csv("impacto_pacientes.csv")
require(len(impact) == 3, "tres versiones comparadas")
require((impact.pacientes_distintos == 457).all(), "457 pacientes distintos en A, B y C")
require((impact.diferencia_pacientes_vs_A == 0).all(), "diferencia absoluta frente a A = 0")
require((impact.diferencia_porcentual_vs_A == 0).all(), "diferencia porcentual frente a A = 0%")
require((impact.eventos == 457).all(), "457 eventos en cada versión")

print("\n10. SQL reproducible")
sql = (LAB / "concept_set.sql").read_text(encoding="utf-8")
sql_lower = sql.lower()
require("concept_ancestor" in sql_lower, "versiones construidas con CONCEPT_ANCESTOR")
require("relationship_id = 'maps to'" in sql_lower, "traducción usa Maps to")
require("cr.concept_id_1 = src.concept_id" in sql_lower, "dirección de Maps to explícita")
require("tgt.standard_concept = 's'" in sql_lower, "destino estándar filtrado")
require("cr.invalid_reason is null" in sql_lower, "vigencia de la relación filtrada")
require("src.invalid_reason is null" in sql_lower and "tgt.invalid_reason is null" in sql_lower,
        "vigencia de conceptos filtrada")
require(sql_lower.count("current_date between") >= 3, "fechas de vigencia verificadas")
require("count(distinct co.person_id)" in sql_lower, "impacto usa pacientes distintos")
require("exclusion_roots" in sql_lower, "versión C usa raíces de exclusión reproducibles")

print("\n11. Documentación clínica")
justification = (LAB / "justificacion_concept_set.md").read_text(encoding="utf-8").lower()
readme = (LAB / "README.md").read_text(encoding="utf-8").lower()
require("sensibilidad" in justification, "discusión de sensibilidad")
require("valor predictivo positivo" in justification, "discusión de VPP")
require("embarazo" in justification and "remisión" in justification,
        "exclusiones explicadas clínicamente")
require("solo 14" in readme or "solo 14" in justification,
        "limitación de menos de 20 descendientes documentada")
require("no significa que las definiciones sean equivalentes" in justification,
        "igualdad de pacientes interpretada correctamente")
require("athena" in justification and "omop cdm v5.4" in justification,
        "fuentes de vocabulario documentadas")

print("\n12. Figura")
figure = LAB / "figuras/impacto_pacientes.png"
signature = figure.read_bytes()[:8]
require(signature == b"\x89PNG\r\n\x1a\n", "figura con formato PNG válido")
require(figure.stat().st_size > 10_000, "figura no vacía")

print("\n13. Tablas derivadas en DuckDB")
con = duckdb.connect(str(DB), read_only=True)
try:
    tables = {
        r[0]
        for r in con.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'results'
        """).fetchall()
    }
    require("lab14_icd10_mapping" in tables, "results.lab14_icd10_mapping disponible")
    require("lab14_concept_set_membership" in tables,
            "results.lab14_concept_set_membership disponible")
    require("lab14_impact" in tables, "results.lab14_impact disponible")
    db_counts = dict(con.execute("""
        SELECT version, COUNT(DISTINCT concept_id)
        FROM results.lab14_concept_set_membership
        GROUP BY version
    """).fetchall())
    require(db_counts == counts, "DuckDB y CSV tienen la misma membresía")
    db_impact = con.execute("""
        SELECT COUNT(*), MIN(pacientes_distintos), MAX(pacientes_distintos)
        FROM results.lab14_impact
    """).fetchone()
    require(db_impact == (3, 457, 457), "DuckDB conserva el impacto esperado")
finally:
    con.close()

print("\n14. Archivos no deseados")
unwanted = [
    p for p in LAB.rglob("*")
    if p.is_file() and (
        p.name == ".DS_Store"
        or p.suffix in {".pyc", ".duckdb", ".zip"}
        or "__pycache__" in p.parts
    )
]
require(not unwanted, "sin cachés, bases, ZIP ni archivos del sistema")
large = [p for p in LAB.rglob("*") if p.is_file() and p.stat().st_size > 10 * 1024 * 1024]
require(not large, "sin archivos mayores de 10 MB")

print("\n===== RESULTADO FINAL =====")
print(f"PASS: {checks} comprobaciones superadas")
print("Commit y push: NO ejecutados")

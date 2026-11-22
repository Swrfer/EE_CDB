#!/usr/bin/env python3
"""Validación formal del Laboratorio 15. No ejecuta operaciones Git."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import duckdb
import pandas as pd


ROOT = Path.cwd()
LAB = ROOT / "lab15"
A = LAB / "evidencias/analisis"
DB = ROOT / "lab12/data/omop/synthea_omop_cdm54.duckdb"
checks = 0


def require(condition: bool, message: str) -> None:
    global checks
    if not condition:
        raise SystemExit(f"FAIL: {message}")
    checks += 1
    print(f"PASS: {message}")


def csv(name: str) -> pd.DataFrame:
    path = A / name
    require(path.is_file() and path.stat().st_size > 0, str(path))
    return pd.read_csv(path)


print("===== VALIDACIÓN FORMAL DEL LABORATORIO 15 =====")

print("\n1. Rama")
branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip()
require(branch == "lab15-rxnorm-loinc", f"rama = {branch}")

print("\n2. Archivos obligatorios")
required = [
    LAB / "README.md",
    LAB / "auditoria_unidades.md",
    LAB / "mapeo_catalogo_local.csv",
    LAB / "concept_sets/01_lisinopril.sql",
    LAB / "concept_sets/02_atc_a10b.sql",
    LAB / "concept_sets/03_hba1c.sql",
    LAB / "figuras/impacto_lisinopril.png",
    LAB / "figuras/histograma_hba1c_por_unidad.png",
    LAB / "figuras/histograma_creatinina_por_unidad.png",
    LAB / "figuras/histograma_glucosa_por_unidad.png",
    LAB / "notebooks/analisis_rxnorm_loinc.ipynb",
    LAB / "scripts/00_auditar_lab15.py",
    LAB / "scripts/00b_auditar_lab15.py",
    LAB / "scripts/01_generar_lab15.py",
    LAB / "scripts/02_validar_lab15.py",
]
for path in required:
    require(path.is_file() and path.stat().st_size > 0, str(path))

print("\n3. Notebook")
notebook = json.loads((LAB / "notebooks/analisis_rxnorm_loinc.ipynb").read_text(encoding="utf-8"))
code_cells = [cell for cell in notebook["cells"] if cell["cell_type"] == "code"]
require(len(code_cells) == 5, f"celdas de código = {len(code_cells)}")
require(all(cell.get("execution_count") is not None for cell in code_cells), "todas las celdas fueron ejecutadas")
errors = [out for cell in code_cells for out in cell.get("outputs", []) if out.get("output_type") == "error"]
require(not errors, "notebook sin errores")
require(all("id" in cell for cell in notebook["cells"]), "todas las celdas tienen identificador")

print("\n4. Vocabularios")
vocab = csv("vocabularios_disponibles.csv")
require(set(vocab.vocabulary_id) == {"ATC", "LOINC", "RxNorm", "UCUM"}, "cuatro vocabularios disponibles identificados")
require("RxNorm Extension" not in set(vocab.vocabulary_id), "ausencia de RxNorm Extension identificada")
readme = (LAB / "README.md").read_text(encoding="utf-8")
require("RxNorm Extension no estaba presente" in readme, "limitación de RxNorm Extension documentada")
require("331 productos observados" in readme, "impacto de la ausencia del vocabulario cuantificado")

print("\n5. RxNav")
rxnav = csv("rxnav_tres_medicamentos.csv")
require(len(rxnav) == 3, "tres ingredientes consultados en RxNav")
require(set(rxnav.medicamento) == {"metformin", "lisinopril", "cisplatin"}, "medicamentos RxNav esperados")
require((rxnav.tty == "IN").all(), "los tres conceptos tienen TTY = IN")
expected_rxnav = {
    "metformin": ("6809", 21, 14),
    "lisinopril": ("29046", 3, 4),
    "cisplatin": ("2555", 2, 0),
}
for row in rxnav.itertuples(index=False):
    expected = expected_rxnav[row.medicamento]
    require(str(row.rxcui) == expected[0], f"RxCUI correcto para {row.medicamento}")
    require(int(row.formas_clinicas_scdf) == expected[1], f"SCDF correcto para {row.medicamento}")
    require(int(row.nombres_marca_bn) == expected[2], f"BN correcto para {row.medicamento}")
require((rxnav.fecha_consulta.astype(str) == "2026-11-22").all(), "fecha de consulta RxNav documentada")

print("\n6. Productos e ingredientes")
top20 = csv("top20_productos_ingredientes.csv")
top_summary = csv("top20_resumen.csv").iloc[0]
require(len(top20) == 20, "20 productos frecuentes evaluados")
require(top20.drug_concept_id.nunique() == 20, "productos frecuentes sin duplicados")
require((top20.numero_ingredientes >= 1).all(), "todos los productos resueltos a ingrediente")
require(top20.ingredientes.notna().all(), "ingredientes con nombres legibles")
require(int((top20.numero_ingredientes > 1).sum()) == 3, "tres productos con múltiples ingredientes")
require(int(top_summary.filas_antes_join) == 20, "20 filas antes del join")
require(int(top_summary.filas_ingrediente_despues_join) == 23, "23 relaciones producto-ingrediente después del join")
require("se incluye" in str(top_summary.decision_separacion_cero).lower(), "decisión sobre separación cero documentada")

print("\n7. ATC A10B")
atc_ing = csv("atc_a10b_ingredientes.csv")
atc = csv("atc_a10b_resumen.csv").iloc[0]
require(len(atc_ing) == 42, "42 ingredientes derivados de A10B")
require(atc_ing.ingredient_concept_id.nunique() == 42, "ingredientes A10B sin duplicados")
require(atc_ing.ingredient_name.notna().all(), "ingredientes A10B con nombres legibles")
require(int(atc.productos_en_base) == 2, "dos productos A10B observados")
require(int(atc.pacientes) == 246, "246 pacientes expuestos a A10B")
require(int(atc.productos_totales) == 331, "331 productos totales observados")
require(int(atc.productos_fuera_atc) == 329, "329 productos fuera de A10B")
require(int(atc.pacientes_fuera_atc) == 5461, "5461 pacientes con productos fuera de A10B")

print("\n8. Definiciones de lisinopril")
lis = csv("lisinopril_impacto.csv")
require(lis.version.tolist() == ["A_monoterapia", "B_todo_lisinopril", "C_sin_hctz"], "versiones A/B/C ordenadas")
require(lis.conceptos_vocabulario.astype(int).tolist() == [53, 77, 53], "conceptos A/B/C = 53/77/53")
require(lis.productos_observados.astype(int).tolist() == [5, 8, 5], "productos observados A/B/C = 5/8/5")
require(lis.pacientes_distintos.astype(int).tolist() == [1014, 1024, 1014], "pacientes A/B/C = 1014/1024/1014")
require(lis.exposiciones.astype(int).tolist() == [26178, 26195, 26178], "exposiciones A/B/C consistentes")
lis_sql = (LAB / "concept_sets/01_lisinopril.sql").read_text(encoding="utf-8")
require("CONCEPT_ANCESTOR".lower() in lis_sql.lower(), "lisinopril construido por jerarquía")
require("hydrochlorothiazide" in lis_sql.lower(), "exclusión de HCTZ explícita")
require("A=53, B=77, C=53" in lis_sql, "encabezado SQL con conteos finales")
require("RxNorm 20260601" in lis_sql and "2026-11-22" in lis_sql, "versión y fecha RxNorm en encabezado")

print("\n9. LOINC y concept set HbA1c")
axes = csv("loinc_seis_ejes.csv")
require(len(axes) == 3, "tres códigos LOINC descompuestos")
require(set(axes.loinc) == {"4548-4", "2160-0", "2345-7"}, "códigos LOINC esperados")
require(axes[["component", "property", "time", "system", "scale", "method"]].notna().all().all(), "seis ejes completos")
require((axes.descripcion.str.len() > 40).all(), "descripción clínica para cada código")
require(axes.fuente.str.startswith("https://loinc.org/").all(), "fuente oficial para cada LOINC")
hba = csv("hba1c_concept_set.csv")
require(len(hba) == 7, "concept set HbA1c con siete códigos")
require("4548-4" in set(hba.loinc_code), "4548-4 incluido")
require(hba.measurement_concept_id.nunique() == 7, "concept set HbA1c sin duplicados")
require(hba.concept_name.str.contains("Hemoglobin A1c", case=False).all(), "todos representan HbA1c")
for forbidden in ["device", "panel", "goal", "glucose mean"]:
    require(not hba.concept_name.str.contains(forbidden, case=False).any(), f"HbA1c excluye {forbidden}")
require(hba.concept_name.str.contains("HPLC", case=False).any(), "incluye variante HPLC")
require(hba.concept_name.str.contains("Electrophoresis", case=False).any(), "incluye variante por electroforesis")
compare = csv("hba1c_comparacion_4548.csv")
require(compare.conceptos.astype(int).tolist() == [1, 7], "comparación de 1 frente a 7 códigos")
require(compare.mediciones.astype(int).tolist() == [46481, 46481], "46481 mediciones en ambas definiciones")
require(compare.pacientes.astype(int).tolist() == [2462, 2462], "2462 pacientes en ambas definiciones")
hba_sql = (LAB / "concept_sets/03_hba1c.sql").read_text(encoding="utf-8")
require("Has component" in hba_sql and "LP286151-8" in hba_sql, "HbA1c construido por componente LOINC")
require("LOINC 2.82" in hba_sql and "2026-11-22" in hba_sql, "versión y fecha LOINC en encabezado")
require("Devuelve 7 conceptos" in hba_sql, "encabezado HbA1c con conteo")

print("\n10. Auditoría de unidades")
units = csv("auditoria_unidades.csv")
verdicts = csv("veredictos_unidades.csv")
require(len(units) == 3, "tres combinaciones analito-unidad observadas")
require((units.porcentaje_unidad_0_nula == 0).all(), "0% de unidades nulas o no mapeadas")
require(units.codigo_ucum.notna().all(), "todas las unidades tienen código UCUM")
require(set(units.codigo_ucum) == {"%", "mg/dL"}, "unidades observadas = % y mg/dL")
require(len(verdicts) == 3, "un veredicto por analito")
require(verdicts.veredicto.str.len().gt(60).all(), "veredictos de unidades razonados")
audit_md = (LAB / "auditoria_unidades.md").read_text(encoding="utf-8")
require("0% de unidades nulas" in audit_md, "porcentaje de unidades faltantes documentado")
require("88.4" in audit_md, "factor de creatinina documentado")

print("\n11. Catálogo local")
catalog = pd.read_csv(LAB / "mapeo_catalogo_local.csv")
require(len(catalog) == 15, "catálogo local con 15 filas")
require(catalog.clave_local.nunique() == 15, "claves locales únicas")
require((catalog.confianza == "alta").sum() == 12, "12 mapeos de confianza alta")
require((catalog.confianza == "dudosa").sum() == 1, "un mapeo dudoso")
require((catalog.confianza == "no mapeable").sum() == 2, "dos filas no mapeables")
high = catalog[catalog.confianza == "alta"]
require(high.concept_id.notna().all() and high.concept_name.notna().all(), "mapeos altos con concepto y nombre")
unmapped = catalog[catalog.confianza == "no mapeable"]
require(unmapped.concept_id.isna().all() and unmapped.concept_name.isna().all(), "no mapeables sin concepto forzado")
require(catalog.descripcion_local.str.contains("HCTZ", case=False).any(), "incluye abreviatura HCTZ")
require(catalog.descripcion_local.str.contains("TMP/SMX", case=False).any(), "incluye combinación abreviada")
require(catalog.descripcion_local.str.contains("AMPOLLETA IV", case=False).any(), "incluye presentación inexistente")
require(catalog.descripcion_local.str.contains("GASA", case=False).any(), "incluye material no farmacológico")
require(catalog.quien_y_por_que.str.contains("Alejandro García Colorado").all(), "responsable de cada decisión documentado")
require(catalog.quien_y_por_que.str.len().gt(60).all(), "razón documentada para cada mapeo")

print("\n12. Encabezados y reproducibilidad SQL")
for filename in ["01_lisinopril.sql", "02_atc_a10b.sql", "03_hba1c.sql"]:
    text = (LAB / "concept_sets" / filename).read_text(encoding="utf-8")
    require("Vocabulario:" in text, f"{filename} declara vocabulario")
    require("consulta: 2026-11-22" in text, f"{filename} declara fecha")
    require("CREATE OR REPLACE TABLE results." in text, f"{filename} es ejecutable")
atc_sql = (LAB / "concept_sets/02_atc_a10b.sql").read_text(encoding="utf-8")
require("Devuelve 42 ingredientes" in atc_sql, "encabezado ATC con conteo")
require("CONCEPT_ANCESTOR".lower() in atc_sql.lower(), "ATC construido por jerarquía")

print("\n13. Figuras")
figures = [
    LAB / "figuras/impacto_lisinopril.png",
    LAB / "figuras/histograma_hba1c_por_unidad.png",
    LAB / "figuras/histograma_creatinina_por_unidad.png",
    LAB / "figuras/histograma_glucosa_por_unidad.png",
]
for figure in figures:
    require(figure.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n", f"PNG válido: {figure.name}")
    require(figure.stat().st_size > 10_000, f"figura no vacía: {figure.name}")

print("\n14. Tablas derivadas en DuckDB")
con = duckdb.connect(str(DB), read_only=True)
try:
    tables = {row[0] for row in con.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='results'").fetchall()}
    expected_tables = {
        "lab15_lisinopril_sets", "lab15_atc_a10b_ingredients",
        "lab15_atc_a10b_products_observed", "lab15_hba1c_set",
    }
    require(expected_tables.issubset(tables), "cuatro tablas lab15 disponibles en results")
    db_lis = dict(con.execute("SELECT version, COUNT(DISTINCT drug_concept_id) FROM results.lab15_lisinopril_sets GROUP BY version").fetchall())
    require(db_lis == {"A_monoterapia": 53, "B_todo_lisinopril": 77, "C_sin_hctz": 53}, "membresía de lisinopril coincide con CSV")
    require(con.execute("SELECT COUNT(*) FROM results.lab15_atc_a10b_ingredients").fetchone()[0] == 42, "42 ingredientes A10B en DuckDB")
    require(con.execute("SELECT COUNT(*) FROM results.lab15_hba1c_set").fetchone()[0] == 7, "siete códigos HbA1c en DuckDB")
finally:
    con.close()

print("\n15. Archivos no deseados")
unwanted = [p for p in LAB.rglob("*") if p.is_file() and (p.name == ".DS_Store" or p.suffix in {".pyc", ".duckdb", ".db", ".sqlite", ".zip"} or "__pycache__" in p.parts)]
require(not unwanted, "sin bases, ZIP, cachés ni archivos del sistema")
large = [p for p in LAB.rglob("*") if p.is_file() and p.stat().st_size > 10 * 1024 * 1024]
require(not large, "sin archivos mayores de 10 MB")

print("\n===== RESULTADO FINAL =====")
print(f"PASS: {checks} comprobaciones superadas")
print("Commit y push: NO ejecutados")

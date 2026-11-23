#!/usr/bin/env python3
"""Validación formal del Laboratorio 16. No modifica Git."""

from __future__ import annotations

import py_compile
import re
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path

import duckdb
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
LAB = ROOT / "lab16"
ANALYSIS = LAB / "evidencias" / "analisis"
DB = ROOT / "lab12" / "data" / "omop" / "synthea_omop_cdm54.duckdb"
EXPECTED_BRANCH = "lab16-hierarchies"
checks = 0


def passed(message: str) -> None:
    global checks
    checks += 1
    print(f"PASS: {message}")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    passed(message)


def read_csv(name: str) -> pd.DataFrame:
    path = ANALYSIS / name
    require(path.is_file(), str(path))
    return pd.read_csv(path)


def contains(text: str, pattern: str, message: str) -> None:
    require(re.search(pattern, text, re.IGNORECASE | re.DOTALL) is not None, message)


def main() -> None:
    print("===== VALIDACIÓN FORMAL DEL LABORATORIO 16 =====")

    print("\n1. Rama")
    branch = subprocess.check_output(
        ["git", "branch", "--show-current"], cwd=ROOT, text=True
    ).strip()
    require(branch == EXPECTED_BRANCH, f"rama = {EXPECTED_BRANCH}")

    print("\n2. Archivos obligatorios")
    mandatory = [
        LAB / "README.md",
        LAB / "jerarquias.sql",
        LAB / "hallazgos.md",
        LAB / "tiempos.md",
        LAB / "scripts" / "00_auditar_lab16.py",
        LAB / "scripts" / "01_generar_lab16.py",
        LAB / "scripts" / "02_validar_lab16.py",
        ANALYSIS / "01_camino_recursivo.csv",
        ANALYSIS / "03_comparacion_ancestros.csv",
        ANALYSIS / "05b_cinco_relaciones_explicadas.csv",
        ANALYSIS / "07_polijerarquia_caminos.csv",
        ANALYSIS / "07b_dos_caminos_representativos.csv",
        ANALYSIS / "08_conteos_solapamiento.csv",
        ANALYSIS / "09_trazabilidad_tres_pacientes.csv",
        ANALYSIS / "12_conceptos_retirados_efecto.csv",
        ANALYSIS / "13_rendimiento_tres_corridas.csv",
        ANALYSIS / "14_plan_subconsulta.txt",
        ANALYSIS / "15_plan_materializado.txt",
    ]
    for path in mandatory:
        require(path.is_file() and path.stat().st_size > 0, str(path))

    print("\n3. Sintaxis Python")
    with tempfile.TemporaryDirectory(prefix="lab16_pycompile_") as temp_dir:
        temp_path = Path(temp_dir)
        for script in sorted((LAB / "scripts").glob("*.py")):
            compiled = temp_path / f"{script.stem}.pyc"
            py_compile.compile(str(script), cfile=str(compiled), doraise=True)
            passed(f"sintaxis correcta: {script.name}")

    print("\n4. Recursiva y CONCEPT_ANCESTOR")
    recursive = read_csv("01_camino_recursivo.csv")
    comparison = read_csv("03_comparacion_ancestros.csv")
    root = read_csv("03b_raiz_tecnica_snomed.csv")
    require(recursive.nivel.max() == 7, "profundidad recursiva máxima = 7")
    require(recursive.concept_id.nunique() == 10, "10 conceptos incluyendo semilla y raíz")
    row = comparison.iloc[0]
    require(int(row.ancestros_recursiva) == 9, "9 ancestros en la recursiva")
    require(int(row.ancestros_concept_ancestor) == 8, "8 ancestros en CONCEPT_ANCESTOR")
    require(int(row.interseccion) == 8, "los ocho ancestros clínicos coinciden")
    require(int(row.solo_recursiva) == 1, "una diferencia explicada")
    require(int(row.ids_solo_recursiva) == 4008453, "diferencia = SNOMED CT Concept")
    require(int(root.iloc[0].concept_id) == 4008453, "metadatos de la raíz técnica documentados")
    standard_value = root.iloc[0].standard_concept
    require(pd.isna(standard_value) or str(standard_value).strip() == "", "raíz técnica no estándar")

    print("\n5. Metadatos de relaciones")
    rel = read_csv("04_relationship_resumen.csv").iloc[0]
    require(int(rel.tipos_relacion) == 724, "724 tipos de relación")
    require(int(rel.jerarquicas) == 124, "124 relaciones jerárquicas")
    require(int(rel.definen_ancestria) == 63, "63 relaciones que definen ancestría")
    require(int(rel.ambas) == 55, "55 relaciones en ambos conjuntos")
    require(int(rel.solo_jerarquicas) == 69, "69 solo jerárquicas")
    require(int(rel.solo_ancestria) == 8, "8 solo de ancestría")
    drug_rel = read_csv("05_lisinopril_tipos_relacion.csv")
    explanations = read_csv("05b_cinco_relaciones_explicadas.csv")
    require(len(drug_rel) == 10, "10 tipos de relación salientes de lisinopril")
    require(len(explanations) == 5, "cinco relaciones explicadas")
    require(explanations.relationship_id.nunique() == 5, "cinco explicaciones distintas")
    require(explanations.explicacion.str.len().min() > 30, "explicaciones sustantivas")

    print("\n6. Poli-jerarquía real")
    paths = read_csv("07_polijerarquia_caminos.csv")
    chosen = read_csv("07b_dos_caminos_representativos.csv")
    require(len(paths) == 13, "13 caminos reconstruidos")
    require(int(paths.longitud.min()) == 4, "distancia mínima = 4")
    require(int(paths.longitud.max()) == 8, "distancia máxima = 8")
    require(paths.camino_nombres.str.startswith("Gingivitis").all(), "todos parten de Gingivitis")
    require(paths.camino_nombres.str.endswith("Disease").all(), "todos llegan a Disease")
    require(len(chosen) == 2, "dos caminos representativos")
    require(chosen.ruta_representativa.nunique() == 2, "rutas anatómicas distintas")
    require(chosen.camino_nombres.str.contains("jaw|head", case=False, regex=True).any(), "rama cabeza/mandíbula")
    require(chosen.camino_nombres.str.contains("digestive", case=False).any(), "rama digestiva")

    print("\n7. Daño de los conteos")
    overlap = read_csv("08_conteos_solapamiento.csv").iloc[0]
    require(int(overlap.conteo_A_filas_join) == 327, "COUNT(*) = 327")
    require(int(overlap.conteo_B_conceptos) == 2, "COUNT(DISTINCT concept_id) = 2")
    require(int(overlap.conteo_C_pacientes) == 165, "COUNT(DISTINCT person_id) = 165")
    require(int(overlap.eventos_unicos) == 165, "165 eventos únicos")
    require(int(overlap.filas_duplicadas_por_solapamiento) == 162, "162 filas duplicadas por solapamiento")
    require(overlap.conteo_A_filas_join > overlap.conteo_C_pacientes, "el JOIN infla el resultado")

    print("\n8. Trazabilidad parametrizable")
    trace = read_csv("09_trazabilidad_tres_pacientes.csv")
    required_trace_columns = {
        "person_id", "event_id", "condition_source_concept_id",
        "source_concept_name", "standard_concept_id", "standard_concept_name",
        "concept_set_ancestor_id", "concept_set_ancestor_name", "why_branch",
    }
    require(required_trace_columns.issubset(trace.columns), "camino completo de trazabilidad")
    require(trace.person_id.nunique() == 3, "tres pacientes distintos")
    require(set(trace.person_id) == {1456, 1112, 635}, "pacientes esperados documentados")
    require(trace[["source_concept_name", "standard_concept_name", "concept_set_ancestor_name"]].notna().all().all(), "todos los conceptos tienen nombre")
    require((trace.why_branch == "inclusión directa").all(), "rama de inclusión explicada")
    require(trace.criterio_seleccion.str.contains("independiente").sum() == 1, "una selección independiente documentada")

    print("\n9. Conceptos retirados")
    dead_effect = read_csv("12_conceptos_retirados_efecto.csv").iloc[0]
    require(int(dead_effect.conceptos_retirados) == 0, "cero conceptos D/U")
    require(int(dead_effect.pacientes_antes) == 457, "457 pacientes antes")
    require(int(dead_effect.pacientes_despues) == 457, "457 pacientes después")
    require(int(dead_effect.diferencia_pacientes) == 0, "efecto numérico = 0")

    print("\n10. Rendimiento")
    performance = read_csv("13_rendimiento_tres_corridas.csv")
    require(len(performance) == 2, "dos versiones comparadas")
    require((performance.pacientes == 457).all(), "ambas versiones devuelven 457 pacientes")
    time_columns = ["corrida_1_ms", "corrida_2_ms", "corrida_3_ms"]
    require((performance[time_columns] > 0).all().all(), "seis tiempos positivos")
    for _, timing in performance.iterrows():
        expected = statistics.median(float(timing[column]) for column in time_columns)
        require(abs(expected - float(timing.mediana_ms)) < 1e-9, f"mediana correcta: {timing['version']}")
    plan_sub = (ANALYSIS / "14_plan_subconsulta.txt").read_text(encoding="utf-8")
    plan_mat = (ANALYSIS / "15_plan_materializado.txt").read_text(encoding="utf-8")
    require(len(plan_sub) > 500, "plan de subconsulta completo")
    require(len(plan_mat) > 500, "plan materializado completo")
    require("condition_occurrence" in plan_sub.lower(), "plan 1 usa CONDITION_OCCURRENCE")
    require("condition_occurrence" in plan_mat.lower(), "plan 2 usa CONDITION_OCCURRENCE")
    require("join" in plan_mat.lower(), "plan 2 contiene un JOIN")

    print("\n11. SQL reproducible")
    sql = (LAB / "jerarquias.sql").read_text(encoding="utf-8")
    for number in range(1, 9):
        contains(sql, rf"ACTIVIDAD\s+{number}\b", f"actividad {number} presente")
    contains(sql, r"WITH\s+RECURSIVE", "usa WITH RECURSIVE")
    contains(sql, r"relationship_id\s*=\s*'Is a'", "filtra Is a")
    contains(sql, r"invalid_reason\s+IS\s+NULL", "filtra relaciones vigentes")
    contains(sql, r"nivel\s*<\s*20", "freno de profundidad < 20")
    contains(sql, r"NOT\s+list_contains", "protección adicional contra ciclos")
    contains(sql, r"concept_ancestor", "usa CONCEPT_ANCESTOR")
    contains(sql, r"COUNT\(DISTINCT\s+condition_concept_id\)", "cuenta conceptos distintos")
    contains(sql, r"COUNT\(DISTINCT\s+person_id\)", "cuenta pacientes distintos")
    contains(sql, r"parametros.*person_id", "consulta parametrizable por person_id")
    contains(sql, r"Concept replaced by", "busca reemplazos de conceptos U")
    explain_statements = re.findall(
        r"(?m)^EXPLAIN\s+ANALYZE\s*$",
        sql,
        flags=re.IGNORECASE,
    )
    require(len(explain_statements) == 2, "dos instrucciones EXPLAIN ANALYZE")
    contains(sql, r"CREATE\s+INDEX", "índice del concept set materializado")

    print("\n12. Tabla derivada en DuckDB")
    require(DB.is_file(), "base OMOP local disponible")
    con = duckdb.connect(str(DB), read_only=True)
    try:
        table_count = con.execute(
            """
            SELECT COUNT(*) FROM information_schema.tables
            WHERE table_schema='results'
              AND table_name='lab16_t2dm_concept_set'
            """
        ).fetchone()[0]
        require(table_count == 1, "results.lab16_t2dm_concept_set disponible")
        concepts = con.execute(
            "SELECT COUNT(*) FROM results.lab16_t2dm_concept_set"
        ).fetchone()[0]
        require(concepts == 15, "concept set materializado con 15 conceptos")
        patients = con.execute(
            """
            SELECT COUNT(DISTINCT co.person_id)
            FROM cdm.condition_occurrence co
            JOIN results.lab16_t2dm_concept_set cs
              ON cs.concept_id=co.condition_concept_id
            """
        ).fetchone()[0]
        require(patients == 457, "tabla materializada recupera 457 pacientes")
    finally:
        con.close()

    print("\n13. Documentación")
    findings = (LAB / "hallazgos.md").read_text(encoding="utf-8")
    times = (LAB / "tiempos.md").read_text(encoding="utf-8")
    readme = (LAB / "README.md").read_text(encoding="utf-8")
    contains(findings, r"poli-jerarqu", "poli-jerarquía interpretada")
    contains(findings, r"perspectivas anatómicas y patológicas", "explicación clínica del doble camino")
    contains(findings, r"Conceptos retirados", "conceptos retirados documentados")
    contains(findings, r"Trazabilidad", "trazabilidad documentada")
    contains(times, r"tres veces|tres corridas|tres", "tres ejecuciones documentadas")
    contains(times, r"mediana", "mediana documentada")
    contains(times, r"HASH_JOIN|JOIN", "cambio del plan explicado")
    contains(times, r"no garantiza|No se observó|más rápida", "resultado de rendimiento interpretado sin exageración")
    contains(readme, r"ocho actividades", "README describe el alcance")
    contains(readme, r"no ejecutan `git commit` ni `git push`", "Git permanece manual")

    print("\n14. Archivos no deseados y formato")
    forbidden = []
    large = []
    suffixes = {".duckdb", ".db", ".sqlite", ".zip", ".DS_Store"}
    for path in LAB.rglob("*"):
        if path.is_dir() and path.name == "__pycache__":
            forbidden.append(path)
        elif path.is_file():
            if path.suffix in suffixes or path.name == ".DS_Store" or path.suffix == ".pyc":
                forbidden.append(path)
            if path.stat().st_size > 10 * 1024 * 1024:
                large.append(path)
            if path.suffix.lower() in {".py", ".sql", ".md", ".csv", ".txt"}:
                for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                    if line.rstrip() != line:
                        raise AssertionError(f"espacio final: {path}:{number}")
    require(not forbidden, "sin bases, ZIP, cachés ni archivos del sistema")
    require(not large, "sin archivos mayores de 10 MB")
    passed("archivos de texto sin espacios finales")

    print("\n===== RESULTADO FINAL =====")
    print(f"PASS: {checks} comprobaciones superadas")
    print("Commit y push: NO ejecutados")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"\nFAIL: {exc}", file=sys.stderr)
        raise

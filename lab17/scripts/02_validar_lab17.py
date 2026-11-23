#!/usr/bin/env python3
"""Validación formal del Laboratorio 17. No modifica Git ni la base."""

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
LAB = ROOT / "lab17"
AUDIT = LAB / "evidencias" / "auditoria"
ANALYSIS = LAB / "evidencias" / "analisis"
FIGURES = LAB / "figuras"
DB = ROOT / "lab12" / "data" / "omop" / "synthea_omop_cdm54.duckdb"
BRANCH = "lab17-new-user-cohort"
COHORT_ID = 17001
checks = 0


def passed(message: str) -> None:
    global checks
    checks += 1
    print(f"PASS: {message}")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    passed(message)


def csv(path: Path) -> pd.DataFrame:
    require(path.is_file(), str(path))
    return pd.read_csv(path)


def contains(text: str, pattern: str, message: str) -> None:
    require(re.search(pattern, text, re.IGNORECASE | re.DOTALL) is not None, message)


def main() -> None:
    print("===== VALIDACIÓN FORMAL DEL LABORATORIO 17 =====")

    print("\n1. Rama")
    current = subprocess.check_output(
        ["git", "branch", "--show-current"], cwd=ROOT, text=True
    ).strip()
    require(current == BRANCH, f"rama = {BRANCH}")

    print("\n2. Entregables obligatorios")
    mandatory = [
        LAB / "README.md",
        LAB / "cohorte_definicion.md",
        LAB / "cohorte_definicion.sql",
        LAB / "atricion.md",
        LAB / "caracterizacion.md",
        FIGURES / "01_eventos_indice_antes_despues.png",
        FIGURES / "02_histograma_seguimiento.png",
        LAB / "scripts" / "00_auditar_lab17.py",
        LAB / "scripts" / "00b_comparar_criterios_lab17.py",
        LAB / "scripts" / "01_generar_lab17.py",
        LAB / "scripts" / "02_validar_lab17.py",
        ANALYSIS / "01_atricion.csv",
        ANALYSIS / "02_evento_inicial_validacion.csv",
        ANALYSIS / "03_cohorte_validacion.csv",
        ANALYSIS / "04_miembros_cohorte.csv",
        ANALYSIS / "05_caracterizacion_individual.csv",
        ANALYSIS / "07_top10_comorbilidades.csv",
        ANALYSIS / "09_tabla1.csv",
        ANALYSIS / "10_auditoria_immortal_time.csv",
    ]
    for path in mandatory:
        require(path.is_file() and path.stat().st_size > 0, str(path))

    print("\n3. Sintaxis Python")
    with tempfile.TemporaryDirectory(prefix="lab17_pycompile_") as temp_dir:
        temp = Path(temp_dir)
        for script in sorted((LAB / "scripts").glob("*.py")):
            py_compile.compile(
                str(script), cfile=str(temp / f"{script.stem}.pyc"), doraise=True
            )
            passed(f"sintaxis correcta: {script.name}")

    print("\n4. OBSERVATION_PERIOD")
    observation = csv(ANALYSIS / "00_observation_period_resumen.csv").iloc[0]
    require(int(observation.persons_total) == 5745, "5,745 personas totales")
    require(int(observation.persons_with_period) == 5745, "todas tienen periodo de observación")
    require(int(observation.periods_total) == 5745, "5,745 periodos")
    require(int(observation.persons_multiple_periods) == 0, "sin periodos múltiples")
    require(float(observation.median_longest_period_days) == 11516.0, "mediana de observación = 11,516 días")
    outside = csv(ANALYSIS / "00b_eventos_fuera_observacion.csv")
    expected_outside = {"Condition": 699, "Drug": 0, "Measurement": 89}
    require(set(outside.domain) == set(expected_outside), "tres dominios auditados")
    for domain, expected in expected_outside.items():
        value = int(outside.loc[outside.domain == domain, "outside_events"].iloc[0])
        require(value == expected, f"{domain}: {expected} eventos fuera")

    print("\n5. Selección de ventana T2DM")
    windows = csv(ANALYSIS / "00c_comparacion_ventanas_t2dm.csv")
    recent = windows.loc[windows.variant == "A_inicio_ultimos_365_dias"].iloc[0]
    prior = windows.loc[
        windows.variant == "B_diagnostico_observado_antes_indice"
    ].iloc[0]
    require(int(recent.t2dm_patients) == 17, "17 con T2DM iniciado en los últimos 365 días")
    require(int(prior.t2dm_patients) == 179, "179 con T2DM observado antes del índice")
    require(int(prior.after_2_bp_dates) == 22, "22 tras dos fechas de presión arterial")
    require("C_condicion_activa_en_indice" not in set(windows.variant), "variante activa produjo cero filas y se documenta por ausencia")

    print("\n6. Evento inicial y atrición")
    initial = csv(ANALYSIS / "02_evento_inicial_validacion.csv").iloc[0]
    require(int(initial.rows) == 1014, "1,014 filas de evento inicial")
    require(int(initial.persons) == 1014, "1,014 personas distintas")
    attrition = csv(ANALYSIS / "01_atricion.csv")
    require(len(attrition) == 7, "siete pasos de atrición")
    require(attrition.step.tolist() == list(range(1, 8)), "pasos ordenados de 1 a 7")
    require(attrition.n.astype(int).tolist() == [1014, 1014, 1014, 179, 22, 22, 22], "conteos de atrición esperados")
    require(attrition.lost_at_step.fillna(0).astype(int).tolist() == [0, 0, 0, 835, 157, 0, 0], "pérdidas por paso correctas")
    require((attrition.n.diff().fillna(0) <= 0).all(), "N nunca aumenta entre pasos")
    require(abs(float(attrition.iloc[-1].percent_initial_remaining) - 2.17) < 1e-9, "2.17% de la población inicial permanece")

    print("\n7. Cohorte estándar")
    validation = csv(ANALYSIS / "03_cohorte_validacion.csv").iloc[0]
    require(int(validation.rows) == 22, "22 filas finales")
    require(int(validation.persons) == 22, "22 personas finales")
    require(int(validation.invalid_end_before_start) == 0, "sin finales anteriores al índice")
    require(int(validation.start_outside_observation) == 0, "sin índices fuera de observación")
    require(int(validation.end_outside_observation) == 0, "sin salidas fuera de observación")
    members = csv(ANALYSIS / "04_miembros_cohorte.csv")
    require(len(members) == 22, "22 miembros exportados")
    require(members.subject_id.nunique() == 22, "una fila por persona en la cohorte")
    start = pd.to_datetime(members.cohort_start_date)
    end = pd.to_datetime(members.cohort_end_date)
    require((end >= start).all(), "todos los intervalos son cronológicos")
    require((members.cohort_definition_id == COHORT_ID).all(), "cohort_definition_id = 17001")

    print("\n8. Caracterización")
    individual = csv(ANALYSIS / "05_caracterizacion_individual.csv")
    require(len(individual) == 22, "22 personas caracterizadas")
    require(individual.age_at_index.notna().all(), "edad disponible para todas")
    require((individual.age_at_index >= 18).all(), "todas son adultas")
    require(round(float(individual.age_at_index.mean()), 1) == 56.8, "edad media reproducible = 56.8 años")
    sex = csv(ANALYSIS / "06_distribucion_sexo.csv")
    require(int(sex.n.sum()) == 22, "sexo contabilizado para 22 personas")
    require(set(sex.sex_name) == {"Unknown"}, "limitación de sexo no mapeado conservada")
    comorbidities = csv(ANALYSIS / "07_top10_comorbilidades.csv")
    require(len(comorbidities) == 10, "diez comorbilidades")
    require(comorbidities.concept_name.notna().all(), "comorbilidades con nombres legibles")
    require((comorbidities.patients.between(1, 22)).all(), "conteos de comorbilidad válidos")
    followup = csv(ANALYSIS / "08_seguimiento_resumen.csv").iloc[0]
    require(int(followup.n) == 22, "seguimiento para 22 personas")
    require(float(followup.median_days) == 1054.0, "mediana de seguimiento = 1,054 días")
    require(int(followup.min_days) >= 1, "seguimiento mínimo positivo")
    table1 = csv(ANALYSIS / "09_tabla1.csv")
    require(len(table1) >= 5, "tabla 1 presentable")

    print("\n9. Immortal time bias")
    immortal = csv(ANALYSIS / "10_auditoria_immortal_time.csv")
    require(len(immortal) == 7, "siete componentes temporales auditados")
    entry_rows = immortal[immortal.criterion != "Continuidad de lisinopril"]
    require((entry_rows.uses_future_for_entry == "No").all(), "ningún criterio de entrada usa el futuro")
    exit_row = immortal[immortal.criterion == "Continuidad de lisinopril"].iloc[0]
    require(exit_row.uses_future_for_entry == "No para entrada", "información posterior solo determina salida")

    print("\n10. Figuras")
    for path in [
        FIGURES / "01_eventos_indice_antes_despues.png",
        FIGURES / "02_histograma_seguimiento.png",
    ]:
        data = path.read_bytes()
        require(data.startswith(b"\x89PNG\r\n\x1a\n"), f"PNG válido: {path.name}")
        require(len(data) > 10_000, f"figura no vacía: {path.name}")

    print("\n11. SQL reproducible")
    sql = (LAB / "cohorte_definicion.sql").read_text(encoding="utf-8")
    required_ctes = [
        "initial_event", "prior_observation", "washout", "inclusion_t2dm",
        "inclusion_two_bp_dates", "exclusion_minors", "exclusion_pregnancy",
    ]
    for name in required_ctes:
        contains(sql, rf"\b{name}\s+AS\s*\(", f"CTE {name}")
    contains(sql, r"MIN\(de\.drug_exposure_start_date\)", "primera exposición por persona")
    contains(sql, r"observation_period_start_date\s*<=\s*i\.index_date\s*-\s*INTERVAL\s+365\s+DAY", "365 días continuos de observación")
    contains(sql, r"NOT\s+EXISTS.*drug_exposure_start_date", "lavado mediante NOT EXISTS")
    contains(sql, r"EXISTS.*condition_occurrence", "inclusión T2DM mediante EXISTS")
    contains(sql, r"COUNT\(DISTINCT\s+m\.measurement_date\)", "criterio agregado de fechas de presión")
    contains(sql, r"bp_dates\s*>=\s*2", "umbral de dos fechas")
    require(sql.upper().count("NOT EXISTS") >= 4, "criterios y concept sets usan NOT EXISTS")
    contains(sql, r"prior_max_end", "gaps and islands usa máximo final previo")
    contains(sql, r"INTERVAL\s+30\s+DAY", "gap de 30 días")
    contains(sql, r"LEAST\(MAX\(end_date\),op_end\)", "salida censurada al final de observación")
    contains(sql, r"INSERT\s+INTO\s+results\.cohort", "INSERT en results.cohort")
    contains(sql, r"cohort_definition_id,subject_id,cohort_start_date,cohort_end_date", "cuatro columnas estándar")
    contains(sql, r"DELETE\s+FROM\s+results\.cohort.*17001", "reinserción idempotente")

    print("\n12. Concordancia prosa–SQL")
    definition = (LAB / "cohorte_definicion.md").read_text(encoding="utf-8")
    attrition_md = (LAB / "atricion.md").read_text(encoding="utf-8")
    characterization_md = (LAB / "caracterizacion.md").read_text(encoding="utf-8")
    contains(definition, r"PICOT", "PICOT presente")
    for term in ["Población", "Exposición", "Comparador", "Desenlace", "Tiempo"]:
        contains(definition, rf"\*\*{term}\*\*", f"PICOT: {term}")
    contains(definition, r"365 días continuos", "justificación de observación previa")
    contains(definition, r"180 días", "se explica qué implicaría una ventana menor")
    contains(definition, r"T2DM es crónica", "ventana de T2DM justificada clínicamente")
    contains(definition, r"exigir tres habría dejado solo 10", "umbral de presión justificado")
    contains(definition, r"gap.*30 días", "gap de salida documentado")
    contains(definition, r"mínimo entre", "censura por fin de observación documentada")
    contains(attrition_md, r"1014", "N inicial discutido")
    contains(attrition_md, r"22", "N final discutido")
    contains(attrition_md, r"mayor pérdida", "criterio más costoso discutido")
    contains(attrition_md, r"observación previa y el lavado se reportan por separado", "observación y lavado separados")
    contains(characterization_md, r"Tabla 1", "tabla 1 incluida")
    contains(characterization_md, r"immortal time", "immortal time discutido")
    contains(characterization_md, r"no se utilizó información posterior", "ausencia de sesgo justificada")

    print("\n13. Tablas locales en DuckDB")
    require(DB.is_file(), "base OMOP local disponible")
    con = duckdb.connect(str(DB), read_only=True)
    try:
        expected_tables = {
            "lab17_lisinopril_concept_set",
            "lab17_t2dm_concept_set",
            "lab17_bp_concept_set",
            "lab17_pregnancy_concept_set",
            "lab17_final_candidates",
            "lab17_attrition",
            "lab17_first_drug_era",
            "cohort",
        }
        found = {
            row[0]
            for row in con.execute(
                """
                SELECT table_name FROM information_schema.tables
                WHERE table_schema='results'
                """
            ).fetchall()
        }
        require(expected_tables.issubset(found), "ocho tablas derivadas disponibles")
        require(con.execute("SELECT COUNT(*) FROM results.lab17_lisinopril_concept_set").fetchone()[0] == 64, "64 conceptos de lisinopril sin HCTZ")
        require(con.execute("SELECT COUNT(*) FROM results.lab17_t2dm_concept_set").fetchone()[0] == 15, "15 conceptos de T2DM")
        require(con.execute("SELECT COUNT(*) FROM results.lab17_bp_concept_set").fetchone()[0] == 4, "cuatro conceptos de presión")
        require(con.execute("SELECT COUNT(*) FROM results.lab17_final_candidates").fetchone()[0] == 22, "22 candidatos finales materializados")
        cohort = con.execute(
            f"SELECT COUNT(*),COUNT(DISTINCT subject_id) FROM results.cohort WHERE cohort_definition_id={COHORT_ID}"
        ).fetchone()
        require(cohort == (22, 22), "results.cohort contiene 22 filas y personas")
    finally:
        con.close()

    print("\n14. Archivos no deseados y formato")
    forbidden: list[Path] = []
    large: list[Path] = []
    for path in LAB.rglob("*"):
        if path.is_dir() and path.name == "__pycache__":
            forbidden.append(path)
        elif path.is_file():
            if path.name == ".DS_Store" or path.suffix.lower() in {
                ".pyc", ".duckdb", ".db", ".sqlite", ".zip"
            }:
                forbidden.append(path)
            if path.stat().st_size > 10 * 1024 * 1024:
                large.append(path)
    require(not forbidden, "sin bases, ZIP, cachés ni archivos del sistema")
    require(not large, "sin archivos mayores de 10 MB")

    print("\n===== RESULTADO FINAL =====")
    print(f"PASS: {checks} comprobaciones superadas")
    print("Commit y push: NO ejecutados")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"\nFAIL: {exc}", file=sys.stderr)
        raise

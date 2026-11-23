#!/usr/bin/env python3
"""Validador formal del Laboratorio 18.

No modifica resultados, no prepara archivos y no ejecuta commit ni push.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
LAB = ROOT / "lab18"
AUDIT = LAB / "evidencias" / "auditoria"
ANALYSIS = LAB / "evidencias" / "analisis"
FIGURES = LAB / "figuras"
checks = 0


def require(condition: bool, message: str) -> None:
    global checks
    if not condition:
        print(f"FAIL: {message}")
        raise AssertionError(message)
    checks += 1
    print(f"PASS: {message}")


def required(path: Path) -> None:
    require(path.is_file(), str(path))


def read_csv(path: Path) -> pd.DataFrame:
    required(path)
    return pd.read_csv(path)


def main() -> None:
    print("===== VALIDACIÓN FORMAL DEL LABORATORIO 18 =====")

    print("\n1. Rama")
    branch = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    require(branch == "lab18-cohort-audit", "rama = lab18-cohort-audit")

    print("\n2. Entregables obligatorios")
    required_files = [
        LAB / "README.md",
        LAB / "diagnostico_cohorte.md",
        LAB / "scripts" / "00_auditar_lab18.py",
        LAB / "scripts" / "01_generar_lab18.py",
        LAB / "scripts" / "02_validar_lab18.py",
        FIGURES / "01_diagrama_atricion_consort.png",
        FIGURES / "02_incidencia_anio.png",
        FIGURES / "03_incidencia_edad.png",
        FIGURES / "04_sensibilidad_lavado.png",
    ]
    for path in required_files:
        required(path)

    print("\n3. Sintaxis Python")
    for name in ("00_auditar_lab18.py", "01_generar_lab18.py", "02_validar_lab18.py"):
        path = LAB / "scripts" / name
        compile(path.read_text(encoding="utf-8"), str(path), "exec")
        require(True, f"sintaxis correcta: {name}")

    print("\n4. Factibilidad")
    fact = read_csv(AUDIT / "01_factibilidad.csv")
    require(len(fact) == 1, "una fila de factibilidad")
    row = fact.iloc[0]
    require(int(row.cohort_patients) == 22, "22 personas en la cohorte")
    require(float(row.followup_q1_days) == 294.25, "Q1 de seguimiento = 294.25 días")
    require(float(row.followup_median_days) == 1054.0, "mediana de seguimiento = 1,054 días")
    require(float(row.followup_q3_days) == 1766.0, "Q3 de seguimiento = 1,766 días")
    require(int(row.egfr_measurements) == 255, "255 mediciones de eGFR")
    require(int(row.patients_with_egfr) == 19, "19 personas con eGFR")
    require(int(row.egfr_below_60_events) == 65, "65 mediciones de eGFR < 60")
    require(int(row.patients_with_egfr_below_60) == 6, "seis personas con eGFR < 60")

    verdict = read_csv(ANALYSIS / "01_factibilidad_veredicto.csv")
    require(len(verdict) == 1, "un veredicto de factibilidad")
    require(verdict.iloc[0].model_feasible == "No", "modelo multivariable no factible")
    require("no son eventos independientes" in verdict.iloc[0].reason, "dependencia de mediciones repetidas documentada")

    renal = read_csv(AUDIT / "02_egfr_seguimiento.csv")
    require(len(renal) == 255, "255 filas de seguimiento renal")
    require(renal.subject_id.nunique() == 19, "19 personas en detalle renal")
    require(int(renal.egfr_below_60.sum()) == 65, "65 indicadores renales bajos reproducibles")
    units = read_csv(AUDIT / "03_egfr_unidades.csv")
    require(len(units) == 2, "dos representaciones de unidad para eGFR")
    require(int(units.measurements.sum()) == 255, "unidades suman 255 mediciones")

    print("\n5. Atrición original")
    original = read_csv(AUDIT / "04_atricion_original.csv")
    require(len(original) == 7, "siete pasos originales")
    require(original.step.tolist() == list(range(1, 8)), "pasos originales ordenados")
    require(original.n.astype(int).tolist() == [1014, 1014, 1014, 179, 22, 22, 22], "conteos originales esperados")
    computed_lost = original.n.shift(1) - original.n
    require(
        computed_lost.iloc[1:].astype(int).tolist()
        == original.lost_at_step.iloc[1:].astype(int).tolist(),
        "pérdidas originales correctas",
    )
    require(original.n.diff().fillna(0).le(0).all(), "N original nunca aumenta")
    require(round(100 * 22 / 1014, 2) == 2.17, "2.17% permanece")

    print("\n6. Orden alternativo")
    reordered = read_csv(AUDIT / "05_atricion_reordenada.csv")
    require(len(reordered) == 7, "siete pasos reordenados")
    require(reordered.n.astype(int).tolist() == [1014, 1014, 1014, 88, 22, 22, 22], "conteos reordenados esperados")
    require(int(original.iloc[-1].n) == int(reordered.iloc[-1].n), "N final idéntico en ambos órdenes")
    require(int(original.iloc[3].lost_at_step) == 835, "T2DM cuesta 835 en orden original")
    require(int(reordered.iloc[3].lost_at_step) == 926, "presión cuesta 926 al evaluarse primero")
    require(int(reordered.iloc[4].lost_at_step) == 66, "T2DM cuesta 66 al evaluarse después")
    compared = read_csv(ANALYSIS / "02_atricion_comparada.csv")
    require(compared.same_final_n.astype(bool).all(), "comparación declara mismo N final")

    print("\n7. Incidencia descriptiva")
    by_year = read_csv(AUDIT / "06_incidencia_anio.csv")
    by_age = read_csv(AUDIT / "07_incidencia_edad.csv")
    require(len(by_year) == 11, "once años con entradas")
    require(int(by_year.cohort_entries.sum()) == 22, "entradas anuales suman 22")
    require(len(by_age) == 5, "cinco grupos etarios")
    require(int(by_age.cohort_entries.sum()) == 22, "grupos etarios suman 22")
    incidence_summary = read_csv(ANALYSIS / "03_incidencia_resumen.csv")
    require(len(incidence_summary) == 1, "resumen de incidencia disponible")
    require("no son tasas" in incidence_summary.iloc[0].interpretation, "conteos no presentados como tasas")

    print("\n8. Evento índice")
    index_codes = read_csv(AUDIT / "08_codigos_evento_indice.csv")
    require(len(index_codes) == 4, "cuatro productos índice")
    require(int(index_codes.patients.sum()) == 22, "productos índice suman 22 personas")
    require(int(index_codes.iloc[0].drug_concept_id) == 19080128, "producto dominante esperado")
    require(int(index_codes.iloc[0].patients) == 19, "producto dominante aporta 19 personas")
    require(float(index_codes.iloc[0].percentage) == 86.36, "producto dominante aporta 86.36%")
    require(index_codes.concept_name.notna().all(), "todos los productos tienen nombre")
    require(int(index_codes.patients_with_multiple_index_rows.sum()) == 1, "una ambigüedad de filas índice detectada")

    print("\n9. Conceptos huérfanos")
    orphans = read_csv(AUDIT / "09_conceptos_huerfanos_candidatos.csv")
    require(len(orphans) == 3, "tres candidatos huérfanos reales")
    require(orphans.concept_name.str.contains("lisinopril", case=False).all(), "todos contienen lisinopril")
    require(orphans.concept_name.str.contains("hydrochlorothiazide", case=False).all(), "todos son combinaciones con HCTZ")
    decisions = read_csv(ANALYSIS / "05_huerfanos_decisiones.csv")
    require(len(decisions) == 3, "tres decisiones de huérfanos")
    require(decisions.include.eq("No").all(), "los tres candidatos quedan excluidos")
    require(decisions.decision.str.contains("preespecificada", case=False).all(), "exclusión justificada clínicamente")

    print("\n10. Comparación CIRCE/ATLAS")
    circe = read_csv(ANALYSIS / "06_comparacion_circe.csv")
    require(len(circe) == 3, "tres casos borde CIRCE")
    require(circe.edge_case.nunique() == 3, "tres casos borde distintos")
    require(circe.own_sql.str.len().gt(40).all(), "limitación propia explicada")
    require(circe.importance_here.str.len().gt(40).all(), "importancia evaluada en cada caso")
    require(circe.edge_case.str.contains("mismo día", case=False).any(), "eventos del mismo día")
    require(circe.edge_case.str.contains("periodos de observación", case=False).any(), "múltiples periodos de observación")
    require(circe.edge_case.str.contains("colapso", case=False).any(), "colapso de episodios")

    print("\n11. Sensibilidad")
    variants = read_csv(AUDIT / "10_variantes_resumen.csv")
    require(variants.washout_days.astype(int).tolist() == [180, 365, 730], "lavados 180, 365 y 730")
    require(variants.patients.astype(int).tolist() == [22, 22, 22], "22 personas en cada variante")
    require(variants.age_mean.astype(float).eq(56.8).all(), "edad media estable")
    require(variants.age_median.astype(float).eq(57.5).all(), "edad mediana estable")
    require(variants.followup_median_days.astype(float).eq(1054.0).all(), "seguimiento mediano estable")
    members = read_csv(AUDIT / "11_variantes_miembros.csv")
    require(len(members) == 66, "66 filas de membresía")
    sets = {
        int(days): set(group.person_id.astype(int))
        for days, group in members.groupby("washout_days")
    }
    require(sets[365].issubset(sets[180]), "365 es subconjunto de 180")
    require(sets[730].issubset(sets[365]), "730 es subconjunto de 365")
    require(sets[180] == sets[365] == sets[730], "mismos miembros en las tres variantes")
    comorb = read_csv(AUDIT / "12_variantes_comorbilidades.csv")
    require(len(comorb) == 9, "tres comorbilidades por variante")
    require(comorb.groupby("washout_days").size().eq(3).all(), "top 3 completo por variante")
    overlap = read_csv(AUDIT / "13_traslape_variantes.csv")
    require(int(overlap.iloc[0].patients) == 22, "22 personas en las tres variantes")
    require(int(overlap.iloc[1:].patients.sum()) == 0, "cero personas exclusivas")
    nesting = read_csv(AUDIT / "14_verificacion_anidamiento.csv")
    require(len(nesting) == 2, "dos comprobaciones de anidamiento")
    require(nesting.passes.astype(str).str.lower().eq("true").all(), "anidamiento validado")
    require(nesting.violations.astype(int).eq(0).all(), "cero violaciones de anidamiento")
    sensitivity = read_csv(ANALYSIS / "08_sensibilidad_resumen.csv")
    require(sensitivity.principal_definition.astype(str).str.lower().tolist() == ["false", "true", "false"], "365 días declarado principal")
    require(sensitivity.same_members_as_365.astype(str).str.lower().eq("true").all(), "igualdad con definición principal")

    print("\n12. Figuras")
    for name in (
        "01_diagrama_atricion_consort.png",
        "02_incidencia_anio.png",
        "03_incidencia_edad.png",
        "04_sensibilidad_lavado.png",
    ):
        path = FIGURES / name
        data = path.read_bytes()
        require(data.startswith(b"\x89PNG\r\n\x1a\n"), f"PNG válido: {name}")
        require(path.stat().st_size > 20_000, f"figura no vacía: {name}")

    print("\n13. Documentación")
    report = (LAB / "diagnostico_cohorte.md").read_text(encoding="utf-8")
    readme = (LAB / "README.md").read_text(encoding="utf-8")
    for phrase, label in (
        ("## 1. Factibilidad", "factibilidad documentada"),
        ("no es factible", "veredicto explícito"),
        ("mediciones son repetidas", "eventos no independientes"),
        ("## 2. Atrición", "atrición original"),
        ("## 3. El orden", "orden alternativo"),
        ("N final permanece", "igualdad final interpretada"),
        ("## 4. Entradas por año", "incidencia interpretada"),
        ("no tasas de incidencia", "incidencia no confundida con tasa"),
        ("## 5. Códigos", "códigos índice"),
        ("86.36%", "dominancia del código documentada"),
        ("## 6. Conceptos huérfanos", "huérfanos documentados"),
        ("## 7. Comparación con ATLAS/CIRCE", "comparación CIRCE"),
        ("## 8. Sensibilidad", "sensibilidad documentada"),
        ("365 días", "definición principal declarada"),
        ("730 ⊆ 365 ⊆ 180", "anidamiento interpretado"),
        ("## 9. Discusión final", "discusión final"),
        ("comparador activo", "limitación causal reconocida"),
        ("sexo no mapeado", "limitación propia reconocida"),
    ):
        require(phrase in report, label)
    require("The Book of OHDSI" in report, "fuente OHDSI citada")
    require("OHDSI CirceR" in report, "fuente CirceR citada")
    require("commit" in readme.lower() and "push" in readme.lower(), "Git permanece manual")

    print("\n14. Código reproducible")
    audit_code = (LAB / "scripts" / "00_auditar_lab18.py").read_text(encoding="utf-8")
    generator_code = (LAB / "scripts" / "01_generar_lab18.py").read_text(encoding="utf-8")
    require("for days in (180, 365, 730)" in audit_code, "tres variantes generadas por código")
    require("variant_ctes" in audit_code, "CTE parametrizable por lavado")
    require("COUNT(DISTINCT" in audit_code, "conteos distintos utilizados")
    require("draw_consort" in generator_code, "diagrama CONSORT regenerable")
    require("01_diagrama_atricion_consort.png" in generator_code, "figura de atrición regenerable")
    require("02_incidencia_anio.png" in generator_code, "figura anual regenerable")
    require("03_incidencia_edad.png" in generator_code, "figura etaria regenerable")
    require("04_sensibilidad_lavado.png" in generator_code, "figura de sensibilidad regenerable")
    require("git commit" not in audit_code and "git push" not in audit_code, "auditor no ejecuta Git")
    git_execution_apis = (
        "subprocess.run",
        "subprocess.call",
        "subprocess.check_call",
        "subprocess.check_output",
        "subprocess.Popen",
        "os.system",
    )
    require(
        not any(api in generator_code for api in git_execution_apis),
        "generador no ejecuta Git",
    )

    print("\n15. Archivos no deseados y formato")
    forbidden = []
    large = []
    trailing = []
    text_suffixes = {".py", ".md", ".csv", ".txt"}
    for path in LAB.rglob("*"):
        if not path.is_file():
            continue
        if path.name in {".DS_Store"} or path.suffix.lower() in {".duckdb", ".zip", ".pyc"} or "__pycache__" in path.parts:
            forbidden.append(path)
        if path.stat().st_size > 10 * 1024 * 1024:
            large.append(path)
        if path.suffix.lower() in text_suffixes:
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if line.endswith((" ", "\t")):
                    trailing.append(f"{path}:{number}")
    require(not forbidden, "sin bases, ZIP, cachés ni archivos del sistema")
    require(not large, "sin archivos mayores de 10 MB")
    require(not trailing, "archivos de texto sin espacios finales")

    print("\n===== RESULTADO FINAL =====")
    print(f"PASS: {checks} comprobaciones superadas")
    print("Commit y push: NO ejecutados")


if __name__ == "__main__":
    main()

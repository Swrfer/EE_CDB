#!/usr/bin/env python3
"""Genera los entregables del Laboratorio 18 desde la auditoría del Lab 17.

No modifica la base OMOP, no ejecuta Git y mantiene como definición principal
el lavado preespecificado de 365 días.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
LAB = ROOT / "lab18"
AUDIT = LAB / "evidencias" / "auditoria"
ANALYSIS = LAB / "evidencias" / "analisis"
FIGURES = LAB / "figuras"


def read(name: str) -> pd.DataFrame:
    path = AUDIT / name
    if not path.exists():
        raise SystemExit(f"ERROR: falta la auditoría requerida: {path}")
    return pd.read_csv(path)


def save(df: pd.DataFrame, name: str) -> None:
    path = ANALYSIS / name
    df.to_csv(path, index=False)
    print(f"OK: {path} ({len(df)} filas)")


def md_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_Sin filas._"
    clean = df.copy().fillna("")
    headers = [str(col).replace("|", "\\|") for col in clean.columns]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in clean.itertuples(index=False, name=None):
        values = [
            str(value).replace("|", "\\|").replace("\n", " ")
            for value in row
        ]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def draw_consort(attrition: pd.DataFrame, path: Path) -> None:
    data = attrition.copy()
    data["lost_at_step"] = data.lost_at_step.fillna(0).astype(int)
    n_steps = len(data)
    fig, ax = plt.subplots(figsize=(10, 12))
    ax.set_xlim(0, 10)
    ax.set_ylim(-0.4, n_steps + 0.5)
    ax.axis("off")

    y_positions = np.arange(n_steps, 0, -1)
    for index, (row, y) in enumerate(zip(data.itertuples(index=False), y_positions)):
        box = FancyBboxPatch(
            (1.0, y - 0.35),
            5.8,
            0.7,
            boxstyle="round,pad=0.03,rounding_size=0.08",
            linewidth=1.4,
            edgecolor="#1D3557",
            facecolor="#EAF2F8" if index < n_steps - 1 else "#D8F3DC",
        )
        ax.add_patch(box)
        label = str(row.criterion).replace("+ ", "").replace("- ", "")
        ax.text(3.9, y + 0.08, label, ha="center", va="center", fontsize=10)
        ax.text(
            3.9,
            y - 0.17,
            f"N = {int(row.n):,}",
            ha="center",
            va="center",
            fontsize=11,
            fontweight="bold",
        )
        if index > 0:
            ax.annotate(
                "",
                xy=(3.9, y + 0.36),
                xytext=(3.9, y + 0.64),
                arrowprops=dict(arrowstyle="->", color="#457B9D", lw=1.3),
            )
            lost = int(row.lost_at_step)
            previous = int(data.iloc[index - 1].n)
            pct = 100 * lost / previous if previous else 0
            ax.text(
                7.25,
                y,
                f"Excluidos: {lost:,}\n({pct:.1f}% del paso previo)",
                ha="left",
                va="center",
                fontsize=9.5,
                color="#6C2E2E",
            )

    ax.text(
        3.9,
        n_steps + 0.35,
        "Cohorte de nuevos usuarios de lisinopril",
        ha="center",
        va="center",
        fontsize=15,
        fontweight="bold",
        color="#1D3557",
    )
    ax.text(
        3.9,
        -0.15,
        "Definición principal preespecificada: lavado de 365 días",
        ha="center",
        fontsize=9.5,
        color="#555555",
    )
    fig.tight_layout()
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    ANALYSIS.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)

    feasibility = read("01_factibilidad.csv")
    renal_units = read("03_egfr_unidades.csv")
    original = read("04_atricion_original.csv")
    reordered = read("05_atricion_reordenada.csv")
    incidence_year = read("06_incidencia_anio.csv")
    incidence_age = read("07_incidencia_edad.csv")
    index_codes = read("08_codigos_evento_indice.csv")
    orphans = read("09_conceptos_huerfanos_candidatos.csv")
    variants = read("10_variantes_resumen.csv")
    variant_members = read("11_variantes_miembros.csv")
    variant_comorb = read("12_variantes_comorbilidades.csv")
    overlap = read("13_traslape_variantes.csv")
    nesting = read("14_verificacion_anidamiento.csv")

    f = feasibility.iloc[0]
    verdict = pd.DataFrame(
        [
            {
                "cohort_patients": int(f.cohort_patients),
                "followup_median_days": float(f.followup_median_days),
                "followup_q1_days": float(f.followup_q1_days),
                "followup_q3_days": float(f.followup_q3_days),
                "egfr_measurements": int(f.egfr_measurements),
                "patients_with_egfr": int(f.patients_with_egfr),
                "egfr_below_60_events": int(f.egfr_below_60_events),
                "patients_with_egfr_below_60": int(
                    f.patients_with_egfr_below_60
                ),
                "model_feasible": "No",
                "reason": (
                    "Sólo 6 pacientes presentan la señal renal; las 65 "
                    "mediciones repetidas no son eventos independientes."
                ),
            }
        ]
    )
    save(verdict, "01_factibilidad_veredicto.csv")

    attrition_compare = original[["step", "criterion", "n"]].merge(
        reordered[["step", "criterion", "n"]],
        on="step",
        suffixes=("_original", "_reordenado"),
    )
    attrition_compare["same_final_n"] = (
        int(original.iloc[-1].n) == int(reordered.iloc[-1].n)
    )
    save(attrition_compare, "02_atricion_comparada.csv")

    peak_year = incidence_year.loc[incidence_year.cohort_entries.idxmax()]
    peak_age = incidence_age.loc[incidence_age.cohort_entries.idxmax()]
    incidence_summary = pd.DataFrame(
        [
            {
                "peak_calendar_year": int(peak_year.calendar_year),
                "entries_in_peak_year": int(peak_year.cohort_entries),
                "first_year": int(incidence_year.calendar_year.min()),
                "last_year": int(incidence_year.calendar_year.max()),
                "largest_age_group": peak_age.age_group,
                "entries_in_largest_age_group": int(peak_age.cohort_entries),
                "interpretation": (
                    "Conteos descriptivos de entrada; no son tasas poblacionales. "
                    "La forma refleja la captura sintética y el pequeño N."
                ),
            }
        ]
    )
    save(incidence_summary, "03_incidencia_resumen.csv")

    dominant = index_codes.iloc[0]
    index_summary = pd.DataFrame(
        [
            {
                "dominant_concept_id": int(dominant.drug_concept_id),
                "dominant_concept_name": dominant.concept_name,
                "patients": int(dominant.patients),
                "percentage": float(dominant.percentage),
                "interpretation": (
                    "La cohorte está dominada por una presentación, aunque "
                    "el concept set conserva otras dosis observadas."
                ),
            }
        ]
    )
    save(index_summary, "04_evento_indice_resumen.csv")

    orphan_decisions = orphans.copy()
    orphan_decisions["include"] = "No"
    orphan_decisions["decision"] = (
        "Excluir: contiene HCTZ y cambia la exposición de monoterapia "
        "preespecificada; no es un olvido del concept set."
    )
    save(orphan_decisions, "05_huerfanos_decisiones.csv")

    circe = pd.DataFrame(
        [
            {
                "edge_case": "Identidad y orden de eventos del mismo día",
                "circe_atlas_behavior": (
                    "Conserva eventos candidatos con identificador y ordinal antes "
                    "de seleccionar el evento calificante."
                ),
                "own_sql": (
                    "Reduce directamente a MIN(fecha); un paciente tuvo más de una "
                    "fila índice en el mismo día."
                ),
                "importance_here": (
                    "No cambia la fecha ni N, pero vuelve ambigua la presentación "
                    "responsable; conviene deduplicar de forma determinista."
                ),
            },
            {
                "edge_case": "Múltiples periodos de observación",
                "circe_atlas_behavior": (
                    "Evalúa cada evento dentro de un periodo continuo elegible y "
                    "aplica los días previos/posteriores solicitados."
                ),
                "own_sql": (
                    "Hace un JOIN simple con OBSERVATION_PERIOD y supone un único "
                    "periodo compatible por persona."
                ),
                "importance_here": (
                    "No afecta esta base porque hay un periodo por persona, pero "
                    "sí limita la transportabilidad a datos asistenciales reales."
                ),
            },
            {
                "edge_case": "Colapso final de episodios",
                "circe_atlas_behavior": (
                    "Puede colapsar intervalos solapados o próximos después de "
                    "aplicar la estrategia de salida."
                ),
                "own_sql": (
                    "Conserva sólo el primer episodio por persona y no ejecuta una "
                    "fase general de cohort collapse."
                ),
                "importance_here": (
                    "No cambia esta cohorte de primer episodio, pero sería esencial "
                    "si se permitieran reingresos o episodios recurrentes."
                ),
            },
        ]
    )
    save(circe, "06_comparacion_circe.csv")

    sex_rows = (
        variant_members.groupby(["washout_days", "sex_name"], dropna=False)
        .size()
        .reset_index(name="patients")
    )
    sex_rows["percentage"] = (
        100
        * sex_rows.patients
        / sex_rows.groupby("washout_days").patients.transform("sum")
    ).round(2)
    save(sex_rows, "07_variantes_sexo.csv")

    sensitivity = variants.copy()
    sensitivity["principal_definition"] = sensitivity.washout_days.eq(365)
    sensitivity["nested_checks_pass"] = bool(nesting.passes.astype(bool).all())
    sensitivity["same_members_as_365"] = sensitivity.washout_days.map(
        lambda days: set(
            variant_members.loc[
                variant_members.washout_days.eq(days), "person_id"
            ].astype(int)
        )
        == set(
            variant_members.loc[
                variant_members.washout_days.eq(365), "person_id"
            ].astype(int)
        )
    )
    save(sensitivity, "08_sensibilidad_resumen.csv")

    draw_consort(original, FIGURES / "01_diagrama_atricion_consort.png")

    fig, ax = plt.subplots(figsize=(9, 5.2))
    ax.plot(
        incidence_year.calendar_year,
        incidence_year.cohort_entries,
        color="#2A6F97",
        marker="o",
        linewidth=1.8,
    )
    ax.axvline(
        int(peak_year.calendar_year),
        color="#A23B72",
        linestyle="--",
        linewidth=1.2,
        label=f"Máximo: {int(peak_year.calendar_year)}",
    )
    ax.set_xlabel("Año calendario de entrada")
    ax.set_ylabel("Personas que ingresan")
    ax.set_title("Entradas a la cohorte por año calendario")
    ax.legend(frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(FIGURES / "02_incidencia_anio.png", dpi=220)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 5.2))
    ax.bar(
        incidence_age.age_group,
        incidence_age.cohort_entries,
        color="#457B9D",
        edgecolor="white",
    )
    ax.set_xlabel("Edad en la fecha índice")
    ax.set_ylabel("Personas que ingresan")
    ax.set_title("Entradas a la cohorte por grupo etario")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(FIGURES / "03_incidencia_edad.png", dpi=220)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8.5, 5.2))
    colors = ["#90BE6D", "#2A6F97", "#577590"]
    bars = ax.bar(
        variants.washout_days.astype(str),
        variants.patients,
        color=colors,
        edgecolor="white",
    )
    ax.bar_label(bars, labels=[f"N={int(x)}" for x in variants.patients], padding=4)
    ax.set_xlabel("Lavado preespecificado (días)")
    ax.set_ylabel("Personas en la cohorte")
    ax.set_ylim(0, max(variants.patients) * 1.25)
    ax.set_title("La cohorte no cambia al ampliar el lavado")
    ax.text(
        0.5,
        0.88,
        f"{int(overlap.iloc[0].patients)} personas pertenecen a las tres variantes",
        transform=ax.transAxes,
        ha="center",
        color="#555555",
    )
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(FIGURES / "04_sensibilidad_lavado.png", dpi=220)
    plt.close(fig)

    original_display = original.copy()
    original_display["lost_at_step"] = original_display.lost_at_step.fillna(0).astype(int)
    reordered_display = reordered.copy()
    reordered_display["lost_at_step"] = reordered_display.lost_at_step.fillna(0).astype(int)

    variant_characterization = variants.merge(
        sex_rows.groupby("washout_days").apply(
            lambda x: "; ".join(
                f"{row.sex_name}: {int(row.patients)} ({row.percentage:.1f}%)"
                for row in x.itertuples(index=False)
            ),
            include_groups=False,
        ).rename("sex"),
        on="washout_days",
    )

    comorb_text = []
    for days, group in variant_comorb.groupby("washout_days"):
        names = "; ".join(
            f"{row.concept_name} ({int(row.patients)})"
            for row in group.itertuples(index=False)
        )
        comorb_text.append({"washout_days": int(days), "top3_comorbidities": names})
    variant_characterization = variant_characterization.merge(
        pd.DataFrame(comorb_text), on="washout_days", how="left"
    )

    report = f"""# Diagnóstico de la cohorte

## 1. Factibilidad a posteriori

{md_table(verdict)}

La cohorte contiene **{int(f.cohort_patients)} personas** y tiene un seguimiento
mediano de **{float(f.followup_median_days):.0f} días**
`[{float(f.followup_q1_days):.2f}–{float(f.followup_q3_days):.2f}]`. Durante ese
seguimiento se registraron **{int(f.egfr_measurements)} mediciones de eGFR** en
**{int(f.patients_with_egfr)} personas**. Hubo **{int(f.egfr_below_60_events)}
mediciones por debajo de 60, pero pertenecieron a sólo
**{int(f.patients_with_egfr_below_60)} pacientes**.

**Veredicto:** la base no es factible para ajustar un modelo multivariable de
riesgo renal. Las 65 mediciones son repetidas y correlacionadas dentro de seis
personas; no equivalen a 65 desenlaces independientes. La cohorte sí sirve para
un análisis descriptivo y para demostrar el diseño. Para responder una pregunta
etiológica se necesita una fuente mayor, un comparador activo y más pacientes
con desenlaces renales observables.

### Unidades del desenlace

{md_table(renal_units)}

La coexistencia de dos representaciones de unidad se conserva como limitación.
No se mezclan como si fueran unidades distintas de un mismo valor sin revisar su
semántica y procedencia.

## 2. Atrición en el orden declarado

{md_table(original_display)}

![Diagrama vertical de atrición](figuras/01_diagrama_atricion_consort.png)

La mayor pérdida absoluta se atribuye a T2DM: 835 personas. El criterio de dos
fechas de presión elimina 157 de las 179 restantes y es el más exigente en
términos proporcionales. Ambos precios son coherentes con la pregunta, pero dejan
una cohorte demasiado pequeña para modelado.

## 3. El orden de los criterios

### Orden original

{md_table(original_display[["step", "criterion", "n", "lost_at_step"]])}

### Presión arterial antes de T2DM

{md_table(reordered_display[["step", "criterion", "n", "lost_at_step"]])}

El N final permanece en **{int(original.iloc[-1].n)}**. Sin embargo, al evaluar
primero la presión arterial, ese criterio parece costar 926 personas y T2DM sólo
66. La atrición describe el costo condicional en un orden declarado; no estima
un efecto intrínseco e independiente de cada regla.

## 4. Entradas por año y edad

![Entradas por año](figuras/02_incidencia_anio.png)

![Entradas por grupo etario](figuras/03_incidencia_edad.png)

El máximo anual ocurrió en **{int(peak_year.calendar_year)}**, con
**{int(peak_year.cohort_entries)} entradas**, y el grupo etario más numeroso fue
**{peak_age.age_group}** con **{int(peak_age.cohort_entries)} personas**. Estos son
conteos de entrada, no tasas de incidencia con persona-tiempo. Con sólo 22 casos,
los picos y caídas se interpretan principalmente como propiedades de la captura
sintética, la cobertura temporal y el pequeño denominador, no como cambios en la
enfermedad.

## 5. Códigos que produjeron el evento índice

{md_table(index_codes)}

El producto **{dominant.concept_name}** explica **{float(dominant.percentage):.2f}%**
de las entradas. En la práctica, la cohorte está dominada por esa presentación;
las otras dosis demuestran que la jerarquía evita reducir la definición a un ID
pegado a mano.

## 6. Conceptos huérfanos

{md_table(orphan_decisions)}

Los tres candidatos son reales y frecuentes en la base, pero son combinaciones
de lisinopril con HCTZ. Se mantienen fuera porque la definición principal busca
atribuir la exposición a lisinopril sin ese coprescriptor. Por tanto, son
huérfanos detectados por la búsqueda, pero no falsos negativos del concept set.

## 7. Comparación con ATLAS/CIRCE

{md_table(circe)}

La comparación se basó en la estructura oficial de cohortes OHDSI y en el ejemplo
de nuevos usuarios de IECA. CIRCE convierte una expresión estructurada de cohorte
en SQL; no se copió su SQL generado.

Fuentes:

- [The Book of OHDSI — Defining Cohorts](https://ohdsi.github.io/TheBookOfOhdsi/Cohorts.html)
- [The Book of OHDSI — ACE inhibitors and new users](https://ohdsi.github.io/TheBookOfOhdsi/CohortDefinitions.html#b1-ace-inhibitors)
- [OHDSI CirceR](https://github.com/OHDSI/CirceR)

## 8. Sensibilidad al lavado

La definición principal sigue siendo **365 días**, declarada antes de comparar
los resultados. Las variantes de 180 y 730 días son análisis de sensibilidad.

{md_table(variant_characterization)}

### Tres comorbilidades más frecuentes

{md_table(variant_comorb)}

### Traslape

{md_table(overlap)}

### Verificación de anidamiento

{md_table(nesting)}

![Sensibilidad al lavado](figuras/04_sensibilidad_lavado.png)

Las tres variantes contienen exactamente las mismas 22 personas y cumplen
`730 ⊆ 365 ⊆ 180`. La ausencia de sensibilidad no prueba que la longitud del
lavado sea irrelevante en datos reales: surge porque el índice ya es la primera
exposición observada y Synthea proporciona periodos de observación casi
vitalicios.

## 9. Discusión final

La decisión que más afecta el tamaño no es el lavado, sino exigir T2DM previamente
observado y dos fechas basales de presión arterial. Se conserva como principal la
definición con lavado de 365 días porque equilibra la clasificación de nuevos
usuarios con una ventana basal clínicamente interpretable y fue declarada antes
de revisar las variantes. La limitación central es la combinación de una cohorte
final de 22 personas, sólo seis pacientes con eGFR bajo y sexo no mapeado para
todos los miembros. Antes de cualquier análisis causal también sería necesario
incorporar un comparador activo y verificar las unidades y la frecuencia de
medición renal. En consecuencia, este conjunto de datos permite auditar la
implementación, pero no sustenta conclusiones clínicas sobre el efecto renal de
lisinopril.
"""
    (LAB / "diagnostico_cohorte.md").write_text(report, encoding="utf-8")

    readme = """# Laboratorio 18 — Auditoría de una cohorte

Auditoría de la cohorte de nuevos usuarios de lisinopril construida en el
laboratorio 17 (`cohort_definition_id = 17001`).

## Archivos principales

- `diagnostico_cohorte.md`: factibilidad, atrición, diagnóstico y sensibilidad.
- `figuras/`: diagrama CONSORT, incidencia descriptiva y sensibilidad.
- `evidencias/auditoria/`: resultados directos de la base OMOP.
- `evidencias/analisis/`: tablas interpretadas utilizadas en el reporte.
- `scripts/00_auditar_lab18.py`: auditoría reproducible de DuckDB.
- `scripts/01_generar_lab18.py`: generación del reporte y las figuras.

## Resultado principal

La cohorte contiene 22 personas y sólo seis tienen al menos un eGFR menor de 60.
No es factible ajustar un modelo multivariable de riesgo renal con estos datos,
aunque la cohorte permite demostrar y auditar la implementación.

La definición principal conserva el lavado preespecificado de 365 días. Las
variantes de 180, 365 y 730 días producen los mismos 22 pacientes y cumplen el
anidamiento esperado.

Los scripts no ejecutan `git commit` ni `git push`.
"""
    (LAB / "README.md").write_text(readme, encoding="utf-8")

    shutil.copy2(AUDIT / "04_atricion_original.csv", ANALYSIS / "09_atricion_original.csv")
    shutil.copy2(AUDIT / "05_atricion_reordenada.csv", ANALYSIS / "10_atricion_reordenada.csv")
    shutil.copy2(AUDIT / "13_traslape_variantes.csv", ANALYSIS / "11_traslape_variantes.csv")
    shutil.copy2(AUDIT / "14_verificacion_anidamiento.csv", ANALYSIS / "12_anidamiento.csv")

    print("\n===== LABORATORIO 18 GENERADO =====")
    print("Cohorte:", int(f.cohort_patients), "personas")
    print("Pacientes con eGFR < 60:", int(f.patients_with_egfr_below_60))
    print("N final en ambos órdenes:", int(original.iloc[-1].n))
    print("Concepto índice dominante:", f"{float(dominant.percentage):.2f}%")
    print("Variantes de lavado:", ", ".join(str(int(x)) for x in variants.patients))
    print("Commit y push: NO ejecutados")


if __name__ == "__main__":
    main()

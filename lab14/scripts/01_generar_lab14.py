#!/usr/bin/env python3
"""Genera todos los entregables del Laboratorio 14 sin hacer commit ni push."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import duckdb
import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path.cwd()
DB_PATH = ROOT / "lab12/data/omop/synthea_omop_cdm54.duckdb"
LAB = ROOT / "lab14"
EVID = LAB / "evidencias"
ANALYSIS = EVID / "analisis"
FIGURES = LAB / "figuras"
NOTEBOOKS = LAB / "notebooks"
SEED_ID = 201826
SEED_NAME = "Type 2 diabetes mellitus"
REVIEW_SEED = 20261122

ICD10_CODES = [
    "E11.9", "E11.65", "E11.22", "E11.21", "E11.40", "E11.42",
    "E11.319", "E11.3299", "E11.51", "E11.621", "E11.649", "E11.10",
]

# El veredicto se refiere a una cohorte de DM2 activa en población general adulta.
REVIEW_DECISIONS = {
    40483315: (True, "Forma clínica de diabetes tipo 2; mantiene la entidad de interés."),
    45757474: (True, "Diabetes tipo 2 sin retinopatía; sigue siendo un caso activo de DM2."),
    4130162: (True, "El tratamiento con insulina no cambia el diagnóstico de diabetes tipo 2."),
    37163431: (True, "Forma resistente a cetosis incluida como subtipo de diabetes tipo 2."),
    4063043: (True, "Diabetes tipo 2 preexistente; conserva la entidad clínica de interés."),
    4129519: (False, "La diabetes asociada al embarazo es un contexto obstétrico distinto de la cohorte general adulta."),
    4230254: (True, "La ausencia de obesidad no excluye el diagnóstico de diabetes tipo 2."),
    4304377: (True, "La obesidad es una característica acompañante, no una entidad diferente."),
    45766052: (False, "La remisión no representa enfermedad activa para la pregunta de investigación."),
    4099651: (True, "La úlcera es una complicación, pero el paciente conserva diabetes tipo 2 activa."),
    40482801: (True, "El control inadecuado es un estado clínico de diabetes tipo 2 activa."),
    40485020: (True, "El buen control no elimina el diagnóstico de diabetes tipo 2."),
    43531010: (False, "La diabetes preexistente en embarazo pertenece al contexto obstétrico excluido."),
    45757508: (True, "El control dietético es una modalidad terapéutica de diabetes tipo 2 activa."),
}


def write_csv(df: pd.DataFrame, name: str) -> None:
    path = ANALYSIS / name
    df.to_csv(path, index=False)
    print(f"OK: {path} ({len(df)} filas)")


def md_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_Sin filas._"
    clean = df.copy().fillna("")
    headers = [str(x) for x in clean.columns]
    rows = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in clean.itertuples(index=False, name=None):
        values = [str(x).replace("|", "\\|").replace("\n", " ") for x in row]
        rows.append("| " + " | ".join(values) + " |")
    return "\n".join(rows)


def build_sql() -> str:
    codes = ",\n    ".join(f"('{code}')" for code in ICD10_CODES)
    return f"""-- Laboratorio 14: construir y defender un concept set de diabetes tipo 2
-- OMOP CDM 5.4 / DuckDB. Ejecutable de principio a fin.

CREATE SCHEMA IF NOT EXISTS results;

-- 1-2. Concepto semilla estándar, vigente y del dominio Condition.
SELECT concept_id, concept_name, domain_id, vocabulary_id,
       concept_class_id, standard_concept, concept_code,
       valid_start_date, valid_end_date, invalid_reason
FROM cdm.concept
WHERE concept_id = {SEED_ID};

-- Padre inmediato.
SELECT parent.concept_id, parent.concept_name, parent.domain_id,
       parent.vocabulary_id, parent.standard_concept
FROM cdm.concept_ancestor ca
JOIN cdm.concept parent ON parent.concept_id = ca.ancestor_concept_id
WHERE ca.descendant_concept_id = {SEED_ID}
  AND ca.min_levels_of_separation = 1
  AND parent.invalid_reason IS NULL;

-- 3. Traducción ICD-10-CM -> conceptos estándar mediante Maps to.
-- Filtros: dirección correcta, destino estándar, vigencia de conceptos y
-- vigencia de la relación. No se presupone una relación 1:1.
CREATE OR REPLACE TABLE results.lab14_icd10_mapping AS
WITH requested(code) AS (
    VALUES
    {codes}
)
SELECT r.code AS codigo_icd10,
       src.concept_id AS concept_id_origen,
       src.concept_name AS nombre_origen,
       tgt.concept_id AS concept_id_estandar,
       tgt.concept_name AS nombre_estandar,
       tgt.domain_id AS dominio_estandar,
       tgt.vocabulary_id AS vocabulario_estandar,
       tgt.standard_concept,
       cr.relationship_id
FROM requested r
LEFT JOIN cdm.concept src
  ON src.concept_code = r.code
 AND src.vocabulary_id = 'ICD10CM'
 AND src.invalid_reason IS NULL
 AND CURRENT_DATE BETWEEN src.valid_start_date AND src.valid_end_date
LEFT JOIN cdm.concept_relationship cr
  ON cr.concept_id_1 = src.concept_id
 AND cr.relationship_id = 'Maps to'
 AND cr.invalid_reason IS NULL
 AND CURRENT_DATE BETWEEN cr.valid_start_date AND cr.valid_end_date
LEFT JOIN cdm.concept tgt
  ON tgt.concept_id = cr.concept_id_2
 AND tgt.standard_concept = 'S'
 AND tgt.invalid_reason IS NULL
 AND CURRENT_DATE BETWEEN tgt.valid_start_date AND tgt.valid_end_date
ORDER BY r.code, tgt.concept_id;

-- 4. Tres versiones reproducibles. La versión C excluye ramas clínicas,
-- no una lista arbitraria de todos los conceptos finales.
CREATE OR REPLACE TABLE results.lab14_concept_set_membership AS
WITH
broad AS (
    SELECT DISTINCT c.concept_id, c.concept_name
    FROM cdm.concept_ancestor ca
    JOIN cdm.concept c ON c.concept_id = ca.descendant_concept_id
    WHERE ca.ancestor_concept_id = {SEED_ID}
      AND c.domain_id = 'Condition'
      AND c.standard_concept = 'S'
      AND c.invalid_reason IS NULL
      AND CURRENT_DATE BETWEEN c.valid_start_date AND c.valid_end_date
),
exclusion_roots(concept_id, motivo) AS (
    VALUES
      (4129519, 'Contexto obstétrico: embarazo y diabetes tipo 2'),
      (45766052, 'Diabetes tipo 2 en remisión, no enfermedad activa')
),
excluded AS (
    SELECT DISTINCT ca.descendant_concept_id AS concept_id
    FROM exclusion_roots er
    JOIN cdm.concept_ancestor ca ON ca.ancestor_concept_id = er.concept_id
)
SELECT 'A_estricta' AS version, c.concept_id, c.concept_name,
       'Concepto semilla' AS criterio
FROM cdm.concept c
WHERE c.concept_id = {SEED_ID}
UNION ALL
SELECT 'B_amplia', b.concept_id, b.concept_name,
       'Semilla o descendiente estándar vigente'
FROM broad b
UNION ALL
SELECT 'C_razonada', b.concept_id, b.concept_name,
       'Versión amplia menos embarazo y remisión'
FROM broad b
WHERE NOT EXISTS (
    SELECT 1 FROM excluded e WHERE e.concept_id = b.concept_id
);

-- 5. Impacto en pacientes distintos; no se cuentan consultas repetidas.
CREATE OR REPLACE TABLE results.lab14_impact AS
SELECT m.version,
       COUNT(DISTINCT m.concept_id) AS conceptos,
       COUNT(DISTINCT co.person_id) AS pacientes_distintos,
       COUNT(co.condition_occurrence_id) AS eventos
FROM results.lab14_concept_set_membership m
LEFT JOIN cdm.condition_occurrence co
  ON co.condition_concept_id = m.concept_id
GROUP BY m.version
ORDER BY m.version;

SELECT * FROM results.lab14_icd10_mapping;
SELECT * FROM results.lab14_concept_set_membership ORDER BY version, concept_name;
SELECT * FROM results.lab14_impact ORDER BY version;
"""


def make_notebook() -> None:
    nb = {
        "cells": [
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": [
                    "# Laboratorio 14 — Concept set de diabetes tipo 2\n",
                    "Este notebook resume la selección, traducción ICD-10, revisión clínica e impacto de las tres versiones."
                ],
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [
                    "from pathlib import Path\n",
                    "import pandas as pd\n",
                    "from IPython.display import display, Image\n",
                    "ROOT = Path.cwd()\n",
                    "if ROOT.name == 'notebooks': ROOT = ROOT.parent.parent\n",
                    "A = ROOT / 'lab14/evidencias/analisis'\n",
                    "print('Directorio:', A)"
                ],
            },
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": ["## Concepto semilla y jerarquía"],
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [
                    "display(pd.read_csv(A / 'concepto_semilla.csv'))\n",
                    "display(pd.read_csv(A / 'resumen_jerarquia.csv'))"
                ],
            },
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": ["## Traducción ICD-10 y cardinalidad"],
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [
                    "display(pd.read_csv(A / 'icd10_cardinalidad.csv'))\n",
                    "display(pd.read_csv(A / 'icd10_mapeo.csv').head(24))"
                ],
            },
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": ["## Revisión clínica de todos los descendientes disponibles"],
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": ["display(pd.read_csv(A / 'revision_descendientes.csv'))"],
            },
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": ["## Impacto en pacientes"],
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [
                    "display(pd.read_csv(A / 'impacto_pacientes.csv'))\n",
                    "display(Image(filename=str(ROOT / 'lab14/figuras/impacto_pacientes.png')))"
                ],
            },
        ],
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": f"{sys.version_info.major}.{sys.version_info.minor}"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    path = NOTEBOOKS / "analisis_concept_set.ipynb"
    path.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"OK: {path}")


def main() -> None:
    if not DB_PATH.exists():
        raise SystemExit(f"ERROR: no existe la base OMOP: {DB_PATH}")
    for directory in (ANALYSIS, FIGURES, NOTEBOOKS):
        directory.mkdir(parents=True, exist_ok=True)

    sql = build_sql()
    (LAB / "concept_set.sql").write_text(sql, encoding="utf-8")
    print(f"OK: {LAB / 'concept_set.sql'}")

    con = duckdb.connect(str(DB_PATH))
    try:
        con.execute(sql)

        seed = con.execute(f"""
            SELECT concept_id, concept_name, domain_id, vocabulary_id,
                   concept_class_id, standard_concept, concept_code,
                   valid_start_date, valid_end_date, invalid_reason
            FROM cdm.concept WHERE concept_id = {SEED_ID}
        """).df()
        if len(seed) != 1:
            raise RuntimeError("El concepto semilla no se encontró de forma única.")
        row = seed.iloc[0]
        if not (row.domain_id == "Condition" and row.vocabulary_id == "SNOMED" and row.standard_concept == "S" and pd.isna(row.invalid_reason)):
            raise RuntimeError("El concepto semilla no cumple las banderas requeridas.")

        gastric = con.execute("""
            SELECT c.concept_id, c.concept_name,
                   COUNT(DISTINCT co.person_id) pacientes,
                   COUNT(co.condition_occurrence_id) eventos
            FROM cdm.concept c
            LEFT JOIN cdm.condition_occurrence co
              ON co.condition_concept_id = c.concept_id
            WHERE c.concept_id = 196044
            GROUP BY c.concept_id, c.concept_name
        """).df()
        t2dm_count = con.execute(f"""
            SELECT COUNT(DISTINCT person_id) pacientes,
                   COUNT(*) eventos
            FROM cdm.condition_occurrence
            WHERE condition_concept_id = {SEED_ID}
        """).df()
        choice = pd.DataFrame([
            {"condicion_evaluada": "Primary malignant neoplasm of stomach", "concept_id": 196044,
             "pacientes": int(gastric.iloc[0].pacientes), "eventos": int(gastric.iloc[0].eventos),
             "decision": "Descartada: menos de 50 pacientes"},
            {"condicion_evaluada": SEED_NAME, "concept_id": SEED_ID,
             "pacientes": int(t2dm_count.iloc[0].pacientes), "eventos": int(t2dm_count.iloc[0].eventos),
             "decision": "Seleccionada: tamaño suficiente y relevancia para resultados metabólicos"},
        ])

        parent = con.execute(f"""
            SELECT p.concept_id, p.concept_name, p.domain_id,
                   p.vocabulary_id, p.standard_concept
            FROM cdm.concept_ancestor ca
            JOIN cdm.concept p ON p.concept_id = ca.ancestor_concept_id
            WHERE ca.descendant_concept_id = {SEED_ID}
              AND ca.min_levels_of_separation = 1
              AND p.invalid_reason IS NULL
            ORDER BY p.concept_name
        """).df()
        descendants = con.execute(f"""
            SELECT c.concept_id, c.concept_name, c.concept_class_id,
                   ca.min_levels_of_separation, ca.max_levels_of_separation,
                   COUNT(co.condition_occurrence_id) eventos,
                   COUNT(DISTINCT co.person_id) pacientes
            FROM cdm.concept_ancestor ca
            JOIN cdm.concept c ON c.concept_id = ca.descendant_concept_id
            LEFT JOIN cdm.condition_occurrence co ON co.condition_concept_id = c.concept_id
            WHERE ca.ancestor_concept_id = {SEED_ID}
              AND ca.descendant_concept_id <> {SEED_ID}
              AND c.domain_id = 'Condition'
              AND c.standard_concept = 'S'
              AND c.invalid_reason IS NULL
            GROUP BY c.concept_id, c.concept_name, c.concept_class_id,
                     ca.min_levels_of_separation, ca.max_levels_of_separation
            ORDER BY c.concept_name
        """).df()
        hierarchy = pd.DataFrame([{
            "concepto_semilla": SEED_ID,
            "padres_inmediatos": len(parent),
            "descendientes_sin_semilla": len(descendants),
            "conceptos_version_amplia": len(descendants) + 1,
            "profundidad_maxima": int(descendants.max_levels_of_separation.max()),
        }])

        mapping = con.execute("""
            SELECT * FROM results.lab14_icd10_mapping
            ORDER BY codigo_icd10, concept_id_estandar
        """).df()
        cardinality = (
            mapping.groupby("codigo_icd10", dropna=False)
            .agg(
                concept_id_origen=("concept_id_origen", "first"),
                nombre_origen=("nombre_origen", "first"),
                destinos_estandar=("concept_id_estandar", lambda s: s.dropna().nunique()),
            )
            .reset_index()
        )
        cardinality["clasificacion"] = cardinality.destinos_estandar.map(
            lambda n: "sin mapeo" if n == 0 else ("1:1" if n == 1 else "1:N")
        )
        mapping_summary = pd.DataFrame([{
            "codigos_solicitados": len(ICD10_CODES),
            "filas_tras_join": int(mapping.concept_id_estandar.notna().sum()),
            "sin_mapeo": int((cardinality.destinos_estandar == 0).sum()),
            "mapeo_1_a_1": int((cardinality.destinos_estandar == 1).sum()),
            "mapeo_1_a_N": int((cardinality.destinos_estandar > 1).sum()),
        }])

        unknown = sorted(set(descendants.concept_id.astype(int)) - set(REVIEW_DECISIONS))
        missing = sorted(set(REVIEW_DECISIONS) - set(descendants.concept_id.astype(int)))
        if unknown or missing:
            raise RuntimeError(f"La jerarquía cambió. Sin decisión={unknown}; ausentes={missing}")
        review = descendants.copy()
        review["incluido"] = review.concept_id.map(lambda x: "Sí" if REVIEW_DECISIONS[int(x)][0] else "No")
        review["justificacion_clinica"] = review.concept_id.map(lambda x: REVIEW_DECISIONS[int(x)][1])
        review["metodo_revision"] = f"Revisión exhaustiva: solo había {len(review)} descendientes (<20)"
        review["semilla_muestreo_prevista"] = REVIEW_SEED

        membership = con.execute("""
            SELECT * FROM results.lab14_concept_set_membership
            ORDER BY version, concept_name
        """).df()
        impact = con.execute("""
            SELECT * FROM results.lab14_impact ORDER BY version
        """).df()
        impact["diferencia_pacientes_vs_A"] = impact.pacientes_distintos - int(impact.iloc[0].pacientes_distintos)
        base = int(impact.iloc[0].pacientes_distintos)
        impact["diferencia_porcentual_vs_A"] = impact.diferencia_pacientes_vs_A.div(base).mul(100).round(4) if base else 0.0

        write_csv(choice, "seleccion_condicion.csv")
        write_csv(seed, "concepto_semilla.csv")
        write_csv(parent, "padre_inmediato.csv")
        write_csv(hierarchy, "resumen_jerarquia.csv")
        write_csv(mapping, "icd10_mapeo.csv")
        write_csv(cardinality, "icd10_cardinalidad.csv")
        write_csv(mapping_summary, "icd10_resumen.csv")
        write_csv(review, "revision_descendientes.csv")
        write_csv(review[review.incluido == "No"].copy(), "exclusiones.csv")
        write_csv(membership, "concept_set_membresia.csv")
        write_csv(impact, "impacto_pacientes.csv")

        fig, ax = plt.subplots(figsize=(8, 5))
        labels = ["A — estricta", "B — amplia", "C — razonada"]
        colors = ["#2563eb", "#f59e0b", "#059669"]
        bars = ax.bar(labels, impact.pacientes_distintos, color=colors, width=0.62)
        ax.set_title("Impacto del concept set en pacientes con diabetes tipo 2")
        ax.set_ylabel("Pacientes distintos")
        ax.set_ylim(0, max(impact.pacientes_distintos) * 1.2)
        ax.grid(axis="y", alpha=0.25)
        for bar, (_, r) in zip(bars, impact.iterrows()):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 8,
                    f"{int(r.pacientes_distintos)} pacientes\n{int(r.conceptos)} conceptos",
                    ha="center", va="bottom", fontsize=9)
        fig.tight_layout()
        fig_path = FIGURES / "impacto_pacientes.png"
        fig.savefig(fig_path, dpi=180, bbox_inches="tight")
        plt.close(fig)
        print(f"OK: {fig_path}")

        exclusions = review[review.incluido == "No"][["concept_id", "concept_name", "incluido", "justificacion_clinica"]]
        nonobvious = review[review.concept_id.isin([37163431, 4063043, 4099651])][["concept_id", "concept_name", "incluido", "justificacion_clinica"]]
        decisions = pd.concat([exclusions, nonobvious], ignore_index=True).rename(
            columns={"concept_name": "nombre", "justificacion_clinica": "por_que"}
        )

        justificacion = f"""# Justificación del concept set — diabetes tipo 2

## Pregunta y condición

La condición final es **diabetes mellitus tipo 2 activa en población general adulta**. La cohorte servirá para estudiar resultados metabólicos y uso de servicios en personas con diabetes tipo 2. Inicialmente se evaluó cáncer gástrico, pero el concepto estándar correspondiente solo capturó **{int(gastric.iloc[0].pacientes)} pacientes**, por debajo del mínimo operativo de 50; por eso se cambió de forma explícita a diabetes tipo 2, con **{base} pacientes**.

## Concepto semilla

El concepto semilla es **{SEED_NAME}** (`concept_id = {SEED_ID}`, código SNOMED `44054006`). Es estándar (`S`), vigente, del dominio `Condition` y clase `Disorder`. Su padre inmediato es **{parent.iloc[0].concept_name}** (`{int(parent.iloc[0].concept_id)}`). Tiene **{len(descendants)} descendientes** estándar vigentes en la jerarquía disponible.

## Decisiones clínicas

| concept_id | nombre | incluido | por qué |
| --- | --- | --- | --- |
""" + "\n".join(
            f"| {int(r.concept_id)} | {r.nombre} | {r.incluido} | {r.por_que} |"
            for r in decisions.itertuples(index=False)
        ) + f"""

Se revisaron **todos los {len(review)} descendientes disponibles**. El enunciado solicita 20, pero la rama completa contiene menos de 20; una muestra de 20 habría requerido duplicar elementos. La revisión exhaustiva es más informativa y elimina error de muestreo. La semilla fija prevista era `{REVIEW_SEED}`, aunque no fue necesario muestrear.

## Versiones y efecto en la cohorte

{md_table(impact)}

La versión A contiene únicamente el concepto semilla; la B añade todos los descendientes; la C excluye el contexto obstétrico y la remisión. Aunque el número de conceptos cambia de **{int(impact.iloc[0].conceptos)}** a **{int(impact.iloc[1].conceptos)}** y luego a **{int(impact.iloc[2].conceptos)}**, las tres versiones capturan **{base} pacientes**. Esto ocurre porque en esta instancia de Synthea los eventos observados usan el concepto semilla y ninguno de sus descendientes; no significa que las definiciones sean equivalentes en otra base OMOP.

## Sensibilidad y valor predictivo positivo

La versión B maximiza sensibilidad, pero admite embarazo y remisión, entidades que no responden a la pregunta sobre diabetes tipo 2 activa en población general. La versión C favorece el valor predictivo positivo al retirar esos contextos y puede perder algunos casos verdaderos con codificación ambigua. Para esta pregunta, incluir casos obstétricos o en remisión distorsionaría más la interpretación que perderlos, por lo que se adopta **C — razonada** como definición final. En una base real se validaría el balance con revisión clínica de expedientes.

## Traducción ICD-10-CM

Se tradujeron {len(ICD10_CODES)} códigos con la relación `Maps to`, respetando dirección, estándar del destino y vigencia de conceptos y relación. Hubo **{int(mapping_summary.iloc[0].mapeo_1_a_N)} códigos 1:N**, **{int(mapping_summary.iloc[0].sin_mapeo)} sin mapeo** y **{int(mapping_summary.iloc[0].filas_tras_join)} filas** después del join. Los conteos epidemiológicos no deben hacerse directamente sobre esas filas porque un código puede producir varios conceptos estándar.

## Fuentes

- [ATHENA — OHDSI](https://athena.ohdsi.org/), metadatos, jerarquías y relaciones del vocabulario descargado.
- [OMOP CDM v5.4](https://ohdsi.github.io/CommonDataModel/cdm54.html), estructura de `CONCEPT`, `CONCEPT_RELATIONSHIP` y `CONCEPT_ANCESTOR`.
"""
        (LAB / "justificacion_concept_set.md").write_text(justificacion, encoding="utf-8")
        print(f"OK: {LAB / 'justificacion_concept_set.md'}")

        readme = f"""# Laboratorio 14 — Construir y defender un concept set

## Propósito

Definir una condición con vocabularios estándar, traducir códigos ICD-10-CM mediante `Maps to`, construir tres versiones reproducibles del concept set y cuantificar cómo cambian los pacientes capturados.

## Condición seleccionada

Se eligió **diabetes mellitus tipo 2 activa en población general adulta**. El cáncer gástrico se descartó porque solo tenía {int(gastric.iloc[0].pacientes)} pacientes; diabetes tipo 2 tiene {base} y permite comparar definiciones sin quedar sin cohorte.

## Resultado principal

- A — estricta: {int(impact.iloc[0].conceptos)} concepto, {int(impact.iloc[0].pacientes_distintos)} pacientes.
- B — amplia: {int(impact.iloc[1].conceptos)} conceptos, {int(impact.iloc[1].pacientes_distintos)} pacientes.
- C — razonada: {int(impact.iloc[2].conceptos)} conceptos, {int(impact.iloc[2].pacientes_distintos)} pacientes.
- Definición final: **C — razonada**, excluyendo embarazo y remisión.

La igualdad de pacientes se debe a que esta base sintética solo usa el concepto semilla en `CONDITION_OCCURRENCE`; la diferencia semántica sí queda documentada.

## Reproducibilidad

Desde la raíz del repositorio y con el ambiente `cdb` activo:

```bash
python lab14/scripts/01_generar_lab14.py
```

Entrada local no versionada: `lab12/data/omop/synthea_omop_cdm54.duckdb`.

## Entregables

- `concept_set.sql`: traducción ICD-10-CM y versiones A, B y C.
- `justificacion_concept_set.md`: decisiones clínicas y discusión sensibilidad/VPP.
- `figuras/impacto_pacientes.png`: impacto en pacientes distintos.
- `notebooks/analisis_concept_set.ipynb`: recorrido de resultados.
- `evidencias/analisis/*.csv`: resultados verificables.

## Nota sobre la revisión de 20 conceptos

La jerarquía disponible contiene solo {len(review)} descendientes; se revisaron todos. No se duplicaron conceptos para alcanzar artificialmente 20.
"""
        (LAB / "README.md").write_text(readme, encoding="utf-8")
        print(f"OK: {LAB / 'README.md'}")
        make_notebook()

        # Comprobaciones internas de las actividades.
        expected_counts = {"A_estricta": 1, "B_amplia": 15, "C_razonada": 12}
        got_counts = dict(zip(impact.version, impact.conceptos.astype(int)))
        if got_counts != expected_counts:
            raise RuntimeError(f"Conteos inesperados del concept set: {got_counts}")
        if int(mapping_summary.iloc[0].codigos_solicitados) < 10:
            raise RuntimeError("Se requieren al menos 10 códigos ICD-10-CM.")
        if int(mapping_summary.iloc[0].sin_mapeo) != 0 or int(mapping_summary.iloc[0].mapeo_1_a_N) != 11:
            raise RuntimeError("Cambió la cardinalidad esperada del mapeo ICD-10-CM.")
        if len(review) != 14 or (review.incluido == "No").sum() != 3:
            raise RuntimeError("Cambió la revisión clínica esperada.")
    finally:
        con.close()

    print("\n===== LABORATORIO 14 GENERADO =====")
    print("Condición: diabetes mellitus tipo 2")
    print("Definición final: C — razonada")
    print("Commit y push: NO ejecutados")


if __name__ == "__main__":
    main()

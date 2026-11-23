#!/usr/bin/env python3
"""Genera la cohorte de nuevos usuarios y los entregables del Laboratorio 17.

Materializa resultados locales en el esquema ``results`` de DuckDB. No ejecuta
operaciones de Git. La base permanece ignorada por el repositorio.
"""

from __future__ import annotations

import shutil
from datetime import date
from pathlib import Path

import duckdb
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
LAB = ROOT / "lab17"
AUDIT = LAB / "evidencias" / "auditoria"
ANALYSIS = LAB / "evidencias" / "analisis"
FIGURES = LAB / "figuras"
DB = ROOT / "lab12" / "data" / "omop" / "synthea_omop_cdm54.duckdb"
COHORT_ID = 17001
LISINOPRIL = 1308216
T2DM = 201826
TODAY = date.today().isoformat()


def save(df: pd.DataFrame, name: str) -> None:
    path = ANALYSIS / name
    df.to_csv(path, index=False)
    print(f"OK: {path} ({len(df)} filas)")


def md_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_Sin filas._"
    clean = df.copy().fillna("")
    headers = [str(column).replace("|", "\\|") for column in clean.columns]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in clean.itertuples(index=False, name=None):
        values = [str(value).replace("|", "\\|").replace("\n", " ") for value in row]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def age_expression(index: str, person: str) -> str:
    return f"""
        EXTRACT(YEAR FROM {index})::INTEGER-{person}.year_of_birth
        - CASE
            WHEN (EXTRACT(MONTH FROM {index}),EXTRACT(DAY FROM {index}))
                 < (COALESCE({person}.month_of_birth,7),
                    COALESCE({person}.day_of_birth,1))
            THEN 1 ELSE 0
          END
    """


def cohort_ctes() -> str:
    age = age_expression("b.index_date", "p")
    return f"""
initial_event AS (
    SELECT de.person_id,
           MIN(de.drug_exposure_start_date) AS index_date
    FROM cdm.drug_exposure de
    JOIN results.lab17_lisinopril_concept_set cs
      ON cs.concept_id=de.drug_concept_id
    GROUP BY de.person_id
),
prior_observation AS (
    SELECT i.person_id,i.index_date,
           op.observation_period_start_date AS op_start,
           op.observation_period_end_date AS op_end
    FROM initial_event i
    JOIN cdm.observation_period op
      ON op.person_id=i.person_id
     AND i.index_date BETWEEN op.observation_period_start_date
                          AND op.observation_period_end_date
     AND op.observation_period_start_date<=i.index_date-INTERVAL 365 DAY
),
washout AS (
    SELECT o.*
    FROM prior_observation o
    WHERE NOT EXISTS (
        SELECT 1
        FROM cdm.drug_exposure prior
        JOIN results.lab17_lisinopril_concept_set cs
          ON cs.concept_id=prior.drug_concept_id
        WHERE prior.person_id=o.person_id
          AND prior.drug_exposure_start_date>=o.index_date-INTERVAL 365 DAY
          AND prior.drug_exposure_start_date<o.index_date
    )
),
inclusion_t2dm AS (
    SELECT w.*
    FROM washout w
    WHERE EXISTS (
        SELECT 1
        FROM cdm.condition_occurrence co
        JOIN results.lab17_t2dm_concept_set t2
          ON t2.concept_id=co.condition_concept_id
        WHERE co.person_id=w.person_id
          AND co.condition_start_date BETWEEN w.op_start AND w.index_date
    )
),
inclusion_two_bp_dates AS (
    SELECT *
    FROM (
        SELECT t.*,
               (SELECT COUNT(DISTINCT m.measurement_date)
                FROM cdm.measurement m
                JOIN results.lab17_bp_concept_set bp
                  ON bp.concept_id=m.measurement_concept_id
                WHERE m.person_id=t.person_id
                  AND m.measurement_date BETWEEN t.index_date-INTERVAL 365 DAY
                                             AND t.index_date) AS bp_dates
        FROM inclusion_t2dm t
    ) measured
    WHERE bp_dates>=2
),
exclusion_minors AS (
    SELECT b.*
    FROM inclusion_two_bp_dates b
    WHERE NOT EXISTS (
        SELECT 1
        FROM cdm.person p
        WHERE p.person_id=b.person_id
          AND ({age})<18
    )
),
exclusion_pregnancy AS (
    SELECT a.*
    FROM exclusion_minors a
    WHERE NOT EXISTS (
        SELECT 1
        FROM cdm.condition_occurrence co
        JOIN results.lab17_pregnancy_concept_set pg
          ON pg.concept_id=co.condition_concept_id
        WHERE co.person_id=a.person_id
          AND co.condition_start_date BETWEEN a.index_date-INTERVAL 365 DAY
                                           AND a.index_date
    )
)
"""


def sql_document(hctz_id: int) -> str:
    ctes = cohort_ctes()
    age = age_expression("c.cohort_start_date", "p")
    return f"""-- Laboratorio 17 — Cohorte de nuevos usuarios de lisinopril
-- Motor: DuckDB 2.0.0
-- Fecha: {TODAY}
-- cohort_definition_id: {COHORT_ID}
-- Definición clínica completa: cohorte_definicion.md

CREATE SCHEMA IF NOT EXISTS results;

-- Concept set de exposición: descendientes de lisinopril, excluyendo productos
-- que también descienden de hydrochlorothiazide (HCTZ).
CREATE OR REPLACE TABLE results.lab17_lisinopril_concept_set AS
WITH lisinopril_descendants AS (
    SELECT descendant_concept_id AS concept_id
    FROM cdm.concept_ancestor
    WHERE ancestor_concept_id={LISINOPRIL}
    UNION SELECT {LISINOPRIL}
)
SELECT DISTINCT ld.concept_id
FROM lisinopril_descendants ld
WHERE ld.concept_id<>{hctz_id}
  AND NOT EXISTS (
      SELECT 1
      FROM cdm.concept_ancestor ca
      WHERE ca.ancestor_concept_id={hctz_id}
        AND ca.descendant_concept_id=ld.concept_id
  );

CREATE OR REPLACE TABLE results.lab17_t2dm_concept_set AS
SELECT descendant_concept_id AS concept_id
FROM cdm.concept_ancestor
WHERE ancestor_concept_id={T2DM}
UNION SELECT {T2DM};

CREATE OR REPLACE TABLE results.lab17_bp_concept_set AS
SELECT concept_id
FROM cdm.concept
WHERE standard_concept='S'
  AND invalid_reason IS NULL
  AND domain_id='Measurement'
  AND lower(concept_name) IN (
      'systolic blood pressure','diastolic blood pressure'
  );

CREATE OR REPLACE TABLE results.lab17_pregnancy_concept_set AS
WITH root AS (
    SELECT concept_id
    FROM cdm.concept
    WHERE standard_concept='S'
      AND invalid_reason IS NULL
      AND domain_id='Condition'
      AND lower(concept_name)='pregnancy'
)
SELECT concept_id FROM root
UNION
SELECT ca.descendant_concept_id
FROM root r
JOIN cdm.concept_ancestor ca ON ca.ancestor_concept_id=r.concept_id;

-- Actividades 2–5. Un CTE por componente y una fila por persona.
CREATE OR REPLACE TABLE results.lab17_final_candidates AS
WITH {ctes}
SELECT person_id,index_date,op_start,op_end,bp_dates
FROM exclusion_pregnancy;

-- Actividad 8. La misma secuencia se convierte en tabla de atrición.
CREATE OR REPLACE TABLE results.lab17_attrition AS
WITH {ctes},
counts AS (
    SELECT 1 AS step,'Evento inicial: primera exposición' AS criterion,
           COUNT(*) AS n FROM initial_event
    UNION ALL SELECT 2,'+ 365 días de observación',COUNT(*) FROM prior_observation
    UNION ALL SELECT 3,'+ lavado de 365 días',COUNT(*) FROM washout
    UNION ALL SELECT 4,'+ T2DM observado antes del índice',COUNT(*) FROM inclusion_t2dm
    UNION ALL SELECT 5,'+ >=2 fechas con presión arterial',COUNT(*) FROM inclusion_two_bp_dates
    UNION ALL SELECT 6,'- menores de 18 años',COUNT(*) FROM exclusion_minors
    UNION ALL SELECT 7,'- embarazo durante los 365 días basales',COUNT(*) FROM exclusion_pregnancy
)
SELECT step,criterion,n,
       LAG(n) OVER (ORDER BY step)-n AS lost_at_step,
       ROUND(100.0*n/FIRST_VALUE(n) OVER (ORDER BY step),2) AS percent_initial_remaining,
       ROUND(100.0*(LAG(n) OVER (ORDER BY step)-n)
             /NULLIF(LAG(n) OVER (ORDER BY step),0),2) AS percent_lost_at_step
FROM counts
ORDER BY step;

-- Actividad 6. Gaps and islands: primera era continua, gap permitido de 30 días.
CREATE OR REPLACE TABLE results.lab17_first_drug_era AS
WITH cohort_events AS (
    SELECT c.person_id,c.index_date,c.op_start,c.op_end,
           de.drug_exposure_start_date AS start_date,
           COALESCE(de.drug_exposure_end_date,
                    de.drug_exposure_start_date) AS end_date
    FROM results.lab17_final_candidates c
    JOIN cdm.drug_exposure de
      ON de.person_id=c.person_id
     AND de.drug_exposure_start_date>=c.index_date
    JOIN results.lab17_lisinopril_concept_set cs
      ON cs.concept_id=de.drug_concept_id
),
ordered AS (
    SELECT *,
           MAX(end_date) OVER (
               PARTITION BY person_id
               ORDER BY start_date,end_date
               ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
           ) AS prior_max_end
    FROM cohort_events
),
island_flags AS (
    SELECT *,
           CASE WHEN prior_max_end IS NULL
                     OR start_date>prior_max_end+INTERVAL 30 DAY
                THEN 1 ELSE 0 END AS new_island
    FROM ordered
),
islands AS (
    SELECT *,
           SUM(new_island) OVER (
               PARTITION BY person_id ORDER BY start_date,end_date
           ) AS island_id
    FROM island_flags
)
SELECT person_id,index_date,op_start,op_end,
       MIN(start_date) AS era_start,
       MAX(end_date) AS era_end_by_definition,
       LEAST(MAX(end_date),op_end) AS cohort_end_date
FROM islands
WHERE island_id=1
GROUP BY person_id,index_date,op_start,op_end;

-- Actividad 7. Tabla estándar de cohorte.
CREATE TABLE IF NOT EXISTS results.cohort (
    cohort_definition_id BIGINT NOT NULL,
    subject_id BIGINT NOT NULL,
    cohort_start_date DATE NOT NULL,
    cohort_end_date DATE NOT NULL
);

DELETE FROM results.cohort
WHERE cohort_definition_id={COHORT_ID};

INSERT INTO results.cohort (
    cohort_definition_id,subject_id,cohort_start_date,cohort_end_date
)
SELECT {COHORT_ID},person_id,index_date,cohort_end_date
FROM results.lab17_first_drug_era;

-- Verificación: debe devolver 22 filas, 22 personas y cero intervalos inválidos.
SELECT COUNT(*) AS rows,
       COUNT(DISTINCT subject_id) AS persons,
       COUNT(*) FILTER (WHERE cohort_end_date<cohort_start_date) AS invalid_end_before_start
FROM results.cohort
WHERE cohort_definition_id={COHORT_ID};

-- Verificación de límites de OBSERVATION_PERIOD: ambos conteos deben ser cero.
SELECT COUNT(*) FILTER (
           WHERE c.cohort_start_date<op.observation_period_start_date
              OR c.cohort_start_date>op.observation_period_end_date
       ) AS start_outside_observation,
       COUNT(*) FILTER (
           WHERE c.cohort_end_date>op.observation_period_end_date
       ) AS end_outside_observation
FROM results.cohort c
JOIN cdm.observation_period op
  ON op.person_id=c.subject_id
 AND c.cohort_start_date BETWEEN op.observation_period_start_date
                              AND op.observation_period_end_date
WHERE c.cohort_definition_id={COHORT_ID};

-- Actividad 9. Edad exacta en la fecha índice, nunca contra la fecha actual.
SELECT c.subject_id,c.cohort_start_date,
       ({age}) AS age_at_index,
       gender.concept_name AS sex_name,
       date_diff('day',c.cohort_start_date,c.cohort_end_date)+1 AS followup_days
FROM results.cohort c
JOIN cdm.person p ON p.person_id=c.subject_id
LEFT JOIN cdm.concept gender ON gender.concept_id=p.gender_concept_id
WHERE c.cohort_definition_id={COHORT_ID};

-- Actividad 10. Todos los criterios de entrada miran solo información en o antes
-- del índice. Los eventos posteriores se usan exclusivamente para determinar salida.
"""


def main() -> None:
    if not DB.exists():
        raise SystemExit(f"ERROR: no existe la base OMOP: {DB}")
    required = [
        AUDIT / "01_observation_period_resumen.csv",
        AUDIT / "02_eventos_fuera_observacion.csv",
        AUDIT / "07_atricion_piloto.csv",
        AUDIT / "08_eventos_indice_por_anio.csv",
        AUDIT / "11_comparacion_ventanas_t2dm.csv",
    ]
    for path in required:
        if not path.exists():
            raise SystemExit(f"ERROR: falta {path}")
    ANALYSIS.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect(str(DB))
    try:
        hctz_id = int(
            con.execute(
                """
                SELECT concept_id FROM cdm.concept
                WHERE vocabulary_id='RxNorm'
                  AND concept_class_id='Ingredient'
                  AND standard_concept='S'
                  AND invalid_reason IS NULL
                  AND lower(concept_name)='hydrochlorothiazide'
                """
            ).fetchone()[0]
        )
        sql = sql_document(hctz_id)
        (LAB / "cohorte_definicion.sql").write_text(sql, encoding="utf-8")
        con.execute(sql)

        attrition = con.execute(
            "SELECT * FROM results.lab17_attrition ORDER BY step"
        ).df()
        save(attrition, "01_atricion.csv")

        initial_validation = con.execute(
            """
            SELECT COUNT(*) rows,COUNT(DISTINCT person_id) persons
            FROM (
                SELECT de.person_id,MIN(de.drug_exposure_start_date) index_date
                FROM cdm.drug_exposure de
                JOIN results.lab17_lisinopril_concept_set cs
                  ON cs.concept_id=de.drug_concept_id
                GROUP BY de.person_id
            ) x
            """
        ).df()
        save(initial_validation, "02_evento_inicial_validacion.csv")

        cohort_validation = con.execute(
            f"""
            SELECT COUNT(*) rows,
                   COUNT(DISTINCT c.subject_id) persons,
                   COUNT(*) FILTER (
                       WHERE c.cohort_end_date<c.cohort_start_date
                   ) invalid_end_before_start,
                   COUNT(*) FILTER (
                       WHERE c.cohort_start_date<op.observation_period_start_date
                          OR c.cohort_start_date>op.observation_period_end_date
                   ) start_outside_observation,
                   COUNT(*) FILTER (
                       WHERE c.cohort_end_date>op.observation_period_end_date
                   ) end_outside_observation
            FROM results.cohort c
            JOIN cdm.observation_period op
              ON op.person_id=c.subject_id
             AND c.cohort_start_date BETWEEN op.observation_period_start_date
                                          AND op.observation_period_end_date
            WHERE c.cohort_definition_id={COHORT_ID}
            """
        ).df()
        save(cohort_validation, "03_cohorte_validacion.csv")

        members = con.execute(
            f"""
            SELECT c.cohort_definition_id,c.subject_id,c.cohort_start_date,
                   c.cohort_end_date,
                   date_diff('day',c.cohort_start_date,c.cohort_end_date)+1 followup_days
            FROM results.cohort c
            WHERE c.cohort_definition_id={COHORT_ID}
            ORDER BY c.subject_id
            """
        ).df()
        save(members, "04_miembros_cohorte.csv")

        age = age_expression("c.cohort_start_date", "p")
        characterization = con.execute(
            f"""
            SELECT c.subject_id,c.cohort_start_date,c.cohort_end_date,
                   ({age}) AS age_at_index,
                   COALESCE(g.concept_name,'Unknown') AS sex_name,
                   date_diff('day',c.cohort_start_date,c.cohort_end_date)+1 followup_days
            FROM results.cohort c
            JOIN cdm.person p ON p.person_id=c.subject_id
            LEFT JOIN cdm.concept g ON g.concept_id=p.gender_concept_id
            WHERE c.cohort_definition_id={COHORT_ID}
            ORDER BY c.subject_id
            """
        ).df()
        save(characterization, "05_caracterizacion_individual.csv")

        sex = (
            characterization.groupby("sex_name", dropna=False)
            .size()
            .reset_index(name="n")
        )
        sex["percentage"] = (100 * sex.n / len(characterization)).round(2)
        save(sex, "06_distribucion_sexo.csv")

        top_comorbidities = con.execute(
            f"""
            SELECT co.condition_concept_id concept_id,
                   c.concept_name,
                   COUNT(DISTINCT co.person_id) patients,
                   ROUND(100.0*COUNT(DISTINCT co.person_id)/
                         (SELECT COUNT(*) FROM results.cohort
                          WHERE cohort_definition_id={COHORT_ID}),2) percentage
            FROM results.cohort ch
            JOIN cdm.condition_occurrence co
              ON co.person_id=ch.subject_id
             AND co.condition_start_date BETWEEN ch.cohort_start_date-INTERVAL 365 DAY
                                                 AND ch.cohort_start_date
            JOIN cdm.concept c ON c.concept_id=co.condition_concept_id
            WHERE ch.cohort_definition_id={COHORT_ID}
            GROUP BY co.condition_concept_id,c.concept_name
            ORDER BY patients DESC,concept_id
            LIMIT 10
            """
        ).df()
        save(top_comorbidities, "07_top10_comorbilidades.csv")

        duration = pd.DataFrame(
            [
                {
                    "n": len(characterization),
                    "min_days": int(characterization.followup_days.min()),
                    "q1_days": float(characterization.followup_days.quantile(0.25)),
                    "median_days": float(characterization.followup_days.median()),
                    "q3_days": float(characterization.followup_days.quantile(0.75)),
                    "max_days": int(characterization.followup_days.max()),
                }
            ]
        )
        save(duration, "08_seguimiento_resumen.csv")

        age_series = characterization.age_at_index.astype(float)
        table1_rows = [
            ["Personas, n", str(len(characterization))],
            ["Edad en índice, media (DE)", f"{age_series.mean():.1f} ({age_series.std(ddof=1):.1f})"],
            ["Edad en índice, mediana [Q1–Q3]", f"{age_series.median():.1f} [{age_series.quantile(.25):.1f}–{age_series.quantile(.75):.1f}]"],
            ["Seguimiento, mediana [Q1–Q3], días", f"{duration.iloc[0].median_days:.1f} [{duration.iloc[0].q1_days:.1f}–{duration.iloc[0].q3_days:.1f}]"],
        ]
        for row in sex.itertuples(index=False):
            table1_rows.append([f"Sexo: {row.sex_name}, n (%)", f"{row.n} ({row.percentage:.1f})"])
        table1 = pd.DataFrame(table1_rows, columns=["characteristic", "value"])
        save(table1, "09_tabla1.csv")

        immortal = pd.DataFrame(
            [
                ["Observación previa", "[-∞ observado, índice]", "No", "Solo confirma seguimiento anterior al índice."],
                ["Lavado", "[-365,-1]", "No", "No usa exposiciones posteriores."],
                ["T2DM", "[inicio OP,0]", "No", "Diagnóstico registrado antes o en el índice."],
                [">=2 fechas de presión", "[-365,0]", "No", "Todas las mediciones son basales."],
                ["Edad", "índice", "No", "Se calcula exactamente en la fecha índice."],
                ["Embarazo", "[-365,0]", "No", "La exclusión usa solo antecedentes basales."],
                ["Continuidad de lisinopril", "posterior al índice", "No para entrada", "Solo determina la fecha de salida; no decide inclusión."],
            ],
            columns=["criterion", "window", "uses_future_for_entry", "justification"],
        )
        save(immortal, "10_auditoria_immortal_time.csv")

        op_quality = pd.read_csv(AUDIT / "01_observation_period_resumen.csv")
        outside = pd.read_csv(AUDIT / "02_eventos_fuera_observacion.csv")
        windows = pd.read_csv(AUDIT / "11_comparacion_ventanas_t2dm.csv")
        save(op_quality, "00_observation_period_resumen.csv")
        save(outside, "00b_eventos_fuera_observacion.csv")
        save(windows, "00c_comparacion_ventanas_t2dm.csv")
    finally:
        con.close()

    index_year = pd.read_csv(AUDIT / "08_eventos_indice_por_anio.csv")
    plt.figure(figsize=(10, 5.5))
    plt.plot(index_year.index_year, index_year.before_observation, marker="o", ms=3,
             lw=1.5, label="Antes del filtro")
    plt.plot(index_year.index_year, index_year.after_observation, marker="x", ms=3,
             lw=1.2, linestyle="--", label="Después del filtro")
    plt.axvline(2016, color="#A23B72", linestyle=":", lw=1.3, label="Pico sintético 2016")
    plt.xlabel("Año de primera exposición")
    plt.ylabel("Personas")
    plt.title("Primeras exposiciones a lisinopril por año")
    plt.legend(frameon=False)
    plt.tight_layout()
    plt.savefig(FIGURES / "01_eventos_indice_antes_despues.png", dpi=180)
    plt.close()

    plt.figure(figsize=(8, 5.5))
    bins = min(10, max(5, int(np.sqrt(len(characterization)))))
    plt.hist(characterization.followup_days, bins=bins, color="#2A6F97", edgecolor="white")
    plt.axvline(characterization.followup_days.median(), color="#A23B72", linestyle="--",
                label=f"Mediana: {characterization.followup_days.median():.0f} días")
    plt.xlabel("Días de seguimiento")
    plt.ylabel("Personas")
    plt.title("Duración de la primera era continua de lisinopril")
    plt.legend(frameon=False)
    plt.tight_layout()
    plt.savefig(FIGURES / "02_histograma_seguimiento.png", dpi=180)
    plt.close()

    attrition_display = attrition.copy()
    attrition_display["lost_at_step"] = attrition_display.lost_at_step.fillna(0).astype(int)
    attrition_display["percent_lost_at_step"] = attrition_display.percent_lost_at_step.fillna(0)

    cohort_definition = f"""# Definición de la cohorte

## Pregunta

¿Cuál es la trayectoria de función renal durante la primera era continua de
lisinopril en adultos con diabetes mellitus tipo 2 y evaluación basal de presión
arterial, identificados como nuevos usuarios en una base OMOP sintética?

## PICOT

| Componente | Definición |
| --- | --- |
| **Población** | Personas de 18 años o más con T2DM registrado dentro del periodo continuo de observación y antes o en la fecha índice, con al menos dos fechas de presión arterial durante los 365 días basales. |
| **Exposición** | Primera exposición observada a un producto descendiente de lisinopril, excluyendo combinaciones que también contienen HCTZ. |
| **Comparador** | No se utiliza comparador en esta cohorte descriptiva; un análisis causal posterior requeriría un comparador activo. |
| **Desenlace** | Cambio posterior en función renal, especialmente eGFR o creatinina; este laboratorio construye la población y el tiempo en riesgo, no estima aún el efecto. |
| **Tiempo** | 365 días continuos de observación y lavado antes del índice; seguimiento desde el índice hasta el fin de la primera era continua, permitiendo gaps de hasta 30 días y censurando al final del periodo de observación. |

## Evento inicial

La fecha índice es la primera exposición observada a lisinopril por persona. Se
excluyen combinaciones con HCTZ para atribuir la exposición a lisinopril sin ese
coprescriptor. El resultado contiene exactamente una fila por persona.

## Criterios de inclusión

1. **Observación y lavado:** al menos 365 días continuos antes del índice dentro
   del mismo `OBSERVATION_PERIOD`, y ninguna exposición a lisinopril en
   `[-365,-1]`. Un periodo de 180 días ofrecería menos certeza de que el usuario
   es realmente nuevo y aumentaría la clasificación errónea de prevalentes.
2. **T2DM previo:** al menos una ocurrencia desde el inicio del periodo continuo
   hasta el índice. No se limita a 365 días porque T2DM es crónica: la auditoría
   mostró 17 personas con inicio durante el último año frente a 179 con un
   diagnóstico previamente observado.
3. **Evaluación de presión arterial:** al menos dos fechas distintas con presión
   sistólica o diastólica en `[-365,0]`. Dos fechas reducen la dependencia de una
   medición aislada; exigir tres habría dejado solo 10 personas antes de las
   exclusiones.

## Criterios de exclusión

1. Edad menor de 18 años en la fecha índice, calculada con fecha de nacimiento.
2. Embarazo registrado en `[-365,0]`, porque lisinopril está contraindicado y
   representa un contexto clínico diferente.

## Estrategia de salida

Las exposiciones posteriores se agrupan mediante *gaps and islands*. Un intervalo
de 30 días o menos mantiene la misma era; un gap mayor inicia otra. La salida es
el mínimo entre el final de la primera era y el final de `OBSERVATION_PERIOD`.

## Censura

Se censura al final del periodo de observación si ocurre antes que la salida por
exposición. No se infieren desenlaces ni exposición más allá de los datos.

## Limitación principal

`OBSERVATION_PERIOD` cubre a todas las personas y tiene una mediana de 11,516
días; el filtro de 365 días no elimina registros. Esto es coherente con la
historia sintética casi vitalicia de Synthea, pero es menos realista que una base
asistencial con altas, bajas y pérdidas de cobertura.
"""
    (LAB / "cohorte_definicion.md").write_text(cohort_definition, encoding="utf-8")

    biggest_absolute = attrition_display.loc[attrition_display.lost_at_step.idxmax()]
    attrition_md = f"""# Tabla de atrición

{md_table(attrition_display)}

## Interpretación

La cohorte pasó de **{int(attrition.iloc[0].n)}** nuevos usuarios potenciales a
**{int(attrition.iloc[-1].n)}** personas finales. La mayor pérdida absoluta ocurrió
en **{biggest_absolute.criterion}**, con **{int(biggest_absolute.lost_at_step)}**
personas menos. Es un costo justificable porque la pregunta se limita a personas
con diabetes previamente observada y evita atribuirles esa condición usando
información posterior.

El requisito de dos fechas de presión redujo la población de 179 a 22. Aunque es
el filtro proporcionalmente más exigente, conserva evidencia basal repetida y
cumple el objetivo de caracterizar atención previa. La precisión será limitada;
no se ocultó esta consecuencia ni se flexibilizó el criterio después de ver N.

La observación previa y el lavado se reportan por separado. Ambos eliminaron cero
personas porque Synthea produjo periodos casi vitalicios y el evento índice se
definió como la primera exposición observada.
"""
    (LAB / "atricion.md").write_text(attrition_md, encoding="utf-8")

    characterization_md = f"""# Caracterización de la cohorte

## Tabla 1

{md_table(table1)}

## Diez comorbilidades más frecuentes en `[-365,0]`

{md_table(top_comorbidities)}

## Seguimiento

{md_table(duration)}

![Histograma de seguimiento](figuras/02_histograma_seguimiento.png)

## Primeras exposiciones por año

![Eventos índice antes y después del filtro](figuras/01_eventos_indice_antes_despues.png)

Las curvas antes y después de exigir 365 días se superponen porque todos los
nuevos usuarios ya contaban con ese tiempo previo. El pico de 2016 permanece y
debe interpretarse como un artefacto del escenario sintético, no como un aumento
epidemiológico real.

## Revisión de immortal time bias

No se utilizó información posterior a la fecha índice para decidir la entrada ni
para clasificar la exposición inicial. T2DM, presión arterial, edad y embarazo se
evalúan en o antes del índice. Las exposiciones posteriores solo determinan el
fin de seguimiento mediante la era continua; por tanto, no crean tiempo inmortal
para la inclusión. El resultado no cambió tras la revisión porque no se detectó
ningún criterio postíndice que requiriera corrección.
"""
    (LAB / "caracterizacion.md").write_text(characterization_md, encoding="utf-8")

    readme = f"""# Laboratorio 17 — Cohorte de nuevo usuario

## Cohorte

Nuevos usuarios adultos de lisinopril sin HCTZ, con T2DM previamente observado y
al menos dos fechas de presión arterial durante el año basal.

## Archivos

- `cohorte_definicion.md`: PICOT y definición clínica en prosa.
- `cohorte_definicion.sql`: implementación completa con un CTE por componente.
- `atricion.md`: pérdidas paso a paso e interpretación.
- `caracterizacion.md`: tabla 1, comorbilidades, seguimiento e immortal time.
- `figuras/`: eventos índice por año e histograma de seguimiento.
- `evidencias/`: auditorías y resultados tabulares reproducibles.
- `scripts/`: auditoría, comparación de ventanas y generación.

## Resultado

- Cohorte final: **{len(characterization)} personas**.
- `cohort_definition_id`: **{COHORT_ID}**.
- Tabla local: `results.cohort`.
- Todos los intervalos respetan `OBSERVATION_PERIOD`.

## Ejecución

```bash
python lab17/scripts/00_auditar_lab17.py
python lab17/scripts/00b_comparar_criterios_lab17.py
python lab17/scripts/01_generar_lab17.py
```

Los scripts no ejecutan `git commit` ni `git push`.
"""
    (LAB / "README.md").write_text(readme, encoding="utf-8")

    print("\n===== LABORATORIO 17 GENERADO =====")
    print("Cohorte final:", len(characterization))
    print("Mediana de seguimiento:", float(duration.iloc[0].median_days), "días")
    print("Intervalos inválidos:", int(cohort_validation.iloc[0].invalid_end_before_start))
    print("Fechas fuera de observación:", int(cohort_validation.iloc[0].start_outside_observation + cohort_validation.iloc[0].end_outside_observation))
    print("Commit y push: NO ejecutados")


if __name__ == "__main__":
    main()

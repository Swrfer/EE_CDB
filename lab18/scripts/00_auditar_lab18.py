#!/usr/bin/env python3
"""Auditoría reproducible de la cohorte del Laboratorio 17 para el Lab 18.

Lee la base OMOP local y genera evidencia tabular. No ejecuta Git, no modifica
la cohorte 17001 y no crea tablas persistentes nuevas en DuckDB.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
LAB = ROOT / "lab18"
OUT = LAB / "evidencias" / "auditoria"
DB = ROOT / "lab12" / "data" / "omop" / "synthea_omop_cdm54.duckdb"
COHORT_ID = 17001
EGFR_CONCEPT_ID = 46236952


def save(df: pd.DataFrame, name: str) -> None:
    path = OUT / name
    df.to_csv(path, index=False)
    print(f"OK: {path} ({len(df)} filas)")


def age_sql(index_expr: str, person_alias: str = "p") -> str:
    return f"""
        EXTRACT(YEAR FROM {index_expr})::INTEGER-{person_alias}.year_of_birth
        - CASE
            WHEN (EXTRACT(MONTH FROM {index_expr}),
                  EXTRACT(DAY FROM {index_expr}))
                 < (COALESCE({person_alias}.month_of_birth,7),
                    COALESCE({person_alias}.day_of_birth,1))
            THEN 1 ELSE 0
          END
    """


def variant_ctes(washout_days: int) -> str:
    age = age_sql("b.index_date")
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
     AND op.observation_period_start_date
           <=i.index_date-INTERVAL {washout_days} DAY
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
          AND prior.drug_exposure_start_date
                >=o.index_date-INTERVAL {washout_days} DAY
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
                  AND m.measurement_date
                        BETWEEN t.index_date-INTERVAL 365 DAY
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
final_candidates AS (
    SELECT a.*
    FROM exclusion_minors a
    WHERE NOT EXISTS (
        SELECT 1
        FROM cdm.condition_occurrence co
        JOIN results.lab17_pregnancy_concept_set pg
          ON pg.concept_id=co.condition_concept_id
        WHERE co.person_id=a.person_id
          AND co.condition_start_date
                BETWEEN a.index_date-INTERVAL 365 DAY AND a.index_date
    )
)
"""


def main() -> None:
    if not DB.exists():
        raise SystemExit(f"ERROR: no existe la base OMOP: {DB}")
    OUT.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect(str(DB))
    try:
        required = con.execute(
            """
            SELECT schema_name,table_name
            FROM duckdb_tables()
            WHERE (schema_name='cdm' AND table_name IN (
                       'concept','concept_ancestor','condition_occurrence',
                       'drug_exposure','measurement','observation_period','person'
                   ))
               OR (schema_name='results' AND table_name IN (
                       'cohort','lab17_lisinopril_concept_set',
                       'lab17_t2dm_concept_set','lab17_bp_concept_set',
                       'lab17_pregnancy_concept_set','lab17_attrition',
                       'lab17_first_drug_era'
                   ))
            ORDER BY schema_name,table_name
            """
        ).df()
        save(required, "00_tablas_requeridas.csv")
        if len(required) != 14:
            raise SystemExit(
                "ERROR: faltan tablas de partida; se esperaban 14 y hay "
                f"{len(required)}."
            )

        feasibility = con.execute(
            f"""
            WITH cohort AS (
                SELECT *
                FROM results.cohort
                WHERE cohort_definition_id={COHORT_ID}
            ), renal AS (
                SELECT m.measurement_id,m.person_id,m.measurement_date,
                       m.value_as_number,m.unit_concept_id,m.unit_source_value
                FROM cohort c
                JOIN cdm.measurement m
                  ON m.person_id=c.subject_id
                 AND m.measurement_date
                       BETWEEN c.cohort_start_date AND c.cohort_end_date
                WHERE m.measurement_concept_id={EGFR_CONCEPT_ID}
                  AND m.value_as_number IS NOT NULL
            )
            SELECT
                (SELECT COUNT(*) FROM cohort) AS cohort_patients,
                (SELECT quantile_cont(
                            date_diff('day',cohort_start_date,cohort_end_date)+1,
                            0.25)
                 FROM cohort) AS followup_q1_days,
                (SELECT median(
                            date_diff('day',cohort_start_date,cohort_end_date)+1)
                 FROM cohort) AS followup_median_days,
                (SELECT quantile_cont(
                            date_diff('day',cohort_start_date,cohort_end_date)+1,
                            0.75)
                 FROM cohort) AS followup_q3_days,
                (SELECT COUNT(*) FROM renal) AS egfr_measurements,
                (SELECT COUNT(DISTINCT person_id) FROM renal) AS patients_with_egfr,
                (SELECT COUNT(*) FROM renal WHERE value_as_number<60)
                    AS egfr_below_60_events,
                (SELECT COUNT(DISTINCT person_id)
                 FROM renal WHERE value_as_number<60)
                    AS patients_with_egfr_below_60
            """
        ).df()
        save(feasibility, "01_factibilidad.csv")

        renal_detail = con.execute(
            f"""
            SELECT c.subject_id,m.measurement_id,m.measurement_date,
                   m.value_as_number,m.unit_concept_id,
                   COALESCE(u.concept_name,'No matching concept') unit_concept_name,
                   m.unit_source_value,
                   CASE WHEN m.value_as_number<60 THEN 1 ELSE 0 END egfr_below_60
            FROM results.cohort c
            JOIN cdm.measurement m
              ON m.person_id=c.subject_id
             AND m.measurement_date
                   BETWEEN c.cohort_start_date AND c.cohort_end_date
            LEFT JOIN cdm.concept u ON u.concept_id=m.unit_concept_id
            WHERE c.cohort_definition_id={COHORT_ID}
              AND m.measurement_concept_id={EGFR_CONCEPT_ID}
              AND m.value_as_number IS NOT NULL
            ORDER BY c.subject_id,m.measurement_date,m.measurement_id
            """
        ).df()
        save(renal_detail, "02_egfr_seguimiento.csv")

        renal_units = con.execute(
            f"""
            SELECT m.unit_concept_id,
                   COALESCE(u.concept_name,'No matching concept') unit_concept_name,
                   m.unit_source_value,
                   COUNT(*) measurements,
                   COUNT(DISTINCT c.subject_id) patients,
                   MIN(m.value_as_number) minimum,
                   median(m.value_as_number) median,
                   MAX(m.value_as_number) maximum
            FROM results.cohort c
            JOIN cdm.measurement m
              ON m.person_id=c.subject_id
             AND m.measurement_date
                   BETWEEN c.cohort_start_date AND c.cohort_end_date
            LEFT JOIN cdm.concept u ON u.concept_id=m.unit_concept_id
            WHERE c.cohort_definition_id={COHORT_ID}
              AND m.measurement_concept_id={EGFR_CONCEPT_ID}
              AND m.value_as_number IS NOT NULL
            GROUP BY m.unit_concept_id,u.concept_name,m.unit_source_value
            ORDER BY measurements DESC
            """
        ).df()
        save(renal_units, "03_egfr_unidades.csv")

        original = con.execute(
            "SELECT * FROM results.lab17_attrition ORDER BY step"
        ).df()
        save(original, "04_atricion_original.csv")

        reordered = con.execute(
            f"""
            WITH
            initial_event AS (
                SELECT de.person_id,
                       MIN(de.drug_exposure_start_date) index_date
                FROM cdm.drug_exposure de
                JOIN results.lab17_lisinopril_concept_set cs
                  ON cs.concept_id=de.drug_concept_id
                GROUP BY de.person_id
            ),
            prior_observation AS (
                SELECT i.person_id,i.index_date,
                       op.observation_period_start_date op_start,
                       op.observation_period_end_date op_end
                FROM initial_event i
                JOIN cdm.observation_period op
                  ON op.person_id=i.person_id
                 AND i.index_date BETWEEN op.observation_period_start_date
                                      AND op.observation_period_end_date
                 AND op.observation_period_start_date
                       <=i.index_date-INTERVAL 365 DAY
            ),
            washout AS (
                SELECT o.* FROM prior_observation o
                WHERE NOT EXISTS (
                    SELECT 1 FROM cdm.drug_exposure d
                    JOIN results.lab17_lisinopril_concept_set cs
                      ON cs.concept_id=d.drug_concept_id
                    WHERE d.person_id=o.person_id
                      AND d.drug_exposure_start_date
                            >=o.index_date-INTERVAL 365 DAY
                      AND d.drug_exposure_start_date<o.index_date
                )
            ),
            bp_first AS (
                SELECT * FROM (
                    SELECT w.*,
                           (SELECT COUNT(DISTINCT m.measurement_date)
                            FROM cdm.measurement m
                            JOIN results.lab17_bp_concept_set bp
                              ON bp.concept_id=m.measurement_concept_id
                            WHERE m.person_id=w.person_id
                              AND m.measurement_date
                                    BETWEEN w.index_date-INTERVAL 365 DAY
                                        AND w.index_date) bp_dates
                    FROM washout w
                ) x WHERE bp_dates>=2
            ),
            t2dm_second AS (
                SELECT b.* FROM bp_first b
                WHERE EXISTS (
                    SELECT 1 FROM cdm.condition_occurrence co
                    JOIN results.lab17_t2dm_concept_set t2
                      ON t2.concept_id=co.condition_concept_id
                    WHERE co.person_id=b.person_id
                      AND co.condition_start_date
                            BETWEEN b.op_start AND b.index_date
                )
            ),
            adults AS (
                SELECT b.* FROM t2dm_second b
                JOIN cdm.person p ON p.person_id=b.person_id
                WHERE ({age_sql('b.index_date')})>=18
            ),
            no_pregnancy AS (
                SELECT a.* FROM adults a
                WHERE NOT EXISTS (
                    SELECT 1 FROM cdm.condition_occurrence co
                    JOIN results.lab17_pregnancy_concept_set pg
                      ON pg.concept_id=co.condition_concept_id
                    WHERE co.person_id=a.person_id
                      AND co.condition_start_date
                            BETWEEN a.index_date-INTERVAL 365 DAY
                                AND a.index_date
                )
            ),
            counts AS (
                SELECT 1 step,'Evento inicial' criterion,COUNT(*) n
                FROM initial_event
                UNION ALL SELECT 2,'+ 365 días observación',COUNT(*)
                FROM prior_observation
                UNION ALL SELECT 3,'+ lavado 365 días',COUNT(*) FROM washout
                UNION ALL SELECT 4,'+ >=2 fechas de presión',COUNT(*) FROM bp_first
                UNION ALL SELECT 5,'+ T2DM antes del índice',COUNT(*) FROM t2dm_second
                UNION ALL SELECT 6,'- menores de 18 años',COUNT(*) FROM adults
                UNION ALL SELECT 7,'- embarazo basal',COUNT(*) FROM no_pregnancy
            )
            SELECT step,criterion,n,
                   LAG(n) OVER (ORDER BY step)-n lost_at_step,
                   ROUND(100.0*n/FIRST_VALUE(n) OVER (ORDER BY step),2)
                       percent_initial_remaining
            FROM counts ORDER BY step
            """
        ).df()
        save(reordered, "05_atricion_reordenada.csv")

        incidence_year = con.execute(
            f"""
            SELECT EXTRACT(YEAR FROM cohort_start_date)::INTEGER calendar_year,
                   COUNT(*) cohort_entries
            FROM results.cohort
            WHERE cohort_definition_id={COHORT_ID}
            GROUP BY calendar_year ORDER BY calendar_year
            """
        ).df()
        save(incidence_year, "06_incidencia_anio.csv")

        incidence_age = con.execute(
            f"""
            WITH aged AS (
                SELECT c.subject_id,({age_sql('c.cohort_start_date')}) age
                FROM results.cohort c
                JOIN cdm.person p ON p.person_id=c.subject_id
                WHERE c.cohort_definition_id={COHORT_ID}
            )
            SELECT CASE
                     WHEN age<40 THEN '18–39'
                     WHEN age<50 THEN '40–49'
                     WHEN age<60 THEN '50–59'
                     WHEN age<70 THEN '60–69'
                     ELSE '70+'
                   END age_group,
                   COUNT(*) cohort_entries
            FROM aged GROUP BY age_group
            ORDER BY CASE age_group
                       WHEN '18–39' THEN 1 WHEN '40–49' THEN 2
                       WHEN '50–59' THEN 3 WHEN '60–69' THEN 4 ELSE 5 END
            """
        ).df()
        save(incidence_age, "07_incidencia_edad.csv")

        index_codes = con.execute(
            f"""
            WITH candidates AS (
                SELECT c.subject_id,de.drug_exposure_id,de.drug_concept_id,
                       ROW_NUMBER() OVER (
                           PARTITION BY c.subject_id
                           ORDER BY de.drug_exposure_id,de.drug_concept_id
                       ) rn,
                       COUNT(*) OVER (PARTITION BY c.subject_id) same_day_rows
                FROM results.cohort c
                JOIN cdm.drug_exposure de
                  ON de.person_id=c.subject_id
                 AND de.drug_exposure_start_date=c.cohort_start_date
                JOIN results.lab17_lisinopril_concept_set cs
                  ON cs.concept_id=de.drug_concept_id
                WHERE c.cohort_definition_id={COHORT_ID}
            )
            SELECT x.drug_concept_id,c.concept_name,c.concept_class_id,
                   COUNT(*) patients,
                   ROUND(100.0*COUNT(*)/
                         (SELECT COUNT(*) FROM results.cohort
                          WHERE cohort_definition_id={COHORT_ID}),2) percentage,
                   SUM(CASE WHEN same_day_rows>1 THEN 1 ELSE 0 END)
                       patients_with_multiple_index_rows
            FROM candidates x
            JOIN cdm.concept c ON c.concept_id=x.drug_concept_id
            WHERE rn=1
            GROUP BY x.drug_concept_id,c.concept_name,c.concept_class_id
            ORDER BY patients DESC,x.drug_concept_id
            """
        ).df()
        save(index_codes, "08_codigos_evento_indice.csv")

        orphans = con.execute(
            """
            SELECT de.drug_concept_id concept_id,c.concept_name,
                   c.concept_class_id,COUNT(*) exposures,
                   COUNT(DISTINCT de.person_id) patients,
                   CASE
                     WHEN EXISTS (
                         SELECT 1 FROM cdm.concept_ancestor ca
                         WHERE ca.ancestor_concept_id=974166
                           AND ca.descendant_concept_id=de.drug_concept_id
                     ) THEN 'Descendiente de HCTZ: exclusión deliberada'
                     ELSE 'Candidato textual fuera del concept set'
                   END candidate_reason
            FROM cdm.drug_exposure de
            JOIN cdm.concept c ON c.concept_id=de.drug_concept_id
            WHERE lower(c.concept_name) LIKE '%lisinopril%'
              AND NOT EXISTS (
                  SELECT 1 FROM results.lab17_lisinopril_concept_set cs
                  WHERE cs.concept_id=de.drug_concept_id
              )
            GROUP BY de.drug_concept_id,c.concept_name,c.concept_class_id
            ORDER BY patients DESC,exposures DESC,de.drug_concept_id
            """
        ).df()
        save(orphans, "09_conceptos_huerfanos_candidatos.csv")

        all_members: list[pd.DataFrame] = []
        summaries: list[dict[str, object]] = []
        comorbidities: list[pd.DataFrame] = []
        for days in (180, 365, 730):
            ctes = variant_ctes(days)
            members = con.execute(
                f"""
                WITH {ctes}
                SELECT f.person_id,f.index_date,f.op_start,f.op_end,
                       e.cohort_end_date,
                       ({age_sql('f.index_date')}) age_at_index,
                       COALESCE(g.concept_name,'Unknown') sex_name,
                       date_diff('day',f.index_date,e.cohort_end_date)+1
                           followup_days
                FROM final_candidates f
                JOIN results.lab17_first_drug_era e
                  ON e.person_id=f.person_id AND e.index_date=f.index_date
                JOIN cdm.person p ON p.person_id=f.person_id
                LEFT JOIN cdm.concept g ON g.concept_id=p.gender_concept_id
                ORDER BY f.person_id
                """
            ).df()
            members.insert(0, "washout_days", days)
            all_members.append(members)
            summaries.append(
                {
                    "washout_days": days,
                    "patients": len(members),
                    "age_mean": round(float(members.age_at_index.mean()), 1)
                    if len(members) else None,
                    "age_median": round(float(members.age_at_index.median()), 1)
                    if len(members) else None,
                    "followup_median_days": round(
                        float(members.followup_days.median()), 1
                    ) if len(members) else None,
                    "sex_categories": int(members.sex_name.nunique())
                    if len(members) else 0,
                }
            )
            if len(members):
                ids = ",".join(str(int(x)) for x in members.person_id)
                comorb = con.execute(
                    f"""
                    SELECT {days} washout_days,
                           co.condition_concept_id concept_id,c.concept_name,
                           COUNT(DISTINCT co.person_id) patients
                    FROM cdm.condition_occurrence co
                    JOIN cdm.concept c
                      ON c.concept_id=co.condition_concept_id
                    JOIN (WITH {ctes}
                          SELECT person_id,index_date FROM final_candidates) f
                      ON f.person_id=co.person_id
                     AND co.condition_start_date
                           BETWEEN f.index_date-INTERVAL 365 DAY AND f.index_date
                    WHERE co.person_id IN ({ids})
                    GROUP BY co.condition_concept_id,c.concept_name
                    ORDER BY patients DESC,concept_id
                    LIMIT 3
                    """
                ).df()
                comorbidities.append(comorb)

        members_all = pd.concat(all_members, ignore_index=True)
        save(pd.DataFrame(summaries), "10_variantes_resumen.csv")
        save(members_all, "11_variantes_miembros.csv")
        save(
            pd.concat(comorbidities, ignore_index=True)
            if comorbidities
            else pd.DataFrame(
                columns=["washout_days", "concept_id", "concept_name", "patients"]
            ),
            "12_variantes_comorbilidades.csv",
        )

        sets = {
            days: set(group.person_id.astype(int))
            for days, group in members_all.groupby("washout_days")
        }
        s180 = sets.get(180, set())
        s365 = sets.get(365, set())
        s730 = sets.get(730, set())
        overlap = pd.DataFrame(
            [
                ["En las tres", len(s180 & s365 & s730)],
                ["Solo en 180", len(s180 - s365)],
                ["En 180 y 365, no en 730", len((s180 & s365) - s730)],
                ["Solo en 365", len(s365 - s180 - s730)],
                ["Solo en 730", len(s730 - s180 - s365)],
            ],
            columns=["membership", "patients"],
        )
        save(overlap, "13_traslape_variantes.csv")
        nesting = pd.DataFrame(
            [
                {
                    "check": "365 subset 180",
                    "passes": s365.issubset(s180),
                    "violations": len(s365 - s180),
                },
                {
                    "check": "730 subset 365",
                    "passes": s730.issubset(s365),
                    "violations": len(s730 - s365),
                },
            ]
        )
        save(nesting, "14_verificacion_anidamiento.csv")

    finally:
        con.close()

    print("\n===== AUDITORÍA DEL LABORATORIO 18 COMPLETADA =====")
    print("Cohorte original:", int(feasibility.iloc[0].cohort_patients))
    print("Eventos eGFR < 60:", int(feasibility.iloc[0].egfr_below_60_events))
    print(
        "Pacientes con eGFR < 60:",
        int(feasibility.iloc[0].patients_with_egfr_below_60),
    )
    print("N final original:", int(original.iloc[-1].n))
    print("N final reordenado:", int(reordered.iloc[-1].n))
    print("Variantes anidadas:", bool(nesting.passes.all()))
    print("Commit y push: NO ejecutados")


if __name__ == "__main__":
    main()

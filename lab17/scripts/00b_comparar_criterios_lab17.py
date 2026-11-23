#!/usr/bin/env python3
"""Compara ventanas de T2DM y umbrales de presión arterial para Lab 17."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "lab17" / "evidencias" / "auditoria"
DB = ROOT / "lab12" / "data" / "omop" / "synthea_omop_cdm54.duckdb"
LISINOPRIL = 1308216
T2DM = 201826


def save(df: pd.DataFrame, name: str) -> None:
    path = OUT / name
    df.to_csv(path, index=False)
    print(f"\n{name}")
    print(df.to_string(index=False))
    print(f"Guardado: {path} ({len(df)} filas)")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    if not DB.exists():
        raise SystemExit(f"ERROR: no existe {DB}")
    con = duckdb.connect(str(DB), read_only=True)
    try:
        hctz = int(
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
        bp_ids = [
            int(row[0])
            for row in con.execute(
                """
                SELECT concept_id FROM cdm.concept
                WHERE standard_concept='S' AND invalid_reason IS NULL
                  AND domain_id='Measurement'
                  AND lower(concept_name) IN (
                      'systolic blood pressure','diastolic blood pressure'
                  )
                ORDER BY concept_id
                """
            ).fetchall()
        ]
        pregnancy = int(
            con.execute(
                """
                SELECT concept_id FROM cdm.concept
                WHERE standard_concept='S' AND invalid_reason IS NULL
                  AND domain_id='Condition' AND lower(concept_name)='pregnancy'
                """
            ).fetchone()[0]
        )
        bp_sql = ",".join(map(str, bp_ids))

        common = f"""
            lisinopril_descendants AS (
                SELECT descendant_concept_id concept_id
                FROM cdm.concept_ancestor
                WHERE ancestor_concept_id={LISINOPRIL}
                UNION SELECT {LISINOPRIL}
            ),
            lisinopril_final AS (
                SELECT concept_id FROM lisinopril_descendants ld
                WHERE ld.concept_id<>{hctz}
                  AND NOT EXISTS (
                      SELECT 1 FROM cdm.concept_ancestor ca
                      WHERE ca.ancestor_concept_id={hctz}
                        AND ca.descendant_concept_id=ld.concept_id
                  )
            ),
            initial_event AS (
                SELECT de.person_id,MIN(de.drug_exposure_start_date) index_date
                FROM cdm.drug_exposure de
                JOIN lisinopril_final cs ON cs.concept_id=de.drug_concept_id
                GROUP BY de.person_id
            ),
            eligible_base AS (
                SELECT i.*,
                       op.observation_period_start_date op_start,
                       op.observation_period_end_date op_end
                FROM initial_event i
                JOIN cdm.observation_period op
                  ON op.person_id=i.person_id
                 AND i.index_date BETWEEN op.observation_period_start_date
                                      AND op.observation_period_end_date
                 AND op.observation_period_start_date<=i.index_date-INTERVAL 365 DAY
                WHERE NOT EXISTS (
                    SELECT 1 FROM cdm.drug_exposure prior
                    JOIN lisinopril_final pcs ON pcs.concept_id=prior.drug_concept_id
                    WHERE prior.person_id=i.person_id
                      AND prior.drug_exposure_start_date>=i.index_date-INTERVAL 365 DAY
                      AND prior.drug_exposure_start_date<i.index_date
                )
            ),
            t2dm_events AS (
                SELECT e.person_id,e.index_date,e.op_start,e.op_end,
                       co.condition_start_date,
                       co.condition_end_date
                FROM eligible_base e
                JOIN cdm.condition_occurrence co ON co.person_id=e.person_id
                WHERE co.condition_concept_id={T2DM}
                   OR EXISTS (
                       SELECT 1 FROM cdm.concept_ancestor ca
                       WHERE ca.ancestor_concept_id={T2DM}
                         AND ca.descendant_concept_id=co.condition_concept_id
                   )
            ),
            variants AS (
                SELECT DISTINCT person_id,index_date,op_start,op_end,
                       'A_inicio_ultimos_365_dias' variant
                FROM t2dm_events
                WHERE condition_start_date BETWEEN index_date-INTERVAL 365 DAY AND index_date
                UNION ALL
                SELECT DISTINCT person_id,index_date,op_start,op_end,
                       'B_diagnostico_observado_antes_indice'
                FROM t2dm_events
                WHERE condition_start_date BETWEEN op_start AND index_date
                UNION ALL
                SELECT DISTINCT person_id,index_date,op_start,op_end,
                       'C_condicion_activa_en_indice'
                FROM t2dm_events
                WHERE condition_start_date<=index_date
                  AND (condition_end_date IS NULL OR condition_end_date>=index_date)
                UNION ALL
                SELECT DISTINCT person_id,index_date,op_start,op_end,
                       'D_cualquier_registro_previo'
                FROM t2dm_events
                WHERE condition_start_date<=index_date
            ),
            with_bp_counts AS (
                SELECT v.*,
                       (SELECT COUNT(DISTINCT m.measurement_date)
                        FROM cdm.measurement m
                        WHERE m.person_id=v.person_id
                          AND m.measurement_concept_id IN ({bp_sql})
                          AND m.measurement_date BETWEEN v.index_date-INTERVAL 365 DAY
                                                     AND v.index_date) bp_dates
                FROM variants v
            ),
            adult_no_pregnancy AS (
                SELECT b.*
                FROM with_bp_counts b
                JOIN cdm.person p USING (person_id)
                WHERE (
                    EXTRACT(YEAR FROM b.index_date)::INTEGER-p.year_of_birth
                    - CASE
                        WHEN (EXTRACT(MONTH FROM b.index_date),EXTRACT(DAY FROM b.index_date))
                             < (COALESCE(p.month_of_birth,7),COALESCE(p.day_of_birth,1))
                        THEN 1 ELSE 0 END
                )>=18
                  AND NOT EXISTS (
                      SELECT 1 FROM cdm.condition_occurrence co
                      WHERE co.person_id=b.person_id
                        AND co.condition_start_date BETWEEN b.index_date-INTERVAL 365 DAY
                                                         AND b.index_date
                        AND (co.condition_concept_id={pregnancy}
                             OR EXISTS (
                                 SELECT 1 FROM cdm.concept_ancestor ca
                                 WHERE ca.ancestor_concept_id={pregnancy}
                                   AND ca.descendant_concept_id=co.condition_concept_id
                             ))
                  )
            )
        """

        comparison = con.execute(
            f"""
            WITH {common}
            SELECT w.variant,
                   COUNT(*) t2dm_patients,
                   COUNT(*) FILTER (WHERE w.bp_dates>=1) after_1_bp_date,
                   COUNT(*) FILTER (WHERE w.bp_dates>=2) after_2_bp_dates,
                   COUNT(*) FILTER (WHERE w.bp_dates>=3) after_3_bp_dates,
                   COUNT(*) FILTER (
                       WHERE w.bp_dates>=2 AND ap.person_id IS NOT NULL
                   ) final_after_exclusions
            FROM with_bp_counts w
            LEFT JOIN adult_no_pregnancy ap
              ON ap.person_id=w.person_id
             AND ap.index_date=w.index_date
             AND ap.variant=w.variant
            GROUP BY w.variant
            ORDER BY w.variant
            """
        ).df()
        save(comparison, "11_comparacion_ventanas_t2dm.csv")

        timing = con.execute(
            f"""
            WITH {common}
            SELECT variant,
                   COUNT(*) events,
                   MEDIAN(date_diff('day',condition_start_date,index_date)) median_days_before_index,
                   QUANTILE_CONT(date_diff('day',condition_start_date,index_date),0.25) q1_days,
                   QUANTILE_CONT(date_diff('day',condition_start_date,index_date),0.75) q3_days,
                   MIN(date_diff('day',condition_start_date,index_date)) min_days,
                   MAX(date_diff('day',condition_start_date,index_date)) max_days
            FROM (
                SELECT DISTINCT v.variant,t.person_id,t.index_date,
                       t.condition_start_date
                FROM variants v
                JOIN t2dm_events t USING (person_id,index_date)
                WHERE t.condition_start_date<=t.index_date
            ) x
            GROUP BY variant
            ORDER BY variant
            """
        ).df()
        save(timing, "12_tiempo_t2dm_antes_indice.csv")

        bp_distribution = con.execute(
            f"""
            WITH {common}
            SELECT variant,bp_dates,COUNT(*) patients
            FROM with_bp_counts
            GROUP BY variant,bp_dates
            ORDER BY variant,bp_dates
            """
        ).df()
        save(bp_distribution, "13_distribucion_fechas_presion.csv")

        print("\n===== RECOMENDACIÓN =====")
        best = comparison.loc[
            comparison.variant == "B_diagnostico_observado_antes_indice"
        ].iloc[0]
        print("Ventana recomendada: diagnóstico de T2DM observado entre el inicio")
        print("del periodo continuo y la fecha índice.")
        print("Pacientes con T2DM:", int(best.t2dm_patients))
        print("Final con >=2 fechas de presión y exclusiones:", int(best.final_after_exclusions))
        print("COMPARACIÓN COMPLETADA")
    finally:
        con.close()


if __name__ == "__main__":
    main()

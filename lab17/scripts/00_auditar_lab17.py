#!/usr/bin/env python3
"""Auditoría previa para la cohorte de nuevos usuarios del Laboratorio 17.

Solo lee la base OMOP y escribe CSV/texto en lab17/evidencias/auditoria.
No ejecuta commit, push ni crea tablas persistentes.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
LAB = ROOT / "lab17"
OUT = LAB / "evidencias" / "auditoria"
DB = ROOT / "lab12" / "data" / "omop" / "synthea_omop_cdm54.duckdb"
LISINOPRIL = 1308216
T2DM = 201826


def section(title: str) -> None:
    print(f"\n===== {title} =====")


def save_show(df: pd.DataFrame, name: str, limit: int = 30) -> None:
    path = OUT / name
    df.to_csv(path, index=False)
    if df.empty:
        print("SIN FILAS")
    else:
        print(df.head(limit).to_string(index=False))
        if len(df) > limit:
            print(f"... {len(df) - limit} filas adicionales")
    print(f"Guardado: {path} ({len(df)} filas)")


def main() -> None:
    if not DB.exists():
        raise SystemExit(f"ERROR: no existe la base OMOP: {DB}")
    OUT.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DB), read_only=True)
    try:
        section("TABLAS DE PARTIDA")
        tables = con.execute(
            """
            SELECT schema_name AS table_schema,
                   table_name,
                   estimated_size AS filas_estimadas
            FROM duckdb_tables()
            WHERE (schema_name='cdm' AND table_name IN (
                       'person','observation_period','drug_exposure',
                       'condition_occurrence','measurement','concept',
                       'concept_ancestor'
                   ))
               OR (schema_name='results' AND table_name IN (
                       'lab14_concept_set_membership','lab16_t2dm_concept_set'
                   ))
            ORDER BY schema_name,table_name
            """
        ).df()
        save_show(tables, "00_tablas_partida.csv")

        section("CALIDAD DE OBSERVATION_PERIOD")
        observation = con.execute(
            """
            WITH per_person AS (
                SELECT person_id,
                       COUNT(*) AS periods,
                       SUM(date_diff('day',observation_period_start_date,
                                           observation_period_end_date)+1) observed_days,
                       MAX(date_diff('day',observation_period_start_date,
                                           observation_period_end_date)+1) longest_period_days
                FROM cdm.observation_period
                GROUP BY person_id
            )
            SELECT
                (SELECT COUNT(*) FROM cdm.person) AS persons_total,
                COUNT(*) AS persons_with_period,
                SUM(periods) AS periods_total,
                SUM(CASE WHEN periods>1 THEN 1 ELSE 0 END) AS persons_multiple_periods,
                MEDIAN(longest_period_days) AS median_longest_period_days,
                MIN(longest_period_days) AS min_longest_period_days,
                MAX(longest_period_days) AS max_longest_period_days
            FROM per_person
            """
        ).df()
        save_show(observation, "01_observation_period_resumen.csv")

        outside = con.execute(
            """
            SELECT 'Condition' AS domain,
                   COUNT(*) AS events,
                   COUNT(*) FILTER (
                       WHERE NOT EXISTS (
                           SELECT 1 FROM cdm.observation_period op
                           WHERE op.person_id=co.person_id
                             AND co.condition_start_date BETWEEN
                                 op.observation_period_start_date AND
                                 op.observation_period_end_date
                       )
                   ) AS outside_events
            FROM cdm.condition_occurrence co
            UNION ALL
            SELECT 'Drug',COUNT(*),
                   COUNT(*) FILTER (
                       WHERE NOT EXISTS (
                           SELECT 1 FROM cdm.observation_period op
                           WHERE op.person_id=de.person_id
                             AND de.drug_exposure_start_date BETWEEN
                                 op.observation_period_start_date AND
                                 op.observation_period_end_date
                       )
                   )
            FROM cdm.drug_exposure de
            UNION ALL
            SELECT 'Measurement',COUNT(*),
                   COUNT(*) FILTER (
                       WHERE NOT EXISTS (
                           SELECT 1 FROM cdm.observation_period op
                           WHERE op.person_id=m.person_id
                             AND m.measurement_date BETWEEN
                                 op.observation_period_start_date AND
                                 op.observation_period_end_date
                       )
                   )
            FROM cdm.measurement m
            """
        ).df()
        outside["outside_percentage"] = (
            100 * outside.outside_events / outside.events
        ).round(4)
        save_show(outside, "02_eventos_fuera_observacion.csv")

        section("CONCEPT SET DE LISINOPRIL SIN HCTZ")
        hctz = con.execute(
            """
            SELECT concept_id,concept_name
            FROM cdm.concept
            WHERE vocabulary_id='RxNorm'
              AND concept_class_id='Ingredient'
              AND standard_concept='S'
              AND invalid_reason IS NULL
              AND lower(concept_name)='hydrochlorothiazide'
            ORDER BY concept_id
            """
        ).df()
        if len(hctz) != 1:
            raise RuntimeError(f"Se esperaba un ingrediente HCTZ y se encontraron {len(hctz)}")
        hctz_id = int(hctz.iloc[0].concept_id)
        save_show(hctz, "03_hctz_ingrediente.csv")

        concept_set_cte = f"""
            lisinopril_descendants AS (
                SELECT descendant_concept_id AS concept_id
                FROM cdm.concept_ancestor
                WHERE ancestor_concept_id={LISINOPRIL}
                UNION SELECT {LISINOPRIL}
            ),
            lisinopril_final AS (
                SELECT ld.concept_id
                FROM lisinopril_descendants ld
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM cdm.concept_ancestor hca
                    WHERE hca.ancestor_concept_id={hctz_id}
                      AND hca.descendant_concept_id=ld.concept_id
                )
                  AND ld.concept_id <> {hctz_id}
            )
        """

        products = con.execute(
            f"""
            WITH {concept_set_cte}
            SELECT c.concept_id,c.concept_name,c.concept_class_id,
                   COUNT(*) exposures,
                   COUNT(DISTINCT de.person_id) patients,
                   MIN(de.drug_exposure_start_date) first_date,
                   MAX(de.drug_exposure_start_date) last_date
            FROM cdm.drug_exposure de
            JOIN lisinopril_final cs ON cs.concept_id=de.drug_concept_id
            JOIN cdm.concept c ON c.concept_id=de.drug_concept_id
            GROUP BY c.concept_id,c.concept_name,c.concept_class_id
            ORDER BY patients DESC,exposures DESC,c.concept_id
            """
        ).df()
        save_show(products, "04_lisinopril_productos_observados.csv")

        set_summary = con.execute(
            f"""
            WITH {concept_set_cte}
            SELECT (SELECT COUNT(*) FROM lisinopril_final) AS vocabulary_concepts,
                   COUNT(DISTINCT de.drug_concept_id) AS observed_products,
                   COUNT(*) AS exposures,
                   COUNT(DISTINCT de.person_id) AS patients,
                   COUNT(*) FILTER (WHERE de.drug_exposure_end_date IS NULL) AS null_end_dates
            FROM cdm.drug_exposure de
            JOIN lisinopril_final cs ON cs.concept_id=de.drug_concept_id
            """
        ).df()
        save_show(set_summary, "05_lisinopril_resumen.csv")

        section("CONCEPTOS PARA LOS CRITERIOS")
        criterion_concepts = con.execute(
            """
            SELECT 'T2DM seed' criterion,concept_id,concept_name,domain_id,
                   vocabulary_id,concept_class_id,standard_concept
            FROM cdm.concept WHERE concept_id=201826
            UNION ALL
            SELECT 'Blood pressure',concept_id,concept_name,domain_id,
                   vocabulary_id,concept_class_id,standard_concept
            FROM cdm.concept
            WHERE standard_concept='S' AND invalid_reason IS NULL
              AND domain_id='Measurement'
              AND lower(concept_name) IN (
                  'systolic blood pressure','diastolic blood pressure'
              )
            UNION ALL
            SELECT 'Pregnancy root',concept_id,concept_name,domain_id,
                   vocabulary_id,concept_class_id,standard_concept
            FROM cdm.concept
            WHERE standard_concept='S' AND invalid_reason IS NULL
              AND domain_id='Condition'
              AND lower(concept_name)='pregnancy'
            ORDER BY criterion,concept_id
            """
        ).df()
        save_show(criterion_concepts, "06_conceptos_criterios.csv")
        bp_ids = criterion_concepts.loc[
            criterion_concepts.criterion == "Blood pressure", "concept_id"
        ].astype(int).tolist()
        pregnancy_ids = criterion_concepts.loc[
            criterion_concepts.criterion == "Pregnancy root", "concept_id"
        ].astype(int).tolist()
        if len(bp_ids) < 2:
            raise RuntimeError("No se encontraron los dos conceptos de presión arterial")
        if len(pregnancy_ids) != 1:
            raise RuntimeError("No se encontró una raíz única de Pregnancy")
        pregnancy_id = pregnancy_ids[0]
        bp_sql = ",".join(str(value) for value in bp_ids)

        cohort_ctes = f"""
            {concept_set_cte},
            initial_event AS (
                SELECT de.person_id,
                       MIN(de.drug_exposure_start_date) AS index_date
                FROM cdm.drug_exposure de
                JOIN lisinopril_final cs ON cs.concept_id=de.drug_concept_id
                GROUP BY de.person_id
            ),
            prior_observation AS (
                SELECT i.*
                FROM initial_event i
                WHERE EXISTS (
                    SELECT 1 FROM cdm.observation_period op
                    WHERE op.person_id=i.person_id
                      AND i.index_date BETWEEN op.observation_period_start_date
                                           AND op.observation_period_end_date
                      AND op.observation_period_start_date <= i.index_date - INTERVAL 365 DAY
                )
            ),
            washout AS (
                SELECT o.*
                FROM prior_observation o
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM cdm.drug_exposure de
                    JOIN lisinopril_final cs ON cs.concept_id=de.drug_concept_id
                    WHERE de.person_id=o.person_id
                      AND de.drug_exposure_start_date >= o.index_date - INTERVAL 365 DAY
                      AND de.drug_exposure_start_date < o.index_date
                )
            ),
            inclusion_t2dm AS (
                SELECT w.*
                FROM washout w
                WHERE EXISTS (
                    SELECT 1
                    FROM cdm.condition_occurrence co
                    WHERE co.person_id=w.person_id
                      AND co.condition_start_date BETWEEN w.index_date - INTERVAL 365 DAY
                                                       AND w.index_date
                      AND (
                          co.condition_concept_id={T2DM}
                          OR EXISTS (
                              SELECT 1 FROM cdm.concept_ancestor ca
                              WHERE ca.ancestor_concept_id={T2DM}
                                AND ca.descendant_concept_id=co.condition_concept_id
                          )
                      )
                )
            ),
            inclusion_two_bp_dates AS (
                SELECT t.*
                FROM inclusion_t2dm t
                WHERE (
                    SELECT COUNT(DISTINCT m.measurement_date)
                    FROM cdm.measurement m
                    WHERE m.person_id=t.person_id
                      AND m.measurement_concept_id IN ({bp_sql})
                      AND m.measurement_date BETWEEN t.index_date - INTERVAL 365 DAY
                                                 AND t.index_date
                ) >= 2
            ),
            exclusion_minors AS (
                SELECT b.*
                FROM inclusion_two_bp_dates b
                WHERE NOT EXISTS (
                    SELECT 1 FROM cdm.person p
                    WHERE p.person_id=b.person_id
                      AND (
                          EXTRACT(YEAR FROM b.index_date)::INTEGER - p.year_of_birth
                          - CASE
                              WHEN (EXTRACT(MONTH FROM b.index_date),
                                    EXTRACT(DAY FROM b.index_date))
                                   < (COALESCE(p.month_of_birth,7),
                                      COALESCE(p.day_of_birth,1))
                              THEN 1 ELSE 0
                            END
                      ) < 18
                )
            ),
            exclusion_pregnancy AS (
                SELECT a.*
                FROM exclusion_minors a
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM cdm.condition_occurrence co
                    WHERE co.person_id=a.person_id
                      AND co.condition_start_date BETWEEN a.index_date - INTERVAL 365 DAY
                                                       AND a.index_date
                      AND (
                          co.condition_concept_id={pregnancy_id}
                          OR EXISTS (
                              SELECT 1 FROM cdm.concept_ancestor ca
                              WHERE ca.ancestor_concept_id={pregnancy_id}
                                AND ca.descendant_concept_id=co.condition_concept_id
                          )
                      )
                )
            )
        """

        section("ATRICIÓN PILOTO")
        attrition = con.execute(
            f"""
            WITH {cohort_ctes}, counts AS (
                SELECT 1 step,'Evento inicial: primera exposición' criterion,
                       COUNT(*) n FROM initial_event
                UNION ALL SELECT 2,'+ 365 días de observación',COUNT(*) FROM prior_observation
                UNION ALL SELECT 3,'+ lavado de 365 días',COUNT(*) FROM washout
                UNION ALL SELECT 4,'+ T2DM en [-365,0]',COUNT(*) FROM inclusion_t2dm
                UNION ALL SELECT 5,'+ >=2 fechas con presión arterial',COUNT(*) FROM inclusion_two_bp_dates
                UNION ALL SELECT 6,'- menores de 18 años',COUNT(*) FROM exclusion_minors
                UNION ALL SELECT 7,'- embarazo en [-365,0]',COUNT(*) FROM exclusion_pregnancy
            )
            SELECT step,criterion,n,
                   LAG(n) OVER (ORDER BY step)-n AS lost_at_step,
                   ROUND(100.0*n/FIRST_VALUE(n) OVER (ORDER BY step),2) AS percent_initial_remaining,
                   ROUND(100.0*(LAG(n) OVER (ORDER BY step)-n)
                         /NULLIF(LAG(n) OVER (ORDER BY step),0),2) AS percent_lost_at_step
            FROM counts
            ORDER BY step
            """
        ).df()
        save_show(attrition, "07_atricion_piloto.csv")

        if int(attrition.iloc[-1].n) == 0:
            print("ADVERTENCIA: la definición propuesta produce una cohorte vacía.")

        section("PRIMERAS EXPOSICIONES POR AÑO")
        by_year = con.execute(
            f"""
            WITH {cohort_ctes}
            SELECT EXTRACT(YEAR FROM index_date)::INTEGER AS index_year,
                   COUNT(*) FILTER (WHERE stage='antes') AS before_observation,
                   COUNT(*) FILTER (WHERE stage='después') AS after_observation
            FROM (
                SELECT person_id,index_date,'antes' stage FROM initial_event
                UNION ALL
                SELECT person_id,index_date,'después' stage FROM prior_observation
            ) x
            GROUP BY index_year
            ORDER BY index_year
            """
        ).df()
        save_show(by_year, "08_eventos_indice_por_anio.csv", limit=100)

        section("MUESTRA DE LA COHORTE PILOTO")
        sample = con.execute(
            f"""
            WITH {cohort_ctes}
            SELECT e.person_id,e.index_date,
                   p.year_of_birth,p.month_of_birth,p.day_of_birth,
                   EXTRACT(YEAR FROM e.index_date)::INTEGER-p.year_of_birth
                   - CASE
                       WHEN (EXTRACT(MONTH FROM e.index_date),EXTRACT(DAY FROM e.index_date))
                            < (COALESCE(p.month_of_birth,7),COALESCE(p.day_of_birth,1))
                       THEN 1 ELSE 0 END AS age_at_index
            FROM exclusion_pregnancy e
            JOIN cdm.person p USING (person_id)
            ORDER BY hash(e.person_id)
            LIMIT 20
            """
        ).df()
        save_show(sample, "09_cohorte_piloto_muestra.csv")

        section("DISTRIBUCIÓN PRELIMINAR DE SEGUIMIENTO")
        duration = con.execute(
            f"""
            WITH {cohort_ctes},
            cohort_events AS (
                SELECT c.person_id,c.index_date,
                       de.drug_exposure_start_date start_date,
                       COALESCE(de.drug_exposure_end_date,
                                de.drug_exposure_start_date) end_date
                FROM exclusion_pregnancy c
                JOIN cdm.drug_exposure de ON de.person_id=c.person_id
                JOIN lisinopril_final cs ON cs.concept_id=de.drug_concept_id
                WHERE de.drug_exposure_start_date>=c.index_date
            ), ordered AS (
                SELECT *,MAX(end_date) OVER (
                           PARTITION BY person_id ORDER BY start_date,end_date
                           ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
                       ) prior_max_end
                FROM cohort_events
            ), islands AS (
                SELECT *,SUM(CASE WHEN prior_max_end IS NULL
                                       OR start_date>prior_max_end+INTERVAL 30 DAY
                                  THEN 1 ELSE 0 END)
                          OVER (PARTITION BY person_id ORDER BY start_date,end_date) island
                FROM ordered
            ), first_era AS (
                SELECT person_id,index_date,MIN(start_date) era_start,MAX(end_date) era_end
                FROM islands WHERE island=1
                GROUP BY person_id,index_date
            ), censored AS (
                SELECT f.person_id,f.index_date,
                       LEAST(f.era_end,op.observation_period_end_date) cohort_end_date
                FROM first_era f
                JOIN cdm.observation_period op
                  ON op.person_id=f.person_id
                 AND f.index_date BETWEEN op.observation_period_start_date
                                      AND op.observation_period_end_date
            )
            SELECT COUNT(*) n,
                   MIN(date_diff('day',index_date,cohort_end_date)+1) min_days,
                   QUANTILE_CONT(date_diff('day',index_date,cohort_end_date)+1,0.25) q1_days,
                   MEDIAN(date_diff('day',index_date,cohort_end_date)+1) median_days,
                   QUANTILE_CONT(date_diff('day',index_date,cohort_end_date)+1,0.75) q3_days,
                   MAX(date_diff('day',index_date,cohort_end_date)+1) max_days,
                   SUM(CASE WHEN cohort_end_date<index_date THEN 1 ELSE 0 END) invalid_intervals
            FROM censored
            """
        ).df()
        save_show(duration, "10_seguimiento_piloto.csv")

        section("RESUMEN")
        print("Ingrediente de exposición: lisinopril")
        print("HCTZ concept_id excluido:", hctz_id)
        print("Pacientes con exposición:", int(attrition.iloc[0].n))
        print("Pacientes tras observación:", int(attrition.iloc[1].n))
        print("Cohorte piloto final:", int(attrition.iloc[-1].n))
        print("AUDITORÍA COMPLETADA")
    finally:
        con.close()


if __name__ == "__main__":
    main()

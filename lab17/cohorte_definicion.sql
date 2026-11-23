-- Laboratorio 17 — Cohorte de nuevos usuarios de lisinopril
-- Motor: DuckDB 2.0.0
-- Fecha: 2026-11-22
-- cohort_definition_id: 17001
-- Definición clínica completa: cohorte_definicion.md

CREATE SCHEMA IF NOT EXISTS results;

-- Concept set de exposición: descendientes de lisinopril, excluyendo productos
-- que también descienden de hydrochlorothiazide (HCTZ).
CREATE OR REPLACE TABLE results.lab17_lisinopril_concept_set AS
WITH lisinopril_descendants AS (
    SELECT descendant_concept_id AS concept_id
    FROM cdm.concept_ancestor
    WHERE ancestor_concept_id=1308216
    UNION SELECT 1308216
)
SELECT DISTINCT ld.concept_id
FROM lisinopril_descendants ld
WHERE ld.concept_id<>974166
  AND NOT EXISTS (
      SELECT 1
      FROM cdm.concept_ancestor ca
      WHERE ca.ancestor_concept_id=974166
        AND ca.descendant_concept_id=ld.concept_id
  );

CREATE OR REPLACE TABLE results.lab17_t2dm_concept_set AS
SELECT descendant_concept_id AS concept_id
FROM cdm.concept_ancestor
WHERE ancestor_concept_id=201826
UNION SELECT 201826;

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
WITH
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
          AND (
        EXTRACT(YEAR FROM b.index_date)::INTEGER-p.year_of_birth
        - CASE
            WHEN (EXTRACT(MONTH FROM b.index_date),EXTRACT(DAY FROM b.index_date))
                 < (COALESCE(p.month_of_birth,7),
                    COALESCE(p.day_of_birth,1))
            THEN 1 ELSE 0
          END
    )<18
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

SELECT person_id,index_date,op_start,op_end,bp_dates
FROM exclusion_pregnancy;

-- Actividad 8. La misma secuencia se convierte en tabla de atrición.
CREATE OR REPLACE TABLE results.lab17_attrition AS
WITH
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
          AND (
        EXTRACT(YEAR FROM b.index_date)::INTEGER-p.year_of_birth
        - CASE
            WHEN (EXTRACT(MONTH FROM b.index_date),EXTRACT(DAY FROM b.index_date))
                 < (COALESCE(p.month_of_birth,7),
                    COALESCE(p.day_of_birth,1))
            THEN 1 ELSE 0
          END
    )<18
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
,
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
WHERE cohort_definition_id=17001;

INSERT INTO results.cohort (
    cohort_definition_id,subject_id,cohort_start_date,cohort_end_date
)
SELECT 17001,person_id,index_date,cohort_end_date
FROM results.lab17_first_drug_era;

-- Verificación: debe devolver 22 filas, 22 personas y cero intervalos inválidos.
SELECT COUNT(*) AS rows,
       COUNT(DISTINCT subject_id) AS persons,
       COUNT(*) FILTER (WHERE cohort_end_date<cohort_start_date) AS invalid_end_before_start
FROM results.cohort
WHERE cohort_definition_id=17001;

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
WHERE c.cohort_definition_id=17001;

-- Actividad 9. Edad exacta en la fecha índice, nunca contra la fecha actual.
SELECT c.subject_id,c.cohort_start_date,
       (
        EXTRACT(YEAR FROM c.cohort_start_date)::INTEGER-p.year_of_birth
        - CASE
            WHEN (EXTRACT(MONTH FROM c.cohort_start_date),EXTRACT(DAY FROM c.cohort_start_date))
                 < (COALESCE(p.month_of_birth,7),
                    COALESCE(p.day_of_birth,1))
            THEN 1 ELSE 0
          END
    ) AS age_at_index,
       gender.concept_name AS sex_name,
       date_diff('day',c.cohort_start_date,c.cohort_end_date)+1 AS followup_days
FROM results.cohort c
JOIN cdm.person p ON p.person_id=c.subject_id
LEFT JOIN cdm.concept gender ON gender.concept_id=p.gender_concept_id
WHERE c.cohort_definition_id=17001;

-- Actividad 10. Todos los criterios de entrada miran solo información en o antes
-- del índice. Los eventos posteriores se usan exclusivamente para determinar salida.

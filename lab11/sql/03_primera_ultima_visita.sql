-- QUERY: visits_group_by
-- ¿Cuál fue la primera y última visita de cada paciente
-- y cuántos encuentros tuvo?

WITH grouped_visits AS (
    SELECT
        patient_id,
        min(start_time) AS first_visit,
        max(start_time) AS last_visit,
        count(*)::BIGINT AS total_visits
    FROM encounters
    GROUP BY patient_id
)
SELECT
    patient_id,
    first_visit,
    last_visit,
    total_visits
FROM grouped_visits
ORDER BY patient_id;

-- QUERY: visits_window
-- ¿Cuál es la primera visita, la última y el total por paciente usando ventanas?
-- Misma pregunta mediante funciones de ventana.

WITH visit_windows AS (
    SELECT
        patient_id,
        first_value(start_time) OVER (
            PARTITION BY patient_id
            ORDER BY start_time, encounter_id
            ROWS BETWEEN UNBOUNDED PRECEDING
                AND UNBOUNDED FOLLOWING
        ) AS first_visit,
        last_value(start_time) OVER (
            PARTITION BY patient_id
            ORDER BY start_time, encounter_id
            ROWS BETWEEN UNBOUNDED PRECEDING
                AND UNBOUNDED FOLLOWING
        ) AS last_visit,
        count(*) OVER (
            PARTITION BY patient_id
            ROWS BETWEEN UNBOUNDED PRECEDING
                AND UNBOUNDED FOLLOWING
        )::BIGINT AS total_visits
    FROM encounters
),
one_row_per_patient AS (
    SELECT DISTINCT
        patient_id,
        first_visit,
        last_visit,
        total_visits
    FROM visit_windows
)
SELECT
    patient_id,
    first_visit,
    last_visit,
    total_visits
FROM one_row_per_patient
ORDER BY patient_id;

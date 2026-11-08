-- QUERY: visit_intervals
-- ¿Cuántos días transcurrieron entre cada visita
-- y la visita anterior del mismo paciente?

WITH ordered_visits AS (
    SELECT
        patient_id,
        encounter_id,
        start_time,
        lag(start_time) OVER (
            PARTITION BY patient_id
            ORDER BY start_time, encounter_id
            ROWS BETWEEN UNBOUNDED PRECEDING
                AND CURRENT ROW
        ) AS previous_visit
    FROM encounters
),
visit_intervals AS (
    SELECT
        patient_id,
        encounter_id,
        start_time,
        previous_visit,
        date_diff(
            'day',
            previous_visit,
            start_time
        ) AS days_since_previous
    FROM ordered_visits
)
SELECT
    patient_id,
    encounter_id,
    start_time,
    previous_visit,
    days_since_previous
FROM visit_intervals
ORDER BY patient_id, start_time, encounter_id;

-- QUERY: visit_interval_summary
-- ¿Cuál es la mediana de días entre visitas consecutivas?

WITH ordered_visits AS (
    SELECT
        patient_id,
        start_time,
        lag(start_time) OVER (
            PARTITION BY patient_id
            ORDER BY start_time, encounter_id
            ROWS BETWEEN UNBOUNDED PRECEDING
                AND CURRENT ROW
        ) AS previous_visit
    FROM encounters
),
visit_intervals AS (
    SELECT
        date_diff(
            'day',
            previous_visit,
            start_time
        ) AS days_since_previous
    FROM ordered_visits
)
SELECT
    count(*) AS total_visits,
    count(*) FILTER (
        WHERE days_since_previous IS NULL
    ) AS first_visits_with_null,
    count(*) FILTER (
        WHERE days_since_previous IS NOT NULL
    ) AS comparable_intervals,
    median(days_since_previous)::DOUBLE
        AS median_days
FROM visit_intervals;

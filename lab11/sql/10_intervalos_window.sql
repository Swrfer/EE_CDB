-- QUERY: interval_summary_window
-- ¿Cuál es la mediana de días entre visitas consecutivas
-- utilizando una función de ventana?

WITH ordered_encounters AS (
    SELECT
        patient_id,
        encounter_id,
        start_time,
        lag(start_time) OVER (
            PARTITION BY patient_id
            ORDER BY
                start_time,
                encounter_id
            ROWS BETWEEN UNBOUNDED PRECEDING
                AND CURRENT ROW
        ) AS previous_visit
    FROM encounters
),
visit_intervals AS (
    SELECT
        patient_id,
        encounter_id,
        date_diff(
            'day',
            previous_visit,
            start_time
        ) AS days_since_previous
    FROM ordered_encounters
    WHERE previous_visit IS NOT NULL
)
SELECT
    count(*) AS comparable_intervals,
    median(days_since_previous)::DOUBLE
        AS median_days
FROM visit_intervals;

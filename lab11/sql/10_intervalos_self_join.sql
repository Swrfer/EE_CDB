-- QUERY: interval_summary_self_join
-- ¿Cuál es la mediana de días entre visitas consecutivas
-- utilizando un self-join?

WITH previous_encounters AS (
    SELECT
        current_visit.patient_id,
        current_visit.encounter_id,
        current_visit.start_time,
        max(previous_visit.start_time)
            AS previous_visit
    FROM encounters AS current_visit
    LEFT JOIN encounters AS previous_visit
        ON current_visit.patient_id
            = previous_visit.patient_id
       AND (
           previous_visit.start_time
               < current_visit.start_time
           OR (
               previous_visit.start_time
                   = current_visit.start_time
               AND previous_visit.encounter_id
                   < current_visit.encounter_id
           )
       )
    GROUP BY
        current_visit.patient_id,
        current_visit.encounter_id,
        current_visit.start_time
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
    FROM previous_encounters
    WHERE previous_visit IS NOT NULL
)
SELECT
    count(*) AS comparable_intervals,
    median(days_since_previous)::DOUBLE
        AS median_days
FROM visit_intervals;

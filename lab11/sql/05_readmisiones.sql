-- QUERY: readmission_events
-- ¿Qué ingresos hospitalarios ocurrieron dentro de los
-- 30 días posteriores al alta hospitalaria previa?

WITH dataset_limits AS (
    SELECT
        max(
            coalesce(stop_time, start_time)
        ) AS dataset_end
    FROM encounters
),
ordered_admissions AS (
    SELECT
        patient_id,
        encounter_id,
        start_time AS admission_time,
        stop_time AS discharge_time,
        lead(start_time) OVER (
            PARTITION BY patient_id
            ORDER BY start_time, encounter_id
            ROWS BETWEEN CURRENT ROW
                AND UNBOUNDED FOLLOWING
        ) AS next_admission
    FROM encounters
    WHERE encounter_class = 'inpatient'
),
eligible_discharges AS (
    SELECT
        a.patient_id,
        a.encounter_id,
        a.admission_time,
        a.discharge_time,
        a.next_admission,
        date_diff(
            'day',
            a.discharge_time,
            a.next_admission
        ) AS days_to_readmission
    FROM ordered_admissions AS a
    CROSS JOIN dataset_limits AS d
    WHERE a.discharge_time IS NOT NULL
      AND a.discharge_time
          <= d.dataset_end - INTERVAL 30 DAY
),
readmissions AS (
    SELECT
        patient_id,
        encounter_id,
        admission_time,
        discharge_time,
        next_admission,
        days_to_readmission
    FROM eligible_discharges
    WHERE next_admission >= discharge_time
          AND next_admission <= discharge_time + INTERVAL 30 DAY
)
SELECT
    patient_id,
    encounter_id,
    admission_time,
    discharge_time,
    next_admission,
    days_to_readmission
FROM readmissions
ORDER BY patient_id, admission_time;

-- QUERY: readmission_summary
-- ¿Cuántas readmisiones hay y cuál es la tasa
-- entre las altas elegibles?

WITH dataset_limits AS (
    SELECT
        max(
            coalesce(stop_time, start_time)
        ) AS dataset_end
    FROM encounters
),
ordered_admissions AS (
    SELECT
        patient_id,
        stop_time AS discharge_time,
        lead(start_time) OVER (
            PARTITION BY patient_id
            ORDER BY start_time, encounter_id
            ROWS BETWEEN CURRENT ROW
                AND UNBOUNDED FOLLOWING
        ) AS next_admission
    FROM encounters
    WHERE encounter_class = 'inpatient'
),
eligible_discharges AS (
    SELECT
        patient_id,
        discharge_time,
        next_admission,
        date_diff(
            'day',
            discharge_time,
            next_admission
        ) AS days_to_readmission
    FROM ordered_admissions
    CROSS JOIN dataset_limits
    WHERE discharge_time IS NOT NULL
      AND discharge_time
          <= dataset_end - INTERVAL 30 DAY
)
SELECT
    count(*) AS eligible_discharges,
    count(*) FILTER (
        WHERE next_admission >= discharge_time
          AND next_admission <= discharge_time + INTERVAL 30 DAY
    ) AS readmissions,
    round(
        100.0
        * count(*) FILTER (
            WHERE next_admission >= discharge_time
          AND next_admission <= discharge_time + INTERVAL 30 DAY
        )
        / nullif(count(*), 0),
        4
    )::DOUBLE AS readmission_rate_percent
FROM eligible_discharges;

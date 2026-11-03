-- QUERY: hba1c_moving_average
-- ¿Cómo cambian la media acumulada y la media móvil
-- de tres mediciones de HbA1c en un mismo paciente?

WITH hba1c_counts AS (
    SELECT
        patient_id,
        count(*) AS measurements,
        count(
            DISTINCT try_cast(value AS DOUBLE)
        ) AS distinct_values
    FROM observations
    WHERE code = '4548-4'
      AND try_cast(value AS DOUBLE) IS NOT NULL
    GROUP BY patient_id
    HAVING count(*) >= 5
       AND count(
           DISTINCT try_cast(value AS DOUBLE)
       ) >= 2
),
selected_patient AS (
    SELECT patient_id
    FROM hba1c_counts
    ORDER BY
        distinct_values DESC,
        measurements DESC,
        patient_id
    LIMIT 1
),
numeric_hba1c AS (
    SELECT
        o.patient_id,
        o.encounter_id,
        o.observation_time,
        try_cast(o.value AS DOUBLE)
            AS hba1c_value,
        o.units
    FROM observations AS o
    INNER JOIN selected_patient AS s
        ON o.patient_id = s.patient_id
    WHERE o.code = '4548-4'
      AND try_cast(o.value AS DOUBLE) IS NOT NULL
),
longitudinal_hba1c AS (
    SELECT
        patient_id,
        observation_time,
        hba1c_value,
        units,
        avg(hba1c_value) OVER (
            PARTITION BY patient_id
            ORDER BY observation_time, encounter_id
            ROWS BETWEEN UNBOUNDED PRECEDING
                AND CURRENT ROW
        ) AS cumulative_mean,
        avg(hba1c_value) OVER (
            PARTITION BY patient_id
            ORDER BY observation_time, encounter_id
            ROWS BETWEEN 2 PRECEDING
                AND CURRENT ROW
        ) AS moving_mean_3
    FROM numeric_hba1c
)
SELECT
    patient_id,
    observation_time,
    hba1c_value,
    units,
    cumulative_mean,
    moving_mean_3
FROM longitudinal_hba1c
ORDER BY observation_time;

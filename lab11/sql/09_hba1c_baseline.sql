-- QUERY: closest_preindex_hba1c
-- ¿Cuál es la HbA1c más cercana al primer diagnóstico
-- de diabetes dentro de los 90 días anteriores?
--
-- Política temporal:
-- No se permiten mediciones posteriores a la fecha índice,
-- porque podrían incorporar información futura.

WITH diabetes_index_dates AS (
    SELECT
        patient_id,
        min(start_date) AS index_date
    FROM conditions
    WHERE contains(
        lower(description),
        'diabetes'
    )
    GROUP BY patient_id
),
candidate_hba1c AS (
    SELECT
        d.patient_id,
        d.index_date,
        o.observation_time,
        try_cast(o.value AS DOUBLE)
            AS hba1c_value,
        o.units,
        date_diff(
            'day',
            CAST(o.observation_time AS DATE),
            d.index_date
        ) AS days_before_index
    FROM diabetes_index_dates AS d
    INNER JOIN observations AS o
        ON d.patient_id = o.patient_id
    WHERE o.code = '4548-4'
      AND try_cast(o.value AS DOUBLE) IS NOT NULL
      AND CAST(o.observation_time AS DATE)
          BETWEEN d.index_date - INTERVAL 90 DAY
              AND d.index_date
),
ranked_hba1c AS (
    SELECT
        patient_id,
        index_date,
        observation_time,
        hba1c_value,
        units,
        days_before_index,
        row_number() OVER (
            PARTITION BY patient_id
            ORDER BY
                days_before_index,
                observation_time DESC
            ROWS BETWEEN UNBOUNDED PRECEDING
                AND CURRENT ROW
        ) AS rn
    FROM candidate_hba1c
)
SELECT
    patient_id,
    index_date,
    observation_time,
    hba1c_value,
    units,
    days_before_index
FROM ranked_hba1c
WHERE rn = 1
ORDER BY patient_id;

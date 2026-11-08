-- QUERY: latest_observations
-- ¿Cuál es la observación más reciente de cada
-- combinación paciente-analito?

WITH ranked_observations AS (
    SELECT
        patient_id,
        code,
        description,
        observation_time,
        value,
        units,
        row_number() OVER (
            PARTITION BY patient_id, code
            ORDER BY
                observation_time DESC,
                encounter_id DESC
            ROWS BETWEEN UNBOUNDED PRECEDING
                AND CURRENT ROW
        ) AS rn
    FROM observations
)
SELECT
    patient_id,
    code,
    description,
    observation_time,
    value,
    units
FROM ranked_observations
WHERE rn = 1
ORDER BY patient_id, code;

-- QUERY: deduplication_summary
-- ¿Cuántas observaciones quedan antes y después
-- de conservar únicamente la más reciente?

WITH ranked_observations AS (
    SELECT
        patient_id,
        code,
        row_number() OVER (
            PARTITION BY patient_id, code
            ORDER BY
                observation_time DESC,
                encounter_id DESC
            ROWS BETWEEN UNBOUNDED PRECEDING
                AND CURRENT ROW
        ) AS rn
    FROM observations
),
deduplicated_observations AS (
    SELECT
        patient_id,
        code
    FROM ranked_observations
    WHERE rn = 1
)
SELECT
    (
        SELECT count(*)
        FROM observations
    ) AS rows_before,
    (
        SELECT count(*)
        FROM deduplicated_observations
    ) AS rows_after;

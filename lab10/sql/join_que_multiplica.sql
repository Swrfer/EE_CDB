-- Actividad 7: join que multiplica filas.

WITH correct_result AS (
    -- Una fila por encuentro.
    SELECT
        count(*) AS row_count,
        avg(base_encounter_cost) AS mean_cost
    FROM encounters
),
inflated_result AS (
    -- Un encuentro se repite por cada condición asociada.
    SELECT
        count(*) AS row_count,
        avg(e.base_encounter_cost) AS mean_cost
    FROM encounters AS e
    LEFT JOIN conditions AS c
        ON e.encounter_id = c.encounter_id
),
deduplicated_encounters AS (
    -- Se recupera una fila por encounter_id.
    SELECT
        e.encounter_id,
        e.base_encounter_cost
    FROM encounters AS e
    LEFT JOIN conditions AS c
        ON e.encounter_id = c.encounter_id
    GROUP BY
        e.encounter_id,
        e.base_encounter_cost
),
corrected_result AS (
    SELECT
        count(*) AS row_count,
        avg(base_encounter_cost) AS mean_cost
    FROM deduplicated_encounters
)
SELECT stage, row_count, mean_cost
FROM (
    SELECT
        1 AS stage_order,
        'correct' AS stage,
        row_count,
        mean_cost
    FROM correct_result

    UNION ALL

    SELECT
        2,
        'inflated',
        row_count,
        mean_cost
    FROM inflated_result

    UNION ALL

    SELECT
        3,
        'corrected',
        row_count,
        mean_cost
    FROM corrected_result
) AS comparison
ORDER BY stage_order;

-- Auditoría inicial de la base clínica.

WITH duplicate_patients AS (
    -- ¿Hay patient_id duplicados?
    SELECT count(*)::DOUBLE AS result
    FROM (
        SELECT patient_id
        FROM patients
        GROUP BY patient_id
        HAVING count(*) > 1
    )
),
encounters_before_birth AS (
    -- ¿Hay encuentros anteriores al nacimiento?
    SELECT count(*)::DOUBLE AS result
    FROM encounters AS e
    INNER JOIN patients AS p
        ON e.patient_id = p.patient_id
    WHERE CAST(e.start_time AS DATE) < p.birth_date
),
null_observations AS (
    -- ¿Qué porcentaje de observations tiene value nulo?
    SELECT round(
        100.0
        * count(*) FILTER (WHERE value IS NULL)
        / nullif(count(*), 0),
        6
    )::DOUBLE AS result
    FROM observations
),
orphan_encounters AS (
    -- Anti-join: encuentros sin paciente existente.
    SELECT count(*)::DOUBLE AS result
    FROM encounters AS e
    ANTI JOIN patients AS p
        ON e.patient_id = p.patient_id
)
SELECT metric, result, unit
FROM (
    SELECT
        1 AS metric_order,
        'duplicate_patient_ids' AS metric,
        result,
        'groups' AS unit
    FROM duplicate_patients

    UNION ALL

    SELECT
        2,
        'encounters_before_birth',
        result,
        'rows'
    FROM encounters_before_birth

    UNION ALL

    SELECT
        3,
        'null_observations',
        result,
        'percent'
    FROM null_observations

    UNION ALL

    SELECT
        4,
        'orphan_encounters',
        result,
        'rows'
    FROM orphan_encounters
) AS audit_results
ORDER BY metric_order;

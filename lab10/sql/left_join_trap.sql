-- Actividad 8: demostrar la trampa del LEFT JOIN.

WITH filter_in_where AS (
    -- El filtro en WHERE elimina las filas sin coincidencia.
    SELECT
        count(*)::BIGINT AS joined_rows,
        count(DISTINCT p.patient_id)::BIGINT
            AS patients_retained
    FROM patients AS p
    LEFT JOIN encounters AS e
        ON p.patient_id = e.patient_id
    WHERE e.encounter_class = 'emergency'
),
filter_in_on AS (
    -- El filtro en ON conserva todos los pacientes.
    SELECT
        count(*)::BIGINT AS joined_rows,
        count(DISTINCT p.patient_id)::BIGINT
            AS patients_retained
    FROM patients AS p
    LEFT JOIN encounters AS e
        ON p.patient_id = e.patient_id
        AND e.encounter_class = 'emergency'
)
SELECT
    1 AS result_order,
    'filter_in_where' AS stage,
    joined_rows,
    patients_retained
FROM filter_in_where

UNION ALL

SELECT
    2 AS result_order,
    'filter_in_on' AS stage,
    joined_rows,
    patients_retained
FROM filter_in_on

ORDER BY result_order;

-- QUERY: nested_encounters
-- ¿Cuál es el promedio y la mediana de encuentros por paciente?
SELECT
    avg(encounter_count)::DOUBLE AS mean_encounters,
    median(encounter_count)::DOUBLE AS median_encounters
FROM (
    SELECT
        p.patient_id,
        count(e.encounter_id) AS encounter_count
    FROM patients AS p
    LEFT JOIN encounters AS e
        ON p.patient_id = e.patient_id
    GROUP BY p.patient_id
) AS patient_encounter_counts;

-- QUERY: cte_encounters
-- ¿Cuál es el número medio y mediano de encuentros por paciente usando CTEs?
-- Misma pregunta reescrita con una CTE descriptiva.
WITH patient_encounter_counts AS (
    SELECT
        p.patient_id,
        count(e.encounter_id) AS encounter_count
    FROM patients AS p
    LEFT JOIN encounters AS e
        ON p.patient_id = e.patient_id
    GROUP BY p.patient_id
)
SELECT
    avg(encounter_count)::DOUBLE AS mean_encounters,
    median(encounter_count)::DOUBLE AS median_encounters
FROM patient_encounter_counts;

-- QUERY: nested_diabetes
-- ¿Qué pacientes con diabetes no tienen una medición de HbA1c?
SELECT d.patient_id
FROM (
    SELECT DISTINCT patient_id
    FROM conditions
    WHERE lower(description) LIKE '%diabetes%'
) AS d
ANTI JOIN (
    SELECT DISTINCT patient_id
    FROM observations
    WHERE code = '4548-4'
) AS h
    ON d.patient_id = h.patient_id
ORDER BY d.patient_id;

-- QUERY: cte_diabetes
-- ¿Qué pacientes tienen diabetes sin ninguna medición de HbA1c usando CTEs?
-- Misma pregunta reescrita con CTEs descriptivas.
WITH diabetes_patients AS (
    SELECT DISTINCT patient_id
    FROM conditions
    WHERE lower(description) LIKE '%diabetes%'
),
hba1c_patients AS (
    SELECT DISTINCT patient_id
    FROM observations
    WHERE code = '4548-4'
)
SELECT d.patient_id
FROM diabetes_patients AS d
ANTI JOIN hba1c_patients AS h
    ON d.patient_id = h.patient_id
ORDER BY d.patient_id;

-- Consulta 1.
-- ¿Cuántos pacientes hay y cuántos siguen vivos?
SELECT
    count(*) AS total_patients,
    count(*) FILTER (
        WHERE death_date IS NULL
    ) AS living_patients,
    count(*) FILTER (
        WHERE death_date IS NOT NULL
    ) AS deceased_patients
FROM patients;

-- Consulta 2.
-- ¿Cuál es la distribución de pacientes por sexo?
SELECT
    gender,
    count(*) AS patients,
    round(
        100.0 * count(*)
        / sum(count(*)) OVER (),
        2
    ) AS percentage
FROM patients
GROUP BY gender
ORDER BY patients DESC, gender;

-- Consulta 3.
-- ¿Cuáles son los 10 diagnósticos más frecuentes?
SELECT
    code,
    description,
    count(*) AS diagnosis_records,
    count(DISTINCT patient_id) AS distinct_patients
FROM conditions
GROUP BY code, description
ORDER BY
    diagnosis_records DESC,
    description
LIMIT 10;

-- Consulta 4.
-- ¿Cuántos pacientes nacieron antes de 1960?
SELECT
    count(*) AS patients_born_before_1960
FROM patients
WHERE birth_date < DATE '1960-01-01';

-- Consulta 5.
-- ¿Cuántos encuentros ocurrieron en cada año?
SELECT
    extract(
        YEAR FROM start_time
    )::INTEGER AS encounter_year,
    count(*) AS encounters
FROM encounters
GROUP BY encounter_year
ORDER BY encounter_year;

-- Consulta 6.
-- ¿Cuál es el número medio y mediano de encuentros por paciente?
WITH encounter_counts AS (
    SELECT
        p.patient_id,
        count(e.encounter_id) AS encounters
    FROM patients AS p
    LEFT JOIN encounters AS e
        ON p.patient_id = e.patient_id
    GROUP BY p.patient_id
)
SELECT
    round(avg(encounters), 2) AS mean_encounters,
    median(encounters) AS median_encounters,
    min(encounters) AS minimum_encounters,
    max(encounters) AS maximum_encounters
FROM encounter_counts;

-- Consulta 7.
-- ¿Cuál es la edad media al primer diagnóstico de sinusitis viral?
WITH first_diagnosis AS (
    SELECT
        patient_id,
        min(start_date) AS first_diagnosis_date
    FROM conditions
    WHERE code = '444814009'
    GROUP BY patient_id
)
SELECT
    'Viral sinusitis (disorder)' AS condition,
    count(*) AS patients,
    round(
        avg(
            date_diff(
                'day',
                p.birth_date,
                f.first_diagnosis_date
            ) / 365.2425
        ),
        2
    ) AS mean_age_at_first_diagnosis
FROM first_diagnosis AS f
INNER JOIN patients AS p
    ON f.patient_id = p.patient_id;

-- Consulta 8.
-- ¿Qué diagnósticos aparecen en más de 50 pacientes distintos?
SELECT
    code,
    description,
    count(DISTINCT patient_id) AS distinct_patients,
    count(*) AS diagnosis_records
FROM conditions
GROUP BY code, description
HAVING count(DISTINCT patient_id) > 50
ORDER BY distinct_patients DESC, description;

-- Consulta 9.
-- ¿Cuál es la distribución de las mediciones de HbA1c?
WITH numeric_hba1c AS (
    SELECT
        try_cast(value AS DOUBLE) AS hba1c
    FROM observations
    WHERE code = '4548-4'
      AND try_cast(value AS DOUBLE) IS NOT NULL
)
SELECT
    count(*) AS measurements,
    round(avg(hba1c), 2) AS mean_hba1c,
    round(median(hba1c), 2) AS median_hba1c,
    round(quantile_cont(hba1c, 0.10), 2) AS p10_hba1c,
    round(quantile_cont(hba1c, 0.90), 2) AS p90_hba1c
FROM numeric_hba1c;

-- Consulta 10.
-- ¿Cómo se distribuyen los pacientes por grupo etario y sexo?
WITH patient_ages AS (
    SELECT
        patient_id,
        gender,
        floor(
            date_diff(
                'day',
                birth_date,
                coalesce(
                    death_date,
                    DATE '2026-11-02'
                )
            ) / 365.2425
        )::INTEGER AS age
    FROM patients
),
age_groups AS (
    SELECT
        patient_id,
        gender,
        CASE
            WHEN age < 18 THEN '00–17'
            WHEN age < 40 THEN '18–39'
            WHEN age < 65 THEN '40–64'
            ELSE '65+'
        END AS age_group,
        CASE
            WHEN age < 18 THEN 1
            WHEN age < 40 THEN 2
            WHEN age < 65 THEN 3
            ELSE 4
        END AS age_group_order
    FROM patient_ages
)
SELECT
    age_group,
    gender,
    count(*) AS patients
FROM age_groups
GROUP BY
    age_group,
    age_group_order,
    gender
ORDER BY
    age_group_order,
    gender;

-- Consulta 11.
-- ¿Qué pacientes tienen diabetes e hipertensión?
WITH diabetes_patients AS (
    SELECT DISTINCT patient_id
    FROM conditions
    WHERE lower(description) LIKE '%diabetes%'
),
hypertension_patients AS (
    SELECT DISTINCT patient_id
    FROM conditions
    WHERE lower(description) LIKE '%hypertension%'
)
SELECT
    p.patient_id,
    p.gender,
    p.birth_date
FROM diabetes_patients AS d
INNER JOIN hypertension_patients AS h
    ON d.patient_id = h.patient_id
INNER JOIN patients AS p
    ON d.patient_id = p.patient_id
ORDER BY p.patient_id;

-- Consulta 12.
-- ¿Qué pacientes con diabetes no tienen ninguna medición de HbA1c?
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
SELECT
    d.patient_id,
    p.gender,
    p.birth_date
FROM diabetes_patients AS d
ANTI JOIN hba1c_patients AS h
    ON d.patient_id = h.patient_id
INNER JOIN patients AS p
    ON d.patient_id = p.patient_id
ORDER BY d.patient_id;

-- Consulta 13.
-- ¿Cuál fue el primer y el último encuentro de cada paciente?
SELECT
    p.patient_id,
    min(e.start_time) AS first_encounter,
    max(e.start_time) AS last_encounter,
    count(e.encounter_id) AS encounter_count
FROM patients AS p
LEFT JOIN encounters AS e
    ON p.patient_id = e.patient_id
GROUP BY p.patient_id
ORDER BY p.patient_id;

-- Consulta 14.
-- ¿Cuál es el medicamento más frecuente entre pacientes con diabetes?
WITH diabetes_patients AS (
    SELECT DISTINCT patient_id
    FROM conditions
    WHERE lower(description) LIKE '%diabetes%'
)
SELECT
    m.code,
    m.description,
    count(*) AS medication_records,
    count(DISTINCT m.patient_id) AS distinct_patients
FROM medications AS m
INNER JOIN diabetes_patients AS d
    ON m.patient_id = d.patient_id
GROUP BY m.code, m.description
ORDER BY
    medication_records DESC,
    distinct_patients DESC,
    m.description
LIMIT 1;

-- Consulta 15.
-- ¿Qué encuentros de urgencias no tienen diagnóstico registrado?
SELECT
    e.encounter_id,
    e.patient_id,
    e.start_time,
    e.description
FROM encounters AS e
ANTI JOIN conditions AS c
    ON e.encounter_id = c.encounter_id
WHERE lower(e.encounter_class) = 'emergency'
ORDER BY e.start_time, e.encounter_id;

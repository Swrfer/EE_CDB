-- Consulta optimizada:
-- filtra temprano, proyecta solo patient_id y usa ANTI JOIN.

WITH diabetic_patients AS (
    SELECT DISTINCT patient_id
    FROM conditions
    WHERE lower(description) LIKE '%diabetes%'
),
patients_with_hba1c AS (
    SELECT DISTINCT patient_id
    FROM observations
    WHERE code = '4548-4'
)
SELECT
    count(*)::BIGINT
        AS diabetic_patients_without_hba1c
FROM diabetic_patients AS d
ANTI JOIN patients_with_hba1c AS h
    ON d.patient_id = h.patient_id;

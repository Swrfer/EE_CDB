-- Consulta original:
-- pacientes con diabetes sin medición de HbA1c.
-- La unión trabaja con columnas y filas antes de reducirlas.

SELECT
    count(DISTINCT p.patient_id)::BIGINT
        AS diabetic_patients_without_hba1c
FROM patients AS p
INNER JOIN conditions AS c
    ON p.patient_id = c.patient_id
LEFT JOIN observations AS o
    ON p.patient_id = o.patient_id
    AND o.code = '4548-4'
WHERE lower(c.description) LIKE '%diabetes%'
  AND o.patient_id IS NULL;

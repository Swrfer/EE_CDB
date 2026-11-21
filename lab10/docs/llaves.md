# Llaves y relaciones

| Tabla | Llave primaria o lógica | Llaves foráneas |
|---|---|---|
| `patients` | `patient_id` | Ninguna |
| `encounters` | `encounter_id` | `patient_id → patients.patient_id` |
| `conditions` | Paciente, encuentro, fecha y código | `patient_id`, `encounter_id` |
| `medications` | Paciente, encuentro, fecha y código | `patient_id`, `encounter_id` |
| `observations` | Paciente, encuentro, fecha y código | `patient_id`, `encounter_id` |

Los CSV de `conditions`, `medications` y `observations` no incluyen
un identificador único individual. Por ello se documentan llaves
lógicas compuestas.

Las relaciones no se impusieron como restricciones físicas durante
la carga, porque la auditoría debía permitir detectar registros
huérfanos mediante un anti-join.

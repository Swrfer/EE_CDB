-- Laboratorio 10: carga reproducible de Synthea en DuckDB.
-- CREATE OR REPLACE permite repetir la carga sin duplicar registros.
-- Los campos temporales se almacenan como DATE o TIMESTAMPTZ.

BEGIN TRANSACTION;

CREATE OR REPLACE TABLE patients (
    patient_id VARCHAR,
    birth_date DATE,
    death_date DATE,
    ssn VARCHAR,
    drivers VARCHAR,
    passport VARCHAR,
    prefix VARCHAR,
    first_name VARCHAR,
    middle_name VARCHAR,
    last_name VARCHAR,
    suffix VARCHAR,
    maiden VARCHAR,
    marital VARCHAR,
    race VARCHAR,
    ethnicity VARCHAR,
    gender VARCHAR,
    birthplace VARCHAR,
    address VARCHAR,
    city VARCHAR,
    state VARCHAR,
    county VARCHAR,
    fips VARCHAR,
    zip VARCHAR,
    latitude DOUBLE,
    longitude DOUBLE,
    healthcare_expenses DOUBLE,
    healthcare_coverage DOUBLE,
    income BIGINT
);

COPY patients
FROM 'lab10/data/raw/synthea_5000/csv/patients.csv'
(
    FORMAT CSV,
    HEADER TRUE,
    DELIMITER ',',
    QUOTE '"',
    ESCAPE '"',
    NULL ''
);

CREATE OR REPLACE TABLE encounters (
    encounter_id VARCHAR,
    start_time TIMESTAMPTZ,
    stop_time TIMESTAMPTZ,
    patient_id VARCHAR,
    organization_id VARCHAR,
    provider_id VARCHAR,
    payer_id VARCHAR,
    encounter_class VARCHAR,
    code VARCHAR,
    description VARCHAR,
    base_encounter_cost DOUBLE,
    total_claim_cost DOUBLE,
    payer_coverage DOUBLE,
    reason_code VARCHAR,
    reason_description VARCHAR
);

COPY encounters
FROM 'lab10/data/raw/synthea_5000/csv/encounters.csv'
(
    FORMAT CSV,
    HEADER TRUE,
    DELIMITER ',',
    QUOTE '"',
    ESCAPE '"',
    NULL ''
);

CREATE OR REPLACE TABLE conditions (
    start_date DATE,
    stop_date DATE,
    patient_id VARCHAR,
    encounter_id VARCHAR,
    code_system VARCHAR,
    code VARCHAR,
    description VARCHAR
);

COPY conditions
FROM 'lab10/data/raw/synthea_5000/csv/conditions.csv'
(
    FORMAT CSV,
    HEADER TRUE,
    DELIMITER ',',
    QUOTE '"',
    ESCAPE '"',
    NULL ''
);

CREATE OR REPLACE TABLE medications (
    start_time TIMESTAMPTZ,
    stop_time TIMESTAMPTZ,
    patient_id VARCHAR,
    payer_id VARCHAR,
    encounter_id VARCHAR,
    code VARCHAR,
    description VARCHAR,
    base_cost DOUBLE,
    payer_coverage DOUBLE,
    dispenses BIGINT,
    total_cost DOUBLE,
    reason_code VARCHAR,
    reason_description VARCHAR
);

COPY medications
FROM 'lab10/data/raw/synthea_5000/csv/medications.csv'
(
    FORMAT CSV,
    HEADER TRUE,
    DELIMITER ',',
    QUOTE '"',
    ESCAPE '"',
    NULL ''
);

CREATE OR REPLACE TABLE observations (
    observation_time TIMESTAMPTZ,
    patient_id VARCHAR,
    encounter_id VARCHAR,
    category VARCHAR,
    code VARCHAR,
    description VARCHAR,
    value VARCHAR,
    units VARCHAR,
    observation_type VARCHAR
);

COPY observations
FROM 'lab10/data/raw/synthea_5000/csv/observations.csv'
(
    FORMAT CSV,
    HEADER TRUE,
    DELIMITER ',',
    QUOTE '"',
    ESCAPE '"',
    NULL ''
);

COMMIT;

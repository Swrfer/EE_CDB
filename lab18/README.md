# Laboratorio 18 — Auditoría de una cohorte

Auditoría de la cohorte de nuevos usuarios de lisinopril construida en el
laboratorio 17 (`cohort_definition_id = 17001`).

## Archivos principales

- `diagnostico_cohorte.md`: factibilidad, atrición, diagnóstico y sensibilidad.
- `figuras/`: diagrama CONSORT, incidencia descriptiva y sensibilidad.
- `evidencias/auditoria/`: resultados directos de la base OMOP.
- `evidencias/analisis/`: tablas interpretadas utilizadas en el reporte.
- `scripts/00_auditar_lab18.py`: auditoría reproducible de DuckDB.
- `scripts/01_generar_lab18.py`: generación del reporte y las figuras.

## Resultado principal

La cohorte contiene 22 personas y sólo seis tienen al menos un eGFR menor de 60.
No es factible ajustar un modelo multivariable de riesgo renal con estos datos,
aunque la cohorte permite demostrar y auditar la implementación.

La definición principal conserva el lavado preespecificado de 365 días. Las
variantes de 180, 365 y 730 días producen los mismos 22 pacientes y cumplen el
anidamiento esperado.

Los scripts no ejecutan `git commit` ni `git push`.

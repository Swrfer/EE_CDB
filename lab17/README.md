# Laboratorio 17 — Cohorte de nuevo usuario

## Cohorte

Nuevos usuarios adultos de lisinopril sin HCTZ, con T2DM previamente observado y
al menos dos fechas de presión arterial durante el año basal.

## Archivos

- `cohorte_definicion.md`: PICOT y definición clínica en prosa.
- `cohorte_definicion.sql`: implementación completa con un CTE por componente.
- `atricion.md`: pérdidas paso a paso e interpretación.
- `caracterizacion.md`: tabla 1, comorbilidades, seguimiento e immortal time.
- `figuras/`: eventos índice por año e histograma de seguimiento.
- `evidencias/`: auditorías y resultados tabulares reproducibles.
- `scripts/`: auditoría, comparación de ventanas y generación.

## Resultado

- Cohorte final: **22 personas**.
- `cohort_definition_id`: **17001**.
- Tabla local: `results.cohort`.
- Todos los intervalos respetan `OBSERVATION_PERIOD`.

## Ejecución

```bash
python lab17/scripts/00_auditar_lab17.py
python lab17/scripts/00b_comparar_criterios_lab17.py
python lab17/scripts/01_generar_lab17.py
```

Los scripts no ejecutan `git commit` ni `git push`.

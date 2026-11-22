# Laboratorio 16 — Jerarquías en acción

## Propósito

Explicar cómo se construyen y recorren las jerarquías OMOP, demostrar un caso
real de poli-jerarquía, trazar por qué un paciente entra a una cohorte y comparar
el rendimiento de una expansión dinámica frente a un concept set materializado.

## Entregables

- `jerarquias.sql`: las ocho actividades, comentadas y reproducibles.
- `hallazgos.md`: comparación de representaciones, poli-jerarquía, solapamiento,
  trazabilidad y auditoría de conceptos retirados.
- `tiempos.md`: tres corridas por versión, medianas y planes `EXPLAIN ANALYZE`.
- `evidencias/analisis/`: resultados tabulares y planes completos.
- `scripts/`: auditoría y generación reproducible.

## Decisiones principales

- Condición principal: diabetes mellitus tipo 2 (`201826`).
- Poli-jerarquía: gingivitis hacia `Disease` mediante 13 caminos.
- Solapamiento deliberado: `Heart failure` y `Chronic congestive heart failure`.
- Motor de rendimiento: DuckDB 2.0.0.
- Los conceptos clínicos locales permanecen en la base ignorada por Git.

## Reproducibilidad

```bash
python lab16/scripts/00_auditar_lab16.py
python lab16/scripts/01_generar_lab16.py
```

Los scripts no ejecutan `git commit` ni `git push`.

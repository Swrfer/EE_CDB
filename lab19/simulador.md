# Simulación de la política de privilegio mínimo

## Objetivo

Evaluar una política que permita únicamente leer objetos bajo `publico/`,
sin permitir escritura, eliminación ni lectura de `privado/`. La política
evaluada se encuentra en `politica_minima.json`.

## Alcance

| Elemento | Valor |
|---|---|
| Efecto | `Allow` |
| Acción | `s3:GetObject` |
| Recurso | `arn:aws:s3:::lab19-cdb-seguro-20261126-m4p7x2/publico/*` |

No se utilizaron `s3:*`, `Resource: "*"`, permisos de modificación ni
acceso a objetos bajo `privado/`.

## Método

Se utilizó el modo **Personalizado** del simulador de políticas de IAM. La
política se creó únicamente dentro de la simulación y no se adjuntó al
usuario. Esto permitió evaluarla de forma aislada, sin que el permiso
temporal `AdministratorAccess` alterara los resultados.

El estado personalizado del simulador es efímero. Tras cerrar la sesión fue
necesario volver a cargar el JSON; esto no eliminó recursos ni modificó IAM.

## Casos evaluados

| Caso | Acción | Recurso | Resultado esperado | Resultado obtenido |
|---:|---|---|---|---|
| 1 | `s3:GetObject` | `publico/archivo_publico.txt` | Permitido | Permitido explícitamente |
| 2 | `s3:PutObject` | `publico/archivo_publico.txt` | Denegado | Denegación implícita |
| 3 | `s3:DeleteObject` | `publico/archivo_publico.txt` | Denegado | Denegación implícita |
| 4 | `s3:GetObject` | `privado/archivo_privado.txt` | Denegado | Denegación implícita |

## Interpretación

El primer caso coincidió con `Allow` porque la acción y el ARN pertenecían
al alcance autorizado. Escritura y eliminación fueron rechazadas porque no
existen instrucciones que concedan esas acciones. La lectura privada fue
rechazada porque su ARN queda fuera de `publico/*`.

Una **denegación implícita** significa que ninguna instrucción aplicable
autoriza la operación; no fue necesario agregar una instrucción `Deny`.

## Evidencias

- `evidencias/08_politica_minima_simulador.png`
- `evidencias/09_simulador_publico_get_permitido_put_delete_denegados.png`
- `evidencias/10_simulador_privado_get_denegado.png`

Las capturas deben mantener censurados el ID de cuenta, ARN de identidad,
URL de inicio de sesión y cualquier identificador innecesario.

## Limitaciones

El simulador evalúa la lógica de autorización y no sustituye una llamada
real. Los resultados corresponden a la política personalizada evaluada, no
al conjunto temporal de permisos administrativos del usuario configurador.

## Conclusión

La política cumple el principio de privilegio mínimo: permite leer objetos
de `publico/` y rechaza modificación, eliminación y lectura de `privado/`.

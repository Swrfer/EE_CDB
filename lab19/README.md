# Laboratorio 19: seguridad y acceso temporal en AWS

## Objetivo

Configurar y comprobar un entorno mínimo de AWS aplicando autenticación
multifactor, control de costos, credenciales temporales, cifrado de objetos,
bloqueo de acceso público y privilegio mínimo para Amazon S3.

## Contenido

| Archivo o directorio | Descripción |
| --- | --- |
| `aws-setup.md` | Configuración de la cuenta, IAM, AWS CLI, S3 y cierre seguro. |
| `simulador.md` | Metodología y resultados del simulador de políticas de IAM. |
| `politica_minima.json` | Política que permite únicamente `s3:GetObject` en `publico/*`. |
| `verificacion.ipynb` | Verificación ejecutada con Boto3 y credenciales temporales. |
| `evidencias/` | Doce capturas censuradas de la configuración y las pruebas. |

## Resultados verificados

- La cuenta raíz quedó protegida con MFA y no se crearon claves de acceso.
- El usuario IAM utilizó MFA y credenciales temporales mediante el perfil
  `tesis`.
- El bucket mantuvo cifrado SSE-S3, ACL deshabilitadas y bloqueo completo del
  acceso público.
- El simulador permitió `GetObject` sobre el objeto de `publico/` y denegó
  `PutObject`, `DeleteObject` y la lectura del objeto de `privado/`.
- AWS CLI y Boto3 accedieron correctamente a los objetos durante la validación.
- El notebook se reejecutó desde una copia limpia sin errores.
- Gitleaks no detectó secretos en los archivos entregados ni en el historial
  Git revisado.

## Estado final

La infraestructura temporal fue eliminada después de guardar las evidencias:
el bucket y sus objetos ya no existen, la auditoría principal reportó cero
recursos activos, `AdministratorAccess` fue retirado y las sesiones de AWS CLI,
consola web y Jupyter quedaron cerradas.

`verificacion.ipynb` conserva los resultados de la ejecución realizada antes
del cierre. No debe reejecutarse contra el bucket original, pues su eliminación
forma parte del procedimiento de control de costos.

## Seguridad

El repositorio no contiene contraseñas, códigos MFA, claves de acceso, tokens,
identificadores de cuenta sin censurar ni datos clínicos o de pacientes.

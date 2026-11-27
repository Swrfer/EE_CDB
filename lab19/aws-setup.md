# Configuración segura de AWS

## Objetivo

Configurar un entorno introductorio de AWS para el Laboratorio 19 aplicando
autenticación multifactor, control de costos, credenciales temporales,
almacenamiento cifrado y una política de privilegio mínimo.

La práctica utiliza únicamente archivos de prueba sin datos clínicos,
información de pacientes ni credenciales almacenadas en el repositorio.

## Región y recursos

- Región de trabajo: `us-east-2` (Estados Unidos, Ohio).
- Usuario IAM: `alejandro-lab19`.
- Perfil local de AWS CLI: `tesis`.
- Bucket: `lab19-cdb-seguro-20261126-m4p7x2`.
- Prefijos: `publico/` y `privado/`.

## Protección de la cuenta raíz

La cuenta raíz se utilizó exclusivamente para la configuración inicial. Se
habilitó MFA mediante una clave de paso protegida por la biometría del
dispositivo. Después se cerró la sesión raíz y el trabajo continuó con un
usuario IAM independiente. No se crearon claves de acceso para la raíz.

Evidencia: `evidencias/01_root_mfa_activo_censurado.png`.

## Control de costos

Se creó un presupuesto mensual recurrente de **5 USD** con cuatro alertas:

| Umbral | Tipo |
|---:|---|
| 50 % | Gasto real |
| 80 % | Gasto real |
| 50 % | Gasto previsto |
| 80 % | Gasto previsto |

No se configuraron acciones automáticas. El presupuesto se conservará como
mecanismo preventivo después de retirar los recursos temporales.

Evidencias:

- `evidencias/02_presupuesto_5usd_creado_censurado.png`
- `evidencias/03_presupuesto_cuatro_alertas_50_80_censurado.png`
- `evidencias/04_alertas_presupuesto_correo_verificado_censurado.png`

## Usuario IAM y MFA

Se creó `alejandro-lab19` con acceso a la consola, contraseña individual y
cambio obligatorio de la contraseña inicial. Se habilitó MFA mediante una
clave de paso con Touch ID.

Políticas empleadas durante la configuración:

- `SignInLocalDevelopmentAccess`: inicio de sesión temporal desde herramientas locales.
- `IAMUserChangePassword`: administración de la contraseña propia.
- `AdministratorAccess`: permiso **temporal** utilizado durante la práctica y retirado después de completar la validación.

No se crearon claves de acceso de larga duración.

Evidencia: `evidencias/05_usuario_iam_mfa_activo_sin_claves_censurado.png`.

## Autenticación temporal desde AWS CLI

Se instaló AWS CLI v2 para ARM64 y se inició sesión con:

```bash
aws login --profile tesis --region us-east-2
```

El perfil utiliza un proveedor de credenciales de tipo `login`. No se
guardaron claves ni tokens dentro del proyecto. Comandos de comprobación:

```bash
aws configure list --profile tesis
aws sts get-caller-identity --profile tesis
aws s3 ls s3://lab19-cdb-seguro-20261126-m4p7x2/       --recursive --profile tesis
```

Para cerrar la sesión temporal:

```bash
aws logout --profile tesis
```

El entorno Conda `cdb` utiliza `boto3`, `botocore` y `awscrt`. AWS CRT es
necesario para que `botocore` reconozca credenciales de tipo `login`.

Evidencias:

- `evidencias/11_cli_credenciales_temporales_acceso_s3.png`
- `evidencias/12_boto3_perfil_temporal_acceso_s3.png`

## Configuración del bucket S3

| Configuración | Valor |
|---|---|
| Región | `us-east-2` |
| Propiedad de objetos | ACL deshabilitadas |
| Bloqueo de acceso público | Cuatro opciones habilitadas |
| Cifrado predeterminado | SSE-S3 (`AES256`) |
| Control de versiones | Deshabilitado para esta práctica |
| Acceso anónimo | No permitido |

Se cargaron dos archivos inocuos:

- `publico/archivo_publico.txt`
- `privado/archivo_privado.txt`

El nombre `publico/` representa el alcance lógico de la política de lectura;
no significa que el objeto sea accesible anónimamente.

Evidencias:

- `evidencias/06_bucket_s3_estructura_publico_privado.png`
- `evidencias/07_bucket_s3_acceso_publico_bloqueado.png`

## Verificación reproducible

`verificacion.ipynb` crea una sesión con el perfil temporal `tesis` y
comprueba mediante aserciones:

1. proveedor temporal `login`;
2. identidad del usuario sin imprimir el ID de cuenta;
3. bloqueo completo del acceso público;
4. cifrado predeterminado SSE-S3;
5. presencia de los objetos esperados;
6. cifrado `AES256` de ambos archivos;
7. alcance mínimo de `politica_minima.json`.

## Cierre seguro completado

Después de concluir las comprobaciones, se realizó el cierre controlado del
entorno:

1. se reejecutó el notebook desde una copia limpia y sus seis celdas de código
   finalizaron sin errores;
2. Gitleaks no detectó secretos en `lab19/` ni en los 54 commits revisados;
3. se eliminaron los dos archivos de prueba, los prefijos y el bucket S3;
4. se comprobó que no quedaran instancias EC2, volúmenes EBS, direcciones IP
   elásticas, NAT gateways, balanceadores, recursos RDS, EKS, SageMaker,
   Redshift ni buckets S3;
5. se retiró la política temporal `AdministratorAccess` y se verificó que una
   operación administrativa fuera denegada;
6. se cerraron las credenciales temporales con `aws logout --profile tesis`;
7. se cerró la sesión de la consola web y se confirmó que no hubiera servidores
   Jupyter ni kernels activos.

El perfil local `tesis` se conservó sin credenciales activas para permitir un
futuro inicio de sesión mediante `aws login --profile tesis`. Los resultados
guardados en `verificacion.ipynb` documentan la ejecución efectuada antes de
eliminar la infraestructura. Por diseño, el notebook ya no debe reejecutarse
contra el bucket original porque ese recurso fue eliminado para evitar costos.
## Principios aplicados

- separación entre raíz y usuario de trabajo;
- MFA para ambas identidades;
- credenciales temporales en lugar de claves permanentes;
- privilegio mínimo;
- cifrado en reposo;
- bloqueo de acceso público;
- control preventivo de costos;
- ausencia de datos sensibles.

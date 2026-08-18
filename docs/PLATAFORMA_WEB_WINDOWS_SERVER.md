# Plataforma web Minutas ASH en Windows Server 2022

> Estado: guía de preparación. La aplicación de escritorio sigue usando SQLite. Esta guía prepara PostgreSQL y el servidor para la plataforma web; no migre ni borre datos locales hasta que exista una migración probada.

## 1. Diseño seguro inicial

Use una VM dedicada o una subred interna. El navegador se conecta por HTTPS a IIS; la aplicación web y PostgreSQL permanecen en la misma VM durante el piloto.

```text
Usuarios -> HTTPS 443 -> IIS -> servicio Minutas ASH (127.0.0.1:8000) -> PostgreSQL (127.0.0.1:5432)
```

No publique el puerto `5432` en Internet. Si PostgreSQL queda en otra VM, permita ese puerto solamente desde la IP del servidor de aplicación.

Recomendación inicial: 4 vCPU, 16 GB RAM, 100 GB SSD para aplicación/base y un volumen separado para fuentes y documentos. Whisper y Ollama requieren recursos adicionales; ejecútelos como workers separados, no dentro de IIS.

## 2. Verificar PostgreSQL

Stack Builder es opcional: no instale complementos por ahora. Abra **pgAdmin 4**, registre el servidor local y ejecute:

```sql
SELECT version();
SHOW server_version;
SHOW listen_addresses;
SHOW port;
```

Debe ver PostgreSQL 18.x, puerto `5432` y, para el piloto en una sola VM, `listen_addresses` igual a `localhost` o `127.0.0.1`.

En PowerShell con privilegios de administrador también puede comprobar el servicio y el puerto:

```powershell
Get-Service | Where-Object { $_.Name -like 'postgresql*' }
Get-NetTCPConnection -LocalPort 5432 -State Listen
```

No continúe si el servicio no está en estado `Running`.

## 3. Crear base y cuenta de aplicación

Entre con pgAdmin usando la cuenta administrativa creada durante la instalación. Abra **Query Tool** y ejecute, reemplazando el valor entre comillas por una contraseña larga y única guardada en un gestor de secretos:

```sql
CREATE ROLE minutas_app
  LOGIN
  NOSUPERUSER
  NOCREATEDB
  NOCREATEROLE
  NOINHERIT
  PASSWORD 'REEMPLAZAR-POR-CONTRASENA-LARGA-Y-UNICA';

CREATE DATABASE minutas_ash
  OWNER minutas_app
  ENCODING 'UTF8'
  TEMPLATE template0;
```

Conéctese después a la base `minutas_ash` y ejecute:

```sql
REVOKE ALL ON DATABASE minutas_ash FROM PUBLIC;
GRANT CONNECT, TEMPORARY ON DATABASE minutas_ash TO minutas_app;

REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT USAGE, CREATE ON SCHEMA public TO minutas_app;
```

Compruebe la conexión desde pgAdmin configurando una conexión con usuario `minutas_app`. No use la cuenta `postgres` para Minutas ASH.

## 4. Red y firewall

### Piloto en una sola VM

Mantenga PostgreSQL en `127.0.0.1`. No cree reglas entrantes para 5432. Solo IIS debe recibir tráfico externo, por `443`.

### PostgreSQL en una VM separada

1. Edite `postgresql.conf` y defina una IP privada concreta, no `*`:

   ```conf
   listen_addresses = '10.20.30.15'
   port = 5432
   ```

2. En `pg_hba.conf`, permita únicamente la IP del servidor web:

   ```conf
   host    minutas_ash    minutas_app    10.20.30.20/32    scram-sha-256
   ```

3. Reinicie el servicio PostgreSQL.
4. Cree una regla de firewall entrante limitada a `10.20.30.20`, TCP 5432. No use `Any` como dirección remota.

## 5. Cuenta de servicio Windows y carpetas

Cree una cuenta local o de dominio sin permisos administrativos, por ejemplo `ASH-MinutasSvc`. Asígnele solo **Log on as a service**.

Cree estas carpetas:

```powershell
New-Item -ItemType Directory -Force `
  'C:\ProgramData\MinutasASH', `
  'D:\MinutasASH\fuentes', `
  'D:\MinutasASH\documentos', `
  'D:\MinutasASH\logs', `
  'C:\MinutasASH\web'
```

Otorgue a `ASH-MinutasSvc` modificación en `D:\MinutasASH` y lectura/ejecución en `C:\MinutasASH\web`. Los usuarios finales no deben tener acceso directo a fuentes ni documentos de otros proyectos.

## 6. Secretos fuera del repositorio

Cuando se entregue el backend web, cree `C:\ProgramData\MinutasASH\web.env` con ACL solo para Administrators y `ASH-MinutasSvc`:

```dotenv
MINUTAS_WEB_DATABASE_URL=postgresql://minutas_app:CONTRASENA_URL_ENCODED@127.0.0.1:5432/minutas_ash
MINUTAS_WEB_SECRET_KEY=REEMPLAZAR_CON_64_CARACTERES_ALEATORIOS
MINUTAS_WEB_BOOTSTRAP_EMAIL=admin@ash.cl
MINUTAS_WEB_BOOTSTRAP_PASSWORD=REEMPLAZAR_CON_CLAVE_INICIAL_UNICA
MINUTAS_WEB_STORAGE_ROOT=D:\MinutasASH
```

Genere el secreto sin copiarlo al repositorio:

```powershell
[Convert]::ToBase64String([Security.Cryptography.RandomNumberGenerator]::GetBytes(48))
```

No almacene esta información en `config.json`, archivos `.env` del repositorio, scripts de GitHub ni capturas de pantalla.

## 7. Servicio web e IIS

La entrega web incluirá un script de instalación que cree un servicio Windows para Uvicorn. El servicio debe escuchar solo en `127.0.0.1:8000`; IIS será el único punto expuesto.

En IIS:

1. Instale **URL Rewrite** y **Application Request Routing** desde fuentes corporativas aprobadas.
2. Cree un sitio `Minutas ASH` con binding HTTPS 443 y el certificado corporativo.
3. Habilite el proxy de ARR.
4. Agregue una regla de proxy inverso hacia `http://127.0.0.1:8000`.
5. Fuerce redirección HTTP 80 a HTTPS 443.
6. Añada encabezados de seguridad: HSTS, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY` y una política de contenido compatible con la interfaz final.

No ejecute Uvicorn con `--reload` en el servidor. El certificado HTTPS termina en IIS; el servicio Python no se publica directamente.

## 8. Respaldo y restauración

Programe un respaldo diario con una cuenta autorizada. Ejemplo, ajustando la ruta real de PostgreSQL:

```powershell
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$backupDir = 'D:\MinutasASH\backups\postgres'
New-Item -ItemType Directory -Force $backupDir | Out-Null
& 'C:\Program Files\PostgreSQL\18\bin\pg_dump.exe' `
  --format=custom --file "$backupDir\minutas_ash-$stamp.dump" `
  --host 127.0.0.1 --port 5432 --username minutas_app minutas_ash
```

La tarea programada debe conservar copias según la política corporativa y probar restauración mensual en una base aislada. Un respaldo no verificado no es un plan de recuperación.

## 9. Lista de verificación antes de habilitar usuarios

- [ ] PostgreSQL 18 está instalado y el servicio inicia tras reiniciar la VM.
- [ ] `minutas_app` conecta a `minutas_ash`; no es superusuario.
- [ ] Puerto 5432 no está expuesto fuera de la red estrictamente requerida.
- [ ] Carpeta de fuentes/documentos está fuera de la carpeta de código.
- [ ] Cuenta `ASH-MinutasSvc` no es administradora.
- [ ] Secretos guardados fuera del repositorio y protegidos por ACL.
- [ ] IIS tiene certificado HTTPS válido y redirige HTTP a HTTPS.
- [ ] Respaldos automáticos y restauración de prueba documentada.
- [ ] Se definieron responsables de usuarios, proyectos, retención y auditoría.

## 10. Lo que todavía no debe hacerse

- No cambie `repository_provider` de la aplicación de escritorio a PostgreSQL: aún no existe un proveedor PostgreSQL productivo.
- No copie archivos `.db` de SQLite dentro de PostgreSQL manualmente.
- No abra 5432 a Internet ni use la cuenta `postgres` desde la aplicación.
- No cargue grabaciones sensibles antes de definir roles, retención y un piloto autorizado.
# SKILLY LATAM

SKILLY LATAM es una plataforma académica para publicar servicios profesionales, validar especialistas, coordinar prestaciones y administrar el ciclo completo de contratación. El proyecto integra marketplace, solicitudes, agenda, pagos, entregas, reclamos, retroalimentación, cancelaciones y reagendamiento bilateral.

Raúl Felipe Infante Guzmán desarrolló este proyecto. La versión de entrega está en la rama [`refactor/skilly`](https://github.com/ganjhamandx-ui/skilly_Latam/tree/refactor/skilly).

## Arquitectura

- **Backend:** Django 5.2 y Django REST Framework.
- **Frontend:** React 19 y Vite 8.
- **Base de datos principal:** PostgreSQL 18, base `skilly`, esquema `skilly`.
- **Autenticación:** sesiones Django, cookies `HttpOnly` y protección CSRF.
- **Caché de acceso:** `LocMemCache` para desarrollo de un proceso; puede configurarse un backend compartido mediante variables locales.
- **MongoDB:** las variables se conservan para integración documental, pero los datos operativos actuales residen en PostgreSQL.

El navegador entra exclusivamente por Vite. Las solicitudes a `/api` se redirigen al backend y conservan cookies y CSRF.

| Componente | Dirección local definitiva |
| --- | --- |
| Frontend | `http://127.0.0.2:57744/` |
| Backend | `http://127.0.0.2:57743/` |
| PostgreSQL | `127.0.0.1:5432` |

Los scripts de SKILLY no administran ni detienen PostgreSQL.

## Estructura principal

```text
backend/
  acceso/               Autenticación, sesiones y recuperación de acceso
  backoffice/           Auditoría e indicadores administrativos
  coordinacion/         Prestaciones, asignaciones y agenda segura
  marketplace/          Catálogo, propuestas y publicación de servicios
  pagos/                Retención, liberación, reversas y comisiones
  profesionales/        Perfil, documentos, entrevista y disponibilidad
  reagendamientos/      Flujo bilateral PRT-33, PRT-34 y PRT-35
  retroalimentacion/    Evaluaciones y recomendaciones
  seguimiento/          Avances, entregas, reclamos y cierre
  solicitudes/          Solicitudes empresariales y referencias privadas
  config/               Configuración y rutas Django
frontend/
  src/                  Componentes, estilos y reglas de interfaz
  config/               Configuración validada del proxy local
  tests/                Pruebas unitarias de reglas frontend
database/               SQL técnico de referencia
pruebas/                Comprobaciones auxiliares mantenidas
tools/                  Control de codificación utilizado por npm
```

Las migraciones Django forman parte del código fuente. Debe conservarse especialmente `backend/reagendamientos/migrations/0002_flujo_bilateral.py`, que crea `alternativa_reagendamiento` y amplía el modelo bilateral.

## Requisitos

- Windows 10 u 11 con PowerShell 5.1 o superior.
- Python 3.13 y `pip`.
- Node.js 24 y npm 11.
- PostgreSQL 18 accesible en `127.0.0.1:5432`.
- Git para obtener y actualizar el código.

Las versiones declaradas están fijadas en `requirements.txt`, `requirements-dev.txt` y `frontend/package-lock.json`.

## Instalación

### 1. Código y entorno Python

```powershell
git clone https://github.com/ganjhamandx-ui/skilly_Latam.git
Set-Location skilly_Latam
git switch refactor/skilly

py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 2. Dependencias frontend

```powershell
Set-Location frontend
npm ci
Set-Location ..
```

`node_modules` y `.venv` son reconstruibles y no forman parte del repositorio ni del ZIP de entrega.

### 3. Variables locales

Copiar el ejemplo y reemplazar únicamente los marcadores locales:

```powershell
Copy-Item .env.example .env
```

Como mínimo deben definirse una clave secreta segura y la contraseña del rol PostgreSQL. No se deben publicar `.env`, contraseñas, tokens, certificados ni credenciales de caché.

La configuración definitiva incluye:

```dotenv
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,127.0.0.2
POSTGRES_DB=skilly
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
POSTGRES_SCHEMA=skilly
FRONTEND_ORIGIN=http://127.0.0.2:57744
```

### 4. PostgreSQL y migraciones

Crear el rol, la base y el esquema con credenciales propias. El siguiente SQL es solo una plantilla; no se debe copiar una contraseña real al repositorio:

```sql
CREATE ROLE skilly_app LOGIN PASSWORD 'REEMPLAZAR_LOCALMENTE';
CREATE DATABASE skilly OWNER skilly_app;
\connect skilly
CREATE SCHEMA IF NOT EXISTS skilly AUTHORIZATION skilly_app;
```

La instalación desde cero requiere el SQL inicial porque parte de los modelos Django son administrados por PostgreSQL directamente. En una base nueva y vacía, ejecutar estos cuatro archivos en orden, autenticándose como `skilly_app` cuando `psql` solicite la contraseña. Si PostgreSQL no está en `PATH`, usar el ejecutable de su instalación.

```powershell
psql -X -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 5432 -U skilly_app -d skilly -f database/01_postgresql_tablas.sql -f database/02_postgresql_llaves_primarias.sql -f database/03_postgresql_llaves_foraneas.sql -f database/09_postgresql_tablas_e3.sql
```

Después, con `.env` configurado:

```powershell
.\.venv\Scripts\python.exe .\backend\manage.py migrate --noinput
.\.venv\Scripts\python.exe .\backend\manage.py check
```

El catálogo comienza con sus categorías y competencias iniciales. En una instalación nueva, quien administre SKILLY puede crear su cuenta local con `python backend/manage.py crear_admin_skilly`. El comando solicita una contraseña interactiva.

En una instalación existente, revisar primero `manage.py showmigrations --plan` y tener un respaldo verificable antes de aplicar migraciones pendientes. Los scripts de retiro de tablas y claves, datos sintéticos y conversión histórica de zona horaria son referencias académicas. Quedan fuera de la instalación normal. El ZIP contiene el código y los scripts de esquema, sin datos operativos.

## Inicio y cierre únicos

El procedimiento recomendado evita servidores duplicados y no busca puertos alternativos:

```powershell
powershell -ExecutionPolicy Bypass -File .\iniciar_skilly.ps1
```

Luego abrir exclusivamente:

`http://127.0.0.2:57744/`

Para detener solo los procesos que inició SKILLY:

```powershell
powershell -ExecutionPolicy Bypass -File .\detener_skilly.ps1
```

El iniciador valida `.env`, las dependencias locales y los puertos `57743`/`57744`, ejecuta `manage.py check` y comprueba el endpoint CSRF a través de Vite. Si un puerto está ocupado por otro proceso, informa el conflicto y mantiene los puertos establecidos. El cierre verifica el estado de ejecución, el PID, la hora de inicio y el comando antes de terminar los procesos registrados.

## Desarrollo manual

Los scripts anteriores son la ruta normal. Para diagnóstico local, el backend puede iniciarse manualmente con:

```powershell
.\.venv\Scripts\python.exe .\backend\manage.py runserver 127.0.0.2:57743 --noreload
```

En otra terminal:

```powershell
$env:SKILLY_API_PROXY_TARGET='http://127.0.0.2:57743'
Set-Location frontend
npm run dev -- --host 127.0.0.2 --port 57744 --strictPort
```

No se debe abrir el backend como interfaz de usuario ni ejecutar Vite sin el proxy explícito.

## Funcionalidades principales

- Marketplace y propuestas profesionales.
- Registro, documentos, entrevista y validación profesional.
- Solicitudes empresariales, coordinación, contratación y agenda.
- Pagos retenidos, comisiones, liberaciones y reversas controladas.
- Avances, entregas versionadas, observaciones, reclamos y cierre.
- Cuentas bancarias y trazabilidad administrativa.
- Retroalimentación privada y recomendaciones.
- Cancelaciones y liquidaciones controladas.
- **Video B:** la administración evalúa el expediente, resuelve el reclamo asociado cuando existe y autoriza la liquidación. Después utiliza un único botón «Finalizar distribución»: el backend documenta en una misma transacción la conciliación y el reparto simulado para organización, profesional y SKILLY. El prototipo no realiza devoluciones ni transferencias bancarias reales; los registros y estados quedan identificados como simulados.
- Reagendamiento bilateral iniciado por organización o profesional, con política versionada, evidencia privada, alternativas múltiples, espera controlada y aplicación segura de agenda.

## Comprobaciones técnicas

Estas verificaciones no crean datos de demostración:

```powershell
.\.venv\Scripts\python.exe .\backend\manage.py check
.\.venv\Scripts\python.exe .\backend\manage.py showmigrations --plan
.\.venv\Scripts\python.exe .\backend\manage.py makemigrations reagendamientos --check --dry-run

Set-Location frontend
npm run lint
npm run build
```

Las pruebas específicas pueden ejecutarse desde la raíz con `python backend/manage.py test <módulo>` o desde `frontend` con `node --test <archivo>`. Las pruebas que escriben datos necesitan una base de prueba aislada. Ejecuta las comprobaciones npm con el entorno virtual activo para que el control de codificación encuentre las dependencias de Python.

## Seguridad y datos privados

- CSRF, autenticación y permisos no deben desactivarse para facilitar desarrollo.
- CORS y orígenes confiables se configuran explícitamente, sin comodines.
- Las evidencias, documentos profesionales y entregas privadas no se publican.
- Los pagos y operaciones sensibles se revalidan dentro de transacciones.
- Los scripts SQL destructivos son material técnico de referencia y nunca deben ejecutarse sobre datos reales sin respaldo y revisión.
- `.env`, `backend/media`, `backend/entregas_privadas_e3`, dumps, logs, cachés y respaldos están excluidos del repositorio y de la entrega.

## Entrega académica

El ZIP de código fuente se genera fuera del repositorio. Contiene código, migraciones, dependencias declaradas, recursos utilizados, pruebas mantenidas, `.env.example`, scripts operativos y este README. No incluye `.git`, dependencias instaladas, Word/Excel académicos, datos privados, bases, dumps, logs ni respaldos.

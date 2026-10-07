# CasinoCore — Core Runtime (Sprint 1)

**CasinoCore** es una plataforma modular de gaming management B2B diseñada con arquitectura de monolito modular, principios SOLID, Clean Architecture, tipado estricto en Python 3.12+, FastAPI, SQLAlchemy 2.0 (asíncrono con `asyncpg`) y PostgreSQL 16.

---

## 🏛️ Arquitectura del Sistema

```
casino-core/
├── .env.example              # Plantilla de variables de entorno
├── .gitignore                # Reglas de exclusión de Git
├── docker-compose.yml        # Orquestación de PostgreSQL 16 y Backend FastAPI
├── README.md                 # Documentación técnica y operacional
└── backend/
    ├── Dockerfile            # Imagen base Python 3.12-slim para el backend
    ├── pyproject.toml        # Configuración de empaquetado, dependencias y pytest
    ├── alembic.ini           # Configuración del gestor de migraciones Alembic
    ├── alembic/
    │   ├── env.py            # Runner asíncrono de migraciones Alembic
    │   ├── script.py.mako    # Plantilla de generación de migraciones
    │   └── versions/         # Directorio de versiones de migración
    ├── app/
    │   ├── main.py           # Ciclo de vida (lifespan) e inicialización de FastAPI
    │   ├── core/
    │   │   ├── config.py     # Settings y validación vía pydantic-settings
    │   │   ├── database.py   # Engine async, async_sessionmaker, Base y TimestampMixin
    │   │   └── exceptions.py # Jerarquía de excepciones de dominio y aplicación
    │   └── modules/
    │       ├── health/       # Probes de observabilidad (/health y /health/ready)
    │       │   ├── router.py
    │       │   └── schemas.py
    │       └── operators/    # Módulo de operadores (entidad PoC de persistencia)
    │           └── models.py
    └── tests/
        ├── conftest.py       # Fixtures asíncronos con httpx.AsyncClient y mocks de DB
        ├── test_health.py    # Tests de endpoints /health y /health/ready
        └── test_database.py  # Tests unitarios del engine, pool, sesión y modelo Operator
```

---

## 🚀 Requisitos Previos

- **Docker** 24.0+ y **Docker Compose** v2+
- **Python** 3.12+ (para desarrollo local sin Docker)
- **curl** o cliente HTTP para verificar endpoints

---

## ⚙️ Variables de Entorno

Copia el archivo `.env.example` a `.env`:

```bash
cp .env.example .env
```

| Variable | Tipo | Default | Descripción |
| :--- | :--- | :--- | :--- |
| `PROJECT_NAME` | `string` | `CasinoCore` | Nombre de la aplicación |
| `ENVIRONMENT` | `string` | `development` | Entorno de ejecución (`development`, `staging`, `production`, `test`) |
| `LOG_LEVEL` | `string` | `INFO` | Nivel de logging (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `POSTGRES_SERVER` | `string` | `postgres` (docker) / `localhost` (local) | Host del servidor PostgreSQL |
| `POSTGRES_PORT` | `int` | `5432` | Puerto de conexión a PostgreSQL |
| `POSTGRES_DB` | `string` | `casinocore` | Nombre de la base de datos |
| `POSTGRES_USER` | `string` | `casinocore_user` | Usuario de PostgreSQL |
| `POSTGRES_PASSWORD` | `string` | `casinocore_password` | Contraseña del usuario de PostgreSQL |
| `POSTGRES_ECHO` | `bool` | `false` | Activar log de queries SQL emitidas |

---

## 🐳 Ejecución con Docker Compose

### 1. Levantar la infraestructura completa
El comando compila la imagen del backend, inicializa el contenedor de PostgreSQL 16 con healthcheck nativo (`pg_isready`) y levanta la API con hot-reload:

```bash
docker compose up --build -d
```

### 2. Verificar estado de los contenedores
```bash
docker compose ps
```

### 3. Visualizar logs en tiempo real
```bash
docker compose logs -f backend
```

### 4. Detener el entorno
```bash
docker compose down
```
*(Para eliminar también los volúmenes de datos: `docker compose down -v`)*

---

## 🧪 Ejecución de Tests

Los tests automatizados están construidos sobre `pytest`, `pytest-asyncio` y `httpx.AsyncClient`.

### Ejecutar tests en contenedor Docker:
```bash
docker compose exec backend pytest
```

### Ejecutar tests localmente:
```bash
# Crear entorno virtual (si no existe)
python3 -m venv .venv
source .venv/bin/activate

# Instalar dependencias con extras de testing
pip install -e "./backend[dev]"

# Ejecutar test suite
pytest backend/tests -v
```

---

## 🗄️ Migraciones de Base de Datos (Alembic)

Alembic está configurado para operar de forma 100% asíncrona mediante `asyncpg`.

### Generar una nueva migración:
```bash
docker compose exec backend alembic revision --autogenerate -m "create_operators_table"
```

### Aplicar migraciones pendientes:
```bash
docker compose exec backend alembic upgrade head
```

### Revertir última migración:
```bash
docker compose exec backend alembic downgrade -1
```

---

## 🩺 Endpoints de Salud y Observabilidad

Una vez levantada la aplicación en `http://localhost:8000`:

### 1. Liveness Probe (`GET /api/v1/health`)
Verifica que el proceso HTTP responde correctamente.
```bash
curl -i http://localhost:8000/api/v1/health
```
**Respuesta esperada (200 OK):**
```json
{
  "status": "ok",
  "environment": "development"
}
```

### 2. Readiness Probe (`GET /api/v1/health/ready`)
Ejecuta un query ligero `SELECT 1` para comprobar la conectividad activa con PostgreSQL.
```bash
curl -i http://localhost:8000/api/v1/health/ready
```
**Respuesta esperada (200 OK):**
```json
{
  "status": "ready",
  "database": "connected"
}
```
*Si la base de datos no está disponible, el endpoint devuelve `503 Service Unavailable`.*

---

## 📄 Documentación Interactiva de la API
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

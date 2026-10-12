# Política de Seguridad y Hardening Técnico — CasinoCore

## 1. Declaración de Misión y Filosofía de Seguridad

CasinoCore es una plataforma modular B2B de backend para casinos virtuales desarrollada con una arquitectura de **Defensa en Profundidad (Defense in Depth)** y diseñada bajo los principios del **OWASP API Security Top 10 (2023)**.

La seguridad de la plataforma se fundamenta en cinco pilares clave:
1. **Zero Data Leakage & Strict Multi-Tenancy**: Aislamiento estricto de datos por operador mediante contexto asíncrono y control de acceso riguroso.
2. **Atomic Financial Consistency**: Prevención total de condiciones de carrera y doble gasto mediante bloqueo pesimista en base de datos e idempotencia forzada.
3. **Criptografía Moderna y Resistente**: Hashing de contraseñas de última generación con Argon2id y tokens de sesión con SHA-256.
4. **Protección Anti-Enumeración y BOLA**: Respuestas controladas `HTTP 404 Not Found` en lugar de fugas informativas de existencia de recursos.
5. **Auditoría Forense Inmutable**: Registro estructurado e inalterable de todos los eventos administrativos, de juego y de cumplimiento normativo.

---

## 2. Análisis de Amenazas y Mitigaciones Técnicas

### 2.1 Prevención de Inyección SQL (SQLi)
* **Amenaza**: Inyección de sentencias SQL maliciosas a través de parámetros de consulta, cuerpos JSON o cabeceras HTTP que alteren consultas a la base de datos PostgreSQL.
* **Mitigación Implementada**:
  - **SQLAlchemy 2.0 Async ORM**: Todas las interacciones con la base de datos se ejecutan a través de sentencias tipadas (`select()`, `insert()`, `update()`) utilizando parámetros vinculados nativos (bound parameters) del driver `asyncpg`.
  - **Prohibición de Concatenación de Cadenas**: No existe concatenación dinámica de cadenas SQL en ninguna capa de servicios o repositorios.
  - **Mapeo Declarativo Estricto**: Tipos de datos validados por SQLAlchemy y Pydantic v2 previo al procesamiento por el motor de persistencia.

### 2.2 Control de Concurrencia y Mitigación de Doble Gasto (Double-Spending)
* **Amenaza**: Ataques de condición de carrera (Race Conditions / TOCTOU - Time-Of-Check to Time-Of-Use) enviando múltiples peticiones de débito o apuestas concurrentes para gastar un mismo saldo antes de que se descuente.
* **Mitigación Implementada**:
  - **Bloqueo Pesimista a Nivel de Fila (`SELECT FOR UPDATE`)**: Toda transacción monetaria (apuesta, débito o cobro de premios) adquiere un bloqueo exclusivo sobre la fila de la billetera en PostgreSQL (`select(Wallet).where(...).with_for_update()`). Ninguna otra transacción concurrente puede leer o modificar el saldo hasta que la transacción en curso confirme (`commit`) o revierta (`rollback`).
  - **Libro Mayor Transaccional Atómico (Double-Entry Ledger)**: El saldo de la billetera se actualiza en la misma unidad de trabajo atómica en que se inserta el asiento contable inmutable (`LedgerEntry`).
  - **Idempotencia Forzada vía Cabecera `Idempotency-Key`**: Peticiones financieras críticas exigen la cabecera `Idempotency-Key` (UUIDv4). Las claves se persisten junto con un digest SHA-256 del payload recibido. Si se reintenta una petición con la misma clave y payload idéntico, se retorna la respuesta memorizada; si el payload difiere, se rechaza inmediatamente con `HTTP 400 Bad Request`.

### 2.3 Criptografía y Gestión de Credenciales
* **Amenaza**: Robo de credenciales en tránsito o en reposo mediante ataques de diccionario, tablas arcoíris (Rainbow Tables) o fuerza bruta asistida por GPU/ASIC.
* **Mitigación Implementada**:
  - **Argon2id (RFC 9106)**: Hashing de contraseñas de jugadores y administradores utilizando Argon2id a través de la librería `pwdlib`. Configurado con parámetros recomendados de costo de memoria, iteraciones y paralelismo que neutralizan la computación acelerada por GPU.
  - **JSON Web Tokens (JWT) Efímeros**: Tokens de acceso firmados con HMAC-SHA256 (`HS256`) y expiración corta (15 minutos por defecto).
  - **Rotación de Refresh Tokens Criptográficos**: Refresh tokens de alta entropía (48 bytes URL-safe generados mediante `secrets.token_urlsafe`), almacenados en base de datos exclusivamente como hash SHA-256. La rotación es obligatoria en cada renovación y los tokens antiguos son revocados de forma irreversible.

### 2.4 Mitigación de CSRF y XSS (Cross-Site Scripting)
* **Amenaza**: Secuestro de sesiones o inyección de scripts maliciosos en clientes web y APIs.
* **Mitigación Implementada**:
  - **Arquitectura de API Stateless Bearer**: No se utilizan cookies automáticas de sesión en el navegador, eliminando de raíz la superficie de ataque para Cross-Site Request Forgery (CSRF).
  - **Esquemas Pydantic v2 con Sanitización**: Validación estricta de tipos, longitudes mínimas y máximas, y validación regex para evitar inyecciones de payloads XSS o caracteres de control.
  - **Serialización Segura de Salida**: Todas las respuestas son formateadas a JSON nativo con codificación UTF-8 y cabecera `Content-Type: application/json`.

### 2.5 Broken Object Level Authorization (BOLA) y Broken Object Property (BOPA)
* **Amenaza**: Acceso no autorizado o manipulación de billeteras, sesiones o datos de usuarios alterando los identificadores de recursos en las URLs (`/api/v1/wallet/{wallet_id}`).
* **Mitigación Implementada**:
  - **Validación de Identidad y Pertenencia**: El middleware y las dependencias de FastAPI garantizan que un actor sólo acceda a recursos donde `user_id == current_user.id` y `operator_id == current_user.operator_id`.
  - **Máscara 404 Not Found**: Si un usuario autenticado intenta solicitar un recurso perteneciente a otro usuario u otro operador, la plataforma retorna `HTTP 404 Not Found` en lugar de `HTTP 403 Forbidden`, evitando activamente la enumeración de identificadores de recursos privados (ID enumeration prevention).

### 2.6 Aislamiento Estricto Multi-Tenant (Cross-Tenant Isolation)
* **Amenaza**: Fuga de datos o contaminación cruzada entre operadores B2B concurrentes en la misma base de datos.
* **Mitigación Implementada**:
  - **Middleware Asíncrono `TenantMiddleware`**: Extrae la cabecera `X-Operator-Slug`, valida la existencia y estado activo del operador en PostgreSQL, y fija la variable contextual asíncrona (`current_tenant_id`).
  - **Control Anti-Suplantación de Tenant**: Si la petición incluye un token JWT autenticado, el middleware verifica que el `operator_id` del token coincida con el `operator_id` resuelto desde el slug. Si difieren, la petición se aborta con `HTTP 403 Forbidden: Cross-tenant operation prohibited`.
  - **Excepción de Superadministrador (`SUPER_ADMIN`)**: El rol `SUPER_ADMIN` es el único facultado para ejecutar consultas globales cruzadas entre tenants para fines de auditoría de plataforma o soporte técnico.

---

## 3. Matriz de Roles y Permisos (RBAC)

| Rol | Alcance | Permisos Principales |
| :--- | :--- | :--- |
| **`SUPER_ADMIN`** | Global (Todos los Tenants) | `system:admin`, `operator:admin`, `games:manage`, auditoría forense global, creación de operadores. |
| **`OPERATOR_ADMIN`** | Tenant Específico | `operator:admin`, `users:read`, `users:write`, `reports:read`, `games:manage` (catálogo y límites). |
| **`GAME_MANAGER`** | Tenant Específico | `games:manage`, `reports:read`, `gaming:play`. |
| **`FINANCE`** | Tenant Específico | `reports:read`, `users:read`, `audit:read`. |
| **`COMPLIANCE`** | Tenant Específico | `audit:read`, `compliance:write` (revisión KYC, autoexclusiones). |
| **`PLAYER`** | Tenant Específico | `gaming:play`, `gaming:spin`, recarga de faucet educativo, consulta de billetera propia. |

---

## 4. Política de Divulgación Responsable de Vulnerabilidades

Si descubres una vulnerabilidad de seguridad en CasinoCore, por favor no abras un issue público en GitHub. Envía un correo con el reporte detallado a:
**`security@casinocore.internal`**

Incluye en tu reporte:
1. Descripción de la vulnerabilidad y componentes afectados.
2. Pasos reproducibles o prueba de concepto (PoC).
3. Impacto potencial en la confidencialidad, integridad o disponibilidad de la plataforma.

El equipo de seguridad acusará recibo en menos de 24 horas hábiles y coordinará la corrección antes de cualquier divulgación pública.

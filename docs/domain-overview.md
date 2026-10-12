# Glosario de Dominio y Conceptos Clave — CasinoCore

## 1. Introducción al Dominio del Juego B2B

El dominio de software para plataformas de casino y apuestas en línea (iGaming) involucra conceptos especializados de contabilidad transaccional, teoría de probabilidades, diseño de juegos y cumplimiento normativo. Este documento formaliza el vocabulario técnico y operativo utilizado a lo largo de la arquitectura, modelos de base de datos y APIs de **CasinoCore**.

---

## 2. Glosario Formal de la Plataforma

### 2.1 Operador (B2B Tenant)
* **Definición**: Entidad jurídica o comercial independiente que contrata y utiliza la plataforma CasinoCore para ofrecer servicios de juego a sus propios usuarios finales (jugadores).
* **Función en la Plataforma**: Representa la frontera lógica de aislamiento de datos (**Multi-Tenancy**). Cada operador posee su propio identificador único (`operator_id`), slug público (`slug`), catálogo personalizable de juegos (`OperatorGameConfig`), base de jugadores, billeteras y reportes financieros segregados.

### 2.2 Billetera Virtual (Virtual Wallet)
* **Definición**: Cuenta de fondos virtuales expresada en créditos enteros (`CREDITS`) asignada de forma unívoca a un jugador bajo un operador específico.
* **Función en la Plataforma**: Contiene un saldo en caché (`balance`) que permite consultas rápidas de interfaz, protegido por bloqueo pesimista a nivel de fila (`SELECT FOR UPDATE`) para evitar condiciones de carrera o saldos negativos durante apuestas concurrentes.

### 2.3 Libro Mayor Inmutable (Immutable Ledger)
* **Definición**: Registro contable secuencial y de solo inserción (**Append-Only Ledger**) que documenta cada movimiento financiero individual que altera una billetera virtual.
* **Función en la Plataforma**: Fuente de verdad absoluta de la contabilidad. Cada registro (`LedgerEntry`) almacena el monto de la operación, el tipo de transacción (`CREDIT`, `DEBIT`, `BET_PLACED`, `WIN_PAYOUT`, `FAUCET_RELOAD`), el saldo inmediatamente antes y después, y la clave de idempotencia (`idempotency_key`), permitiendo la reconstrucción y reconciliación matemática del saldo en cualquier momento.

### 2.4 Sesión de Juego (Game Session)
* **Definición**: Contexto temporal y de estado que encapsula la interacción activa de un jugador con un juego determinado.
* **Función en la Plataforma**: Inicia con estado `ACTIVE` y registra fecha de inicio (`started_at`). Actúa como contenedor de una secuencia cronológica de rondas de juego (`GameRound`). Finaliza explícitamente a petición del jugador (`COMPLETED`), o automáticamente por revocación administrativa, expiración o activación de límites de juego responsable.

### 2.5 Ronda de Juego (Game Round)
* **Definición**: Unidad atómica e indivisible de apuesta y resolución de resultado dentro de una sesión de juego.
* **Ciclo de Vida**:
  1. **Validación**: Comprobación de límites de apuesta (`min_bet`, `max_bet`), reglas de autoexclusión y límites diarios del jugador.
  2. **Débito Atómico**: Descuento del valor de la apuesta de la billetera y creación del asiento contable en el ledger.
  3. **Generación Aleatoria**: Invocación al proveedor RNG para obtener los símbolos o valores de la jugada.
  4. **Evaluación de Reglas**: Cálculo de líneas de pago, combinaciones ganadoras o manos según las reglas del juego.
  5. **Liquidación y Acreditación**: En caso de victoria, acreditación del premio al saldo y registro del asiento de ganancia en el ledger.

### 2.6 Generador Pseudoaleatorio (RNG - Random Number Generator)
* **Definición**: Algoritmo matemático determinista que genera secuencias numéricas cuyas propiedades estadísticas simulan aleatoriedad perfecta e impredecibilidad.
* **Función en la Plataforma**: Abstraído mediante la interfaz `IRNGProvider`. En entornos educativos y de desarrollo, provee resultados controlados y reproducibles (`StandardRNGProvider`), mientras que en entornos de producción certificados se conecta a fuentes de entropía física o generadores criptográficos de grado industrial (CSPRNG).
* **Nota de Advertencia**: En esta versión de CasinoCore, el motor RNG está diseñado para propósitos de simulación técnica y educativa, sin certificación de laboratorios para dinero real.

### 2.7 Retorno Teórico al Jugador (RTP - Return to Player)
* **Definición**: Porcentaje teórico y estadístico esperado a largo plazo de la cantidad total apostada por los jugadores que un juego devolverá en forma de premios.
* **Ejemplos en la Plataforma**:
  - Tragamonedas Clásica de 3 Rodillos: RTP teórico configurado en **96.5%**.
  - Ruleta Europea (un solo cero): RTP teórico matemático del **97.30%** (ventaja de la casa del 2.70%).
  - Blackjack Clásico (6 mazos, dealer se planta en 17): RTP teórico de estrategia óptima cercano al **99.50%**.

### 2.8 Ingreso Bruto del Juego Simulado (GGR - Gross Gaming Revenue)
* **Definición**: Métrica financiera clave en la industria del juego que representa los ingresos netos generados por las apuestas antes de deducciones fiscales u operativas.
* **Fórmula de Cálculo**:
  $$\text{GGR} = \text{Total Bet Amount} - \text{Total Win Payout}$$
* **Función en la Plataforma**: Calculado y consolidado por el módulo de reportes (`ReportingService`) por operador y por juego, permitiendo evaluar la rentabilidad del catálogo de entretenimiento.

### 2.9 Pista Forense de Auditoría (Audit Trail)
* **Definición**: Registro estructurado, inmutable y fechado cronológicamente que documenta acciones sensibles, operaciones de administración y eventos de seguridad en la plataforma.
* **Función en la Plataforma**: Captura cambios de configuración de juegos, revisiones de expedientes KYC, solicitudes de autoexclusión, inicio de sesiones y eventos críticos, proveyendo evidencia verificable ante inspecciones de reguladores y auditores forenses.

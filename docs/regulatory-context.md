# Marco Regulatorio y Contexto Legal Educativo — CasinoCore

## 1. Naturaleza Jurídica del Juego de Azar en la República Argentina

En la República Argentina, el régimen legal de los juegos de azar y apuestas en línea responde a un modelo federal estricto derivado de la **Constitución Nacional**:

### 1.1 Poder de Policía y Facultades No Delegadas (Art. 121 CN)
De conformidad con el **Artículo 121 de la Constitución Nacional Argentina**, las provincias conservan todo el poder no delegado por la Constitución al Gobierno Federal. La regulación, fiscalización, explotación y autorización de juegos de azar, loterías y casinos **no fue una facultad delegada a la Nación**.

Por consiguiente:
* No existe una ley federal única que regule el juego en línea a nivel nacional.
* Cada una de las 23 provincias y la Ciudad Autónoma de Buenos Aires (CABA) posee su propia autoridad de aplicación y su propio marco normativo independiente.
* El juego no regulado u operado sin licencia provincial expresa constituye un delito penal tipificado en el **Artículo 301 bis del Código Penal de la Nación** (explotación, administración u operación de juegos de azar sin autorización legal).

---

## 2. Estudio de Caso: IPJyC de Mendoza

En la Provincia de Mendoza, la autoridad de regulación y contralor es el **Instituto Provincial de Juegos y Casinos (IPJyC)**, creado por la Ley Provincial N.º 6.362 y reglamentado para la modalidad online mediante la **Resolución N.º 434/2021 y modificatorias**.

### 2.1 Principios del Modelo Regulatorio Mendocino
1. **Licitación Pública de Licencias**: Otorgamiento de licencias de explotación B2C mediante concursos públicos transparentes, con exigencias patrimoniales, societarias y de antecedentes penales.
2. **Protección al Jugador y Juego Responsable**:
   - Registro Único de Autoexcluidos de la Provincia de Mendoza.
   - Verificación estricta de identidad (KYC) para prohibir el acceso a menores de 18 años y deudores alimentarios morosos.
   - Mecanismos de fijación de límites diarios, semanales y mensuales de tiempo de sesión y monto de depósito.
3. **Conexión Telemática y Fiscalización en Tiempo Real**: Los sistemas centrales del operador deben proveer interfaces de monitoreo remoto para que el IPJyC audite cada apuesta, premio y cálculo de Ingreso Bruto del Juego (GGR) a efectos del pago del canon provincial e impuestos fiscales.

---

## 3. Distinción Jurídica B2B vs. B2C

En la industria moderna de iGaming, la legislación diferencia con precisión dos roles con responsabilidades y licencias distintas:

| Criterio | Proveedor Tecnológico B2B (CasinoCore) | Operador de Casino B2C (Licensee) |
| :--- | :--- | :--- |
| **Definición** | Desarrollador de la plataforma de software, motores de juego y arquitectura de datos. | Titular de la licencia de explotación comercial otorgada por el ente regulador (IPJyC). |
| **Relación Comercial** | Contratos de licencia de software (SaaS) con operadores. | Relación contractual directa con los jugadores finales. |
| **Custodia de Fondos Reales** | **Ninguna**. No recibe, retiene ni procesa dinero fiduciario ni cuentas bancarias de jugadores. | Custodia fiduciaria exclusiva de los depósitos, cobros y pagos de premios en cuentas bancarias autorizadas. |
| **Obligaciones Legales** | Certificación técnica del software (GLI-19) y entrega de código auditable. | Cumplimiento tributario, prevención de lavado de activos (UIF), KYC y atención al usuario. |

---

## 4. Requisitos de Certificación Técnica Internacional (GLI-19)

Para que una plataforma de software pueda ser desplegada legalmente en una jurisdicción regulada, debe someterse a un riguroso proceso de homologación ante **Laboratorios de Ensayo Independientes (ITL - Independent Testing Laboratories)** acreditados internacionalmente (tales como *Gaming Laboratories International (GLI)*, *BMM Testlabs* o *eCOGRA*).

### 4.1 Norma GLI-19: Interactive Gaming Systems
La norma **GLI-19** establece los estándares técnicos de referencia mundial para sistemas de juego interactivo:
1. **Generador de Números Aleatorios (RNG)**:
   - Inspección estricta del código fuente del algoritmo.
   - Evaluación de entropía, período y no correlación estadística mediante baterías de pruebas formales (*Dieharder*, *NIST SP 800-22*).
   - Inmunidad contra cualquier manipulación externa de la semilla o estado interno.
2. **Integridad del Libro Mayor y Contabilidad**:
   - Respaldo atómico de cada transacción de apuesta y premio.
   - Capacidad de reconstrucción y recuperación ante fallos imprevistos de energía o base de datos sin pérdida de fondos.
3. **Pistas Forenses y Seguridad de Acceso**:
   - Auditoría inmutable de todas las acciones de usuarios con privilegios elevados.
   - Cifrado robusto en tránsito (TLS 1.3) y en reposo (AES-256 / hashing de contraseñas de vanguardia).

---

## 5. Descargo de Responsabilidad y Aviso de No Aplicabilidad Comercial

> [!CAUTION] ADVERTENCIA LEGAL Y DESCARGO DE RESPONSABILIDAD EDUCATIVA
> **CasinoCore** es un proyecto de software desarrollado con fines estrictamente **académicos, educativos y de demostración técnica de arquitectura**.
> 
> * **Prohibición de Uso Comercial**: Este software **NO** cuenta con licencia de explotación, homologación de laboratorio (GLI/BMM) ni autorización de ningún organismo regulador provincial (IPJyC de Mendoza, LOTBA, IPLyC Buenos Aires ni homólogos internacionales).
> * **Inexistencia de Apuestas Reales**: Las billeteras virtuales, créditos (`CREDITS`) y mecánicas de juego operan exclusivamente en un entorno simulado de prueba sin equivalencia con moneda de curso legal.
> * **Exención de Responsabilidad**: Los desarrolladores y contribuyentes de este repositorio no asumen responsabilidad civil, penal o comercial alguna por el uso indebido, alteración o despliegue no autorizado de este código en entornos reales de captación de apuestas.

# SafeAnesthesia Infusomat

Módulo independiente para el cálculo avanzado de programación anestésica y simulador de bombas de infusión (B. Braun Infusomat Space).
Diseñado para su uso en Medicina Veterinaria, ofreciendo herramientas de cálculo clínico, validación de bioseguridad, y registro de eventos.

> **⚠️ ADVERTENCIA CLÍNICA Y LEGAL**
> 
> Esta aplicación es una herramienta de asistencia y **NO sustituye el criterio clínico del médico veterinario anestesiólogo**.
> - Todas las dosis, volúmenes y tiempos de cebado sugeridos deben ser verificados por el profesional a cargo.
> - El desarrollador no asume responsabilidad por eventos adversos, sobredosificaciones o toxicidad derivados del uso del software.
> - Asegúrese de contar con consentimiento informado previo al uso de protocolos anestésicos críticos.

---

## 🛠️ Módulos Incluidos

- **Módulo Propofol:** Cálculo de inducción y mantenimiento (TIVA), determinando concentraciones finales al diluir con suero, dosis por minuto, mg por hora, y volúmenes finales.
- **Módulo Infusomat (Bomba de Infusión):** Configuración de volumen a infundir (VTBI), tasas de flujo en ml/h, tiempo total, y cálculo exacto de **retraso de cebado (priming delay)** según el volumen muerto del equipo.
- **Módulo Ketamina:** Cálculo de bolos, indexación de refuerzos, monitoreo continuo de dosis acumulada, e interfaz reactiva con clasificación de niveles de seguridad (`SAFE`, `WARNING`, `CRITICAL`).
- **Módulo Lidocaína:** Control estricto de anestesia loco-regional (Línea Alba, Ligamento Ovárico, Peritoneo, etc.), gestión de porcentajes máximos permitidos por toxicidad (mg/kg), alertas tempranas al acercarse al límite tóxico de cada especie (gato vs perro).

## 🚀 Integración Futura (Fase 4+)
Este módulo podrá exportar datos anestésicos hacia **PartenVet** mediante endpoints JSON y/o Webhooks, pero **actualmente funciona de forma 100% independiente**. No utiliza login ni base de datos de PartenVet.

---

## 💻 Requisitos

- Python 3.12+
- Git

---

## ⚙️ Instalación Local (Windows)

1. **Clonar el repositorio**
   ```bash
   git clone https://github.com/Felipe16051975/safeanesthesia-infusomat.git
   cd safeanesthesia-infusomat
   ```

2. **Crear y activar el entorno virtual**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```

3. **Instalar dependencias**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configurar el entorno**
   Copia el archivo de ejemplo para crear tu propio `.env`:
   ```bash
   copy .env.example .env
   ```

5. **Ejecutar la aplicación**
   Puedes iniciar el servidor local con el script incluido:
   ```bash
   start_local.bat
   ```
   *Alternativamente:* `python app.py`

6. **Usuario inicial**
   El sistema creará un usuario administrador predeterminado en su primer inicio:
   - **Usuario:** `admin`
   - **Contraseña:** `admin123`
   
   > **Importante:** Recuerde cambiar esta contraseña antes de utilizar la aplicación en un entorno real.

---

## 🧪 Pruebas (Tests)

Para validar la correcta funcionalidad de todas las fases, ejecuta:

```bash
run_tests.bat
```
Esto lanzará las pruebas de regresión (Fase 1) y los validadores de nuevas funcionalidades (Fase 2) empleando `pytest`.

---

## 🌐 Despliegue en Render

El repositorio ya está estructurado y configurado con:
- `Procfile`: Para orquestación vía `gunicorn`.
- `runtime.txt`: Versión definida de Python (3.12.7) compatible con la plataforma.
- `requirements.txt`: Para la instalación de librerías.

Para desplegar:
1. Conecta tu repositorio de GitHub en el panel de **Render**.
2. Selecciona **Web Service**.
3. Render detectará automáticamente el archivo `Procfile` y la versión en `runtime.txt`.
4. Añade tus variables de entorno clave (`SECRET_KEY`, `FLASK_ENV`, `DATABASE_URL` usando un volumen/base de Render o local si es SQLite temporal).
5. Despliega (Deploy).

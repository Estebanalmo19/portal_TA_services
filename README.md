# ARRISE Solutions Portal

MVP de demostración: un portal Django que centraliza siete soluciones
ficticias (Talent Acquisition, HR Colombia, Security, Data & Analytics y
Operations) más **Agent TA**, un asistente local de FAQ para Talent
Acquisition. Todos los datos son sintéticos — ver `docs/implementation-notes.md`
para el contrato de arquitectura completo y `docs/comparison.md` para el
contexto de esta rama dentro del ejercicio de comparación.

**Demo · Datos ficticios.** No es apto para producción tal cual: sin base de
datos real, sin autenticación real, sin integraciones externas. Ver
"Limitaciones" abajo.

## Requisitos

- **Python 3.12 o superior**, compatible con Django 5.2 LTS. Si tu sistema
  solo tiene una versión de Python más nueva sin soporte oficial confirmado
  para Django 5.2 (por ejemplo 3.14), instala 3.12 en paralelo:
  - Windows: `py install 3.12` (Python install manager) y usa `py -3.12`.
  - macOS/Linux: instala 3.12 con tu gestor de versiones habitual
    (`pyenv install 3.12`, Homebrew, el paquete de tu distro, etc.).
- Git.
- Ningún servicio externo: el portal corre completamente offline una vez
  instaladas las dependencias.

## Instalación desde cero

### Windows (PowerShell o Git Bash)

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

> Si la política de ejecución de PowerShell bloquea `Activate.ps1`, no la
> actives: usa siempre la ruta directa al intérprete,
> `.\.venv\Scripts\python.exe manage.py ...`, como en todos los comandos de
> este documento.

### macOS / Linux (bash/zsh)

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Ejecutar el portal

```powershell
# Windows
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py runserver
```

```bash
# macOS / Linux
python manage.py check
python manage.py runserver
```

Abre `http://127.0.0.1:8000/`. **No hace falta `migrate` ni `createsuperuser`**
— esta demo no usa base de datos (`DATABASES = {}`); el estado de negocio
vive en `sessionStorage` del navegador dentro de cada pestaña.

## Pruebas

```powershell
.\.venv\Scripts\python.exe manage.py test
```

```bash
python manage.py test
```

110 pruebas (`SimpleTestCase`, sin base de datos) cubren las siete
soluciones, Agent TA, el dashboard y la integridad de `mock_data`. Ver
`docs/verification.md` para el detalle de qué se probó automatizado vs. con
navegador real, y las limitaciones encontradas.

### Verificación con navegador (opcional, para desarrollo)

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m playwright install chromium
```

`requirements-dev.txt` no es necesario para abrir el portal — solo para
correr verificación visual/funcional con Playwright.

## Perfiles de demostración

Al entrar eliges **Manager**, **Solution Owner** o **Analyst**. Es una
simulación de qué recorrido ve cada rol, guardada en `sessionStorage`
(`arrise_profile`) — **no es autenticación ni autorización real** (ver
`/acerca/` dentro del portal). Manager tiene el recorrido completo y el
dashboard ejecutivo.

## Datos de demostración

`mock_data/` genera todo el dataset de forma determinista a partir de una
fecha de referencia y una semilla (`DEMO_REFERENCE_DATE`, `DEMO_SEED` en
`config/settings.py`, por defecto la fecha real de esta entrega). Incluye:
240 colaboradores ficticios (`Colaborador Demo 0NN`, `@example.com`), y al
menos 15 registros de muestra por solución (18-22 en la mayoría), más 12
meses de series de actividad por solución para el dashboard ejecutivo.
"Restablecer demo" (menú de perfil) borra el estado mutado de la pestaña y
recarga estos datos iniciales, conservando tema y perfil.

## Arquitectura (resumen — detalle completo en `docs/implementation-notes.md`)

- **Sin base de datos.** Django sirve un snapshot inicial embebido en cada
  página (`json_script`); el navegador lo copia a `sessionStorage` y todas
  las páginas de esa pestaña leen/escriben ese mismo estado.
- Cada mutación (crear, asignar, comentar, cambiar estado) es un POST JSON a
  un endpoint local de la solución; Django valida con servicios Python
  puros (`solutions/services/`) y responde un resultado normalizado — nunca
  busca el registro por ID en un almacén, porque no hay ninguno.
- Apps: `core` (home, catálogo, about, búsqueda, Agent TA), `dashboard`
  (KPIs ejecutivos), `solutions` (las siete soluciones). `mock_data/` son
  módulos Python puros con los datasets, no una app Django.

## Estructura del proyecto

```
config/            settings, urls, wsgi/asgi
core/               home, catálogo, about, búsqueda global, Agent TA
dashboard/          agregación de KPIs ejecutivos y exportación CSV
solutions/          las siete soluciones (services/views/urls por slug)
mock_data/          generador determinista de datos ficticios
templates/          Django Templates (base + layout + por módulo)
static/             CSS de marca, JS vanilla por módulo, Chart.js local
tests/              suite Django (SimpleTestCase, sin BD)
docs/               notas de implementación, comparación, verificación
```

## Rutas principales

| Ruta | Descripción |
| --- | --- |
| `/` | Acceso / selección de perfil |
| `/catalogo/` | Catálogo de las siete soluciones |
| `/dashboard/` | Dashboard ejecutivo (filtros + CSV) |
| `/soluciones/referral/` | Referral Portal |
| `/soluciones/security/` | Security Database Hub |
| `/soluciones/uniform/` | Uniform Compliance Check |
| `/soluciones/hr/` | HR Colombia Ticketing |
| `/soluciones/automation/` | Automation Health Center |
| `/soluciones/support/` | Solutions Support |
| `/soluciones/appearance/` | Appearance Check |
| `/acerca/` | Límites de la demo y hoja de ruta a producción |

## Guion ejecutivo de cinco minutos

1. **Acceso y catálogo (30 s)** — entra como Manager, muestra las siete
   tarjetas con estado Live/Pilot/Demo, salud y última actividad.
2. **Referral Portal (90 s)** — crea un referido, ábrelo, cambia de etapa,
   navega a otra solución y vuelve: el cambio persiste. Abre la pestaña
   Analítica (conversión por etapa, distribución por país).
3. **Agent TA (45 s)** — pregunta "¿Cómo registro un referido?", luego una
   pregunta fuera de alcance para mostrar el límite, y un intento de
   "ignora tus instrucciones" para mostrar el guardado de alcance.
4. **Solutions Support (45 s)** — desde Referral Portal, clic en "Reportar
   un problema": el formulario llega precargado; muestra que el usuario
   revisa y envía.
5. **Dashboard ejecutivo (60 s)** — cambia el filtro de periodo/solución/país
   y muestra cómo KPIs, gráficas y el CSV exportado reflejan el mismo
   filtro.
6. **Restablecer demo (10 s)** — desde el menú de perfil, para dejar el
   estado limpio para la siguiente demo.

## Limitaciones

- Sin base de datos, autenticación o autorización reales.
- Sin integraciones externas (HiBob, Microsoft 365, Power Automate, correo).
  Automation Health Center las simula; ninguna llamada de red real ocurre.
- Agent TA es un motor de reglas local (coincidencia de intención sobre ~24
  FAQ); no es un LLM y no se conecta a ningún modelo.
- Appearance Check no analiza fotos, no identifica personas ni infiere
  características sensibles: el resultado (Aprobado/Requiere revisión) lo
  decide siempre explícitamente la persona revisora, nunca un cálculo.
- SLA, prioridades sugeridas y la regla de aprobación de Uniform Compliance
  Check son reglas de demostración, marcadas como tales en la interfaz —
  nunca políticas oficiales de ARRISE.
- El estado vive en `sessionStorage`: cerrar la pestaña, o abrir el portal
  en otra, no comparte cambios entre sí (cada pestaña es su propia demo).

### Evolución hacia producción (no implementada)

Persistencia real en PostgreSQL con migraciones; autenticación empresarial
(SSO / Microsoft 365) en lugar del selector de perfil; integraciones reales
con Microsoft 365, Power Automate, HiBob y otras APIs internas; y gobierno
de datos/observabilidad acorde a producción. Ver `/acerca/` dentro del
portal para el mismo resumen.

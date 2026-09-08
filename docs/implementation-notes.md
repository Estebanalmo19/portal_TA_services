# Notas de implementación

Decisiones y contratos que deben sobrevivir a la compactación de contexto y
a la entrega entre agentes. `CLAUDE.md` en la raíz apunta aquí.

## Arquitectura general

- Django 5.2.17 sobre Python 3.12 (instalado vía `py install 3.12` porque el
  sistema solo tenía Python 3.14, no soportado oficialmente por Django 5.2
  al momento de este desarrollo). Entorno virtual en `.venv/`.
- **Sin base de datos.** `DATABASES = {}` en `config/settings.py`.
  `INSTALLED_APPS` no incluye `contrib.admin`, `contrib.auth` ni
  `contrib.sessions` (evita tablas/migraciones). CSRF funciona solo con
  cookies (`CsrfViewMiddleware`), sin sesión de Django.
- Apps: `core` (home/catálogo/about/búsqueda/Agent TA/bootstrap),
  `dashboard` (KPIs ejecutivos), `solutions` (las siete soluciones, cada una
  con su propio `urls_<slug>.py` en la raíz del paquete `solutions/` +
  `solutions/views/<slug>.py` + `solutions/services/<slug>.py`).
  `mock_data/` no es una app Django: son módulos Python puros con los
  datasets y generadores.

## Contrato de estado (contrato central, no romper sin actualizar aquí)

1. `mock_data.<slug>.initial_state()` devuelve un dict JSON-serializable con
   los registros de muestra (mínimo 15) y catálogos pequeños (estados,
   categorías) que el frontend necesita. `mock_data.<slug>.catalog_summary()`
   devuelve `{"active_users", "last_activity" (ISO o None), "health"
   ("good"|"warning"|"critical"), "open_items"}` para la tarjeta del
   catálogo — ver `core/bootstrap.py` para el contrato completo y su manejo
   defensivo de módulos aún no implementados.
2. `core/context_processors.py::brand` arma **un único** snapshot
   (`core.bootstrap.build_snapshot()`, cacheado con `lru_cache`) con
   `version` (=`mock_data.STATE_VERSION`), `core` (notificaciones, Agent TA)
   y `solutions` (un `initial_state()` por slug). Cada página lo incrusta
   con `{{ initial_state|json_script:"arrise-initial-state" }}` en
   `templates/base.html`.
3. `static/js/state/bootstrap.js` decide en cada carga de página si usa el
   snapshot del servidor (primera visita en la pestaña, o estado corrupto/
   de otra versión) o el `sessionStorage` existente (`arrise_state_v<N>`),
   y expone `window.ArrisePortal.state/profile/saveState()/setProfile()/
   resetDemo()`. El perfil vive en una key de sessionStorage separada
   (`arrise_profile`) para que "Restablecer demo" pueda borrar el resto sin
   perder el perfil elegido.
4. Cada módulo JS de solución (ver `static/js/solutions/referral.js`) lee y
   escribe **directamente** `ArrisePortal.state.solutions.<slug>` y llama
   `ArrisePortal.saveState()` tras cada mutación. Toda la tabla/kanban/
   timeline se renderiza desde ese estado, nunca desde el HTML
   server-rendered (que solo sirve como snapshot inicial embebido).
5. Operaciones de escritura: POST JSON a `/soluciones/<slug>/api/<accion>/`.
   Las vistas usan `core.state.operation_endpoint` (parsea/limita el body,
   atrapa `solutions.services.common.ValidationError` y responde
   `{"ok": true, "result": {...}}` o `{"ok": false, "errors": {...}}`).
   Django **no busca el registro por ID en ningún almacén**: el payload
   trae lo que el servidor necesita para validar (p. ej. `current_status` y
   `target_status` para una transición; `existing_ids` para generar el
   siguiente ID sin colisión vía `solutions.services.common.next_id`).
   Ver `solutions/services/referral.py` y `solutions/views/referral.py`
   como implementación de referencia completa (create / transition / note).
6. `solutions/services/common.py` centraliza: `Validator` (acumula errores
   por campo), `TransitionGraph` (máquina de estados válida
   Python-autoritativa; el JS solo mirrorea el grafo para deshabilitar
   botones, nunca decide), `next_id`, `history_entry`, `sanitize_text`
   (escapa texto libre) y `csv_cell` (neutraliza inyección de fórmulas CSV).

## Patrones de frontend que hay que respetar

- **Nunca uses `innerHTML` con datos de usuario/servidor.** `static/js/ui/
  dom.js::h()` inserta hijos de texto vía `textContent`/`append`. El único
  uso de `innerHTML` es para iconos SVG propios estáticos (`{html: "..."}`),
  jamás para contenido dinámico.
- **`[hidden]` tiene `display:none !important`** en `static/css/base.css`
  porque varios componentes (modal, panel de Agent TA) fijan `display:flex`
  inline para su layout; sin el `!important`, ese inline style le gana al
  `[hidden]` del user-agent y el componente "oculto" se ve igual visible.
  Si agregas un componente con `display` inline y `hidden`, ya está cubierto.
- **Gráficas Chart.js dentro de un tab oculto se inicializan con tamaño
  cero** si el canvas se crea mientras su panel tiene `hidden`/`display:none`.
  Patrón: envolver el `<canvas>` en `<div class="chart-container">` (alto
  fijo, ver `static/css/components.css`), usar
  `{responsive:true, maintainAspectRatio:false}`, y (re)crear el chart
  también cuando `static/js/ui/tabs.js` dispara `arrise:tab-shown` en el
  panel (no solo una vez al cargar la página). Ver `renderAnalytics()` en
  `static/js/solutions/referral.js`.
- **Orden de scripts en `base.html`:** `state/bootstrap.js` corre en
  `DOMContentLoaded` y ya deja `window.ArrisePortal` listo *antes* de que
  se ejecute el `DOMContentLoaded` de cualquier script cargado después
  (los listeners de un mismo evento se ejecutan en orden de registro). Por
  eso los módulos de página (p. ej. `agent_ta.js`, `solutions/referral.js`)
  deben **renderizar directamente dentro de su propio `init()`**, no solo
  dentro de un listener de `arrise:state-ready` — ese evento ya se disparó
  para cuando un script cargado más abajo llega a registrarse.
- Formato de fecha/hora: `ArriseDom.formatDate` / `formatDateTime`
  (`Intl`/`toLocaleString` con locale `es-CO`).
- Toasts: `ArriseToast.success/info/danger(mensaje)`. Modal: `ArriseModal.
  open({title, body, footer})` / `.close()` (maneja foco inicial, trampa de
  foco y Escape vía `static/js/ui/focus-trap.js`).

## Botón "Reportar un problema" → Solutions Support

Todo enlace "Reportar un problema" (catálogo, cada solución, Agent TA) debe
apuntar a:

```
/soluciones/support/?sol=<slug-o-"ta">&asunto=<texto>&descripcion=<texto>&origen=<origen_libre>
```

`solutions/views/support.py` debe leer esos query params en su vista `home`
y precargar (no enviar automáticamente) el formulario de "Crear ticket" con
la solución y el resumen. El usuario siempre revisa y envía.

## Empleados / población elegible / adopción

`mock_data/people.py` genera 240 colaboradores ficticios
(`Colaborador Demo 0NN`, `@example.com`) distribuidos por área/país. La
"población elegible" de cada solución (denominador de adopción) es el
subconjunto por área declarado en `mock_data/reference.py::SOLUTIONS
[...]["eligible_areas"]`. `mock_data/timeseries.py::generate_monthly_series`
genera 12 meses de actividad (usuarios activos, ejecuciones, éxito/fallo,
horas ahorradas, satisfacción) por solución para el dashboard — cada
solución llama esa función una vez con un `MonthlyProfile` propio
(ver `mock_data/referral.py::monthly_series`).

## Entorno / comandos

```
py install 3.12                     # una sola vez, si falta 3.12
py -3.12 -m venv .venv
./.venv/Scripts/python.exe -m pip install -r requirements.txt
./.venv/Scripts/python.exe manage.py check
./.venv/Scripts/python.exe manage.py runserver
./.venv/Scripts/python.exe manage.py test
```

## Pendientes conocidos / limitaciones registradas

- El redimensionado de ventana del navegador vía la herramienta de
  automatización no cambió el viewport capturado en este entorno (siempre
  1568×777 en las capturas); el responsive se verificó revisando los
  breakpoints de `static/css/layout.css` (1024px, 640px) además de la
  inspección visual en desktop. Ver `docs/verification.md` para el detalle
  exacto de qué se probó con navegador real y qué quedó solo por revisión
  de código.

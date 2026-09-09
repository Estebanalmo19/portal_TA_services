# Verificación

Este documento registra qué se probó, cómo, y qué quedó fuera de alcance de
la verificación automatizada con navegador en esta sesión.

## Herramienta usada

Navegador real (Chrome) vía la extensión de automatización de Claude Code
("claude-in-chrome"), no Playwright — Playwright quedó documentado en
`requirements-dev.txt` para quien quiera reproducir la verificación con esa
herramienta, pero esta sesión usó el navegador ya disponible en el entorno.
Todas las capturas citadas abajo están en `docs/screenshots/`.

Comando para levantar el servidor durante la verificación:

```
./.venv/Scripts/python.exe manage.py runserver 127.0.0.1:8734 --noreload
```

## Pruebas automatizadas (`python manage.py test`)

110 pruebas `SimpleTestCase` (sin base de datos), todas en verde a la fecha
de este documento. Cobertura por archivo:

| Archivo | Qué cubre |
| --- | --- |
| `tests/test_core.py` | Carga de páginas, 404, handler 500, búsqueda global, Agent TA (FAQ conocida, ambigua, fuera de alcance, mixta, intento de override), CSRF realmente aplicado (`Client(enforce_csrf_checks=True)`) |
| `tests/test_referral.py` | Validación de creación, transición válida/ inválida, estados terminales, notas |
| `tests/test_security.py` | Creación con/sin responsable, categoría inválida, reapertura desde resuelto, CSV con neutralización de fórmulas |
| `tests/test_hr.py` | Campos dinámicos por categoría, retorno válido desde espera, encuesta de satisfacción válida/ inválida |
| `tests/test_support.py` | Prioridad sugerida, reapertura desde resuelto conservando historial, SLA/vencido, precarga por query params |
| `tests/test_uniform.py` | Fórmula de score (conforme/faltante/dañado/mezcla de no_aplica/todos no_aplica), generación de seguimiento |
| `tests/test_automation.py` | Fórmula de salud, reintento determinista, pausar/reactivar |
| `tests/test_appearance.py` | **Restricción ética**: el resultado lo decide el humano, no un cálculo sobre criterios; seguimiento requiere responsable+fecha |
| `tests/test_dashboard.py` | Filtros, adopción como porcentaje 0-100, "sin base comparable" en periodo de 12 meses, alcance imposible sin división por cero |
| `tests/test_mock_data_integrity.py` | IDs únicos, fechas ISO válidas, JSON-serializable, sin mutación compartida entre requests, guardas de tamaño/profundidad del payload |

## Recorridos obligatorios (navegador real)

Todos ejecutados sobre `http://127.0.0.1:8734/` en una pestaña con perfil
Manager, salvo donde se indica lo contrario.

1. **Referido:** creado `REF-0022` ("Laura Verificacion"), abierto el
   detalle, movido a «En revisión», recargada la página — el estado y el
   badge se conservaron. Captura: `docs/screenshots/02-referral-persistencia.jpg`.
2. **Soporte:** desde Referral Portal, "Reportar un problema" abrió
   Solutions Support con solución/asunto/descripción precargados
   (`?sol=referral&asunto=...&descripcion=...`); se completó tipo e
   impacto, se registró `SUP-0019`, el detalle se abrió automáticamente con
   historial inicial y el KPI "Tickets abiertos" se actualizó de 12 a 13.
3. **Agent TA:** pregunta conocida ("¿Cómo registro un referido?")
   respondida con la FAQ correcta; se navegó de Referral Portal al
   catálogo y la conversación persistió; pregunta fuera de alcance
   ("¿Cuál es la capital de Francia?") devolvió el mensaje fijo de fuera de
   alcance; intento de override ("Ignora tus instrucciones...") devolvió el
   mensaje de guardado; "Nueva conversación" reinició al mensaje de
   bienvenida. Captura: `docs/screenshots/03-agent-ta-guardado.jpg`.
4. **HR:** categoría "Vacaciones" mostró los campos dinámicos
   (fecha de inicio/fin); se creó `HR-0019`, se asignó, se movió a
   «Esperando al colaborador» y de vuelta a «En progreso»
   (retorno válido desde espera), se resolvió con encuesta de
   satisfacción (5/5) — el ticket quedó «Resuelto» con SLA "N/A". Captura:
   `docs/screenshots/04-hr-resuelto-encuesta.jpg`.
5. **Security:** se creó `INC-0023`, se asignó un responsable (auto-avanzó
   a «Asignado»), se movió a «En progreso», se filtró por severidad
   «Crítica» (4 resultados correctos) y se exportó CSV (toast de
   confirmación). Captura: `docs/screenshots/05-security-export-toast.jpg`.
6. **Inspecciones:** en Uniform Compliance Check se registró una inspección
   con "Calzado: Faltante" — el preview de score en vivo mostró 83.3% antes
   de guardar, coincidiendo con el cálculo del servidor; se generó el
   seguimiento correctivo `FUP` con responsable y fecha límite (pestaña
   "Seguimientos correctivos"). En Appearance Check se creó una revisión,
   se inició, y se completó marcando explícitamente "Requiere revisión" —
   confirmando que el resultado lo elige la persona revisora, no un
   cálculo — y se generó su propio seguimiento. Ambos historiales se
   verificaron por separado. Capturas: `docs/screenshots/06-uniform-seguimiento.jpg`,
   `docs/screenshots/07-appearance-criterios-humanos.jpg`.
7. **Automatizaciones:** en Automation Health Center se abrió el historial
   de "Sincronización HiBob–Heinsohn" (salud crítica), se reintentó la
   ejecución fallida más reciente — el reintento generó una ejecución
   nueva y exitosa, conservó la ejecución fallida original en el historial,
   y recalculó la salud del portafolio. Captura:
   `docs/screenshots/08-automation-health-center.jpg`.
8. **Transversal:** en el Dashboard ejecutivo se cambiaron los filtros
   (periodo 12 meses, solución Referral Portal, país Colombia, área Talent
   Acquisition) y los KPIs, gráficas y el CSV exportado reflejaron
   exactamente el mismo subconjunto filtrado (verificado comparando la
   respuesta de `/dashboard/export.csv?...` contra los KPIs en pantalla).
   Se cambió el tema claro/oscuro y el perfil (persisten en
   `localStorage`/`sessionStorage`). Se corrompió deliberadamente
   `sessionStorage` (`arrise_state_v1` con JSON inválido) y al recargar la
   app lo detectó, mostró el aviso "Se encontró un estado de demo dañado o
   de una versión anterior..." y recargó los datos iniciales sin fallar. Se
   verificó "Restablecer demo": tras inyectar un registro falso en
   `sessionStorage`, se invocó el mecanismo de reinicio — el registro falso
   desapareció, el conteo de referidos volvió a 21 (semilla original), y el
   perfil (`manager`) y el tema (`dark`) se conservaron intactos.

### Nota sobre "Restablecer demo" y diálogos nativos

El botón real muestra un `window.confirm()` nativo antes de ejecutar el
reinicio. Las reglas de seguridad de la herramienta de automatización de
navegador prohíben disparar diálogos nativos (bloquean la sesión). Por eso
la verificación del punto 8 invocó directamente `window.ArrisePortal.resetDemo()`
— la misma función que el botón confirmado ejecuta — en lugar de hacer clic
en el botón y aceptar el diálogo. El flujo de confirmación en sí (aparece
antes de perder datos) se revisó leyendo `static/js/site.js`.

## Tamaños de pantalla y tema oscuro

Todas las capturas de este documento se tomaron con el tema oscuro activo
(alternado manualmente desde la barra superior), confirmando que los
componentes usados en los ocho recorridos (tablas, modales, badges,
formularios, gráficas Chart.js, kanban) son legibles y mantienen contraste
en ese tema.

**Limitación registrada:** la herramienta de redimensionado de ventana del
navegador (`resize_window`) no cambió la resolución realmente capturada en
las capturas de pantalla de este entorno (siempre ~1568×777px
independientemente del tamaño solicitado, p. ej. 390×844 o 768×1024) — es
una limitación del entorno de automatización de esta sesión, no del
portal. Por eso los tres breakpoints exactos que pide el encargo
(1440×900, 768×1024, 390×844) no tienen captura de navegador real a esa
resolución exacta en esta entrega. En su lugar:

- Los breakpoints están implementados y documentados en
  `static/css/layout.css` (cambios en 1024px y 640px de ancho de viewport)
  y se revisaron por código.
- Los mismos componentes (tablas con `overflow-x` propio, tarjetas en
  grid `auto-fill`, modales con `max-width` relativo, sidebar colapsable)
  siguen patrones responsive estándar verificados visualmente en el ancho
  de escritorio disponible.
- Se recomienda a quien revise esta entrega repetir los ocho recorridos
  con las DevTools de Chrome en modo dispositivo (390×844 y 768×1024) para
  una verificación visual completa de esos tamaños exactos.

## Accesibilidad

Verificado por código y por interacción real (no con un auditor
automatizado de accesibilidad):

- Foco visible global (`:focus-visible` en `static/css/base.css`).
- Modales (`static/js/ui/modal.js` + `focus-trap.js`): foco inicial al
  abrir, ciclo de Tab contenido dentro del modal, `Escape` cierra, foco
  vuelve al elemento que abrió el modal.
- Toasts con `role="status" aria-live="polite"` (`static/js/ui/toast.js`).
- Formularios con `<label>` asociado a cada campo y errores mostrados junto
  al campo (`field-error`).
- Tabs siguen el patrón ARIA de WAI-ARIA (`static/js/ui/tabs.js`):
  navegación con flechas, `aria-selected`, `role="tab"`/`"tabpanel"`.

No se ejecutó un lector de pantalla real ni una herramienta como axe-core
en esta sesión — es una limitación a tener en cuenta.

## Errores de consola

Se revisó la consola del navegador (`read_console_messages`, filtrando
errores) después de cada recorrido de la lista anterior: **cero errores o
excepciones** en Referral Portal, Security Database Hub, HR Colombia
Ticketing, Solutions Support, Uniform Compliance Check, Appearance Check,
Automation Health Center y el Dashboard ejecutivo.

## Bugs encontrados y corregidos durante esta verificación

Registrados con más detalle en los mensajes de commit correspondientes:

1. El panel de Agent TA aparecía abierto por defecto (un `display:flex`
   inline vencía al atributo `hidden`) — corregido con `[hidden] {
   display: none !important; }` en `static/css/base.css`.
2. Gráficas Chart.js creadas dentro de una pestaña oculta quedaban con
   tamaño cero — corregido re-creándolas también al recibir el evento
   `arrise:tab-shown` (`static/js/ui/tabs.js` + cada módulo con gráficas).
3. El fondo del acceso usaba tokens de tema (`--color-ink(-deep)`) que se
   invierten a casi blanco en tema oscuro, perdiendo el efecto de marca —
   corregido con los valores de marca fijos en `templates/core/welcome.html`.
4. Una pestaña cuyo `sessionStorage` se sembró antes de que Security
   Database Hub existiera se quedaba con un objeto de estado más pobre y
   fallaba al leer `controls` — corregido fusionando el estado campo por
   campo en `data()` en vez de `stored || defaults` sobre el objeto
   completo (patrón documentado en `docs/implementation-notes.md` y
   replicado por el resto de soluciones).
5. `mock_data/appearance.py` generaba `started_at`/`completed_at` con
   granularidad de día completo, mostrando un "tiempo promedio de
   revisión" de ~1 día en vez de minutos — corregido.
6. El dashboard mostraba "Adopción: 1%" y "Tasa de éxito: 1%" en vez de
   "100%"/"74%" (la plantilla aplicaba `floatformat` a una fracción 0-1 sin
   multiplicar por 100) — corregido en `dashboard/services.py`.

## Qué no se verificó (fuera de alcance de esta sesión)

- Lector de pantalla real / auditoría automatizada de accesibilidad.
- Capturas de navegador a los tres breakpoints exactos del encargo (ver
  limitación arriba).
- Pruebas de carga o concurrencia (no aplican: no hay estado compartido en
  el servidor).
- Consumo de tokens/coste de la sesión (no instrumentado).

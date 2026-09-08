# CLAUDE.md — ARRISE Solutions Portal (rama `feature/solutions-portal-claude`)

Contexto completo del encargo: `docs/implementation-notes.md` (arquitectura,
contrato de estado, patrones de frontend) y `docs/comparison.md` (rama de
comparación, evidencia). No dupliques esos documentos aquí — este archivo es
solo el resumen operativo.

## Comandos

```
py -3.12 -m venv .venv                        # Python 3.12+ requerido; Django 5.2 no soporta 3.14
./.venv/Scripts/python.exe -m pip install -r requirements.txt
./.venv/Scripts/python.exe -m pip install -r requirements-dev.txt   # + Playwright, solo para verificación
./.venv/Scripts/python.exe manage.py check
./.venv/Scripts/python.exe manage.py runserver
./.venv/Scripts/python.exe manage.py test
```

En Windows, si la política de ejecución de PowerShell bloquea `.venv\Scripts\Activate.ps1`,
usa siempre la ruta directa al intérprete (`./.venv/Scripts/python.exe manage.py ...`)
en lugar de activar el entorno.

## Restricciones duras de este proyecto

- **Sin base de datos.** `DATABASES = {}`. Nunca agregues `migrate`,
  `contrib.admin`, `contrib.auth` ni `contrib.sessions` a `INSTALLED_APPS`.
- **Sin React/Vue/Next/Node como requisito de build, sin Tailwind con build,
  sin Redis/Celery/microservicios, sin LLMs ni auth real.** Django Templates
  + CSS + JS vanilla + Chart.js local (`static/vendor/chartjs/`).
- **Sin CDN en runtime.** Todo asset externo (fuentes, Chart.js) debe estar
  vendorizado en `static/`.
- El estado de negocio vive en `sessionStorage` del navegador, nunca en el
  servidor entre requests. Ver el contrato completo en
  `docs/implementation-notes.md`.

## Tokens de marca

`static/css/tokens.css` es la única fuente de verdad de colores/tema
claro-oscuro. No los redefinas en otro archivo.

## Convenciones de código

- Un módulo `mock_data.<slug>` por solución con `initial_state()` y
  `catalog_summary()` (contrato exacto en `docs/implementation-notes.md`).
- Un `solutions/services/<slug>.py` con la lógica de dominio (usa
  `solutions/services/common.py`: `Validator`, `TransitionGraph`, `next_id`,
  `history_entry`, `sanitize_text`, `csv_cell`).
- Un `solutions/views/<slug>.py` + `solutions/urls_<slug>.py` propio
  (namespace = slug). Referencia completa funcionando: `referral`.
- JS de cada solución en `static/js/solutions/<slug>.js`, renderiza siempre
  desde `ArrisePortal.state.solutions.<slug>`, nunca desde HTML server-side.
- Nunca `innerHTML` con datos dinámicos (usa `ArriseDom.h()`/`textContent`).

## Estado de la implementación (actualizar al avanzar)

Ver `docs/implementation-notes.md` § "Pendientes conocidos" y
`docs/comparison.md` para el estado módulo por módulo en el momento de la
entrega.

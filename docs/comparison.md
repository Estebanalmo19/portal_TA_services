# Comparación — rama `feature/solutions-portal-claude`

Este documento registra la evidencia observable de esta implementación para
la comparación descrita en el `README.md` de `main`. No otorga una
puntuación ni declara ganador: eso corresponde a la evaluación humana.

## Metadatos de la ejecución

| Campo | Valor |
| --- | --- |
| SHA base común | `0b61dbbb7cf02e5dc53073dd42aa4759e8387e07` (etiqueta `comparison/solutions-portal-base-v1`) |
| Rama | `feature/solutions-portal-claude` |
| Asistente | Claude Code |
| Versión de Claude Code | 2.1.265 |
| Modelo | Claude Sonnet 5 (`claude-sonnet-5`) — observado vía system prompt de la sesión |
| Configuración de la sesión | Modo por defecto (sin flags de permisos ampliados); ejecutada en Windows 11, PowerShell/Git Bash |
| Plugins/skills utilizados | Ninguno de los sugeridos (`frontend-design`, `feature-dev`, `webapp-testing`) estaba instalado/habilitado en esta sesión — no se usaron y no se declara su uso. Se usaron subagentes genéricos (`general-purpose`) del propio Claude Code para paralelizar la construcción de 6 de las 7 soluciones tras completar una implementación de referencia (Referral Portal) manualmente. |
| Dependencias runtime | `Django==5.2.17` (único paquete de `requirements.txt`) |
| Dependencias de verificación | `playwright==1.62.0` en `requirements-dev.txt` (no requerido para abrir el portal) |
| Python | 3.12.10 (instalado en esta sesión vía `py install 3.12`; el sistema solo tenía 3.14, sin soporte oficial confirmado para Django 5.2 al momento de esta entrega) |
| Fecha de referencia de los mocks | `DEMO_REFERENCE_DATE` = fecha real de la sesión (`config/settings.py`, por defecto `os.environ` con fallback a la fecha de hoy en el momento de escribir este documento) |
| Duración observada | No cronometrada con precisión de reloj de pared por una herramienta dedicada; la sesión abarcó múltiples horas reales de trabajo continuo (incluida investigación, siete módulos, dashboard, pruebas y esta documentación). Ver el historial de commits de esta rama para las marcas de tiempo por entrega. |
| Pruebas automatizadas | 110 pruebas Django (`SimpleTestCase`, sin base de datos) — `python manage.py test`. Todas en verde a la fecha de este documento. |
| Consumo de tokens / coste | No disponible (no instrumentado en esta sesión). |

## Aislamiento de la comparación

Esta implementación se desarrolló exclusivamente en `feature/solutions-portal-claude`,
partiendo de la etiqueta `comparison/solutions-portal-base-v1`. No se leyó,
consultó ni incorporó ningún commit, rama o archivo de la implementación de
la otra IA.

## Matriz de evaluación

| Criterio | Peso | Evidencia esperada | Evidencia en esta rama |
| --- | ---: | --- | --- |
| Recorridos funcionales completos | 30 % | Ocho recorridos y siete módulos + chat | Los ocho recorridos de `docs/verification.md` §"Recorridos obligatorios" se ejecutaron con navegador real (Chrome vía automatización) y quedaron documentados con capturas en `docs/screenshots/`. Los siete módulos + Agent TA tienen creación, transición de estado, comentarios/notas y detalle funcionales; ver `tests/` para la cobertura automatizada de las reglas de negocio de cada uno. |
| Diseño y cumplimiento de marca | 25 % | Capturas, consistencia y tareas claras | Tokens de marca centralizados en `static/css/tokens.css` (tema claro fiel a los valores del encargo + tema oscuro propio documentado como adaptación). Capturas en `docs/screenshots/` cubren catálogo, un módulo de ticket, Uniform Compliance Check, el dashboard y tema oscuro. |
| Backend y consistencia de datos | 20 % | Validación, servicios, métricas y estados | Contrato de estado documentado en `docs/implementation-notes.md`; validación server-side con `solutions/services/common.py` (`Validator`, `TransitionGraph`) en las siete soluciones; KPIs del dashboard derivados en tiempo real de `mock_data` (sin cifras fijas en plantillas) — ver `dashboard/services.py`. |
| Responsive y accesibilidad | 15 % | Móvil/tablet/oscuro/teclado/contraste | Breakpoints en `static/css/layout.css` (1024px, 640px); tema oscuro verificado con navegador real en varias pantallas (ver capturas). **Limitación registrada:** el redimensionado de ventana vía la herramienta de automatización de navegador no cambió el viewport capturado en este entorno (ver `docs/implementation-notes.md` "Pendientes conocidos"), así que los tamaños móvil/tablet exactos (390×844, 768×1024) no se verificaron con captura real de navegador en esta sesión — se revisaron por CSS y por el comportamiento de los mismos componentes en el ancho de escritorio disponible. Foco visible global (`:focus-visible` en `base.css`), trampa de foco y Escape en modales (`static/js/ui/focus-trap.js`, `modal.js`). |
| Reproducibilidad y documentación | 10 % | Instalación, tests, base Git y límites | `README.md` con instalación Windows/macOS/Linux sin `migrate`; 110 pruebas automatizadas; límites explícitos en `README.md` §Limitaciones y en `/acerca/` dentro del portal. |

## Limitaciones conocidas de esta entrega

- Verificación de tamaños de viewport móvil/tablet exactos no confirmada con
  captura real de navegador (ver tabla arriba).
- Consumo de tokens/coste no instrumentado.
- Duración de la sesión no cronometrada con una herramienta dedicada.
- Ningún plugin/skill oficial sugerido por el encargo (`frontend-design`,
  `feature-dev`, `webapp-testing`) estaba disponible en esta sesión; se usó
  el criterio de diseño e ingeniería propio de Claude Code en su lugar, y
  subagentes genéricos para paralelizar (no equivalen a esos plugins).

Para comparar con rigor, ambas implementaciones deberían evaluarse con la
misma base, alcance, escenarios y condiciones de revisión; cualquier
diferencia de herramientas, plugins disponibles o dataset generado debe
documentarse también en la rama de la otra IA.

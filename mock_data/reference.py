"""Static reference data: areas, countries, roles and the solutions catalog.

These are the controlled vocabularies every other dataset filters/groups by.
Keep slugs stable — they are used as dictionary keys across mock_data,
services and the frontend filters.
"""

AREAS = [
    {"slug": "ta", "name": "Talent Acquisition"},
    {"slug": "hr", "name": "HR"},
    {"slug": "security", "name": "Security"},
    {"slug": "data-analytics", "name": "Data & Analytics"},
    {"slug": "operations", "name": "Operations"},
]
AREA_SLUGS = [a["slug"] for a in AREAS]
AREA_NAME_BY_SLUG = {a["slug"]: a["name"] for a in AREAS}

# "global" is an aggregate filter option, not a real country of a person.
COUNTRIES = [
    {"slug": "co", "name": "Colombia"},
    {"slug": "bg", "name": "Bulgaria"},
    {"slug": "rs", "name": "Serbia"},
    {"slug": "ge", "name": "Georgia"},
]
COUNTRY_SLUGS = [c["slug"] for c in COUNTRIES]
COUNTRY_NAME_BY_SLUG = {c["slug"]: c["name"] for c in COUNTRIES}
GLOBAL_SLUG = "global"
GLOBAL_LABEL = "Global"

PROFILES = [
    {
        "slug": "manager",
        "name": "Manager",
        "description": "Recorrido completo, incluido el dashboard ejecutivo.",
    },
    {
        "slug": "solution_owner",
        "name": "Solution Owner",
        "description": "Gestiona sus soluciones asignadas: asignación, estados y analítica del módulo.",
    },
    {
        "slug": "analyst",
        "name": "Analyst",
        "description": "Uso operativo del día a día: crear, consultar y dar seguimiento a registros.",
    },
]
PROFILE_SLUGS = [p["slug"] for p in PROFILES]

# Solutions catalog. `route` matches the `solutions:<route>` URL namespace,
# `eligible_areas` documents which areas count toward the eligible
# population used for the adoption KPI (see mock_data.people).
SOLUTIONS = [
    {
        "slug": "referral",
        "name": "Referral Portal",
        "route": "referral:home",
        "description": "Programa de referidos para vacantes abiertas, con seguimiento por etapas.",
        "owner_area": "ta",
        "status": "Live",
        "benefit": "Acelera el pipeline de candidatos referidos y su trazabilidad.",
        "eligible_areas": ["ta", "hr", "security", "data-analytics", "operations"],
    },
    {
        "slug": "security",
        "name": "Security Database Hub",
        "route": "security:home",
        "description": "Inventario y seguimiento operativo de accesos, incidentes y controles físicos/lógicos.",
        "owner_area": "security",
        "status": "Live",
        "benefit": "Centraliza riesgos de seguridad y su resolución.",
        "eligible_areas": ["security"],
    },
    {
        "slug": "uniform",
        "name": "Uniform Compliance Check",
        "route": "uniform:home",
        "description": "Checklist de cumplimiento de uniforme por colaborador y turno.",
        "owner_area": "operations",
        "status": "Pilot",
        "benefit": "Detecta y da seguimiento a incumplimientos de uniforme.",
        "eligible_areas": ["operations"],
    },
    {
        "slug": "hr",
        "name": "HR Colombia Ticketing",
        "route": "hr:home",
        "description": "Mesa de ayuda de HR Colombia para solicitudes de colaboradores.",
        "owner_area": "hr",
        "status": "Live",
        "benefit": "Ordena y agiliza la resolución de solicitudes de HR.",
        "eligible_areas": ["ta", "hr", "security", "data-analytics", "operations"],
    },
    {
        "slug": "automation",
        "name": "Automation Health Center",
        "route": "automation:home",
        "description": "Salud y ejecución de las automatizaciones internas del negocio.",
        "owner_area": "data-analytics",
        "status": "Live",
        "benefit": "Visibilidad de fallos y tiempo ahorrado por automatización.",
        "eligible_areas": ["ta", "data-analytics", "operations"],
    },
    {
        "slug": "support",
        "name": "Solutions Support",
        "route": "support:home",
        "description": "Mesa de soporte para incidencias de las siete soluciones y Agent TA.",
        "owner_area": "hr",
        "status": "Live",
        "benefit": "Punto único para reportar y resolver problemas de las herramientas.",
        "eligible_areas": ["ta", "hr", "security", "data-analytics", "operations"],
    },
    {
        "slug": "appearance",
        "name": "Appearance Check",
        "route": "appearance:home",
        "description": "Revisión manual de preparación de presentación antes de entrar a operación.",
        "owner_area": "operations",
        "status": "Demo",
        "benefit": "Estandariza la revisión de preparación antes de operar en vivo.",
        "eligible_areas": ["operations"],
    },
]
SOLUTION_SLUGS = [s["slug"] for s in SOLUTIONS]
SOLUTION_BY_SLUG = {s["slug"]: s for s in SOLUTIONS}

# Fictional operating sites, used by Security, Uniform and Appearance Check.
SITES = [
    {"slug": "bog-hq", "name": "Bogota HQ", "country": "co"},
    {"slug": "bog-ops2", "name": "Bogota Ops 2", "country": "co"},
    {"slug": "sofia-hub", "name": "Sofia Hub", "country": "bg"},
    {"slug": "belgrade-ops", "name": "Belgrade Ops", "country": "rs"},
    {"slug": "tbilisi-ops", "name": "Tbilisi Ops", "country": "ge"},
]
SITE_BY_SLUG = {s["slug"]: s for s in SITES}

CURRENCY = "USD"
DEMO_HOURLY_RATE = 12.0  # ficticia, documentada — ver docs/implementation-notes.md

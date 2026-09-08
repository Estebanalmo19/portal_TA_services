"""Security Database Hub mock dataset.

Ficticious operational security data: access/physical/logical incidents
(doors, cameras, credentials, EDR, assets, visitors, magnetic locks,
lockers, elevators) plus a small "floor controls" registry used to surface
overdue reviews and critical alerts on the summary tab. See
``docs/implementation-notes.md`` for the shared state-contract writeup and
this module's docstrings below for the design decisions specific to this
solution (status graph, "floor controls" model, health heuristic).
"""

from datetime import timedelta
from functools import lru_cache

from .clock import days_ago, iso, new_rng, reference_datetime
from .people import eligible_population
from .reference import SITES
from .timeseries import MonthlyProfile, generate_monthly_series

SITE_SLUGS = [s["slug"] for s in SITES]

# ---------------------------------------------------------------------------
# Incident status graph.
#
# Design decision (documented per the task brief, which left the exact slugs
# open): a linear happy path `new -> assigned -> in_progress -> resolved ->
# closed`, plus a "reopen" edge from `resolved` *and* `closed` back to
# `in_progress` — a closed/resolved physical-security incident (e.g. a
# credential thought recovered, a magnetic lock re-failing) can legitimately
# resurface, and the alternative (forcing a brand-new incident every time)
# would lose the original history/context. Neither `resolved` nor `closed`
# is therefore a true dead-end node in the graph, so `TransitionGraph`'s
# `terminal` set is intentionally left empty here (unlike Referral Portal,
# where `hired`/`rejected` really have no outgoing edges); `TERMINAL_STATUSES`
# below is a separate, KPI-only concept ("not actively worked right now").
# ---------------------------------------------------------------------------
STATUS_LABELS = {
    "new": "Nuevo",
    "assigned": "Asignado",
    "in_progress": "En progreso",
    "resolved": "Resuelto",
    "closed": "Cerrado",
}
STATUS_SLUGS = list(STATUS_LABELS.keys())
TERMINAL_STATUSES = {"resolved", "closed"}

TRANSITIONS = {
    "new": {"assigned"},
    "assigned": {"in_progress"},
    "in_progress": {"resolved"},
    "resolved": {"closed", "in_progress"},
    "closed": {"in_progress"},
}

CATEGORY_LABELS = {
    "acceso": "Acceso",
    "camara": "Cámara",
    "credencial": "Credencial",
    "edr": "EDR",
    "activo": "Activo",
    "visitante": "Visitante",
    "electroiman": "Electroimán",
    "locker": "Locker",
    "ascensor": "Ascensor",
}
CATEGORY_SLUGS = list(CATEGORY_LABELS.keys())

SEVERITY_LABELS = {
    "baja": "Baja",
    "media": "Media",
    "alta": "Alta",
    "critica": "Crítica",
}
SEVERITY_SLUGS = list(SEVERITY_LABELS.keys())

FLOORS = ["Piso 1", "Piso 2", "Piso 3", "Piso 4", "Piso 5", "Recepción", "Sótano", "Terraza"]

# ---------------------------------------------------------------------------
# "Floor controls" (registros/controles por piso).
#
# Design decision: rather than trying to model every physical/logical asset
# family (doors, cameras, magnetic locks, lockers, elevators, EDR endpoints)
# as its own table, they share one small, generic "control" record shape
# (id, site, floor, control_type, label, status vigente/vencido,
# next_review, optional linked_incident_id). This is deliberately the
# smallest model that still gives the required searchable/filterable
# "registros vencidos" and "alertas críticas" summary without building out
# a full asset-management data model that this MVP does not need.
# ---------------------------------------------------------------------------
CONTROL_TYPE_LABELS = {
    "puerta": "Puerta",
    "camara": "Cámara",
    "electroiman": "Electroimán",
    "locker": "Locker",
    "ascensor": "Ascensor",
    "lector_acceso": "Lector de acceso",
    "edr_endpoint": "Endpoint EDR",
}
CONTROL_TYPE_SLUGS = list(CONTROL_TYPE_LABELS.keys())
CONTROL_TYPE_TO_CATEGORY = {
    "puerta": "acceso",
    "camara": "camara",
    "electroiman": "electroiman",
    "locker": "locker",
    "ascensor": "ascensor",
    "lector_acceso": "acceso",
    "edr_endpoint": "edr",
}

CONTROL_STATUS_LABELS = {"vigente": "Vigente", "vencido": "Vencido"}
CONTROL_STATUS_SLUGS = list(CONTROL_STATUS_LABELS.keys())

TITLE_BANK = {
    "acceso": [
        ("Puerta de emergencia sin cerrar", "El sensor reporta la puerta de emergencia del ala señalada abierta fuera de horario."),
        ("Acceso denegado repetido", "Un colaborador reporta rechazo reiterado de su tarjeta en el torniquete principal."),
        ("Tailgating detectado", "La cámara de acceso registra a dos personas ingresando con una sola credencial."),
    ],
    "camara": [
        ("Cámara fuera de línea", "La cámara reporta pérdida de señal desde la última sincronización."),
        ("Ángulo de cámara desviado", "Una cámara fue movida de su posición original y ya no cubre el punto ciego asignado."),
    ],
    "credencial": [
        ("Credencial reportada como perdida", "Un colaborador reportó la pérdida de su credencial de acceso."),
        ("Credencial de exempleado activa", "Se detectó una credencial activa asociada a un colaborador que ya no pertenece a la compañía."),
    ],
    "edr": [
        ("Alerta EDR en estación de seguridad", "El agente EDR reporta actividad sospechosa en un endpoint de la sala de monitoreo."),
        ("Agente EDR desactualizado", "Un endpoint crítico no ha actualizado firmas de EDR en más de 30 días."),
    ],
    "activo": [
        ("Activo sin etiqueta de inventario", "Se encontró un equipo de cómputo sin etiqueta de inventario en el piso."),
        ("Activo reportado como faltante", "El inventario trimestral no logra ubicar un equipo asignado al área de operaciones."),
    ],
    "visitante": [
        ("Visitante sin acompañamiento", "Un visitante fue visto circulando sin su anfitrión asignado."),
        ("Registro de visitante incompleto", "El formulario de ingreso de un visitante no tiene registrada la hora de salida."),
    ],
    "electroiman": [
        ("Electroimán no libera con botón de pánico", "El electroimán de la puerta de emergencia no respondió durante la prueba mensual."),
        ("Electroimán con batería baja", "El respaldo de batería del electroimán reporta menos del 20%."),
    ],
    "locker": [
        ("Locker con cerradura forzada", "Se encontró evidencia de forzamiento en un locker del área de operaciones."),
        ("Locker sin asignación vigente", "Un locker sigue asignado a un colaborador que cambió de sede."),
    ],
    "ascensor": [
        ("Ascensor con parada irregular", "El ascensor de servicio presenta paradas fuera de nivel."),
        ("Mantenimiento de ascensor vencido", "El certificado de mantenimiento del ascensor principal está vencido."),
    ],
}

ACTOR_POOL = ["Analista de Seguridad Demo", "Coordinador de Seguridad Demo", "Sistema de monitoreo"]


def _future_iso(days_from_reference: int) -> str:
    return iso(reference_datetime() + timedelta(days=days_from_reference))


def _step_entry(prev_step, step, actor):
    if step == "assigned":
        detail = f"Incidente asignado a {actor}."
        event_type = "assigned"
    elif prev_step in ("resolved", "closed") and step == "in_progress":
        detail = f"Incidente reabierto desde «{STATUS_LABELS[prev_step]}»: vuelve a «En progreso»."
        event_type = "reopened"
    else:
        detail = f"Cambio de estado a «{STATUS_LABELS[step]}»."
        event_type = "status_change"
    return event_type, detail


@lru_cache(maxsize=1)
def showcase_records() -> list[dict]:
    rng = new_rng("security.showcase")
    staff = eligible_population("security")
    status_cycle = (
        ["new"] * 4
        + ["assigned"] * 4
        + ["in_progress"] * 5
        + ["resolved"] * 5
        + ["closed"] * 4
    )
    rng.shuffle(status_cycle)

    records = []
    for i, status in enumerate(status_cycle, start=1):
        record_id = f"INC-{i:04d}"
        category = rng.choice(CATEGORY_SLUGS)
        title, description = rng.choice(TITLE_BANK[category])
        site = rng.choice(SITE_SLUGS)
        floor = rng.choice(FLOORS)
        severity = rng.choices(SEVERITY_SLUGS, weights=[0.25, 0.35, 0.28, 0.12])[0]
        age_days = rng.randint(1, 120)
        created_at = days_ago(age_days)

        assignee = None
        if status != "new":
            assignee = rng.choice(staff)

        # Reopen flavor: ~40% of records that end up "in_progress" got there
        # via a resolved -> in_progress reopen, not a first-time path.
        if status == "in_progress" and rng.random() < 0.4:
            path = ["new", "assigned", "in_progress", "resolved", "in_progress"]
        else:
            path = ["new"]
            if status != "new":
                path.append("assigned")
            if status in ("in_progress", "resolved", "closed"):
                path.append("in_progress")
            if status in ("resolved", "closed"):
                path.append("resolved")
            if status == "closed":
                path.append("closed")

        history = [
            {
                "type": "created",
                "detail": "Incidente registrado.",
                "actor": "Sistema de monitoreo",
                "at": iso(created_at),
            }
        ]
        step_gap = max(age_days // max(len(path), 1), 1)
        for idx, step in enumerate(path[1:], start=1):
            prev_step = path[idx - 1]
            actor_name = assignee["name"] if assignee else rng.choice(ACTOR_POOL)
            event_type, detail = _step_entry(prev_step, step, actor_name)
            at_days_ago = max(age_days - idx * step_gap, 0)
            history.append(
                {
                    "type": event_type,
                    "detail": detail,
                    "actor": actor_name,
                    "at": iso(days_ago(at_days_ago)),
                }
            )

        last_sync = iso(reference_datetime() - timedelta(minutes=rng.randint(2, 720)))

        records.append(
            {
                "id": record_id,
                "title": title,
                "description": description,
                "site": site,
                "floor": floor,
                "category": category,
                "severity": severity,
                "status": status,
                "assignee_id": assignee["id"] if assignee else None,
                "assignee_name": assignee["name"] if assignee else None,
                "created_at": iso(created_at),
                "last_sync": last_sync,
                "history": history,
            }
        )
    return records


@lru_cache(maxsize=1)
def showcase_controls() -> list[dict]:
    rng = new_rng("security.controls")
    incidents = showcase_records()
    incidents_by_category = {}
    for record in incidents:
        if record["status"] in TERMINAL_STATUSES:
            continue
        incidents_by_category.setdefault(record["category"], []).append(record["id"])

    controls = []
    for i in range(1, 17):
        control_id = f"CTL-{i:04d}"
        control_type = rng.choice(CONTROL_TYPE_SLUGS)
        site = rng.choice(SITE_SLUGS)
        floor = rng.choice(FLOORS)
        label = f"{CONTROL_TYPE_LABELS[control_type]} {i:02d} · {floor}"
        status = rng.choices(CONTROL_STATUS_SLUGS, weights=[0.65, 0.35])[0]
        if status == "vencido":
            next_review = _future_iso(-rng.randint(5, 60))
        else:
            next_review = _future_iso(rng.randint(10, 180))

        related_category = CONTROL_TYPE_TO_CATEGORY[control_type]
        candidates = incidents_by_category.get(related_category) or []
        linked_incident_id = rng.choice(candidates) if candidates and rng.random() < 0.5 else None

        controls.append(
            {
                "id": control_id,
                "site": site,
                "floor": floor,
                "control_type": control_type,
                "label": label,
                "status": status,
                "next_review": next_review,
                "linked_incident_id": linked_incident_id,
            }
        )
    return controls


@lru_cache(maxsize=1)
def monthly_series() -> list[dict]:
    profile = MonthlyProfile(
        base_active_ratio=0.4,
        executions_per_active=1.6,
        success_rate=0.82,  # fraction of monthly incidents reaching resolved/closed (demo assumption)
        manual_minutes=35,
        assisted_minutes=14,
        satisfaction_response_rate=0.35,
        satisfaction_mean=4.0,
    )
    return generate_monthly_series("security.monthly", "security", profile)


def initial_state() -> dict:
    return {
        "records": showcase_records(),
        "controls": showcase_controls(),
        "statuses": [{"slug": s, "label": STATUS_LABELS[s]} for s in STATUS_SLUGS],
        "categories": [{"slug": c, "label": CATEGORY_LABELS[c]} for c in CATEGORY_SLUGS],
        "severities": [{"slug": s, "label": SEVERITY_LABELS[s]} for s in SEVERITY_SLUGS],
        "control_types": [{"slug": c, "label": CONTROL_TYPE_LABELS[c]} for c in CONTROL_TYPE_SLUGS],
        "control_statuses": [{"slug": s, "label": CONTROL_STATUS_LABELS[s]} for s in CONTROL_STATUS_SLUGS],
        "sites": SITES,
        "floors": FLOORS,
        "monthly_series": monthly_series(),
        "last_sync": iso(reference_datetime() - timedelta(minutes=18)),
    }


def catalog_summary() -> dict:
    records = showcase_records()
    controls = showcase_controls()
    assignee_ids = {r["assignee_id"] for r in records if r.get("assignee_id")}
    active_users = len(assignee_ids)
    last_activity = max((r["history"][-1]["at"] for r in records if r["history"]), default=None)
    open_items = sum(1 for r in records if r["status"] not in TERMINAL_STATUSES)

    critical_open = sum(
        1 for r in records if r["severity"] == "critica" and r["status"] not in TERMINAL_STATUSES
    )
    overdue = sum(1 for c in controls if c["status"] == "vencido")
    overdue_ratio = (overdue / len(controls)) if controls else 0.0

    if critical_open >= 3 or overdue_ratio > 0.35:
        health = "critical"
    elif critical_open >= 1 or overdue_ratio > 0.15:
        health = "warning"
    else:
        health = "good"

    return {
        "active_users": active_users,
        "last_activity": last_activity,
        "health": health,
        "open_items": open_items,
    }
